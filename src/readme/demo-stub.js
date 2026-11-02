// Fake chrome.* API with demo data — only for rendering the popup screenshot in the README image.
(function () {
  const lang = new URLSearchParams(location.search).get('lang') || 'ru';
  localStorage.setItem('grabber-lang', lang);
  const en = lang === 'en';
  const mk = (data) => ({
    get: async (k) => { const o = {}; (Array.isArray(k) ? k : [k]).forEach((x) => { if (x in data) o[x] = data[x]; }); return o; },
    set: async (o) => Object.assign(data, o),
    remove: async (k) => { delete data[k]; },
  });
  const now = Date.now();
  const yt = { name: 'YouTube', url: 'https://youtube.com', color: '#E62117', letter: 'YT' };
  const sc = { name: 'SoundCloud', url: 'https://soundcloud.com', color: '#FF5500', letter: 'SC' };
  const jobs = {
    a: { id: 'a', title: 'Night Drive — lo-fi mix', kind: 'audio', format: 'MP3 320', site: sc, phase: 'downloading', percent: 64, speed: 13000000, eta: 18, created: now },
    b: { id: 'b', title: en ? 'Timelapse: Moscow City at night' : 'Таймлапс: Москва-Сити ночью', kind: 'video', format: 'MP4 2160p', site: yt, phase: 'done', size: 412000000, created: now - 1000, file: 'x' },
  };
  window.chrome = {
    runtime: {
      getURL: () => 'about:blank',
      sendMessage: async (m) => {
        if (m.cmd === 'ping') return { ok: true, defaultDir: String.raw`C:\Users\Name\Grabber\downloads`, status: 'ok', version: '2026.10.26' };
        if (m.cmd === 'info') return {
          ok: true, title: en ? 'Aerial footage: northern lights over the Barents Sea' : 'Аэросъёмка Териберки: северное сияние над Баренцевым морем', uploader: 'Arctic Frames',
          duration: 767, site: 'Youtube', domain: 'youtube.com', heights: [2160, 1440, 1080, 720, 480], hasVideo: true,
          thumbnail: 'thumb.png', // copied next to popup.html by render.ps1
        };
        return {};
      },
    },
    storage: { local: mk({}), session: mk({ jobs, ytdlp: { status: 'ok', version: '2026.10.26' } }), onChanged: { addListener() {} } },
    tabs: { query: async () => [{ url: 'https://www.youtube.com/watch?v=demo' }], create() {} },
  };
})();
