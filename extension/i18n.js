// Grabber UI strings (RU / EN). Language = saved choice, else the browser language.
// Pages: elements with data-i18n="key" get their text, data-i18n-html — markup,
// data-i18n-title / data-i18n-aria — attributes. Scripts call GrabberI18n.t('key', {vars}).
(function (g) {
  'use strict';

  const M = {
    ru: {
      by: 'by beyond',
      menu_title: 'Скачать через Grabber',
      lang_title: 'Switch to English',
      open_downloads: 'Открыть папку загрузок',
      link: 'Ссылка:',
      searching: 'Ищу медиа на странице…',
      searching_sub: 'ищу медиа…',
      what_to_download: 'Что скачать',
      video: 'Видео',
      audio: 'Звук',
      sound_only: 'Только звук',
      sound_only_sub: '— у этого сайта нет видео',
      quality: 'Качество',
      format: 'Формат',
      max: 'Макс.',
      h264_title: 'H.264 + AAC — для монтажа',
      h264_sub: 'MP4 · на YouTube до 1080p',
      h264_warn: 'В H.264 YouTube отдаёт максимум 1080p — файл будет 1080p.',
      cover_title: 'Обложка и теги',
      cover_sub: 'Встроить обложку, название и автора',
      download: 'Скачать',
      added: 'Добавлено',
      added_sub: 'в списке загрузок',
      sub_h264: 'MP4 · H.264 · {q}',
      sub_orig: 'Исходный кодек · {q}',
      sub_cover: ' · с обложкой',
      quality_note: 'Для этого видео нет 720p и выше — доступно только исходное качество ({h}p).',

      empty_none_title: 'На странице нет медиа',
      empty_none_text: 'Grabber не нашёл видео или звук. Возможно, сайт не поддерживается или плеер ещё не загрузился.',
      empty_service_title: 'Здесь нечего скачивать',
      empty_service_text: 'Это служебная страница браузера — chrome:// или новая вкладка. Откройте страницу с видео или треком и нажмите на значок Grabber.',
      rescan: 'Искать снова',
      sites: 'Список сайтов',

      err_private_title: 'Приватное видео',
      err_private_text: 'Автор закрыл доступ. Если доступ у вас есть — войдите в аккаунт на сайте в этом браузере и нажмите «Повторить».',
      err_age_title: 'Видео 18+',
      err_age_text: 'Сайт просит подтвердить возраст. Войдите в аккаунт, где возраст подтверждён, и нажмите «Повторить».',
      err_region_title: 'Недоступно в вашем регионе',
      err_region_text: 'Правообладатель ограничил показ в вашей стране — сайт не отдаёт файл.',
      err_notfound_title: 'Здесь нечего скачать',
      err_notfound_text: 'Похоже, это не страница видео или трека, а лента, библиотека или профиль. Откройте сам ролик или трек — нажмите на его название — и попробуйте снова.',
      err_login_title: 'Нужно войти в аккаунт',
      err_login_text: 'Сайт не пускает без входа. Войдите на сайте в этом браузере и нажмите «Повторить».',
      err_busy_title: 'Сайт просит подождать',
      err_busy_text: 'Слишком много запросов подряд. Подождите пару минут и нажмите «Повторить».',
      err_network_title: 'Нет связи с сайтом',
      err_network_text: 'Не удалось достучаться до сайта. Проверьте интернет (или VPN) и нажмите «Повторить».',
      err_other_title: 'Не получилось получить видео',
      err_other_text: 'Сайт ответил ошибкой. Попробуйте ещё раз — или перезапустите браузер, чтобы подтянулась свежая версия yt-dlp.',
      err_helper_title: 'Помощник не отвечает',
      retry: 'Повторить',
      copy_error: 'Скопировать ошибку',

      helper_title: 'Помощник не установлен',
      helper_text: 'Grabber скачивает через локальный помощник с yt-dlp и ffmpeg. Его нужно поставить один раз.',
      helper_step1: 'Запустите <span class="g-kbd">Grabber-Setup.exe</span>',
      helper_step2: 'Перезапустите браузер',
      recheck: 'Проверить снова',
      helper_help: 'Где взять установщик?',

      downloads: 'Загрузки',
      clear: 'Очистить',
      save_to: 'Сохранять в:',
      reset_folder: 'Вернуть по умолчанию',
      change: 'Изменить',
      open_in_explorer: 'Открыть в проводнике',
      open_folder_aria: 'Открыть папку {p}',

      st_preparing: 'Подготовка…',
      st_left: 'осталось {t}',
      st_processing: 'Обработка ffmpeg: склеиваю видео и звук…',
      st_done: 'Готово',
      st_error: 'Ошибка: {e}',
      st_failed: 'не удалось скачать',
      st_cancelled: 'Отменено',
      act_cancel: 'Отмена',
      act_show: 'Показать в папке',
      act_retry: 'Повторить',

      yt_ok: 'yt-dlp обновлён до последней версии',
      yt_updating: 'Обновляю yt-dlp…',
      yt_failed: 'yt-dlp не обновился ·',
      yt_retry: 'повторить',
      helper_missing: 'Помощник не найден',
      helper_gone: 'Помощник отключился',
      helper_noresp: 'Помощник не отвечает',

      units: ['Б', 'КБ', 'МБ', 'ГБ'],
      per_sec: '/с',
      decimal: ',',

      help_title: 'Как установить помощник',
      help_intro: 'Grabber скачивает через небольшую программу-помощник на вашем компьютере (yt-dlp + ffmpeg). Браузер не умеет ставить её сам, поэтому это нужно сделать один раз.',
      help_where_h: 'Где взять установщик',
      help_where_p: 'Файл <code>Grabber-Setup.exe</code> — его вам прислали вместе с расширением. Последняя версия всегда есть на странице проекта: <a href="https://github.com/stylist111/grabber/releases/latest" target="_blank" rel="noopener">GitHub → Releases</a>.',
      help_install_h: 'Установка',
      help_s1: 'Запустите <code>Grabber-Setup.exe</code>. Если Windows покажет синее окно — нажмите «Подробнее» → «Выполнить в любом случае».',
      help_s2: 'Нажимайте «Далее» и дождитесь «Почти готово!». Компоненты весят около 200 МБ.',
      help_s3: 'Полностью закройте браузер и откройте его снова.',
      help_s4: 'Нажмите на значок Grabber — всё должно работать.',

      upd_title: 'Вышла новая версия Grabber {v}',
      upd_text: 'Запустите новый установщик — настройки сохранятся.',
      upd_get: 'Скачать',
      upd_later: 'Позже',
    },

    en: {
      by: 'by beyond',
      menu_title: 'Download with Grabber',
      lang_title: 'Переключить на русский',
      open_downloads: 'Open downloads folder',
      link: 'Link:',
      searching: 'Looking for media on this page…',
      searching_sub: 'looking for media…',
      what_to_download: 'What to download',
      video: 'Video',
      audio: 'Audio',
      sound_only: 'Audio only',
      sound_only_sub: '— this site has no video',
      quality: 'Quality',
      format: 'Format',
      max: 'Max',
      h264_title: 'H.264 + AAC — for editing',
      h264_sub: 'MP4 · up to 1080p on YouTube',
      h264_warn: 'YouTube serves H.264 up to 1080p — the file will be 1080p.',
      cover_title: 'Cover & tags',
      cover_sub: 'Embed cover art, title and artist',
      download: 'Download',
      added: 'Added',
      added_sub: 'to the downloads list',
      sub_h264: 'MP4 · H.264 · {q}',
      sub_orig: 'Original codec · {q}',
      sub_cover: ' · with cover',
      quality_note: 'This video has no 720p or higher — only the original quality ({h}p) is available.',

      empty_none_title: 'No media on this page',
      empty_none_text: 'Grabber found no video or audio. The site may be unsupported, or the player hasn’t loaded yet.',
      empty_service_title: 'Nothing to download here',
      empty_service_text: 'This is a browser page — chrome:// or a new tab. Open a page with a video or track and click the Grabber icon.',
      rescan: 'Search again',
      sites: 'Supported sites',

      err_private_title: 'Private video',
      err_private_text: 'The author restricted access. If you have access, sign in to the site in this browser and click “Retry”.',
      err_age_title: 'Age-restricted video',
      err_age_text: 'The site asks to confirm your age. Sign in to an account with a confirmed age and click “Retry”.',
      err_region_title: 'Not available in your region',
      err_region_text: 'The rights holder blocked it in your country — the site won’t serve the file.',
      err_notfound_title: 'Nothing to download here',
      err_notfound_text: 'This looks like a feed, library or profile rather than a video or track page. Open the video or track itself — click its title — and try again.',
      err_login_title: 'Sign-in required',
      err_login_text: 'The site won’t let you in without an account. Sign in to the site in this browser and click “Retry”.',
      err_busy_title: 'The site asks you to wait',
      err_busy_text: 'Too many requests in a row. Wait a couple of minutes and click “Retry”.',
      err_network_title: 'Can’t reach the site',
      err_network_text: 'The site didn’t respond. Check your internet (or VPN) and click “Retry”.',
      err_other_title: 'Couldn’t get the video',
      err_other_text: 'The site returned an error. Try again — or restart the browser to pull the latest yt-dlp.',
      err_helper_title: 'Helper is not responding',
      retry: 'Retry',
      copy_error: 'Copy error',

      helper_title: 'Helper is not installed',
      helper_text: 'Grabber downloads through a local helper with yt-dlp and ffmpeg. It needs to be installed once.',
      helper_step1: 'Run <span class="g-kbd">Grabber-Setup.exe</span>',
      helper_step2: 'Restart the browser',
      recheck: 'Check again',
      helper_help: 'Where do I get the installer?',

      downloads: 'Downloads',
      clear: 'Clear',
      save_to: 'Save to:',
      reset_folder: 'Reset to default',
      change: 'Change',
      open_in_explorer: 'Open in Explorer',
      open_folder_aria: 'Open folder {p}',

      st_preparing: 'Preparing…',
      st_left: '{t} left',
      st_processing: 'ffmpeg: merging video and audio…',
      st_done: 'Done',
      st_error: 'Error: {e}',
      st_failed: 'download failed',
      st_cancelled: 'Cancelled',
      act_cancel: 'Cancel',
      act_show: 'Show in folder',
      act_retry: 'Retry',

      yt_ok: 'yt-dlp is up to date',
      yt_updating: 'Updating yt-dlp…',
      yt_failed: 'yt-dlp update failed ·',
      yt_retry: 'retry',
      helper_missing: 'Helper not found',
      helper_gone: 'Helper disconnected',
      helper_noresp: 'Helper is not responding',

      units: ['B', 'KB', 'MB', 'GB'],
      per_sec: '/s',
      decimal: '.',

      help_title: 'How to install the helper',
      help_intro: 'Grabber downloads through a small helper program on your computer (yt-dlp + ffmpeg). Browsers can’t install it themselves, so it has to be done once.',
      help_where_h: 'Where to get the installer',
      help_where_p: 'The <code>Grabber-Setup.exe</code> file — you got it together with the extension. The latest version is always on the project page: <a href="https://github.com/stylist111/grabber/releases/latest" target="_blank" rel="noopener">GitHub → Releases</a>.',
      help_install_h: 'Installation',
      help_s1: 'Run <code>Grabber-Setup.exe</code>. If Windows shows a blue window, click “More info” → “Run anyway”.',
      help_s2: 'Click “Next” and wait for “Almost done!”. The components are about 200 MB.',
      help_s3: 'Close the browser completely and open it again.',
      help_s4: 'Click the Grabber icon — everything should work.',

      upd_title: 'Grabber {v} is out',
      upd_text: 'Run the new installer — your settings stay.',
      upd_get: 'Download',
      upd_later: 'Later',
    },
  };

  // The first release is Russian only. The English strings above are kept ready:
  // set FORCED = null to bring back automatic choice (+ the RU/EN toggle and _locales/en).
  const FORCED = 'ru';
  const KEY = 'grabber-lang';
  function detect() {
    if (FORCED) return FORCED;
    let saved = null;
    try { saved = g.localStorage && g.localStorage.getItem(KEY); } catch (e) { /* service worker: no localStorage */ }
    if (saved === 'ru' || saved === 'en') return saved;
    const nav = (g.navigator && g.navigator.language || 'en').toLowerCase();
    return nav.startsWith('ru') || nav.startsWith('uk') || nav.startsWith('be') ? 'ru' : 'en';
  }

  let lang = detect();

  function t(key, vars) {
    let s = M[lang][key];
    if (s === undefined) s = M.en[key];
    if (s === undefined) return key;
    if (vars && typeof s === 'string') s = s.replace(/\{(\w+)\}/g, (_, n) => (vars[n] == null ? '' : vars[n]));
    return s;
  }

  function apply(root) {
    root = root || document;
    root.documentElement && (root.documentElement.lang = lang);
    root.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    root.querySelectorAll('[data-i18n-html]').forEach((el) => { el.innerHTML = t(el.dataset.i18nHtml); });
    root.querySelectorAll('[data-i18n-title]').forEach((el) => { el.title = t(el.dataset.i18nTitle); });
    root.querySelectorAll('[data-i18n-aria]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  }

  function set(l) {
    lang = l === 'ru' ? 'ru' : 'en';
    try { g.localStorage.setItem(KEY, lang); } catch (e) { /* ignore */ }
    if (g.chrome && chrome.storage) chrome.storage.local.set({ lang });
  }

  // Service worker: the saved choice lives in chrome.storage (no localStorage there).
  async function load() {
    if (!(g.chrome && chrome.storage)) return lang;
    const { lang: l } = await chrome.storage.local.get('lang');
    if (!FORCED && (l === 'ru' || l === 'en')) lang = l;
    return lang;
  }

  g.GrabberI18n = { t, apply, set, load, get lang() { return lang; } };
})(self);
