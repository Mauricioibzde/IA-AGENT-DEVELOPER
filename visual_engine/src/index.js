/**
 * @forge/visual-engine public API
 */

export { createBrowser, closeBrowser, detectChromePath } from './browser.js';
export { captureScreenshot } from './capture.js';
export { compareImages } from './compareImages.js';
export { DEVICE_PRESETS, DEFAULT_VIEWPORT, listViewports, resolveViewport } from './viewports.js';
export {
  ensureDir,
  writePng,
  writeJson,
  safeId,
  createComparisonDir,
  resolveUnderRoot,
} from './artifacts.js';
export { stabilizePage, STABILIZE_CSS } from './stabilize.js';

import fs from 'node:fs';
import path from 'node:path';
import { createBrowser, closeBrowser } from './browser.js';
import { captureScreenshot } from './capture.js';
import { compareImages } from './compareImages.js';
import { createComparisonDir, writePng, writeJson } from './artifacts.js';
import { resolveViewport } from './viewports.js';

/**
 * Unified compare entry (Phase 1: url-url and image-image).
 * @param {object} request
 */
export async function compare(request) {
  const started = Date.now();
  const source = request.source || {};
  const target = request.target || {};
  const options = request.options || {};
  const viewport = resolveViewport(request.viewport);
  const artifactsRoot = request.artifactsRoot || path.join(process.cwd(), 'artifacts');
  const { id, dir } = createComparisonDir(artifactsRoot, request.comparisonId);

  let referenceBuf;
  let actualBuf;
  let htmlA = '';
  let htmlB = '';
  const warnings = [];
  let mode = 'unknown';

  if (source.type === 'image' && target.type === 'image') {
    mode = 'image-vs-image';
    referenceBuf = fs.readFileSync(source.value);
    actualBuf = fs.readFileSync(target.value);
  } else if (source.type === 'url' && target.type === 'url') {
    mode = 'url-vs-url';
    const browser = await createBrowser(options.browser || {});
    try {
      // Separate pages — never share one page across parallel viewports.
      const pageA = await browser.newPage();
      const pageB = await browser.newPage();
      const [capA, capB] = await Promise.all([
        captureScreenshot(pageA, source.value, viewport, options),
        captureScreenshot(pageB, target.value, viewport, options),
      ]);
      referenceBuf = capA.png;
      actualBuf = capB.png;
      htmlA = capA.html;
      htmlB = capB.html;
      warnings.push(...(capA.consoleErrors || []).map((e) => `source console: ${e}`));
      warnings.push(...(capB.consoleErrors || []).map((e) => `target console: ${e}`));
      await pageA.close().catch(() => {});
      await pageB.close().catch(() => {});
    } finally {
      await closeBrowser(browser);
    }
  } else if (source.type === 'image' && target.type === 'url') {
    mode = 'mockup-vs-url';
    referenceBuf = fs.readFileSync(source.value);
    const browser = await createBrowser(options.browser || {});
    try {
      const page = await browser.newPage();
      const cap = await captureScreenshot(page, target.value, viewport, options);
      actualBuf = cap.png;
      htmlB = cap.html;
      warnings.push(...(cap.consoleErrors || []).map((e) => `target console: ${e}`));
      await page.close().catch(() => {});
    } finally {
      await closeBrowser(browser);
    }
  } else if (source.type === 'url' && target.type === 'image') {
    mode = 'url-vs-image';
    actualBuf = fs.readFileSync(target.value);
    const browser = await createBrowser(options.browser || {});
    try {
      const page = await browser.newPage();
      const cap = await captureScreenshot(page, source.value, viewport, options);
      referenceBuf = cap.png;
      htmlA = cap.html;
      await page.close().catch(() => {});
    } finally {
      await closeBrowser(browser);
    }
  } else {
    throw new Error(`Unsupported compare mode: ${source.type} vs ${target.type}`);
  }

  const metrics = compareImages(referenceBuf, actualBuf, {
    threshold: options.threshold ?? 0.1,
    requireCompatibleAspect: options.requireCompatibleAspect === true,
  });
  warnings.push(...(metrics.warnings || []));

  const refPath = path.join(dir, 'reference.png');
  const actPath = path.join(dir, 'actual.png');
  const diffPath = path.join(dir, 'diff.png');
  writePng(referenceBuf, refPath);
  writePng(actualBuf, actPath);
  if (metrics.diffPngBuffer) writePng(metrics.diffPngBuffer, diffPath);

  const report = {
    comparisonId: id,
    status: metrics.comparable === false ? 'incompatible' : 'completed',
    mode,
    similarity: metrics.similarity,
    viewport,
    summary: {
      differentPixels: metrics.diffPixels,
      totalPixels: metrics.totalPixels,
      diffPercent: metrics.diffPercent,
      regions: null,
      criticalRegions: null,
    },
    artifacts: {
      reference: refPath,
      actual: actPath,
      diff: metrics.diffPngBuffer ? diffPath : null,
      directory: dir,
    },
    normalization: metrics.normalization,
    warnings,
    domChanges: options.includeDomDiff ? { note: 'DOM diff wired in Phase 4', htmlLengths: { a: htmlA.length, b: htmlB.length } } : [],
    styleChanges: [],
    performance: { durationMs: Date.now() - started },
    recommendations: warnings.length
      ? ['Review warnings before trusting the similarity score.']
      : [],
  };

  writeJson(report, path.join(dir, 'report.json'));
  writeJson(
    { comparisonId: id, mode, createdAt: new Date().toISOString(), viewport },
    path.join(dir, 'metadata.json')
  );
  return report;
}

/**
 * Capture a single URL to artifacts.
 */
export async function capture(request) {
  const artifactsRoot = request.artifactsRoot || path.join(process.cwd(), 'artifacts');
  const { id, dir } = createComparisonDir(artifactsRoot, request.comparisonId || `cap-${Date.now()}`);
  const viewport = resolveViewport(request.viewport);
  const browser = await createBrowser(request.options?.browser || {});
  try {
    const page = await browser.newPage();
    const cap = await captureScreenshot(page, request.url, viewport, request.options || {});
    const out = path.join(dir, 'actual.png');
    writePng(cap.png, out);
    const result = {
      comparisonId: id,
      status: 'completed',
      mode: 'capture',
      viewport,
      artifacts: { actual: out, directory: dir },
      consoleErrors: cap.consoleErrors,
      networkFailures: cap.networkFailures,
    };
    writeJson(result, path.join(dir, 'report.json'));
    await page.close().catch(() => {});
    return result;
  } finally {
    await closeBrowser(browser);
  }
}
