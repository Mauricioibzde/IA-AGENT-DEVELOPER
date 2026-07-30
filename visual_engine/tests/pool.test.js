import test from 'node:test';
import assert from 'node:assert/strict';
import { BrowserPool } from '../src/pool.js';

test('BrowserPool tracks acquire/release without launching when mocked', async () => {
  let launches = 0;
  const fakeBrowser = { connected: true, close: async () => {} };
  const pool = new BrowserPool({ idleMs: 10 });
  pool.acquire = async function acquire() {
    this._acquires += 1;
    this._clearIdle();
    if (!this._browser) {
      launches += 1;
      this._browser = fakeBrowser;
      this._launches += 1;
    }
    this._inUse += 1;
    return this._browser;
  };

  const a = await pool.acquire();
  const b = await pool.acquire();
  assert.equal(a, b);
  assert.equal(launches, 1);
  pool.release();
  pool.release();
  const stats = pool.stats();
  assert.equal(stats.acquires, 2);
  assert.equal(stats.launches, 1);
  assert.equal(stats.inUse, 0);
  await pool.drain();
  assert.equal(pool.stats().alive, false);
});
