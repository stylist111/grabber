importScripts('i18n.js');
const T = (k, v) => self.GrabberI18n.t(k, v);

const HOST = 'com.grabber.host';
const REPO = 'stylist111/grabber';
let port = null;
const pending = new Map(); // id -> resolve (info / pong / pickdir)

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

async function getJobs() {
  return (await chrome.storage.session.get('jobs')).jobs || {};
}

// Serialize read-modify-write so fast progress updates don't clobber each other.
let queue = Promise.resolve();
function mutateJobs(fn) {
  queue = queue.then(async () => {
    const jobs = await getJobs();
    fn(jobs);
    await chrome.storage.session.set({ jobs });
  }).catch(() => {});
  return queue;
}

function patchJob(id, patch) {
  return mutateJobs((jobs) => { if (jobs[id]) jobs[id] = { ...jobs[id], ...patch }; });
}

const ACTIVE = ['preparing', 'downloading', 'processing'];

function connect() {
  if (port) return port;
  port = chrome.runtime.connectNative(HOST);
  port.onMessage.addListener(onHostMessage);
  port.onDisconnect.addListener(() => {
    const err = chrome.runtime.lastError?.message || T('helper_gone');
    port = null;
    for (const [, resolve] of pending) resolve({ ok: false, error: err });
    pending.clear();
    mutateJobs((jobs) => {
      for (const j of Object.values(jobs)) {
        if (ACTIVE.includes(j.phase)) { j.phase = 'error'; j.error = err; }
      }
    });
  });
  return port;
}

function request(msg) {
  return new Promise((resolve) => {
    const id = uid();
    pending.set(id, resolve);
    try {
      connect().postMessage({ ...msg, id });
    } catch (e) {
      pending.delete(id);
      resolve({ ok: false, error: String(e.message || e) });
    }
  });
}

function post(msg) {
  try { connect().postMessage(msg); return true; } catch { return false; }
}

async function onHostMessage(m) {
  if (pending.has(m.id) && ['info', 'pong', 'pickdir'].includes(m.type)) {
    pending.get(m.id)({ ok: true, ...m });
    pending.delete(m.id);
    return;
  }
  if (m.type === 'update') {
    await chrome.storage.session.set({ ytdlp: { status: m.status, version: m.version } });
  } else if (m.type === 'progress') {
    await patchJob(m.id, m.stage === 'processing'
      ? { phase: 'processing' }
      : { phase: 'downloading', percent: m.percent, speed: m.speed, eta: m.eta });
  } else if (m.type === 'done') {
    await patchJob(m.id, { phase: 'done', percent: 100, file: m.file, size: m.size });
  } else if (m.type === 'error') {
    await patchJob(m.id, m.error === 'Отменено' ? { phase: 'cancelled' } : { phase: 'error', error: m.error });
  }
}

// job = { title, site, url, kind, format, opts } — opts goes to the host as is.
async function startDownload(job, reuseId) {
  const id = reuseId || uid();
  await mutateJobs((jobs) => {
    jobs[id] = {
      ...job, id, phase: 'preparing', percent: null, speed: null, eta: null, error: null,
      created: jobs[id]?.created || Date.now(),
    };
  });
  const { dir } = await chrome.storage.local.get('dir');
  if (!post({ type: 'download', id, dir: dir || '', url: job.url, ...job.opts })) {
    await patchJob(id, { phase: 'error', error: T('helper_noresp') });
  }
  return id;
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  (async () => {
    switch (msg.cmd) {
      case 'info': return reply(await request({ type: 'info', url: msg.url }));
      case 'ping': {
        const r = await request({ type: 'ping' });
        if (r.ok) await chrome.storage.session.set({ ytdlp: { status: r.status, version: r.version } });
        return reply(r);
      }
      case 'check-update':
        await checkUpdate();
        return reply({});
      case 'update-ytdlp':
        post({ type: 'update' });
        return reply({});
      case 'pickdir': {
        // The popup closes when the dialog takes focus, so the result is saved here, not there.
        const { dir } = await chrome.storage.local.get('dir');
        const r = await request({ type: 'pickdir', initial: dir || '' });
        if (r.path) await chrome.storage.local.set({ dir: r.path });
        return reply(r);
      }
      case 'download': return reply({ id: await startDownload(msg.job) });
      case 'retry': {
        const job = (await getJobs())[msg.id];
        if (job) await startDownload(job, msg.id);
        return reply({});
      }
      case 'cancel':
        post({ type: 'cancel', id: msg.id });
        return reply({});
      case 'open':
        post({ type: 'open', path: msg.path || '' });
        return reply({});
      case 'clear':
        await mutateJobs((jobs) => {
          for (const k of Object.keys(jobs)) if (!ACTIVE.includes(jobs[k].phase)) delete jobs[k];
        });
        return reply({});
    }
  })();
  return true;
});

// Right-click menu: same UI in a standalone 400×600 window.
async function createMenu() {
  await self.GrabberI18n.load();
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'grab', title: T('menu_title'),
      contexts: ['page', 'link', 'video', 'audio'],
    });
  });
}
chrome.runtime.onInstalled.addListener(createMenu);

// New Grabber release? Ask GitHub at most every 6 hours (one anonymous request to the public API);
// the popup shows a banner when the latest release is newer than this extension.
const UPDATE_EVERY = 6 * 3600 * 1000;

function isNewer(a, b) {
  const pa = String(a).split('.').map(Number), pb = String(b).split('.').map(Number);
  for (let i = 0; i < 3; i++) if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) > (pb[i] || 0);
  return false;
}

async function checkUpdate(force) {
  const { updateCheckedAt = 0 } = await chrome.storage.local.get('updateCheckedAt');
  if (!force && Date.now() - updateCheckedAt < UPDATE_EVERY) return;
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: 'application/vnd.github+json' } });
    if (!r.ok) return;
    const rel = await r.json();
    const version = String(rel.tag_name || '').replace(/^v/, '');
    const setup = (rel.assets || []).find((a) => /Setup\.exe$/i.test(a.name));
    const update = isNewer(version, chrome.runtime.getManifest().version)
      ? { version, url: setup ? setup.browser_download_url : rel.html_url } : null;
    await chrome.storage.local.set({ updateCheckedAt: Date.now(), update });
  } catch { /* offline — try again next time */ }
}

chrome.runtime.onStartup.addListener(() => checkUpdate());
chrome.runtime.onInstalled.addListener(() => checkUpdate(true));
chrome.storage.onChanged.addListener((ch, area) => { if (area === 'local' && ch.lang) createMenu(); });

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const src = info.srcUrl && !info.srcUrl.startsWith('blob:') ? info.srcUrl : null;
  const url = info.linkUrl || src || info.pageUrl || tab?.url;
  if (!url) return;
  chrome.windows.create({
    url: chrome.runtime.getURL('popup/popup.html') + '?mode=window&url=' + encodeURIComponent(url),
    type: 'popup', width: 400, height: 630, focused: true,
  });
});
