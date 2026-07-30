/**
 * Pixel comparison with explicit normalization + overlay.
 */

import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';
import { buildOverlay, normalizePair } from './normalize.js';

/**
 * Compare two PNG buffers.
 * @param {Buffer} bufferA
 * @param {Buffer} bufferB
 * @param {object} [options]
 * @param {number} [options.threshold=0.1]
 * @param {'crop'|'contain'|'cover'|'fit'|'none'} [options.fit='contain']
 * @param {boolean} [options.requireCompatibleAspect]
 * @param {number} [options.aspectTolerance=0.08]
 */
export function compareImages(bufferA, bufferB, options = {}) {
  const threshold = options.threshold ?? 0.1;
  const alpha = options.alpha ?? 0.5;
  const includeAA = options.includeAA !== false;
  const fit = options.fit || 'contain';
  const aspectTolerance = options.aspectTolerance ?? 0.08;

  let imageA;
  let imageB;
  try {
    imageA = PNG.sync.read(bufferA);
    imageB = PNG.sync.read(bufferB);
  } catch (err) {
    throw new Error(`Invalid PNG input: ${err.message || err}`);
  }

  const aspectA = imageA.width / imageA.height;
  const aspectB = imageB.width / imageB.height;
  const aspectDelta = Math.abs(aspectA - aspectB) / Math.max(aspectA, aspectB);
  const warnings = [];

  if (aspectDelta > aspectTolerance) {
    warnings.push(
      `Aspect ratios differ (${aspectA.toFixed(3)} vs ${aspectB.toFixed(3)}). Using fit=${fit}; score may be imperfect.`
    );
    if (options.requireCompatibleAspect) {
      return {
        width: imageA.width,
        height: imageA.height,
        diffPngBuffer: null,
        overlayPngBuffer: null,
        normalizedA: null,
        normalizedB: null,
        diffPixels: null,
        totalPixels: imageA.width * imageA.height,
        diffPercent: null,
        similarity: null,
        comparable: false,
        warnings,
        normalization: {
          originalA: { width: imageA.width, height: imageA.height },
          originalB: { width: imageB.width, height: imageB.height },
          fit,
          aspectDelta,
        },
      };
    }
  }

  const normalized = normalizePair(imageA, imageB, {
    fit,
    width: options.width,
    height: options.height,
    allowUpscale: options.allowUpscale !== false,
  });
  warnings.push(...(normalized.warnings || []));

  if (!normalized.comparable) {
    return {
      width: normalized.width,
      height: normalized.height,
      diffPngBuffer: null,
      overlayPngBuffer: null,
      normalizedA: null,
      normalizedB: null,
      diffPixels: null,
      totalPixels: normalized.width * normalized.height,
      diffPercent: null,
      similarity: null,
      comparable: false,
      warnings,
      normalization: {
        originalA: { width: imageA.width, height: imageA.height },
        originalB: { width: imageB.width, height: imageB.height },
        compared: { width: normalized.width, height: normalized.height },
        fit,
        aspectDelta,
        meta: normalized.meta,
      },
    };
  }

  const { a: croppedA, b: croppedB, width, height } = normalized;
  const diffImage = new PNG({ width, height });
  const diffPixels = pixelmatch(croppedA.data, croppedB.data, diffImage.data, width, height, {
    threshold,
    alpha,
    includeAA,
  });

  const totalPixels = width * height;
  const diffPercent = totalPixels > 0 ? (diffPixels / totalPixels) * 100 : 0;
  const similarity = totalPixels > 0 ? 1 - diffPixels / totalPixels : 1;
  const overlay = buildOverlay(croppedA, croppedB, diffImage);

  return {
    width,
    height,
    diffPngBuffer: PNG.sync.write(diffImage),
    overlayPngBuffer: PNG.sync.write(overlay),
    normalizedA: PNG.sync.write(croppedA),
    normalizedB: PNG.sync.write(croppedB),
    diffPixels,
    totalPixels,
    diffPercent: Number(diffPercent.toFixed(4)),
    similarity: Number(similarity.toFixed(6)),
    comparable: true,
    warnings,
    normalization: {
      originalA: { width: imageA.width, height: imageA.height },
      originalB: { width: imageB.width, height: imageB.height },
      compared: { width, height },
      fit,
      aspectDelta,
      meta: normalized.meta,
    },
  };
}
