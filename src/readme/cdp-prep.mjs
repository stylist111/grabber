// Prepare a visible Chrome window for the toolbar screenshot: load Grabber, open a page.
// node cdp-prep.mjs <port> <extensionDir> <url>
const [port, extDir, url] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect(endpoint, pick) {
  for (let i = 0; i < 75; i++) {
    try {
      const j = await (await fetch(`http://127.0.0.1:${port}/json/${endpoint}`)).json();
      const wsUrl = pick(j);
      if (wsUrl) {
        const ws = new WebSocket(wsUrl);
        await new Promise((r) => ws.addEventListener('open', r));
        let seq = 0;
        const waits = new Map();
        ws.addEventListener('message', (e) => {
          const m = JSON.parse(e.data);
          if (m.id && waits.has(m.id)) { waits.get(m.id)(m); waits.delete(m.id); }
        });
        ws.call = (method, params = {}) => new Promise((r) => { const id = ++seq; waits.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
        return ws;
      }
    } catch {}
    await sleep(200);
  }
  throw new Error('CDP not reachable');
}

const browser = await connect('version', (j) => j.webSocketDebuggerUrl);
console.log('loadUnpacked', JSON.stringify((await browser.call('Extensions.loadUnpacked', { path: extDir })).result));
const page = await connect('list', (l) => l.find((t) => t.type === 'page')?.webSocketDebuggerUrl);
await page.call('Page.navigate', { url });
await sleep(5000);
// Dismiss a cookie banner if the site shows one.
await page.call('Runtime.evaluate', {
  expression: `[...document.querySelectorAll('button')].find((b) => /Принять все|Accept all/i.test(b.textContent))?.click()`,
});
await sleep(3000);
console.log('ready');
process.exit(0);
