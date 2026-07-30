/**
 * Safe artifact paths for comparison runs.
 */

import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

export function writePng(buffer, filepath) {
  ensureDir(path.dirname(filepath));
  fs.writeFileSync(filepath, buffer);
}

export function writeJson(obj, filepath) {
  ensureDir(path.dirname(filepath));
  fs.writeFileSync(filepath, JSON.stringify(obj, null, 2), 'utf8');
}

/** Sanitize a single path segment (no separators / traversal). */
export function safeId(raw, fallback = 'run') {
  const s = String(raw || '')
    .trim()
    .replace(/\.\./g, '')
    .replace(/[\\/]+/g, '-')
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/\.+/g, '.')
    .replace(/^[-.]+|[-.]+$/g, '')
    .slice(0, 80);
  return s || fallback;
}

/**
 * Create a comparison artifact directory under root.
 * Layout: root/<comparisonId>/
 */
export function createComparisonDir(root, comparisonId) {
  const id = safeId(comparisonId, randomUUID());
  const dir = path.resolve(root, id);
  const resolvedRoot = path.resolve(root);
  if (!dir.startsWith(resolvedRoot + path.sep) && dir !== resolvedRoot) {
    throw new Error('Artifact path escapes root');
  }
  ensureDir(dir);
  return { id, dir };
}

/**
 * Resolve a file path under root; reject traversal.
 */
export function resolveUnderRoot(root, relOrAbs) {
  const resolvedRoot = path.resolve(root);
  const target = path.resolve(resolvedRoot, relOrAbs);
  if (!target.startsWith(resolvedRoot + path.sep) && target !== resolvedRoot) {
    throw new Error(`Path escapes artifact root: ${relOrAbs}`);
  }
  return target;
}
