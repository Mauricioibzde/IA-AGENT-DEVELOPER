/**
 * Puppeteer browser lifecycle (adapted from puppeteer-compare services/browser.js).
 * Does NOT listen on a port — library only.
 */

import fs from 'node:fs';
import puppeteer from 'puppeteer-core';

const DEFAULT_ARGS = [
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-dev-shm-usage',
  '--disable-accelerated-2d-canvas',
  '--hide-scrollbars',
  '--mute-audio',
];

/**
 * Detect Chrome/Chromium executable (Windows-first for Forge notebooks).
 * @returns {string|null}
 */
export function detectChromePath() {
  const fromEnv =
    process.env.CHROME_EXECUTABLE_PATH ||
    process.env.PUPPETEER_EXECUTABLE_PATH ||
    process.env.FORGE_CHROME_PATH;
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;

  const platform = process.platform;
  const candidates = [];

  if (platform === 'win32') {
    candidates.push(
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      process.env.LOCALAPPDATA
        ? `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`
        : null,
      process.env.PROGRAMFILES
        ? `${process.env.PROGRAMFILES}\\Google\\Chrome\\Application\\chrome.exe`
        : null,
      process.env['PROGRAMFILES(X86)']
        ? `${process.env['PROGRAMFILES(X86)']}\\Google\\Chrome\\Application\\chrome.exe`
        : null,
      process.env.LOCALAPPDATA
        ? `${process.env.LOCALAPPDATA}\\Microsoft\\Edge\\Application\\msedge.exe`
        : null,
      'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
    );
  } else if (platform === 'darwin') {
    candidates.push(
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Chromium.app/Contents/MacOS/Chromium',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
    );
  } else {
    candidates.push(
      '/usr/bin/google-chrome',
      '/usr/bin/google-chrome-stable',
      '/usr/bin/chromium-browser',
      '/usr/bin/chromium',
      '/snap/bin/chromium'
    );
  }

  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return null;
}

/**
 * @param {object} [opts]
 * @returns {Promise<import('puppeteer-core').Browser>}
 */
export async function createBrowser(opts = {}) {
  const executablePath = opts.executablePath || detectChromePath();
  if (!executablePath) {
    throw new Error(
      'Chrome/Chromium not found. Install Chrome or set CHROME_EXECUTABLE_PATH.'
    );
  }
  const headless = opts.headless !== false;
  return puppeteer.launch({
    executablePath,
    headless,
    args: [...DEFAULT_ARGS, ...(opts.args || [])],
    defaultViewport: null,
  });
}

/**
 * @param {import('puppeteer-core').Browser|null|undefined} browser
 */
export async function closeBrowser(browser) {
  if (!browser) return;
  try {
    await browser.close();
  } catch (err) {
    console.error('[visual-engine] closeBrowser:', err?.message || err);
  }
}
