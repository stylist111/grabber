# Grabber — установка одной командой (Windows 10/11, PowerShell):
#
#   irm https://raw.githubusercontent.com/stylist111/grabber/main/install.ps1 | iex
#
# Скачивает Grabber-Setup.exe из последнего релиза, сверяет его SHA-256 с SHA256SUMS.txt того же релиза,
# ставит без окон (как обычный установщик, без прав администратора) и открывает страницу расширений
# браузера по умолчанию. Повторный запуск — обновление.
#
# NB: файл сохранён в UTF-8 БЕЗ BOM. `irm | iex` в PowerShell 5.1 спотыкается о BOM в начале текста,
# а кириллицу читает правильно, потому что GitHub отдаёт его с charset=utf-8.

& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'   # без этого скачивание в PowerShell 5.1 идёт в разы медленнее
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $repo = 'stylist111/grabber'
    $base = "https://github.com/$repo/releases/latest/download"
    $uninstKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{6B0E2F4A-9C1D-4E57-8A3B-5D2C7F1E9A40}_is1'

    function Say($text, $color = 'Gray') { Write-Host $text -ForegroundColor $color }

    $wasInstalled = Test-Path $uninstKey
    $tmp = Join-Path $env:TEMP ('grabber-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        Say "`nGrabber: скачиваю установщик..." Cyan
        $exe = Join-Path $tmp 'Grabber-Setup.exe'
        Invoke-WebRequest "$base/Grabber-Setup.exe" -OutFile $exe -UseBasicParsing
        $sums = (Invoke-WebRequest "$base/SHA256SUMS.txt" -UseBasicParsing).Content
        if ($sums -is [byte[]]) { $sums = [Text.Encoding]::UTF8.GetString($sums) }

        $line = ($sums -split "`n") | Where-Object { $_ -match 'Grabber-Setup\.exe' } | Select-Object -First 1
        if (-not $line) { throw 'В релизе нет контрольной суммы установщика.' }
        $expected = ($line.Trim() -split '\s+')[0].ToLower()
        $actual = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
        if ($expected -ne $actual) { throw 'Файл скачался с ошибкой (не совпала контрольная сумма). Запустите команду ещё раз.' }
        Say 'Файл проверен.' Green

        Say 'Устанавливаю и докачиваю yt-dlp и ffmpeg (в первый раз — пару минут)...' Cyan
        $p = Start-Process $exe -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
        if ($p.ExitCode -ne 0) { throw "Установщик завершился с ошибкой (код $($p.ExitCode))." }

        $dir = (Get-ItemProperty $uninstKey -ErrorAction SilentlyContinue).InstallLocation
        if (-not $dir) { $dir = Join-Path $env:USERPROFILE 'Grabber' }
        $dir = $dir.TrimEnd('\')
        if (-not (Test-Path (Join-Path $dir 'app\com.grabber.host.json'))) {
            throw "Не получилось скачать компоненты. Проверьте интернет и запустите команду ещё раз. Подробности: $dir\install.log"
        }
        $ext = Join-Path $dir 'extension'
        try { Set-Clipboard -Value $ext } catch {}
    }
    catch {
        Say "`nОшибка: $($_.Exception.Message)" Red
        return
    }
    finally {
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($wasInstalled) {
        Say "`nГотово, Grabber обновлён. Перезапустите браузер." Green
        return
    }

    Say "`nПочти готово! Осталось подключить расширение:" Green
    Say '  1. На открывшейся странице расширений включите «Режим разработчика».'
    Say '  2. Нажмите «Загрузить распакованное расширение» -> Ctrl+V -> «Выбор папки».'
    Say '  3. Перезапустите браузер и закрепите значок Grabber (пазл -> булавка).'
    Say "`n  Путь уже в буфере обмена: $ext" DarkGray

    # Открываем страницу расширений в браузере по умолчанию (Chrome, Edge, Brave и Яндекс понимают chrome://).
    try {
        $progId = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice').ProgId
        $cmd = (Get-ItemProperty "Registry::HKEY_CLASSES_ROOT\$progId\shell\open\command").'(default)'
        if ($cmd -match '^"([^"]+)"' -or $cmd -match '^(\S+)') {
            $browser = $Matches[1]
            if ((Split-Path $browser -Leaf) -match '^(chrome|msedge|brave|browser)\.exe$') {
                Start-Process $browser 'chrome://extensions/'
            }
        }
    } catch {}
}
