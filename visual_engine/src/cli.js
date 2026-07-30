#!/usr/bin/env node
/**
 * JSON CLI bridge for the Forge Python facade.
 * Usage:
 *   node src/cli.js '{"op":"compare_images","source":{"type":"image","value":"a.png"},...}'
 *   echo '{...}' | node src/cli.js
 */

import fs from 'node:fs';
import { compare, capture, detectChromePath, listViewports, compareImages } from './index.js';

async function readInput() {
  const arg = process.argv[2];
  if (arg && arg !== '-') {
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

async function main() {
  const req = await readInput();
  const op = req.op || 'compare';

  if (op === 'ping') {
    console.log(
      JSON.stringify({
        ok: true,
        chrome: detectChromePath(),
        viewports: listViewports().length,
      })
    );
    return;
  }

  if (op === 'list_viewports') {
    console.log(JSON.stringify({ ok: true, viewports: listViewports(req.category || null) }));
    return;
  }

  if (op === 'compare_images' || (op === 'compare' && req.source?.type === 'image' && req.target?.type === 'image')) {
    // Fast path without browser for tests / Python unit bridge.
    if (req.inline === true) {
      const a = fs.readFileSync(req.source.value);
      const b = fs.readFileSync(req.target.value);
      const metrics = compareImages(a, b, req.options || {});
      const { diffPngBuffer, ...rest } = metrics;
      console.log(
        JSON.stringify({
          ok: true,
          status: rest.comparable === false ? 'incompatible' : 'completed',
          mode: 'image-vs-image',
          ...rest,
          hasDiffBuffer: Boolean(diffPngBuffer),
        })
      );
      return;
    }
  }

  if (op === 'capture') {
    const result = await capture(req);
    console.log(JSON.stringify({ ok: true, ...result }));
    return;
  }

  if (op === 'compare' || op === 'compare_images') {
    const result = await compare(req);
    console.log(JSON.stringify({ ok: true, ...result }));
    return;
  }

  throw new Error(`Unknown op: ${op}`);
}

main().catch((err) => {
  console.log(JSON.stringify({ ok: false, error: String(err.message || err) }));
  process.exitCode = 1;
});
