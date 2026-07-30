/**
 * Image normalization for fair pixel comparisons.
 * Modes: none | crop | contain | cover | fit (alias of contain)
 */

import { PNG } from 'pngjs';

/**
 * Nearest-neighbor scale (deterministic, dependency-free).
 * @param {PNG} source
 * @param {number} width
 * @param {number} height
 */
export function scaleNearest(source, width, height) {
  const out = new PNG({ width, height });
  for (let y = 0; y < height; y++) {
    const sy = Math.min(source.height - 1, Math.floor((y * source.height) / height));
    for (let x = 0; x < width; x++) {
      const sx = Math.min(source.width - 1, Math.floor((x * source.width) / width));
      const si = (source.width * sy + sx) << 2;
      const di = (width * y + x) << 2;
      out.data[di] = source.data[si];
      out.data[di + 1] = source.data[si + 1];
      out.data[di + 2] = source.data[si + 2];
      out.data[di + 3] = source.data[si + 3];
    }
  }
  return out;
}

/**
 * @param {PNG} source
 * @param {number} width
 * @param {number} height
 * @param {number} [fillR=0]
 * @param {number} [fillG=0]
 * @param {number} [fillB=0]
 * @param {number} [fillA=0]
 */
export function padTo(source, width, height, fillR = 0, fillG = 0, fillB = 0, fillA = 0) {
  const out = new PNG({ width, height });
  // fill
  for (let i = 0; i < width * height; i++) {
    const idx = i << 2;
    out.data[idx] = fillR;
    out.data[idx + 1] = fillG;
    out.data[idx + 2] = fillB;
    out.data[idx + 3] = fillA;
  }
  const ox = Math.floor((width - source.width) / 2);
  const oy = Math.floor((height - source.height) / 2);
  const copyW = Math.min(source.width, width);
  const copyH = Math.min(source.height, height);
  const srcX = ox < 0 ? -ox : 0;
  const srcY = oy < 0 ? -oy : 0;
  const dstX = Math.max(0, ox);
  const dstY = Math.max(0, oy);
  const w = Math.min(copyW - srcX, width - dstX);
  const h = Math.min(copyH - srcY, height - dstY);
  if (w > 0 && h > 0) {
    PNG.bitblt(source, out, srcX, srcY, w, h, dstX, dstY);
  }
  return out;
}

export function cropTopLeft(source, width, height) {
  if (source.width === width && source.height === height) return source;
  const out = new PNG({ width, height });
  const w = Math.min(source.width, width);
  const h = Math.min(source.height, height);
  PNG.bitblt(source, out, 0, 0, w, h, 0, 0);
  return out;
}

/**
 * Normalize two PNGs to a shared canvas using fit mode.
 * @returns {{ a: PNG, b: PNG, width: number, height: number, meta: object }}
 */
export function normalizePair(imageA, imageB, options = {}) {
  const mode = (options.fit || options.mode || 'contain').toLowerCase();
  const align = options.align || 'center';
  const warnings = [];

  if (mode === 'none') {
    if (imageA.width !== imageB.width || imageA.height !== imageB.height) {
      warnings.push('fit=none but dimensions differ — comparison aborted.');
      return {
        a: imageA,
        b: imageB,
        width: imageA.width,
        height: imageA.height,
        comparable: false,
        warnings,
        meta: { mode, align },
      };
    }
    return {
      a: imageA,
      b: imageB,
      width: imageA.width,
      height: imageA.height,
      comparable: true,
      warnings,
      meta: { mode, align },
    };
  }

  if (mode === 'crop') {
    const width = Math.min(imageA.width, imageB.width);
    const height = Math.min(imageA.height, imageB.height);
    if (imageA.width !== width || imageA.height !== height || imageB.width !== width || imageB.height !== height) {
      warnings.push(`Cropped to ${width}x${height} (top-left).`);
    }
    return {
      a: cropTopLeft(imageA, width, height),
      b: cropTopLeft(imageB, width, height),
      width,
      height,
      comparable: true,
      warnings,
      meta: { mode: 'crop', align: 'top-left', compared: { width, height } },
    };
  }

  // contain / fit: scale each to fit inside max box, then pad to same canvas
  // cover: scale each to cover max box, then crop center
  const maxW = Math.max(imageA.width, imageB.width);
  const maxH = Math.max(imageA.height, imageB.height);
  const targetW = Number(options.width) || maxW;
  const targetH = Number(options.height) || maxH;

  function scaleForContain(img) {
    let scale = Math.min(targetW / img.width, targetH / img.height);
    if (options.allowUpscale === false) {
      scale = Math.min(scale, 1);
    }
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const scaled = w === img.width && h === img.height ? img : scaleNearest(img, w, h);
    return padTo(scaled, targetW, targetH, 0, 0, 0, 0);
  }

  function scaleForCover(img) {
    const scale = Math.max(targetW / img.width, targetH / img.height);
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const scaled = scaleNearest(img, w, h);
    const ox = Math.floor((w - targetW) / 2);
    const oy = Math.floor((h - targetH) / 2);
    const out = new PNG({ width: targetW, height: targetH });
    PNG.bitblt(scaled, out, Math.max(0, ox), Math.max(0, oy), targetW, targetH, 0, 0);
    return out;
  }

  if (mode === 'cover') {
    warnings.push(`Normalized with cover to ${targetW}x${targetH}.`);
    return {
      a: scaleForCover(imageA),
      b: scaleForCover(imageB),
      width: targetW,
      height: targetH,
      comparable: true,
      warnings,
      meta: { mode: 'cover', align: 'center', compared: { width: targetW, height: targetH } },
    };
  }

  // contain (default) / fit
  warnings.push(`Normalized with contain to ${targetW}x${targetH} (transparent pad, align=${align}).`);
  return {
    a: scaleForContain(imageA),
    b: scaleForContain(imageB),
    width: targetW,
    height: targetH,
    comparable: true,
    warnings,
    meta: { mode: mode === 'fit' ? 'fit' : 'contain', align, compared: { width: targetW, height: targetH } },
  };
}

/**
 * Build a simple overlay: actual image with red tint where pixels differ.
 * @param {PNG} reference
 * @param {PNG} actual
 * @param {PNG} [diff]
 */
export function buildOverlay(reference, actual, diff) {
  const width = actual.width;
  const height = actual.height;
  const out = new PNG({ width, height });
  for (let i = 0; i < width * height; i++) {
    const idx = i << 2;
    const dr = diff ? diff.data[idx] : 0;
    const dg = diff ? diff.data[idx + 1] : 0;
    const db = diff ? diff.data[idx + 2] : 0;
    const changed = dr > 40 || dg > 40 || db > 40;
    if (changed) {
      out.data[idx] = Math.min(255, Math.floor(actual.data[idx] * 0.45 + 220 * 0.55));
      out.data[idx + 1] = Math.floor(actual.data[idx + 1] * 0.35);
      out.data[idx + 2] = Math.floor(actual.data[idx + 2] * 0.35);
      out.data[idx + 3] = 255;
    } else {
      out.data[idx] = actual.data[idx];
      out.data[idx + 1] = actual.data[idx + 1];
      out.data[idx + 2] = actual.data[idx + 2];
      out.data[idx + 3] = actual.data[idx + 3];
    }
  }
  return out;
}
