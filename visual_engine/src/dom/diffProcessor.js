/**
 * Classify DiffDOM actions (from puppeteer-compare).
 */

export function processDiff(diff) {
  const action = diff.action;
  if (action === 'modifyTextElement') {
    return {
      type: 'text',
      before: diff.oldValue ?? null,
      after: diff.newValue ?? null,
      attribute: null,
    };
  }
  if (action === 'modifyAttribute' || diff.attribute) {
    return {
      type: 'attribute',
      before: diff.attribute != null ? `${diff.attribute}: ${diff.oldValue}` : null,
      after: diff.attribute != null ? `${diff.attribute}: ${diff.newValue}` : null,
      attribute: diff.attribute || null,
    };
  }
  if (action === 'addElement') {
    return { type: 'add', before: null, after: summarizeNode(diff.element), attribute: null };
  }
  if (action === 'removeElement') {
    return { type: 'remove', before: summarizeNode(diff.element), after: null, attribute: null };
  }
  return { type: action || 'change', before: null, after: null, attribute: null };
}

function summarizeNode(node) {
  if (!node || typeof node !== 'object') return null;
  const tag = node.nodeName || node.name || 'node';
  const id = node.id ? `#${node.id}` : '';
  return `${tag}${id}`.toLowerCase();
}

export function calculateChangeCounters(processedDiffs) {
  const counters = { textChanges: 0, attributeChanges: 0, additions: 0, removals: 0, other: 0 };
  for (const diff of processedDiffs) {
    if (diff.type === 'text') counters.textChanges++;
    else if (diff.type === 'attribute') counters.attributeChanges++;
    else if (diff.type === 'add') counters.additions++;
    else if (diff.type === 'remove') counters.removals++;
    else counters.other++;
  }
  return counters;
}
