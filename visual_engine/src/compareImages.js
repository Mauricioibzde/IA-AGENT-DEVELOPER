/**
 * Pixel comparison (adapted from puppeteer-compare services/image.js).
 * Adds explicit resize metadata and refuses silent misleading scores when
 * aspect ratios differ beyond a tolerance.
 */

import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

/**
 * @typedef {'crop'|'none'} FitMode
 */

/**
 * @param {PNG} source
 * @param {number} width
 * @param {number} height
 */
function cropTo(source, width, height) {
  if (source.width === width && source.height === height) return source;
  const output = new PNG({ width, height });
  const w = Math.min(source.width, width);
  const h = Math.min(source.height, height);
  PNG.bitblt(source, output, 0, 0, w, h, 0, 0);
  return output;
}

/**
 * Compare two PNG buffers.
 * @param {Buffer} bufferA
 * @param {Buffer} bufferB
 * @param {object} [options]
 * @param {number} [options.threshold=0.1]
 * @param {number} [options.alpha=0.5]
 * @param {boolean} [options.includeAA=true]
 * @param {FitMode} [options.fit='crop']
 * @param {number} [options.aspectTolerance=0.02]
 */
export function compareImages(bufferA, bufferB, options = {}) {
  const threshold = options.threshold ?? 0.1;
  const alpha = options.alpha ?? 0.5;
  const includeAA = options.includeAA !== false;
  const fit = options.fit || 'crop';
  const aspectTolerance = options.aspectTolerance ?? 0.02;

  const imageA = PNG.sync.read(bufferA);
  const imageB = PNG.sync.read(bufferB);

  const aspectA = imageA.width / imageA.height;
  const aspectB = imageB.width / imageB.height;
  const aspectDelta = Math.abs(aspectA - aspectB) / Math.max(aspectA, aspectB);
  const warnings = [];
  let comparable = true;

  if (aspectDelta > aspectTolerance) {
    warnings.push(
      `Aspect ratios differ significantly (${aspectA.toFixed(3)} vs ${aspectB.toFixed(3)}). Score may be misleading.`
    );
    if (options.requireCompatibleAspect) {
      comparable = false;
    }
  }

  const width = Math.min(imageA.width, imageB.width);
  const height = Math.min(imageA.height, imageB.height);
  const resized =
    imageA.width !== width ||
    imageA.height !== height ||
    imageB.width !== width ||
    imageB.height !== height;

  if (resized) {
    warnings.push(
      `Images resized/cropped to ${width}x${height} (original A=${imageA.width}x${imageA.height}, B=${imageB.width}x${imageB.height}, fit=${fit}).`
    );
  }

  if (!comparable) {
    return {
      width,
      height,
      diffPngBuffer: null,
      diffPixels: null,
      totalPixels: width * height,
      diffPercent: null,
      similarity: null,
      comparable: false,
      warnings,
      normalization: {
        originalA: { width: imageA.width, height: imageA.height },
        originalB: { width: imageB.width, height: imageB.height },
        compared: { width, height },
        fit,
        aspectDelta,
      },
    };
  }

  const croppedA = cropTo(imageA, width, height);
  const croppedB = cropTo(imageB, width, height);
  const diffImage = new PNG({ width, height });

  const diffPixels = pixelmatch(croppedA.data, croppedB.data, diffImage.data, width, height, {
    threshold,
    alpha,
    includeAA,
  });

  const totalPixels = width * height;
  const diffPercent = totalPixels > 0 ? (diffPixels / totalPixels) * 100 : 0;
  const similarity = totalPixels > 0 ? 1 - diffPixels / totalPixels : 1;

  return {
    width,
    height,
    diffPngBuffer: PNG.sync.write(diffImage),
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
    },
  };
}
