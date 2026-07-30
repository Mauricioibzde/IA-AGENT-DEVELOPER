import test from 'node:test';
import assert from 'node:assert/strict';
import { PNG } from 'pngjs';
import { compareImages } from '../src/compareImages.js';
import { normalizePair, scaleNearest } from '../src/normalize.js';

function solidPng(width, height, rgba = [255, 0, 0, 255]) {
  const img = new PNG({ width, height });
  for (let i = 0; i < width * height; i++) {
    const idx = i * 4;
    img.data[idx] = rgba[0];
    img.data[idx + 1] = rgba[1];
    img.data[idx + 2] = rgba[2];
    img.data[idx + 3] = rgba[3];
  }
  return img;
}

function solidBuf(width, height, rgba) {
  return PNG.sync.write(solidPng(width, height, rgba));
}

test('scaleNearest doubles size', () => {
  const src = solidPng(2, 2, [10, 20, 30, 255]);
  const out = scaleNearest(src, 4, 4);
  assert.equal(out.width, 4);
  assert.equal(out.height, 4);
  assert.equal(out.data[0], 10);
});

test('contain normalizes different sizes to same canvas', () => {
  const a = solidPng(40, 20);
  const b = solidPng(20, 40);
  const result = normalizePair(a, b, { fit: 'contain' });
  assert.equal(result.comparable, true);
  assert.equal(result.a.width, result.b.width);
  assert.equal(result.a.height, result.b.height);
  assert.equal(result.width, 40);
  assert.equal(result.height, 40);
});

test('compareImages contain produces overlay', () => {
  const a = solidBuf(30, 20, [255, 0, 0, 255]);
  const b = solidBuf(20, 30, [0, 0, 255, 255]);
  const result = compareImages(a, b, { fit: 'contain' });
  assert.equal(result.comparable, true);
  assert.ok(result.overlayPngBuffer);
  assert.ok(result.normalizedA);
  assert.ok(result.diffPixels > 0);
  assert.equal(result.normalization.fit, 'contain');
});

test('cover mode shares canvas size', () => {
  const a = solidPng(60, 20);
  const b = solidPng(20, 60);
  const result = normalizePair(a, b, { fit: 'cover', width: 40, height: 40 });
  assert.equal(result.width, 40);
  assert.equal(result.height, 40);
  assert.equal(result.a.width, 40);
  assert.equal(result.b.width, 40);
});
