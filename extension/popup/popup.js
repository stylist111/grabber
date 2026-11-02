// Grabber popup logic. All rendering goes through window.GrabberUI (ui.js).
(async function () {
  'use strict';
  const UI = window.GrabberUI;
  const I18n = window.GrabberI18n;
  const T = I18n.t;
  const send = (msg) => chrome.runtime.sendMessage(msg);

  I18n.apply();

  const AUDIO = { 'MP3 320': 'mp3', 'M4A': 'm4a', 'WAV': 'wav', 'FLAC': 'flac', 'Opus': 'opus' };
  const STEPS = [2160, 1440, 1080, 720];
  const SERVICE = /^(chrome|edge|brave|browser|opera|vivaldi|about|chrome-extension|devtools|view-source|file|data|javascript):/i;
  const STORE = /^https:\/\/(chromewebstore\.google\.com|chrome\.google\.com\/webstore|microsoftedge\.microsoft\.com\/addons)/i;

  /* ---------- режим ---------- */
  const params = new URLSearchParams(location.search);
  const isWindow = params.get('mode') === 'window';
  const targetUrl = params.get('url');
  UI.setMode(isWindow ? 'window' : 'popup', { url: targetUrl });

  /* ---------- выбор, папка, yt-dlp ---------- */
  const saved = await chrome.storage.local.get(['selection']);
  if (saved.selection) UI.setSelection(saved.selection);
  UI.on('selection-change', (sel) => chrome.storage.local.set({ selection: sel }));

  let defaultDir = '';
  async function renderFolder() {
    const { dir } = await chrome.storage.local.get('dir');
    UI.setFolder({ path: dir || defaultDir || 'Grabber\\downloads', isDefault: !dir });
  }
  renderFolder();

  function renderYtdlp(v) {
    if (!v) return;
    UI.setYtdlp({ status: v.status === 'idle' ? 'updating' : v.status, version: v.version });
  }
  chrome.storage.session.get('ytdlp').then(({ ytdlp }) => renderYtdlp(ytdlp || { status: 'updating' }));

  /* ---------- медиа ---------- */
  let url = targetUrl;
  let media = null;

  // Only these two Chrome errors mean "not installed". "Failed to start…", "Error when communicating…"
  // and "Native host has exited." are hiccups (e.g. the installer is swapping files), and a site's
  // "404 Not Found" from yt-dlp has nothing to do with the helper.
  function hostMissing(err) {
    return /Specified native messaging host not found|native messaging host is forbidden/i.test(err || '');
  }

  async function checkHelper() {
    let r;
    for (let i = 0; i < 3 && !r?.ok; i++) {
      if (i) await new Promise((ok) => setTimeout(ok, 700));
      r = await send({ cmd: 'ping' });
    }
    if (!r?.ok) {
      if (hostMissing(r?.error)) UI.showHelperMissing();
      else UI.showError({ kind: 'other', title: T('err_helper_title'), code: r?.error || '', site: { name: hostOf(url), url } });
      return false;
    }
    defaultDir = r.defaultDir;
    renderFolder();
    renderYtdlp(r);
    return true;
  }

  async function loadMedia() {
    UI.showLoading();
    if (!url) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      url = tab?.url;
    }
    if (!url || SERVICE.test(url) || STORE.test(url)) return UI.showEmpty('service');
    if (!(await checkHelper())) return;

    const info = await send({ cmd: 'info', url });
    if (!info?.ok) {
      if (hostMissing(info?.error)) return UI.showHelperMissing();
      if (/Unsupported URL|No video formats|no suitable formats|There's no video/i.test(info?.error || '')) {
        return UI.showEmpty('none');
      }
      return UI.showError(mapError(info?.error, url));
    }
    media = toMedia(info, url);
    UI.showMedia(media);
    shownIds = ''; // the helper screen hid the list; force a full redraw
    renderJobs(lastJobs);
  }

  // color/letter only matter for the fallback when the real favicon can't load.
  const KNOWN = { Youtube: ['YouTube', '#E62117', 'YT'], Soundcloud: ['SoundCloud', '#FF5500', 'SC'] };
  function siteOf(info, pageUrl) {
    const k = KNOWN[info.site];
    if (k) return { name: k[0], url: pageUrl, color: k[1], letter: k[2] };
    return { name: info.domain || info.site || hostOf(pageUrl), url: pageUrl };
  }

  function hostOf(u) {
    try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; }
  }

  function toMedia(info, pageUrl) {
    const maxH = info.heights?.length ? info.heights[0] : 0;
    const hasVideo = !!info.hasVideo;
    // -S res:N takes the closest resolution not above N, so every step up to the max works.
    const qualities = ['Макс.'].concat(STEPS.filter((h) => maxH >= h - 8).map((h) => h + 'p'));
    return {
      title: info.title,
      author: info.uploader || '',
      duration: fmtTime(info.duration),
      // No thumbnail → transparent pixel, so the dark placeholder shows instead of a broken image.
      thumbnail: info.thumbnail || 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',
      site: siteOf(info, pageUrl),
      hasVideo,
      qualities,
      qualityNote: hasVideo && qualities.length === 1 && maxH
        ? T('quality_note', { h: maxH }) : '',
    };
  }

  function mapError(message, pageUrl) {
    const m = String(message || 'Unknown error');
    let kind = 'other';
    if (/private video|is private/i.test(m)) kind = 'private';
    else if (/confirm your age|age.restricted|inappropriate for some users|Sign in to confirm your age/i.test(m)) kind = 'age';
    else if (/not (made this video )?available in your country|geo.?restrict|not available in your (country|region)/i.test(m)) kind = 'region';
    return { kind, code: m, site: { name: hostOf(pageUrl), url: pageUrl } };
  }

  UI.on('rescan', loadMedia);
  UI.on('retry-media', loadMedia);
  UI.on('recheck-helper', loadMedia);
  UI.on('helper-help', () => chrome.tabs.create({ url: chrome.runtime.getURL('help.html') }));
  UI.on('retry-ytdlp', () => send({ cmd: 'update-ytdlp' }));

  /* ---------- скачать ---------- */
  UI.on('download', async (sel) => {
    if (!media) return;
    UI.flashAdded();
    const video = sel.tab === 'video' && media.hasVideo;
    const height = video && sel.quality !== 'Макс.' ? parseInt(sel.quality, 10) : null;
    const format = video
      ? (sel.h264 ? 'MP4 ' : '') + (height ? height + 'p' : T('max'))
      : sel.audioFormat;
    await send({
      cmd: 'download',
      job: {
        title: media.title, site: media.site, url, kind: video ? 'video' : 'audio', format,
        opts: video
          ? { mode: 'video', height, h264: sel.h264 }
          : { mode: 'audio', audio: AUDIO[sel.audioFormat] || 'mp3', meta: sel.cover },
      },
    });
  });

  /* ---------- загрузки ---------- */
  function fmtTime(s) {
    if (s == null || isNaN(s)) return '';
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
    return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(x).padStart(2, '0');
  }

  function fmtBytes(b, perSec) {
    if (!b) return '';
    const u = T('units');
    let i = 0;
    while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
    return b.toFixed(i >= 2 ? 1 : 0).replace('.', T('decimal')) + ' ' + u[i] + (perSec ? T('per_sec') : '');
  }

  function toItem(j) {
    return {
      id: j.id, title: j.title || j.url, kind: j.kind, format: j.format, site: j.site,
      status: j.phase, percent: j.percent, speed: fmtBytes(j.speed, true),
      eta: j.eta ? fmtTime(j.eta) : '', size: fmtBytes(j.size), error: j.error, file: j.file,
    };
  }

  let shownIds = '';
  let shownItems = {};
  function renderJobs(jobs) {
    const list = Object.values(jobs || {}).sort((a, b) => b.created - a.created).map(toItem);
    const ids = list.map((i) => i.id).join(',');
    if (ids !== shownIds) {
      UI.setDownloads(list);
    } else {
      // Same set: patch only changed rows so buttons don't flicker under the cursor.
      for (const it of list) {
        if (JSON.stringify(it) !== JSON.stringify(shownItems[it.id])) UI.updateDownload(it);
      }
    }
    shownIds = ids;
    shownItems = Object.fromEntries(list.map((i) => [i.id, i]));
  }

  let lastJobs = (await chrome.storage.session.get('jobs')).jobs;
  renderJobs(lastJobs);

  UI.on('cancel', (it) => send({ cmd: 'cancel', id: it.id }));
  UI.on('retry', (it) => send({ cmd: 'retry', id: it.id }));
  UI.on('show-in-folder', (it) => send({ cmd: 'open', path: it.file || '' }));
  UI.on('clear-downloads', () => send({ cmd: 'clear' }));

  /* ---------- папка ---------- */
  UI.on('open-folder', async () => send({ cmd: 'open', path: (await chrome.storage.local.get('dir')).dir || '' }));
  UI.on('change-folder', () => send({ cmd: 'pickdir' }));
  UI.on('reset-folder', () => chrome.storage.local.remove('dir'));

  chrome.storage.onChanged.addListener((ch, area) => {
    if (area === 'session' && ch.jobs) { lastJobs = ch.jobs.newValue; renderJobs(lastJobs); }
    if (area === 'session' && ch.ytdlp) renderYtdlp(ch.ytdlp.newValue);
    if (area === 'local' && ch.dir) renderFolder();
    if (area === 'local' && (ch.update || ch.updateLaterUntil)) renderUpdate();
  });

  /* ---------- вышла новая версия ---------- */
  const $ref = (n) => document.querySelector(`[data-ref="${n}"]`);
  function isNewer(a, b) {
    const pa = String(a).split('.').map(Number), pb = String(b).split('.').map(Number);
    for (let i = 0; i < 3; i++) if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) > (pb[i] || 0);
    return false;
  }
  async function renderUpdate() {
    const { update, updateLaterUntil = 0 } = await chrome.storage.local.get(['update', 'updateLaterUntil']);
    // compare with the running version too: right after updating, the stored notice is stale
    const show = !!update && isNewer(update.version, chrome.runtime.getManifest().version) && Date.now() > updateLaterUntil;
    $ref('update').hidden = !show;
    if (show) $ref('updateTitle').textContent = T('upd_title', { v: update.version });
  }
  $ref('updateGet').onclick = async () => {
    const { update } = await chrome.storage.local.get('update');
    if (update) chrome.tabs.create({ url: update.url });
  };
  // "Later" hides it for a day; it comes back on the next popup after that.
  $ref('updateLater').onclick = () => chrome.storage.local.set({ updateLaterUntil: Date.now() + 24 * 3600 * 1000 });
  renderUpdate();
  send({ cmd: 'check-update' });

  loadMedia();
})();
