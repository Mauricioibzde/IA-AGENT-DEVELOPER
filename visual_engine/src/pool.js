/**
 * Lightweight browser pool — reuse one Chromium across pages/viewports
 * within a single CLI process. Idle browsers are closed after timeout.
 */

import { createBrowser, closeBrowser } from './browser.js';

const DEFAULT_IDLE_MS = 30_000;

class BrowserPool {
  constructor(opts = {}) {
    this.idleMs = Number(opts.idleMs) > 0 ? Number(opts.idleMs) : DEFAULT_IDLE_MS;
    this.browserOpts = opts.browser || {};
    this._browser = null;
    this._inUse = 0;
    this._idleTimer = null;
    this._launches = 0;
    this._acquires = 0;
  }

  stats() {
    return {
      launches: this._launches,
      acquires: this._acquires,
      inUse: this._inUse,
      alive: Boolean(this._browser && this._browser.connected !== false),
    };
  }

  async acquire() {
    this._acquires += 1;
    this._clearIdle();
    if (!this._browser || this._browser.connected === false) {
      this._browser = await createBrowser(this.browserOpts);
      this._launches += 1;
    }
    this._inUse += 1;
    return this._browser;
  }

  release() {
    this._inUse = Math.max(0, this._inUse - 1);
    if (this._inUse === 0) this._scheduleIdleClose();
  }

  async withBrowser(fn) {
    const browser = await this.acquire();
    try {
      return await fn(browser);
    } finally {
      this.release();
    }
  }

  async drain() {
    this._clearIdle();
    const b = this._browser;
    this._browser = null;
    this._inUse = 0;
    await closeBrowser(b);
  }

  _scheduleIdleClose() {
    this._clearIdle();
    this._idleTimer = setTimeout(() => {
      if (this._inUse === 0) {
        const b = this._browser;
        this._browser = null;
        closeBrowser(b);
      }
    }, this.idleMs);
    // Allow process to exit with idle timer pending.
    if (typeof this._idleTimer.unref === 'function') this._idleTimer.unref();
  }

  _clearIdle() {
    if (this._idleTimer) {
      clearTimeout(this._idleTimer);
      this._idleTimer = null;
    }
  }
}

/** Shared default pool for a CLI process. */
export const defaultPool = new BrowserPool();

export function createPool(opts = {}) {
  return new BrowserPool(opts);
}

export { BrowserPool };
