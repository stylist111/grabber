/*
 * Grabber UI v2 — слой отображения.
 * Ничего не знает о yt-dlp, native messaging и chrome.* (кроме необязательного faviconUrl).
 * Ваша логика вызывает методы window.GrabberUI и подписывается на действия через GrabberUI.on(...).
 *
 *   GrabberUI.on('download', (sel) => …)       // sel = { tab:'video'|'audio', quality, h264, audioFormat, cover }
 *   GrabberUI.on('cancel' | 'retry' | 'show-in-folder', (item) => …)
 *   GrabberUI.on('open-folder' | 'change-folder' | 'reset-folder' | 'clear-downloads'
 *                | 'rescan' | 'retry-media' | 'copy-error' | 'recheck-helper' | 'retry-ytdlp' | 'helper-help', () => …)
 *   GrabberUI.on('selection-change', (sel) => …) // чтобы сохранить выбор в chrome.storage
 */
(function () {
  'use strict';

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var T = function (k, v) { return window.GrabberI18n ? window.GrabberI18n.t(k, v) : k; };
  // 'Макс.' stays the internal value (saved selections use it); only its label is translated.
  var qLabel = function (q) { return q === 'Макс.' ? T('max') : q; };
  var ref = function (name, root) { return (root || document).querySelector('[data-ref="' + name + '"]'); };

  var VIDEO_QUALITIES = ['Макс.', '2160p', '1440p', '1080p', '720p'];
  var AUDIO_FORMATS = ['MP3 320', 'M4A', 'WAV', 'FLAC', 'Opus'];
  var H264_LIMITED = ['Макс.', '2160p', '1440p']; // на YouTube в H.264 отдаётся максимум 1080p

  var ICON = {
    video: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="3.5" width="12" height="9" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M6.8 6.3v3.4L9.7 8z" fill="currentColor"/></svg>',
    audio: '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 12V3.6l7-1.4v8.4" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><circle cx="4.4" cy="12" r="1.6" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="11.4" cy="10.6" r="1.6" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
    download: '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2.5v7M5 6.5l3 3 3-3M3.5 13h9" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    check: '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5 6.5 11.5 12.5 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    x: '<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    folder: '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4.5a1 1 0 0 1 1-1h3.2l1.5 1.5H13a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
    retry: '<svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true"><path d="M13 8a5 5 0 1 1-1.5-3.6M13 2.5v3h-3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    search: '<svg width="22" height="22" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M10.4 10.4 14 14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
    browser: '<svg width="22" height="22" viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="3" width="12" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M2 6h12" stroke="currentColor" stroke-width="1.4"/></svg>',
    lock: '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
    globe: '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M2 8h12M8 2c-2 2.2-2 9.8 0 12M8 2c2 2.2 2 9.8 0 12" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>',
    alert: '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2 14.5 13.5h-13z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 6.5v3.2M8 11.6v.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    warnSmall: '<svg width="11" height="11" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2 14.5 13.5h-13z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8 6.5v3.2M8 11.6v.1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    spinSmall: '<svg class="g-spin" width="10" height="10" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill="none" stroke="#2B66F6" stroke-opacity=".25" stroke-width="2.6"/><path d="M14 8a6 6 0 0 0-6-6" fill="none" stroke="#2B66F6" stroke-width="2.6" stroke-linecap="round"/></svg>'
  };

  var ERRORS = {
    private: { icon: 'lock', key: 'err_private', retry: true },
    age: { icon: '18+', key: 'err_age', retry: true },
    region: { icon: 'globe', key: 'err_region', retry: false },
    notfound: { icon: 'search', key: 'err_notfound', retry: true },
    login: { icon: 'lock', key: 'err_login', retry: true },
    busy: { icon: 'alert', key: 'err_busy', retry: true },
    network: { icon: 'globe', key: 'err_network', retry: true },
    other: { icon: 'alert', key: 'err_other', retry: true }
  };

  var EMPTY = {
    none: { icon: 'search', key: 'empty_none', actions: true },
    service: { icon: 'browser', key: 'empty_service', actions: false }
  };

  var handlers = {};
  var state = {
    media: null,
    tab: 'video',
    quality: '1080p',
    audioFormat: 'MP3 320',
    h264: true,
    cover: true,
    addedTimer: null,
    lastError: '',
    folderPath: ''
  };

  function emit(name, payload) { if (handlers[name]) handlers[name](payload); }
  function text(el, v) { if (el) el.textContent = v == null ? '' : String(v); }
  function show(el, on) { if (el) el.hidden = !on; }

  /* ---------- favicon ---------- */
  // В MV3 нужно разрешение "favicon" в manifest.json. Без chrome.runtime вернёт null → буквенная заглушка.
  function faviconUrl(pageUrl, size) {
    try {
      if (!pageUrl || !window.chrome || !chrome.runtime || !chrome.runtime.getURL) return null;
      var u = new URL(chrome.runtime.getURL('/_favicon/'));
      u.searchParams.set('pageUrl', pageUrl);
      u.searchParams.set('size', String(size || 32));
      return u.toString();
    } catch (e) { return null; }
  }
  function favNode(site, size) {
    // site: { name, url, favicon?, color?, letter? } — color/letter нужны только для буквенной заглушки
    site = site || {};
    var src = site.favicon || faviconUrl(site.url, 32);
    var n;
    if (src) {
      n = document.createElement('img');
      n.className = 'g-fav'; n.alt = ''; n.width = size || 16; n.height = size || 16; n.src = src;
      n.onerror = function () { n.replaceWith(letterFav(site.name, size, site.color, site.letter)); };
    } else {
      n = letterFav(site.name, size, site.color, site.letter);
    }
    return n;
  }
  function letterFav(name, size, color, letter) {
    var s = document.createElement('span');
    s.className = 'g-fav g-fav--letter';
    if (color) s.style.background = color;
    if (size) { s.style.width = size + 'px'; s.style.height = size + 'px'; }
    s.textContent = (letter || (name || '?').trim().slice(0, 1)).toUpperCase();
    return s;
  }
  function putFav(slot, site, size) {
    if (!slot) return;
    slot.replaceChildren(favNode(site, size));
  }

  /* ---------- путь с многоточием в середине ---------- */
  function middleEllipsis(path, max) {
    max = max || 42;
    if (!path || path.length <= max) return path || '';
    var sep = path.indexOf('\\') >= 0 ? '\\' : '/';
    var parts = path.split(sep);
    if (parts.length <= 3) return path.slice(0, Math.ceil(max / 2) - 1) + '…' + path.slice(-Math.floor(max / 2));
    var head = parts.slice(0, 2).join(sep);
    var tail = [];
    for (var i = parts.length - 1; i > 1; i--) {
      var candidate = [parts[i]].concat(tail).join(sep);
      if ((head + sep + '…' + sep + candidate).length > max && tail.length) break;
      tail.unshift(parts[i]);
    }
    var res = head + sep + '…' + sep + tail.join(sep);
    if (res.length > max) res = parts[0] + sep + '…' + sep + tail.join(sep);
    return res;
  }

  /* ---------- виды ---------- */
  function setView(name) {
    document.querySelectorAll('[data-view]').forEach(function (v) { v.hidden = v.getAttribute('data-view') !== name; });
  }

  function selection() {
    return { tab: state.tab, quality: state.quality, h264: state.h264, audioFormat: state.audioFormat, cover: state.cover };
  }

  function renderControls() {
    var m = state.media || {};
    var isVideo = state.tab === 'video';
    var tabs = ref('tabs');
    show(tabs, m.hasVideo !== false);
    show(ref('soundOnly'), m.hasVideo === false);
    tabs.querySelectorAll('[data-tab]').forEach(function (b) {
      var on = b.getAttribute('data-tab') === state.tab;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });

    var list = isVideo ? (m.qualities && m.qualities.length ? m.qualities : VIDEO_QUALITIES) : AUDIO_FORMATS;
    var current = isVideo ? state.quality : state.audioFormat;
    if (list.indexOf(current) < 0) {
      current = isVideo ? (list.indexOf('1080p') >= 0 ? '1080p' : list[0]) : list[0];
      if (isVideo) state.quality = current; else state.audioFormat = current;
    }
    text(ref('chipsLabel'), isVideo ? T('quality') : T('format'));
    var chips = ref('chips');
    chips.replaceChildren();
    list.forEach(function (label) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'g-chip' + (label === current ? ' is-on' : '');
      b.setAttribute('aria-pressed', label === current ? 'true' : 'false');
      b.textContent = qLabel(label);
      b.addEventListener('click', function () {
        if (isVideo) state.quality = label; else state.audioFormat = label;
        renderControls(); emit('selection-change', selection());
      });
      chips.appendChild(b);
    });

    var noteText = isVideo && m.qualityNote ? m.qualityNote : '';
    show(ref('note'), !!noteText); text(ref('noteText'), noteText);

    var sw = ref('optSwitch');
    if (isVideo) {
      text(ref('optTitle'), T('h264_title'));
      text(ref('optSub'), T('h264_sub'));
      sw.setAttribute('aria-checked', state.h264 ? 'true' : 'false');
    } else {
      text(ref('optTitle'), T('cover_title'));
      text(ref('optSub'), T('cover_sub'));
      sw.setAttribute('aria-checked', state.cover ? 'true' : 'false');
    }
    var above1080 = (m.qualities || VIDEO_QUALITIES).some(function (q) { return q === '1440p' || q === '2160p'; });
    var warn = isVideo && state.h264 && above1080 && /youtube/i.test(m.site && m.site.name || '') && H264_LIMITED.indexOf(state.quality) >= 0;
    show(ref('h264Warn'), warn);
    renderButton();
  }

  function renderButton() {
    var btn = ref('download');
    var added = btn.classList.contains('is-added');
    var isVideo = state.tab === 'video';
    if (added) {
      ref('btnMain').innerHTML = '<span></span>' + ICON.check;
      text(ref('btnMain').firstChild, T('added'));
      text(ref('btnSub'), T('added_sub'));
      return;
    }
    ref('btnMain').innerHTML = ICON.download + '<span></span>';
    text(ref('btnMain').lastChild, T('download'));
    text(ref('btnSub'), isVideo
      ? T(state.h264 ? 'sub_h264' : 'sub_orig', { q: qLabel(state.quality) })
      : state.audioFormat + (state.cover ? T('sub_cover') : ''));
  }

  /* ---------- загрузки ---------- */
  function renderItem(it) {
    var node = document.getElementById('g-tpl-item').content.firstElementChild.cloneNode(true);
    node.dataset.id = it.id;
    var status = it.status;
    node.classList.toggle('is-done', status === 'done');
    node.classList.toggle('is-error', status === 'error');
    node.classList.toggle('is-cancelled', status === 'cancelled');
    ref('kindIcon', node).innerHTML = it.kind === 'audio' ? ICON.audio : ICON.video;
    var favSlot = ref('fav', node);
    var f = favNode(it.site, 14); f.classList.add('g-item__fav'); favSlot.replaceWith(f);
    text(ref('title', node), it.title);
    text(ref('fmt', node), it.format || '');

    var line = '';
    var bar = ref('bar', node), fill = ref('fill', node);
    var actions = ref('actions', node);
    var act = function (label, cls, icon, evt) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'g-act' + (cls ? ' ' + cls : '');
      b.innerHTML = icon + '<span></span>';
      text(b.lastChild, label);
      b.addEventListener('click', function () { emit(evt, it); });
      actions.appendChild(b);
    };
    switch (status) {
      case 'preparing':
        line = T('st_preparing'); bar.hidden = false; bar.classList.add('is-indeterminate');
        act(T('act_cancel'), '', ICON.x, 'cancel'); break;
      case 'downloading':
        line = Math.round(it.percent || 0) + '%' + (it.speed ? ' · ' + it.speed : '') + (it.eta ? ' · ' + T('st_left', { t: it.eta }) : '');
        bar.hidden = false; fill.style.width = Math.max(0, Math.min(100, it.percent || 0)) + '%';
        bar.setAttribute('role', 'progressbar'); bar.setAttribute('aria-valuemin', '0'); bar.setAttribute('aria-valuemax', '100'); bar.setAttribute('aria-valuenow', String(Math.round(it.percent || 0)));
        act(T('act_cancel'), '', ICON.x, 'cancel'); break;
      case 'processing':
        line = it.processingText || T('st_processing'); bar.hidden = false; bar.classList.add('is-indeterminate'); break;
      case 'done':
        line = T('st_done') + (it.size ? ' · ' + it.size : '');
        act(T('act_show'), 'g-act--link', ICON.folder, 'show-in-folder'); break;
      case 'error':
        line = T('st_error', { e: it.error || T('st_failed') });
        act(T('act_retry'), '', ICON.retry, 'retry'); break;
      case 'cancelled':
        line = T('st_cancelled');
        act(T('act_retry'), '', ICON.retry, 'retry'); break;
    }
    text(ref('line', node), line);
    ref('line', node).title = line;
    return node;
  }

  /* ---------- публичный API ---------- */
  var UI = {
    on: function (name, fn) { handlers[name] = fn; return UI; },

    /** 'popup' | 'window'. Для окна передайте ссылку из контекстного меню. */
    setMode: function (mode, opts) {
      document.body.classList.toggle('is-window', mode === 'window');
      var src = ref('source');
      var url = opts && opts.url;
      show(src, mode === 'window' && !!url);
      if (url) {
        text(ref('sourceUrl'), url.replace(/^https?:\/\/(www\.)?/, ''));
        putFav(ref('sourceFav'), { name: opts.siteName, url: url });
      }
    },

    /** status: 'ok' | 'updating' | 'failed' | 'missing' */
    setYtdlp: function (o) {
      var el = ref('status');
      el.classList.toggle('is-warn', o.status === 'failed' || o.status === 'missing');
      if (o.status === 'ok') { el.innerHTML = '<span class="g-status__dot"></span><span class="g-mono"></span>'; text(el.lastChild, 'yt-dlp ' + (o.version || '')); el.title = T('yt_ok'); }
      else if (o.status === 'updating') { el.innerHTML = ICON.spinSmall + '<span></span>'; text(el.lastChild, T('yt_updating')); el.title = ''; }
      else if (o.status === 'failed') { el.innerHTML = ICON.warnSmall + '<span></span><button class="g-link" style="font-size:11px" type="button"></button>'; text(el.querySelector('span'), T('yt_failed')); text(el.querySelector('button'), T('yt_retry')); el.querySelector('button').onclick = function () { emit('retry-ytdlp'); }; }
      else if (o.status === 'missing') { el.innerHTML = ICON.warnSmall + '<span></span>'; text(el.lastChild, T('helper_missing')); }
    },

    showLoading: function () { setView('loading'); },

    /**
     * media = {
     *   title, author, duration: '12:47', thumbnail: 'https://…',
     *   site: { name: 'YouTube', url: 'https://www.youtube.com/watch?v=…', favicon? },
     *   hasVideo: true,                  // false → только звук (SoundCloud и т.п.), вкладки нет
     *   qualities: ['Макс.','1080p','720p'], // только доступные, в порядке убывания; 'Макс.' — всегда первым
     *   qualityNote: ''                  // напр. «Для этого видео нет 720p и выше — доступно только исходное качество (360p).»
     * }
     */
    showMedia: function (media) {
      state.media = media;
      if (media.hasVideo === false) state.tab = 'audio';
      var thumb = ref('thumb');
      thumb.src = media.thumbnail || '';
      thumb.classList.toggle('is-cover', media.hasVideo === false);
      text(ref('title'), media.title);
      ref('title').title = media.title || '';
      text(ref('meta'), [media.site && media.site.name, media.author].filter(Boolean).join(' · '));
      ref('meta').title = [media.site && media.site.name, media.author, media.duration].filter(Boolean).join(' · ');
      text(ref('dur'), media.duration || ''); show(ref('dur'), !!media.duration);
      putFav(ref('metaFav'), media.site);
      setView('media');
      renderControls();
    },

    /** kind: 'none' (нет медиа / не поддерживается) | 'service' (chrome://, новая вкладка) */
    showEmpty: function (kind) {
      var e = EMPTY[kind] || EMPTY.none;
      ref('emptyIcon').innerHTML = ICON[e.icon];
      text(ref('emptyTitle'), T(e.key + '_title')); text(ref('emptyText'), T(e.key + '_text'));
      show(ref('emptyActions'), e.actions);
      setView('empty');
    },

    /** err = { kind:'private'|'age'|'region'|'other', code:'ERROR: [youtube] …', site:{name,url}, title?, text? } */
    showError: function (err) {
      var e = ERRORS[err.kind] || ERRORS.other;
      var ic = ref('errIcon');
      if (e.icon === '18+') ic.textContent = '18+'; else ic.innerHTML = ICON[e.icon];
      text(ref('errTitle'), err.title || T(e.key + '_title'));
      text(ref('errText'), err.text || T(e.key + '_text'));
      text(ref('errCode'), err.code || '');
      state.lastError = err.code || '';
      show(ref('errRetry'), e.retry);
      text(ref('errSite'), (err.site && err.site.name ? err.site.name + ' ·' : ''));
      text(ref('errUrl'), err.site && err.site.url ? err.site.url.replace(/^https?:\/\/(www\.)?/, '') : '');
      putFav(ref('errFav'), err.site);
      setView('error');
    },

    showHelperMissing: function () {
      UI.setYtdlp({ status: 'missing' });
      setView('helper');
      show(ref('downloads'), false);
    },

    /** Короткий фидбек после нажатия «Скачать» (1,6 с). */
    flashAdded: function () {
      var btn = ref('download');
      btn.classList.add('is-added');
      renderButton();
      clearTimeout(state.addedTimer);
      state.addedTimer = setTimeout(function () { btn.classList.remove('is-added'); renderButton(); }, 1600);
    },

    /**
     * items — новые сверху: [{ id, title, kind:'video'|'audio', format:'MP4 1080p', site:{name,url,favicon?},
     *   status:'preparing'|'downloading'|'processing'|'done'|'error'|'cancelled',
     *   percent, speed:'12,4 МБ/с', eta:'0:18', size:'58,3 МБ', error:'HTTP 403 — сайт отклонил запрос' }]
     * Пустой массив скрывает блок целиком (состояние q).
     */
    setDownloads: function (items) {
      var wrap = ref('downloads'), list = ref('dlList');
      var helperShown = !document.querySelector('[data-view="helper"]').hidden;
      show(wrap, items && items.length > 0 && !helperShown);
      text(ref('dlCount'), items && items.length ? '· ' + items.length : '');
      list.replaceChildren.apply(list, (items || []).map(renderItem));
    },

    /** Точечное обновление одного элемента (прогресс), без перерисовки всего списка. */
    updateDownload: function (item) {
      var old = document.querySelector('.g-item[data-id="' + CSS.escape(String(item.id)) + '"]');
      if (old) old.replaceWith(renderItem(item));
    },

    /** { path:'C:\\Users\\…\\Grabber', isDefault:true } */
    setFolder: function (o) {
      state.folderPath = o.path || '';
      text(ref('pathText'), middleEllipsis(o.path, 26));
      ref('path').title = o.path || '';
      ref('path').setAttribute('aria-label', T('open_folder_aria', { p: o.path || '' }));
      text(ref('tipPath'), o.path || '');
      show(ref('resetFolder'), !o.isDefault);
    },

    /** Восстановить сохранённый выбор (из chrome.storage). */
    setSelection: function (sel) {
      ['tab', 'quality', 'h264', 'audioFormat', 'cover'].forEach(function (k) { if (sel && sel[k] !== undefined) state[k] = sel[k]; });
      if (state.media) renderControls();
    },
    getSelection: selection,
    getLastError: function () { return state.lastError; },
    middleEllipsis: middleEllipsis,
    faviconUrl: faviconUrl
  };

  /* ---------- делегирование кликов ---------- */
  document.addEventListener('click', function (e) {
    var tabBtn = e.target.closest('[data-tab]');
    if (tabBtn && !tabBtn.disabled) {
      state.tab = tabBtn.getAttribute('data-tab');
      renderControls(); emit('selection-change', selection());
      return;
    }
    if (e.target.closest('[data-ref="optSwitch"]')) {
      if (state.tab === 'video') state.h264 = !state.h264; else state.cover = !state.cover;
      renderControls(); emit('selection-change', selection());
      return;
    }
    var a = e.target.closest('[data-action]');
    if (!a) return;
    var action = a.getAttribute('data-action');
    if (action === 'helper-help') e.preventDefault();
    if (action === 'download') {
      if (a.classList.contains('is-added') || a.disabled) return;
      emit('download', selection());
      return;
    }
    if (action === 'copy-error') {
      if (navigator.clipboard && state.lastError) navigator.clipboard.writeText(state.lastError);
    }
    emit(action);
  });

  window.GrabberUI = UI;
})();
