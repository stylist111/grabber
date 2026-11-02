// Screenshot of the real chrome://extensions page via the DevTools protocol
// (the CLI --screenshot can't open chrome:// URLs), plus the positions of the elements
// the guide circles: Developer mode, Load unpacked, the Grabber card.
// node cdp-shot.mjs <port> <extensionDir> <out.png> <width> <height>  → prints rects JSON (in % of the image)
import { writeFileSync } from 'node:fs';

const [port, extDir, out, w, h] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect(pick) {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/${pick === 'browser' ? 'version' : 'list'}`)).json();
      const url = pick === 'browser' ? list.webSocketDebuggerUrl : list.find((t) => t.type === 'page')?.webSocketDebuggerUrl;
      if (url) {
        const ws = new WebSocket(url);
        await new Promise((r) => ws.addEventListener('open', r));
        let seq = 0;
        const waits = new Map();
        ws.addEventListener('message', (e) => {
          const m = JSON.parse(e.data);
          if (m.id && waits.has(m.id)) { waits.get(m.id)(m); waits.delete(m.id); }
        });
        ws.send2 = (method, params = {}) => new Promise((r) => { const id = ++seq; waits.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
        return ws;
      }
    } catch {}
    await sleep(200);
  }
  throw new Error('CDP not reachable');
}

const browser = await connect('browser');
const loaded = await browser.send2('Extensions.loadUnpacked', { path: extDir });
console.error('loadUnpacked:', JSON.stringify(loaded.result || loaded.error));

const page = await connect('page');
await page.send2('Emulation.setDeviceMetricsOverride', { width: +w, height: +h, deviceScaleFactor: 2, mobile: false });
await page.send2('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }] });
await page.send2('Page.navigate', { url: 'chrome://extensions' });
await sleep(2000);
await page.send2('Runtime.evaluate', { expression: `
  (() => {
    const tb = document.querySelector('extensions-manager').shadowRoot.querySelector('extensions-toolbar').shadowRoot;
    const t = tb.querySelector('#devMode');
    if (!t.checked) t.click();
    document.activeElement && document.activeElement.blur();
  })()` });
await sleep(1200);

// Element boxes (CSS px of the page = CSS px of the screenshot / 2).
const r = await page.send2('Runtime.evaluate', { returnByValue: true, expression: `
  (() => {
    const box = (el) => { const b = el.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
    const union = (a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])];
    const mgr = document.querySelector('extensions-manager').shadowRoot;
    const tb = mgr.querySelector('extensions-toolbar').shadowRoot;
    const toggle = tb.querySelector('#devMode');
    // the "Developer mode" text sits right before the toggle
    const label = [...tb.querySelectorAll('*')].filter((e) => e.children.length === 0 && /\\S/.test(e.textContent)
      && e.getBoundingClientRect().right <= toggle.getBoundingClientRect().left + 2
      && Math.abs(e.getBoundingClientRect().top - toggle.getBoundingClientRect().top) < 20).pop();
    const load = tb.querySelector('#loadUnpacked');
    const item = mgr.querySelector('extensions-item-list').shadowRoot.querySelector('extensions-item');
    const card = item.shadowRoot.querySelector('#card') || item;
    return { dev: union(box(label), box(toggle)), load: box(load), card: box(card) };
  })()` });
if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails));
const rects = r.result.result.value;
const W = +w, H = +h, pad = 5;
const pct = ([l, t, rr, b]) => {
  const L = Math.max(0, l - pad), T = Math.max(0, t - pad), R = Math.min(W, rr + pad), B = Math.min(H, b + pad);
  return { left: +(L / W * 100).toFixed(2), top: +(T / H * 100).toFixed(2), width: +((R - L) / W * 100).toFixed(2), height: +((B - T) / H * 100).toFixed(2) };
};
const shot = await page.send2('Page.captureScreenshot', { format: 'png' });
writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
console.log(JSON.stringify({ dev: pct(rects.dev), load: pct(rects.load), card: pct(rects.card) }));
process.exit(0);
