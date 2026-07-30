/**
 * Group pixel-diff image into bounding-box regions.
 */

import { PNG } from 'pngjs';

function isDiffPixel(data, idx, threshold = 40) {
  // pixelmatch paints differing pixels with noticeable RGB (often red-ish).
  const r = data[idx];
  const g = data[idx + 1];
  const b = data[idx + 2];
  const a = data[idx + 3];
  if (a < 10) return false;
  return r > threshold || g > threshold || b > threshold;
}

/**
 * Find connected components on a coarse grid for speed.
 * @param {Buffer} diffPngBuffer
 * @param {object} [options]
 */
export function findDiffRegions(diffPngBuffer, options = {}) {
  if (!diffPngBuffer) return [];
  const img = PNG.sync.read(diffPngBuffer);
  const { width, height } = img;
  const cell = Math.max(2, Number(options.cellSize) || 4);
  const cols = Math.ceil(width / cell);
  const rows = Math.ceil(height / cell);
  const active = new Uint8Array(cols * rows);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (width * y + x) << 2;
      if (!isDiffPixel(img.data, idx, options.threshold ?? 40)) continue;
      const cx = Math.floor(x / cell);
      const cy = Math.floor(y / cell);
      active[cy * cols + cx] = 1;
    }
  }

  const visited = new Uint8Array(cols * rows);
  const regions = [];
  const dirs = [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
    [1, 1],
    [1, -1],
    [-1, 1],
    [-1, -1],
  ];

  for (let cy = 0; cy < rows; cy++) {
    for (let cx = 0; cx < cols; cx++) {
      const start = cy * cols + cx;
      if (!active[start] || visited[start]) continue;
      const stack = [[cx, cy]];
      visited[start] = 1;
      let minX = cx;
      let minY = cy;
      let maxX = cx;
      let maxY = cy;
      let cells = 0;
      while (stack.length) {
        const [x, y] = stack.pop();
        cells++;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
        for (const [dx, dy] of dirs) {
          const nx = x + dx;
          const ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
          const ni = ny * cols + nx;
          if (!active[ni] || visited[ni]) continue;
          visited[ni] = 1;
          stack.push([nx, ny]);
        }
      }
      const x = minX * cell;
      const y = minY * cell;
      const w = Math.min(width - x, (maxX - minX + 1) * cell);
      const h = Math.min(height - y, (maxY - minY + 1) * cell);
      const area = w * h;
      if (area < (options.minArea || 64)) continue;
      const severity =
        area > width * height * 0.08 ? 'high' : area > width * height * 0.02 ? 'medium' : 'low';
      regions.push({
        id: `region-${regions.length + 1}`,
        x,
        y,
        width: w,
        height: h,
        area,
        cellCount: cells,
        severity,
        category: guessCategory({ width: w, height: h, area, imageWidth: width, imageHeight: height }),
      });
    }
  }

  regions.sort((a, b) => b.area - a.area);
  return regions.slice(0, options.maxRegions || 40);
}

function guessCategory(region) {
  const ratio = region.width / Math.max(1, region.height);
  if (region.area > region.imageWidth * region.imageHeight * 0.15) return 'layout';
  if (ratio > 4 || ratio < 0.25) return 'spacing';
  if (region.width > region.imageWidth * 0.5 && region.height < 80) return 'typography';
  return 'layout';
}
