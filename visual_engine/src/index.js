/**
 * @forge/visual-engine public API
 */

export { createBrowser, closeBrowser, detectChromePath } from './browser.js';
export { captureScreenshot } from './capture.js';
export { compareImages } from './compareImages.js';
export { normalizePair, buildOverlay, scaleNearest } from './normalize.js';
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
export { getDomDiffSummary } from './dom/domDiff.js';
export { findDiffRegions } from './regions.js';
export { collectLayoutSnapshot, diffLayouts } from './layout.js';
export { correlateRegions } from './correlate.js';

import fs from 'node:fs';
import path from 'node:path';
import { createBrowser, closeBrowser } from './browser.js';
import { captureScreenshot } from './capture.js';
import { compareImages } from './compareImages.js';
import { createComparisonDir, writePng, writeJson } from './artifacts.js';
import { resolveViewport } from './viewports.js';
import { getDomDiffSummary } from './dom/domDiff.js';
import { findDiffRegions } from './regions.js';
import { diffLayouts } from './layout.js';
import { correlateRegions } from './correlate.js';

/**
 * Unified compare entry (URL/image/mockup) with pixel + DOM/layout analysis.
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
  const wantDom = options.includeDomDiff !== false;
  const wantLayout = options.includeLayout !== false;

  let referenceBuf;
  let actualBuf;
  let htmlA = '';
  let htmlB = '';
  let layoutA = [];
  let layoutB = [];
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
      layoutA = capA.layout || [];
      layoutB = capB.layout || [];
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
      layoutB = cap.layout || [];
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
      layoutA = cap.layout || [];
      await page.close().catch(() => {});
    } finally {
      await closeBrowser(browser);
    }
  } else {
    throw new Error(`Unsupported compare mode: ${source.type} vs ${target.type}`);
  }

  const metrics = compareImages(referenceBuf, actualBuf, {
    threshold: options.threshold ?? 0.1,
    fit: options.fit || 'contain',
    requireCompatibleAspect: options.requireCompatibleAspect === true,
    width: options.normalizeWidth,
    height: options.normalizeHeight,
  });
  warnings.push(...(metrics.warnings || []));

  const refPath = path.join(dir, 'reference.png');
  const actPath = path.join(dir, 'actual.png');
  const diffPath = path.join(dir, 'diff.png');
  const overlayPath = path.join(dir, 'overlay.png');
  const normRefPath = path.join(dir, 'reference-normalized.png');
  const normActPath = path.join(dir, 'actual-normalized.png');
  writePng(referenceBuf, refPath);
  writePng(actualBuf, actPath);
  if (metrics.normalizedA) writePng(metrics.normalizedA, normRefPath);
  if (metrics.normalizedB) writePng(metrics.normalizedB, normActPath);
  if (metrics.diffPngBuffer) writePng(metrics.diffPngBuffer, diffPath);
  if (metrics.overlayPngBuffer) writePng(metrics.overlayPngBuffer, overlayPath);

  // Pixel regions → correlate with actual-page layout when available.
  let regions = [];
  if (metrics.diffPngBuffer && options.includeRegions !== false) {
    regions = findDiffRegions(metrics.diffPngBuffer, {
      cellSize: options.regionCellSize || 4,
      maxRegions: options.maxRegions || 40,
    });
    const correlateAgainst = layoutB.length ? layoutB : layoutA;
    if (correlateAgainst.length) {
      regions = correlateRegions(regions, correlateAgainst);
    }
  }

  let domChanges = { kind: 'dom', total: 0, items: [] };
  if (wantDom && htmlA && htmlB) {
    domChanges = getDomDiffSummary(htmlA, htmlB, {
      ignoredSelectors: options.ignoredSelectors || [],
    });
    writeJson(domChanges, path.join(dir, 'dom-diff.json'));
  } else if (wantDom && mode === 'image-vs-image') {
    domChanges = {
      kind: 'dom',
      total: 0,
      items: [],
      note: 'DOM diff requires HTML from URL captures.',
    };
  }

  let layoutDiff = { kind: 'layout', counts: {}, layoutChanges: [], styleChanges: [], added: [], removed: [] };
  if (wantLayout && (layoutA.length || layoutB.length)) {
    layoutDiff = diffLayouts(layoutA, layoutB);
    writeJson(layoutDiff, path.join(dir, 'layout-diff.json'));
  }

  const criticalRegions = regions.filter((r) => r.severity === 'high').length;
  const recommendations = [];
  if (warnings.length) recommendations.push('Review warnings before trusting the similarity score.');
  if (criticalRegions) recommendations.push(`${criticalRegions} critical visual region(s) need attention.`);
  if (domChanges.total > 20) recommendations.push('Large DOM delta — inspect structural changes before pixel tuning.');
  if (layoutDiff.counts?.layout > 0) {
    recommendations.push(`${layoutDiff.counts.layout} element(s) moved or resized.`);
  }

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
      regions: regions.length,
      criticalRegions,
      domChanges: domChanges.total || 0,
      layoutChanges: layoutDiff.counts?.layout || 0,
      styleChanges: layoutDiff.counts?.style || 0,
    },
    artifacts: {
      reference: refPath,
      actual: actPath,
      diff: metrics.diffPngBuffer ? diffPath : null,
      overlay: metrics.overlayPngBuffer ? overlayPath : null,
      referenceNormalized: metrics.normalizedA ? normRefPath : null,
      actualNormalized: metrics.normalizedB ? normActPath : null,
      domDiff: htmlA && htmlB ? path.join(dir, 'dom-diff.json') : null,
      layoutDiff: layoutA.length || layoutB.length ? path.join(dir, 'layout-diff.json') : null,
      directory: dir,
    },
    regions,
    normalization: metrics.normalization,
    warnings,
    domChanges,
    styleChanges: layoutDiff.styleChanges || [],
    layoutChanges: layoutDiff.layoutChanges || [],
    layoutDiff,
    analyses: {
      pixel: { kind: 'pixel', similarity: metrics.similarity, diffPercent: metrics.diffPercent },
      dom: { kind: 'dom', total: domChanges.total || 0 },
      layout: { kind: 'layout', ...(layoutDiff.counts || {}) },
      style: { kind: 'style', total: layoutDiff.counts?.style || 0 },
    },
    performance: { durationMs: Date.now() - started },
    recommendations,
  };

  writeJson(report, path.join(dir, 'report.json'));
  writeJson(
    { comparisonId: id, mode, createdAt: new Date().toISOString(), viewport, summary: report.summary },
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
