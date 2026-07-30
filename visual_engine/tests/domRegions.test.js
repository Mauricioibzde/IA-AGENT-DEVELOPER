import test from 'node:test';
import assert from 'node:assert/strict';
import { PNG } from 'pngjs';
import { getDomDiffSummary } from '../src/dom/domDiff.js';
import { findDiffRegions } from '../src/regions.js';
import { correlateRegions } from '../src/correlate.js';
import { diffLayouts } from '../src/layout.js';
import { pathToCssSelector } from '../src/dom/pathConverter.js';

test('pathToCssSelector builds readable path', () => {
  const sel = pathToCssSelector([
    { name: 'html', index: 0 },
    { name: 'body', index: 0 },
    { name: 'div', id: 'main', index: 1 },
  ]);
  assert.match(sel, /div#main/);
});

test('getDomDiffSummary detects text change', () => {
  const a = '<html><body><p class="t">Hello</p></body></html>';
  const b = '<html><body><p class="t">World</p></body></html>';
  const summary = getDomDiffSummary(a, b);
  assert.ok(summary.total >= 1);
  assert.ok(summary.textChanges >= 1 || summary.items.some((i) => i.type === 'text'));
  assert.equal(summary.kind, 'dom');
});

test('getDomDiffSummary detects added node', () => {
  const a = '<html><body><div id="root"></div></body></html>';
  const b = '<html><body><div id="root"><span>x</span></div></body></html>';
  const summary = getDomDiffSummary(a, b);
  assert.ok(summary.total >= 1);
  assert.ok(summary.additions >= 1 || summary.items.some((i) => i.type === 'add'));
});

test('findDiffRegions groups red pixels', () => {
  const img = new PNG({ width: 40, height: 40 });
  // fill black
  for (let i = 0; i < 40 * 40; i++) {
    const idx = i * 4;
    img.data[idx] = 0;
    img.data[idx + 1] = 0;
    img.data[idx + 2] = 0;
    img.data[idx + 3] = 255;
  }
  // red blob
  for (let y = 5; y < 15; y++) {
    for (let x = 5; x < 18; x++) {
      const idx = (40 * y + x) * 4;
      img.data[idx] = 255;
      img.data[idx + 1] = 0;
      img.data[idx + 2] = 0;
    }
  }
  const regions = findDiffRegions(PNG.sync.write(img), { cellSize: 2, minArea: 16 });
  assert.ok(regions.length >= 1);
  assert.ok(regions[0].width >= 8);
  assert.ok(regions[0].severity);
});

test('correlateRegions attaches probable element with confidence', () => {
  const regions = [{ id: 'region-1', x: 10, y: 10, width: 40, height: 80, area: 3200, severity: 'medium', category: 'layout' }];
  const elements = [
    { selector: '.sidebar', tag: 'aside', id: null, classes: ['sidebar'], text: 'nav', rect: { x: 8, y: 8, width: 44, height: 90 } },
    { selector: '.hero', tag: 'section', rect: { x: 200, y: 10, width: 400, height: 200 } },
  ];
  const out = correlateRegions(regions, elements);
  assert.equal(out[0].probableElement.selector, '.sidebar');
  assert.ok(['high', 'medium', 'low'].includes(out[0].probableElement.confidence));
});

test('diffLayouts detects move and style change', () => {
  const a = [
    { selector: '.box', tag: 'div', rect: { x: 0, y: 0, width: 100, height: 40 }, styles: { color: 'rgb(0,0,0)', backgroundColor: 'rgb(255,255,255)', fontSize: '16px', fontWeight: '400', display: 'block' } },
  ];
  const b = [
    { selector: '.box', tag: 'div', rect: { x: 16, y: 0, width: 100, height: 40 }, styles: { color: 'rgb(255,0,0)', backgroundColor: 'rgb(255,255,255)', fontSize: '16px', fontWeight: '400', display: 'block' } },
  ];
  const diff = diffLayouts(a, b);
  assert.equal(diff.counts.layout, 1);
  assert.equal(diff.counts.style, 1);
  assert.equal(diff.layoutChanges[0].delta.x, 16);
});
