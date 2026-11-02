# Renders the guide images: popup screenshots with demo data (ru/en), then the two-part guide
# for each language at 2x, and the repository banners. Output: docs\guide\<lang>\Grabber — 1. ….png,
# docs\banner-<lang>.png, docs\social-preview.png
# The real Chrome screenshots in real\ are taken separately (cdp-shot.mjs, capture-toolbar.py).
$ErrorActionPreference = 'Stop'
$langs = @('ru')   # English texts exist in readme.html / banner.html — add 'en' here to render them
$here = $PSScriptRoot
$root = Split-Path (Split-Path $here)
$chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
$tmp = Join-Path $env:TEMP ('grabber-readme-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory $tmp | Out-Null

function Stop-Ours { Get-CimInstance Win32_Process -Filter "Name='chrome.exe' OR Name='msedge.exe'" |
    Where-Object { $_.CommandLine -like "*$tmp*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }

# 1. Popup with demo data, one per language
Copy-Item "$root\extension" "$tmp\ext" -Recurse
Copy-Item "$here\demo-stub.js", "$here\thumb.png" "$tmp\ext\popup"
$html = [IO.File]::ReadAllText("$tmp\ext\popup\popup.html")
$html = $html.Replace('<script src="../i18n.js"></script>', '<script src="demo-stub.js"></script><script src="../i18n.js"></script>')
[IO.File]::WriteAllText("$tmp\ext\popup\popup.html", $html, (New-Object Text.UTF8Encoding $false))
$popup = "file:///" + ("$tmp\ext\popup\popup.html" -replace '\\', '/')
foreach ($lang in $langs) {
    $out = "$here\popup-$lang.png"
    $p = Start-Process -FilePath $chrome -PassThru -WindowStyle Hidden -ArgumentList @(
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=3',
        "--user-data-dir=$tmp\profile-$lang", '--allow-file-access-from-files', '--virtual-time-budget=4000',
        '--window-size=380,600', "--screenshot=$out", "$popup`?lang=$lang")
    if (-not $p.WaitForExit(60000)) { Stop-Ours; throw "popup screenshot timed out: $lang" }
    if (-not (Test-Path $out)) { throw "popup screenshot failed: $lang" }
}

# 2. Guide pages, height = content
$names = @{
    ru = @('Grabber — 1. Установка.png', 'Grabber — 2. Как скачать.png')
    en = @('Grabber — 1. Installation.png', 'Grabber — 2. How to download.png')
}
$port = Get-Random -Minimum 20000 -Maximum 40000
Start-Process -FilePath $chrome -WindowStyle Hidden -ArgumentList @(
    '--headless=new', '--hide-scrollbars', "--remote-debugging-port=$port", "--user-data-dir=$tmp\profile-guide",
    '--allow-file-access-from-files', 'about:blank') | Out-Null
try {
    $page = "file:///" + ("$here\readme.html" -replace '\\', '/')
    $banner = "file:///" + ("$here\banner.html" -replace '\\', '/')
    foreach ($lang in $langs) {
        $dir = "$root\docs\guide\$lang"
        New-Item -ItemType Directory -Force $dir | Out-Null
        foreach ($part in 1, 2) {
            node "$here\page-shot.mjs" $port "$page`?part=$part&lang=$lang" (Join-Path $dir $names[$lang][$part - 1]) 1200 2
            if ($LASTEXITCODE) { throw "guide render failed: $lang $part" }
        }
        # README header (2x) …
        node "$here\page-shot.mjs" $port "$banner`?lang=$lang" "$root\docs\banner-$lang.png" 1280 2
        if ($LASTEXITCODE) { throw "banner render failed: $lang" }
    }
    # … and the 1280x640 GitHub social preview (Settings → Social preview)
    node "$here\page-shot.mjs" $port "$banner`?lang=ru" "$root\docs\social-preview.png" 1280 1
    if ($LASTEXITCODE) { throw "social preview render failed" }
} finally {
    Stop-Ours
}
Write-Host "OK: $root\docs"
