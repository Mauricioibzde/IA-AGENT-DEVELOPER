/**
 * Deterministic page capture (adapted from puppeteer-compare screenshot.js).
 */

import { stabilizePage } from './stabilize.js';
import { resolveViewport } from './viewports.js';

const DEFAULT_TIMEOUT = 60_000;
const DEFAULT_WAIT_MS = 1500;

/**
 * @param {import('puppeteer-core').Page} page
 * @param {string} url
 * @param {object} viewport
 * @param {object} [options]
 */
export async function captureScreenshot(page, url, viewport, options = {}) {
  const waitMs = options.waitMs ?? DEFAULT_WAIT_MS;
  const fullPage = options.fullPage !== false;
  const waitUntil = options.waitUntil || 'networkidle2';
  const timeout = options.timeoutMs ?? DEFAULT_TIMEOUT;
  const vp = resolveViewport(viewport);

  await page.setViewport({
    width: vp.width,
    height: vp.height,
    deviceScaleFactor: vp.deviceScaleFactor || 1,
  });

  if (options.auth?.httpAuth) {
    await page.authenticate(options.auth.httpAuth).catch(() => {});
  }
  if (options.auth?.headers && Object.keys(options.auth.headers).length) {
    await page.setExtraHTTPHeaders(options.auth.headers);
  }

  const consoleErrors = [];
  const networkFailures = [];
  const onConsole = (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  };
  const onRequestFailed = (req) => {
    networkFailures.push({ url: req.url(), errorText: req.failure()?.errorText || 'failed' });
  };
  page.on('console', onConsole);
  page.on('requestfailed', onRequestFailed);

  try {
    await page.goto(url, { waitUntil, timeout });
  } catch (err) {
    // Still try to screenshot partial render
    consoleErrors.push(`navigation: ${err.message}`);
  }

  if (waitMs > 0) {
    await new Promise((r) => setTimeout(r, waitMs));
  }

  if (options.stabilize !== false) {
    await stabilizePage(page);
  }

  if (Array.isArray(options.ignoredSelectors) && options.ignoredSelectors.length) {
    await page
      .evaluate((selectors) => {
        for (const sel of selectors) {
          try {
            document.querySelectorAll(sel).forEach((el) => {
              el.style.visibility = 'hidden';
            });
          } catch (_) {
            /* ignore bad selectors */
          }
        }
      }, options.ignoredSelectors)
      .catch(() => {});
  }

  const png = await page.screenshot({ fullPage, type: 'png' });
  const html = options.includeHtml === false ? '' : await page.content();

  page.off('console', onConsole);
  page.off('requestfailed', onRequestFailed);

  return {
    png,
    html,
    viewport: vp,
    consoleErrors: consoleErrors.slice(0, 40),
    networkFailures: networkFailures.slice(0, 40),
  };
}
