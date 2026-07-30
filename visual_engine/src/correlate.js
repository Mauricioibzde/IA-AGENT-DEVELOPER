/**
 * Correlate pixel-diff regions with DOM/layout elements.
 */

function overlapArea(a, b) {
  const x1 = Math.max(a.x, b.x);
  const y1 = Math.max(a.y, b.y);
  const x2 = Math.min(a.x + a.width, b.x + b.width);
  const y2 = Math.min(a.y + a.height, b.y + b.height);
  const w = Math.max(0, x2 - x1);
  const h = Math.max(0, y2 - y1);
  return w * h;
}

function iou(a, b) {
  const inter = overlapArea(a, b);
  if (!inter) return 0;
  const union = a.width * a.height + b.width * b.height - inter;
  return union > 0 ? inter / union : 0;
}

function confidenceFromScore(score, containment) {
  if (score >= 0.35 || containment >= 0.7) return 'high';
  if (score >= 0.12 || containment >= 0.35) return 'medium';
  if (score > 0 || containment > 0.1) return 'low';
  return 'low';
}

/**
 * @param {Array} regions
 * @param {Array} elements layout snapshot (actual page preferred)
 */
export function correlateRegions(regions = [], elements = []) {
  const list = Array.isArray(elements) ? elements : elements.elements || [];
  return (regions || []).map((region) => {
    let best = null;
    let bestScore = 0;
    let bestContain = 0;
    for (const el of list) {
      const rect = el.rect;
      if (!rect) continue;
      const score = iou(region, rect);
      const contain = overlapArea(region, rect) / Math.max(1, region.area || region.width * region.height);
      const combined = score * 0.6 + contain * 0.4;
      if (combined > bestScore) {
        bestScore = combined;
        bestContain = contain;
        best = el;
      }
    }
    if (!best || bestScore < 0.02) {
      return {
        ...region,
        probableElement: null,
        diagnosis: `${region.category || 'diff'} region without a confident element match.`,
      };
    }
    const confidence = confidenceFromScore(bestScore, bestContain);
    const dx = (best.rect?.width || 0) - region.width;
    const diagnosis =
      confidence === 'high'
        ? `Likely ${best.selector} (${best.tag}) overlapping this region.`
        : `Possible match ${best.selector} (confidence ${confidence}).`;
    return {
      ...region,
      probableElement: {
        selector: best.selector,
        tag: best.tag,
        id: best.id,
        classes: best.classes,
        text: best.text,
        confidence,
        overlapScore: Number(bestScore.toFixed(3)),
        rect: best.rect,
      },
      diagnosis,
      hints: {
        widthDeltaGuess: dx,
      },
    };
  });
}
