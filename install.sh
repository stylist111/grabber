#!/bin/bash
# Grabber — установка одной командой (macOS 11+, Apple Silicon и Intel). В «Терминале»:
#
#   curl -fsSL https://raw.githubusercontent.com/stylist111/grabber/main/install.sh | bash
#
# Скачивает Grabber-macOS.tar.gz из последнего релиза, сверяет SHA-256 с SHA256SUMS.txt того же релиза,
# раскладывает в ~/Grabber (без прав администратора), докачивает yt-dlp, ffmpeg и deno, регистрирует
# помощник в браузерах и копирует путь к расширению в буфер обмена. Повторный запуск — обновление:
# загрузки, настройки и уже скачанные компоненты остаются.
#
# Для проверки сборки до релиза: GRABBER_BASE=file:///путь/к/dist bash install.sh

set -euo pipefail

# Всё внутри функции: bash читает скрипт из curl целиком и только потом выполняет,
# так что оборванная на середине загрузка ничего не сломает.
main() {
    local base="${GRABBER_BASE:-https://github.com/stylist111/grabber/releases/latest/download}"
    local dir="$HOME/Grabber"
    local pkg="Grabber-macOS.tar.gz"

    say() { printf '%b\n' "$*"; }
    fail() { say "\n\033[31mОшибка: $*\033[0m"; exit 1; }

    [ "$(uname -s)" = Darwin ] || fail 'эта команда — для macOS. Для Windows: https://github.com/stylist111/grabber#windows'

    local was=0
    [ -x "$dir/app/grabber_host" ] && was=1

    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT

    say "\n\033[36mGrabber: скачиваю…\033[0m"
    curl -fL --retry 3 --progress-bar -o "$TMP/$pkg" "$base/$pkg" || fail 'не получилось скачать. Проверьте интернет и запустите команду ещё раз.'
    curl -fsSL --retry 3 -o "$TMP/sums" "$base/SHA256SUMS.txt" || fail 'не получилось скачать контрольную сумму.'

    local expected actual
    expected="$(awk -v f="$pkg" '$2 == f || $2 == "*" f { print tolower($1); exit }' "$TMP/sums")"
    [ -n "$expected" ] || fail 'в релизе нет контрольной суммы.'
    actual="$(shasum -a 256 "$TMP/$pkg" | awk '{ print $1 }')"
    [ "$expected" = "$actual" ] || fail 'файл скачался с ошибкой (не совпала контрольная сумма). Запустите команду ещё раз.'
    say '\033[32mФайл проверен.\033[0m'

    tar -xzf "$TMP/$pkg" -C "$TMP"
    [ -x "$TMP/Grabber/app/grabber_host" ] || fail 'архив повреждён.'

    # Новые app/ и extension/; bin/ (yt-dlp, ffmpeg, deno) и downloads/ остаются как были.
    mkdir -p "$dir"
    rm -rf "$dir/app" "$dir/extension"
    mv "$TMP/Grabber/app" "$TMP/Grabber/extension" "$dir/"

    say '\n\033[36mДокачиваю yt-dlp, ffmpeg и deno (в первый раз — пару минут)…\033[0m'
    "$dir/app/grabber_host" --install </dev/null || fail "не получилось. Пришлите текст выше автору."

    if [ "$was" = 1 ]; then
        say '\n\033[32mГотово, Grabber обновлён. Перезапустите браузер (⌘ + Q).\033[0m\n'
        return
    fi

    say '\n\033[32mПочти готово! Осталось подключить расширение:\033[0m'
    say '  1. В браузере откройте страницу расширений и включите «Режим разработчика».'
    say '  2. Нажмите «Загрузить распакованное расширение» → ⌘ + Shift + G → ⌘ + V → Return → «Выбрать».'
    say '  3. Перезапустите браузер (⌘ + Q) и закрепите значок Grabber (пазл → булавка).'
    say "\n\033[90m  Путь уже в буфере обмена: $dir/extension\033[0m\n"

    # Страница расширений в Chrome, если он есть (остальные браузеры — вручную, адрес в инструкции).
    # В фоне: `open` может ждать ответа браузера сколько угодно, а Терминал не должен висеть.
    if [ -z "${CI:-}" ] && { [ -d "/Applications/Google Chrome.app" ] || [ -d "$HOME/Applications/Google Chrome.app" ]; }; then
        (open -a "Google Chrome" "chrome://extensions/" >/dev/null 2>&1 &)
    fi
}

main "$@"
