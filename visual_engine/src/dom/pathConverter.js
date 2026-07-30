/**
 * DiffDOM path → CSS selector (from puppeteer-compare).
 */

function stepToCssSelector(step) {
  if (!step || typeof step !== 'object') return '';
  const tagName = step.name || '*';
  const id = step.id ? `#${step.id}` : '';
  const classes = step.class ? `.${String(step.class).split(/\s+/).filter(Boolean).join('.')}` : '';
  const index = Number.isFinite(step.index) ? `:nth-child(${step.index + 1})` : '';
  return `${tagName}${id}${classes}${index}`;
}

export function pathToCssSelector(pathArray = []) {
  return (pathArray || [])
    .map(stepToCssSelector)
    .filter(Boolean)
    .join(' > ');
}
