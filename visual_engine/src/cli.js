#!/usr/bin/env node
/**
 * JSON CLI bridge for the Forge Python facade.
 *
 * One-shot:
 *   node src/cli.js '{"op":"ping"}'
 *   echo '{...}' | node src/cli.js
 *
 * Persistent worker (reuses Chromium pool across compares):
 *   node src/cli.js --serve
 *   stdin: one JSON object per line
 *   stdout: one JSON object per line
 */

import fs from 'node:fs';
import readline from 'node:readline';
import {
  compare,
  compareMulti,
  capture,
  detectChromePath,
  listViewports,
  compareImages,
  defaultPool,
} from './index.js';

async function readOneShotInput() {
  const arg = process.argv[2];
  if (arg && arg !== '-' && arg !== '--serve') {
    if (arg.endsWith('.json') && fs.existsSync(arg)) {
      return JSON.parse(fs.readFileSync(arg, 'utf8'));
    }
    return JSON.parse(arg);
  }
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString('utf8').trim();
  if (!text) throw new Error('Empty CLI input');
  return JSON.parse(text);
}

async function handleRequest(req) {
  const op = req.op || 'compare';

  if (op === 'ping') {
    return {
      ok: true,
      chrome: detectChromePath(),
      viewports: listViewports().length,
      pool: defaultPool.stats(),
    };
  }

  if (op === 'pool_stats') {
    return { ok: true, pool: defaultPool.stats() };
  }

  if (op === 'pool_drain') {
    await defaultPool.drain();
    return { ok: true, pool: defaultPool.stats() };
  }

  if (op === 'shutdown') {
    await defaultPool.drain();
    return { ok: true, shutdown: true };
  }

  if (op === 'list_viewports') {
    return { ok: true, viewports: listViewports(req.category || null) };
  }

  if (op === 'compare_images' || (op === 'compare' && req.source?.type === 'image' && req.target?.type === 'image')) {
    if (req.inline === true) {
      const a = fs.readFileSync(req.source.value);
      const b = fs.readFileSync(req.target.value);
      const metrics = compareImages(a, b, req.options || {});
      const { diffPngBuffer, ...rest } = metrics;
      return {
        ok: true,
        status: rest.comparable === false ? 'incompatible' : 'completed',
        mode: 'image-vs-image',
        ...rest,
        hasDiffBuffer: Boolean(diffPngBuffer),
      };
    }
  }

  if (op === 'capture') {
    const result = await capture(req);
    return { ok: true, ...result };
  }

  if (op === 'compare_multi') {
    const result = await compareMulti(req);
    return { ok: true, ...result };
  }

  if (op === 'compare' || op === 'compare_images') {
    const result = await compare(req);
    return { ok: true, ...result };
  }

  throw new Error(`Unknown op: ${op}`);
}

async function serve() {
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  process.stderr.write('[visual-cli] serve mode ready\n');
  for await (const line of rl) {
    const text = String(line || '').trim();
    if (!text) continue;
    let req;
    try {
      req = JSON.parse(text);
    } catch (err) {
      process.stdout.write(`${JSON.stringify({ ok: false, error: `Invalid JSON: ${err.message}` })}\n`);
      continue;
    }
    try {
      const result = await handleRequest(req);
      process.stdout.write(`${JSON.stringify(result)}\n`);
      if (result?.shutdown) {
        rl.close();
        break;
      }
    } catch (err) {
      process.stdout.write(`${JSON.stringify({ ok: false, error: String(err.message || err) })}\n`);
    }
  }
  try {
    await defaultPool.drain();
  } catch {
    // ignore
  }
}

async function main() {
  if (process.argv.includes('--serve')) {
    await serve();
    return;
  }
  const req = await readOneShotInput();
  const result = await handleRequest(req);
  console.log(JSON.stringify(result));
}

main().catch((err) => {
  console.log(JSON.stringify({ ok: false, error: String(err.message || err) }));
  process.exitCode = 1;
});
