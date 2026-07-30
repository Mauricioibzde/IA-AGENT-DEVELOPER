import test from 'node:test';
import assert from 'node:assert/strict';
import { PNG } from 'pngjs';
import { compareImages } from '../src/compareImages.js';
import { safeId, createComparisonDir, resolveUnderRoot } from '../src/artifacts.js';
import { resolveViewport, listViewports } from '../src/viewports.js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function solidPng(width, height, rgba = [255, 0, 0, 255]) {
  const img = new PNG({ width, height });
  for (let i = 0; i < width * height; i++) {
    const idx = i * 4;
    img.data[idx] = rgba[0];
    img.data[idx + 1] = rgba[1];
    img.data[idx + 2] = rgba[2];
    img.data[idx + 3] = rgba[3];
  }
  return PNG.sync.write(img);
}

test('identical images → similarity 1', () => {
  const buf = solidPng(40, 30, [10, 20, 30, 255]);
  const result = compareImages(buf, buf);
  assert.equal(result.comparable, true);
  assert.equal(result.diffPixels, 0);
  assert.equal(result.similarity, 1);
  assert.ok(result.diffPngBuffer);
});

test('different colors → low similarity', () => {
  const a = solidPng(20, 20, [255, 0, 0, 255]);
  const b = solidPng(20, 20, [0, 0, 255, 255]);
  const result = compareImages(a, b, { threshold: 0.05 });
  assert.equal(result.comparable, true);
  assert.ok(result.diffPixels > 0);
  assert.ok(result.similarity < 0.5);
});

test('incompatible aspect with requireCompatibleAspect', () => {
  const a = solidPng(100, 50);
  const b = solidPng(50, 100);
  const result = compareImages(a, b, { requireCompatibleAspect: true });
  assert.equal(result.comparable, false);
  assert.equal(result.similarity, null);
  assert.ok(result.warnings.length >= 1);
});

test('safeId strips traversal', () => {
  assert.equal(safeId('../evil/../x'), 'evil-x');
  assert.ok(!safeId('a/b').includes('/'));
});

test('artifact dir rejects escape', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 've-art-'));
  const { dir, id } = createComparisonDir(root, 'cmp-1');
  assert.ok(fs.existsSync(dir));
  assert.equal(id, 'cmp-1');
  assert.throws(() => resolveUnderRoot(root, '../outside.txt'));
});

test('viewport presets include desktop and mobile', () => {
  const all = listViewports();
  assert.ok(all.some((v) => v.id.includes('desktop')));
  assert.ok(all.some((v) => v.id.includes('iphone') || v.id.includes('mobile')));
  const vp = resolveViewport({ width: 800, height: 600 });
  assert.equal(vp.width, 800);
  assert.equal(vp.height, 600);
});
