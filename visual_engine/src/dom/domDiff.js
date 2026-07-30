/**
 * Structural DOM Diff using jsdom (rewritten — DiffDOM v5 returned empty diffs
 * against JSDOM documents in our tests, so we walk the trees ourselves).
 */

import { JSDOM } from 'jsdom';

function removeIgnored(document, selectors = []) {
  for (const selector of selectors) {
    try {
      document.querySelectorAll(selector).forEach((el) => el.remove());
    } catch {
      /* ignore */
    }
  }
}

function cssPath(el) {
  if (!el || el.nodeType !== 1) return '';
  const parts = [];
  let node = el;
  while (node && node.nodeType === 1 && node.tagName.toLowerCase() !== 'html') {
    let part = node.tagName.toLowerCase();
    if (node.id) {
      part += `#${node.id}`;
      parts.unshift(part);
      break;
    }
    const cls = [...(node.classList || [])].slice(0, 2);
    if (cls.length) part += cls.map((c) => `.${c}`).join('');
    const parent = node.parentElement;
    if (parent) {
      const same = [...parent.children].filter((c) => c.tagName === node.tagName);
      if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
    }
    parts.unshift(part);
    node = parent;
  }
  return parts.join(' > ');
}

function attrsOf(el) {
  const out = {};
  if (!el?.attributes) return out;
  for (const attr of el.attributes) {
    if (attr.name === 'class' || attr.name === 'style') continue; // compared lightly
    out[attr.name] = attr.value;
  }
  return out;
}

function textOf(el) {
  if (!el) return '';
  // Direct text only (avoid deep subtree noise)
  let text = '';
  for (const child of el.childNodes || []) {
    if (child.nodeType === 3) text += child.textContent || '';
  }
  return text.replace(/\s+/g, ' ').trim();
}

function walk(elA, elB, items, stats, depth = 0) {
  if (depth > 40 || items.length >= 400) return;

  if (elA && !elB) {
    items.push({ type: 'remove', path: cssPath(elA), before: elA.tagName?.toLowerCase(), after: null, attribute: null });
    stats.removals++;
    return;
  }
  if (!elA && elB) {
    items.push({ type: 'add', path: cssPath(elB), before: null, after: elB.tagName?.toLowerCase(), attribute: null });
    stats.additions++;
    return;
  }
  if (!elA || !elB) return;

  if (elA.tagName !== elB.tagName) {
    items.push({
      type: 'change',
      path: cssPath(elB),
      before: elA.tagName.toLowerCase(),
      after: elB.tagName.toLowerCase(),
      attribute: null,
      action: 'replaceTag',
    });
    stats.other++;
  }

  const aAttrs = attrsOf(elA);
  const bAttrs = attrsOf(elB);
  const keys = new Set([...Object.keys(aAttrs), ...Object.keys(bAttrs)]);
  for (const key of keys) {
    if ((aAttrs[key] || '') !== (bAttrs[key] || '')) {
      items.push({
        type: 'attribute',
        path: cssPath(elB),
        before: `${key}: ${aAttrs[key] ?? ''}`,
        after: `${key}: ${bAttrs[key] ?? ''}`,
        attribute: key,
        action: 'modifyAttribute',
      });
      stats.attributeChanges++;
    }
  }

  // class changes
  const classA = [...(elA.classList || [])].sort().join(' ');
  const classB = [...(elB.classList || [])].sort().join(' ');
  if (classA !== classB) {
    items.push({
      type: 'attribute',
      path: cssPath(elB),
      before: `class: ${classA}`,
      after: `class: ${classB}`,
      attribute: 'class',
      action: 'modifyAttribute',
    });
    stats.attributeChanges++;
  }

  const tA = textOf(elA);
  const tB = textOf(elB);
  if (tA !== tB) {
    items.push({
      type: 'text',
      path: cssPath(elB),
      before: tA,
      after: tB,
      attribute: null,
      action: 'modifyTextElement',
    });
    stats.textChanges++;
  }

  const kidsA = [...(elA.children || [])];
  const kidsB = [...(elB.children || [])];
  const n = Math.max(kidsA.length, kidsB.length);
  for (let i = 0; i < n; i++) {
    walk(kidsA[i] || null, kidsB[i] || null, items, stats, depth + 1);
  }
}

/**
 * @param {string} htmlA
 * @param {string} htmlB
 * @param {object} [options]
 */
export function getDomDiffSummary(htmlA, htmlB, options = {}) {
  if (!htmlA || !htmlB) {
    return emptyDom('DOM diff requires HTML from both sides.');
  }
  const ignoreSelectors = options.ignoredSelectors || options.ignoreSelectors || [];
  let domA;
  let domB;
  try {
    domA = new JSDOM(String(htmlA));
    domB = new JSDOM(String(htmlB));
  } catch (err) {
    return { ...emptyDom(), error: String(err.message || err) };
  }
  removeIgnored(domA.window.document, ignoreSelectors);
  removeIgnored(domB.window.document, ignoreSelectors);

  const items = [];
  const stats = { textChanges: 0, attributeChanges: 0, additions: 0, removals: 0, other: 0 };
  const rootA = domA.window.document.body || domA.window.document.documentElement;
  const rootB = domB.window.document.body || domB.window.document.documentElement;
  walk(rootA, rootB, items, stats);

  return {
    total: items.length,
    ...stats,
    items: items.slice(0, 400),
    kind: 'dom',
  };
}

function emptyDom(note) {
  return {
    total: 0,
    textChanges: 0,
    attributeChanges: 0,
    additions: 0,
    removals: 0,
    other: 0,
    items: [],
    kind: 'dom',
    note,
  };
}
