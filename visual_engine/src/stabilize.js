/**
 * Deterministic capture helpers — reduce false positives from animation/cursor.
 */

export const STABILIZE_CSS = `
*, *::before, *::after {
  animation: none !important;
  animation-duration: 0s !important;
  transition: none !important;
  transition-duration: 0s !important;
  caret-color: transparent !important;
  scroll-behavior: auto !important;
}
html { scrollbar-width: none !important; }
body { cursor: none !important; }
::-webkit-scrollbar { display: none !important; }
`;

/**
 * Inject stabilization CSS and wait for fonts/images when possible.
 * @param {import('puppeteer-core').Page} page
 */
export async function stabilizePage(page) {
  await page.addStyleTag({ content: STABILIZE_CSS }).catch(() => {});
  await page
    .evaluate(async () => {
      if (document.fonts?.ready) {
        try {
          await document.fonts.ready;
        } catch (_) {
          /* ignore */
        }
      }
      const imgs = Array.from(document.images || []);
      await Promise.all(
        imgs.map((img) => {
          if (img.complete) return Promise.resolve();
          return new Promise((resolve) => {
            img.addEventListener('load', resolve, { once: true });
            img.addEventListener('error', resolve, { once: true });
            setTimeout(resolve, 2000);
          });
        })
      );
    })
    .catch(() => {});
}
