<p align="center"><img src="docs/banner-ru.png" alt="Grabber — скачать видео и звук в два клика" width="100%"></p>

# Grabber

Расширение для браузера, которое скачивает видео и звук с YouTube, SoundCloud, VK, TikTok, Twitch, Vimeo и [ещё 1000+ сайтов](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) в два клика. Открыли страницу, нажали значок, выбрали качество — готово.

- **Видео до 4K** или **MP4 в H.264 + AAC**, который открывается в любом плеере и монтажке
- **Звук**: MP3 320, M4A, WAV, FLAC, Opus — с обложкой и тегами
- Правый клик по любой ссылке → **Скачать через Grabber**
- Выбор папки, прогресс, отмена и повтор загрузки
- **Всё работает на вашем компьютере.** Без серверов посередине, аккаунтов, рекламы и слежки
- Загрузчик ([yt-dlp](https://github.com/yt-dlp/yt-dlp)) обновляется сам, поэтому сайты продолжают качаться

Работает на **Windows 10/11** в **Chrome, Edge, Brave и Яндекс.Браузере**.

## Установка

1. Скачайте **`Grabber-Setup.exe`** со страницы [Releases](https://github.com/stylist111/grabber/releases/latest) и запустите.
   Windows может показать синее окно *«Система Windows защитила ваш компьютер»* — у установщика нет платной цифровой подписи. Нажмите **Подробнее → Выполнить в любом случае**.
2. Откройте меню браузера **⋮ → Расширения → Управление расширениями**, включите **Режим разработчика**, нажмите **Загрузить распакованное расширение**, вставьте путь **Ctrl+V** (установщик уже скопировал его) и нажмите **Выбор папки**.
3. Перезапустите браузер и закрепите значок Grabber (значок пазла → булавка).

Инструкция в картинках: [установка](docs/guide/ru/Grabber%20—%201.%20Установка.png) · [как скачать](docs/guide/ru/Grabber%20—%202.%20Как%20скачать.png)

> **Почему через «Режим разработчика», а не из Chrome Web Store?** Магазин не пропускает расширения, которые скачивают с YouTube. Загрузка распакованного расширения — штатная функция Chrome, и загружается ровно тот код, что лежит в этом репозитории.

## Как это устроено

```
расширение (окно, кнопки)  ──native messaging──▶  grabber_host.exe  ──▶  yt-dlp + ffmpeg  ──▶  ваша папка
```

Само по себе расширение скачивать с YouTube не умеет, поэтому у Grabber две части:

- **`extension/`** — расширение Chrome (Manifest V3): окно, список загрузок, настройки.
- **`src/host.py`** — небольшой локальный помощник, собранный в `grabber_host.exe`. Браузер запускает его через [native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging), а он вызывает официальные сборки [yt-dlp](https://github.com/yt-dlp/yt-dlp) и [ffmpeg](https://ffmpeg.org). Общаться с ним может только расширение с ID этого проекта.

Установщик скачивает yt-dlp, ffmpeg и [deno](https://deno.com) (нужен для YouTube) с их официальных страниц на GitHub. Дальше yt-dlp обновляется сам при каждом запуске браузера и раз в 3 часа.

## Безопасность

- **Сборки делаются из этого репозитория.** Каждый релиз собирает [GitHub Actions](.github/workflows/release.yml) из исходников с тегом, с контрольной суммой SHA-256 и подписанным [подтверждением происхождения сборки](https://docs.github.com/ru/actions/security-for-github-actions/using-artifact-attestations). Проверить, что ваш `Grabber-Setup.exe` настоящий:
  ```powershell
  gh attestation verify Grabber-Setup.exe --repo stylist111/grabber
  Get-FileHash Grabber-Setup.exe   # сравните с SHA256SUMS.txt в релизе
  ```
- **Скачивайте только со страницы [Releases](https://github.com/stylist111/grabber/releases)** этого репозитория. Копии из других мест могут быть изменены.
- Помощник принимает только обычные ссылки `http(s)` и передаёт их в yt-dlp как данные (никогда как параметры), не открывает сетевых портов и ничего не хранит, кроме локального лога.
- Нашли уязвимость? См. [SECURITY.md](SECURITY.md).

## Сборка из исходников

Нужно: Windows, Python 3.11+, Node.js (для картинок инструкции), Google Chrome, [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```powershell
python -m pip install pyinstaller pillow numpy
powershell -ExecutionPolicy Bypass -File src\build.ps1              # → dist\Grabber-Setup.exe
powershell -ExecutionPolicy Bypass -File src\build.ps1 -SkipRender  # не перерисовывать картинки в docs\
```

| Путь | Что внутри |
|---|---|
| `extension/` | расширение (окно в `popup/`, тексты интерфейса в `i18n.js`) |
| `src/host.py` | помощник: установка, регистрация в браузерах, загрузки, автообновление yt-dlp |
| `src/setup.iss` | установщик Inno Setup |
| `src/guide.html` | страница с инструкцией, которую открывает установщик |
| `src/readme/` | исходники картинок инструкции и обложек из `docs/` |
| `.github/workflows/release.yml` | сборка релизов |

## Правовое

Grabber — это инструмент. Скачивайте только то, на что у вас есть право, и соблюдайте правила сайтов и авторские права. Авторы не несут ответственности за использование.

## Благодарности

[yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) · [FFmpeg](https://ffmpeg.org) (GPL, скачивается при установке, не входит в сборку) · [Deno](https://deno.com) (MIT) · шрифты [Inter](https://rsms.me/inter/) и [JetBrains Mono](https://www.jetbrains.com/lp/mono/) (SIL OFL 1.1)

## Лицензия

[MIT](LICENSE) © beyond
