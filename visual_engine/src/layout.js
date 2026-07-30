/**
 * Collect visible element boxes + key computed styles from a Puppeteer page.
 */

/**
 * @param {import('puppeteer-core').Page} page
 * @param {object} [options]
 */
export async function collectLayoutSnapshot(page, options = {}) {
  const limit = options.limit || 350;
  try {
    return await page.evaluate((max) => {
      function buildSelector(el) {
        if (el.id) return `#${CSS.escape(el.id)}`;
        const tag = el.tagName.toLowerCase();
        const cls = [...el.classList].slice(0, 3).map((c) => `.${CSS.escape(c)}`).join('');
        if (cls) return `${tag}${cls}`;
        const parent = el.parentElement;
        if (!parent) return tag;
        const siblings = [...parent.children].filter((c) => c.tagName === el.tagName);
        const idx = siblings.indexOf(el) + 1;
        return `${tag}:nth-of-type(${idx})`;
      }

      const nodes = Array.from(document.body?.querySelectorAll('*') || []);
      const out = [];
      for (const el of nodes) {
        if (out.length >= max) break;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        if (r.bottom < 0 || r.right < 0) continue;
        const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100);
        out.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          classes: [...el.classList].slice(0, 8),
          selector: buildSelector(el),
          text,
          rect: {
            x: Math.round(r.x),
            y: Math.round(r.y),
            width: Math.round(r.width),
            height: Math.round(r.height),
          },
          styles: {
            color: cs.color,
            backgroundColor: cs.backgroundColor,
            fontSize: cs.fontSize,
            fontWeight: cs.fontWeight,
            display: cs.display,
            position: cs.position,
            zIndex: cs.zIndex,
          },
          visible: true,
        });
      }
      return out;
    }, limit);
  } catch (err) {
    return { error: String(err.message || err), elements: [] };
  }
}

/**
 * Compare two layout snapshots → layout/style change lists.
 */
export function diffLayouts(layoutA = [], layoutB = []) {
  const listA = Array.isArray(layoutA) ? layoutA : layoutA.elements || [];
  const listB = Array.isArray(layoutB) ? layoutB : layoutB.elements || [];
  const mapA = new Map(listA.map((e) => [e.selector, e]));
  const mapB = new Map(listB.map((e) => [e.selector, e]));

  const layoutChanges = [];
  const styleChanges = [];
  const added = [];
  const removed = [];

  for (const [sel, b] of mapB) {
    const a = mapA.get(sel);
    if (!a) {
      added.push({ selector: sel, tag: b.tag, rect: b.rect });
      continue;
    }
    const dx = Math.abs((a.rect?.x || 0) - (b.rect?.x || 0));
    const dy = Math.abs((a.rect?.y || 0) - (b.rect?.y || 0));
    const dw = Math.abs((a.rect?.width || 0) - (b.rect?.width || 0));
    const dh = Math.abs((a.rect?.height || 0) - (b.rect?.height || 0));
    if (dx > 1 || dy > 1 || dw > 1 || dh > 1) {
      layoutChanges.push({
        selector: sel,
        before: a.rect,
        after: b.rect,
        delta: { x: b.rect.x - a.rect.x, y: b.rect.y - a.rect.y, width: b.rect.width - a.rect.width, height: b.rect.height - a.rect.height },
      });
    }
    const styleKeys = ['color', 'backgroundColor', 'fontSize', 'fontWeight', 'display'];
    const changedStyles = {};
    for (const key of styleKeys) {
      if ((a.styles?.[key] || '') !== (b.styles?.[key] || '')) {
        changedStyles[key] = { before: a.styles?.[key], after: b.styles?.[key] };
      }
    }
    if (Object.keys(changedStyles).length) {
      styleChanges.push({ selector: sel, changes: changedStyles });
    }
  }

  for (const [sel, a] of mapA) {
    if (!mapB.has(sel)) {
      removed.push({ selector: sel, tag: a.tag, rect: a.rect });
    }
  }

  return {
    kind: 'layout',
    added: added.slice(0, 80),
    removed: removed.slice(0, 80),
    layoutChanges: layoutChanges.slice(0, 120),
    styleChanges: styleChanges.slice(0, 120),
    counts: {
      added: added.length,
      removed: removed.length,
      layout: layoutChanges.length,
      style: styleChanges.length,
    },
  };
}
