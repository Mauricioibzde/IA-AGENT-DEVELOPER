/**
 * Device / viewport presets (adapted from puppeteer-compare config/config.js).
 */

export const DEVICE_PRESETS = {
  desktop: [
    { id: 'desktop_4k', name: 'Desktop 4K', width: 3840, height: 2160, deviceScaleFactor: 1 },
    { id: 'desktop_full_hd', name: 'Desktop Full HD', width: 1920, height: 1080, deviceScaleFactor: 1 },
    { id: 'desktop_standard', name: 'Desktop Standard', width: 1366, height: 768, deviceScaleFactor: 1 },
  ],
  laptop: [
    { id: 'laptop_15', name: 'Laptop 15"', width: 1440, height: 900, deviceScaleFactor: 1 },
    { id: 'laptop_13', name: 'Laptop 13"', width: 1280, height: 800, deviceScaleFactor: 1 },
  ],
  tablet: [
    { id: 'ipad_pro_12', name: 'iPad Pro 12.9"', width: 1024, height: 1366, deviceScaleFactor: 2 },
    { id: 'ipad_air', name: 'iPad Air', width: 820, height: 1180, deviceScaleFactor: 2 },
    { id: 'ipad_mini', name: 'iPad Mini', width: 768, height: 1024, deviceScaleFactor: 2 },
  ],
  mobile: [
    { id: 'iphone_15_pro_max', name: 'iPhone 15 Pro Max', width: 430, height: 932, deviceScaleFactor: 3 },
    { id: 'iphone_15', name: 'iPhone 15', width: 393, height: 852, deviceScaleFactor: 3 },
    { id: 'iphone_se', name: 'iPhone SE', width: 375, height: 667, deviceScaleFactor: 2 },
    { id: 'samsung_galaxy_s24', name: 'Samsung Galaxy S24', width: 412, height: 915, deviceScaleFactor: 2.625 },
    { id: 'mobile_small', name: 'Mobile small (320px)', width: 320, height: 568, deviceScaleFactor: 2 },
  ],
};

export const DEFAULT_VIEWPORT = { width: 1366, height: 768, deviceScaleFactor: 1 };

/** Flatten presets; optional category filter. */
export function listViewports(category = null) {
  if (category && DEVICE_PRESETS[category]) {
    return [...DEVICE_PRESETS[category]];
  }
  return Object.values(DEVICE_PRESETS).flat();
}

export function resolveViewport(input) {
  if (!input) return { ...DEFAULT_VIEWPORT };
  if (typeof input === 'string') {
    const all = listViewports();
    const hit = all.find((v) => v.id === input || v.name === input);
    if (hit) {
      return {
        width: hit.width,
        height: hit.height,
        deviceScaleFactor: hit.deviceScaleFactor || 1,
        id: hit.id,
        name: hit.name,
      };
    }
  }
  const width = Number(input.width) || DEFAULT_VIEWPORT.width;
  const height = Number(input.height) || DEFAULT_VIEWPORT.height;
  const deviceScaleFactor = Number(input.deviceScaleFactor) || 1;
  return { width, height, deviceScaleFactor, id: input.id, name: input.name };
}
