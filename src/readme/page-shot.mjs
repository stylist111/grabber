// Screenshot a local page at a fixed width and exactly the height of its content.
// node page-shot.mjs <port> <url> <out.png> <width> <scale>
import { writeFileSync } from 'node:fs';

const [port, url, out, w, scale] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let wsUrl;
for (let i = 0; i < 50 && !wsUrl; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    wsUrl = list.find((t) => t.type === 'page')?.webSocketDebuggerUrl;
  } catch { await sleep(200); }
}
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener('open', r));
let seq = 0;
const waits = new Map();
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && waits.has(m.id)) { waits.get(m.id)(m); waits.delete(m.id); }
});
const call = (method, params = {}) => new Promise((r) => { const id = ++seq; waits.set(id, r); ws.send(JSON.stringify({ id, method, params })); });

await call('Emulation.setDeviceMetricsOverride', { width: +w, height: 1000, deviceScaleFactor: +scale, mobile: false });
await call('Page.navigate', { url });
await sleep(1500);
const r = await call('Runtime.evaluate', {
  returnByValue: true, awaitPromise: true,
  expression: `document.fonts.ready.then(() => Math.ceil(document.querySelector('.wrap').getBoundingClientRect().height))`,
});
const h = r.result.result.value;
await call('Emulation.setDeviceMetricsOverride', { width: +w, height: h, deviceScaleFactor: +scale, mobile: false });
await sleep(500);
const shot = await call('Page.captureScreenshot', { format: 'png' });
writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
console.log(`saved ${out} (${w}x${h} @${scale}x)`);
process.exit(0);
