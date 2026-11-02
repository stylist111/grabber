; Grabber installer (Inno Setup 6). Built by build.ps1 → dist\Grabber-Setup.exe
; Russian only for now (an English build can come later as a separate installer).
#ifndef AppVer
  #define AppVer "0.0.0"
#endif
#ifndef AppDir
  #error Build with src\build.ps1 (passes /DAppDir=<PyInstaller output>)
#endif

[Setup]
AppId={{6B0E2F4A-9C1D-4E57-8A3B-5D2C7F1E9A40}
AppName=Grabber
AppVersion={#AppVer}
AppPublisher=beyond
DefaultDirName={%USERPROFILE}\Grabber
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Grabber-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\app\grabber_host.exe
UninstallDisplayName=Grabber
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; The only thing that can hold our files is the helper the browser started: [Code] stops it itself.
CloseApplications=no
RestartApplications=no

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Messages]
FinishedHeadingLabel=Почти готово!
FinishedLabelNoIcons=Осталось подключить расширение в браузере:%n%n1. Откройте меню браузера ⋮ → Расширения → Управление расширениями.%n2. Включите «Режим разработчика».%n3. Нажмите «Загрузить распакованное расширение», вставьте путь Ctrl+V и нажмите «Выбор папки».%n4. Перезапустите браузер.%n%nПуть к папке расширения уже скопирован в буфер обмена.
FinishedLabel=Осталось подключить расширение в браузере:%n%n1. Откройте меню браузера ⋮ → Расширения → Управление расширениями.%n2. Включите «Режим разработчика».%n3. Нажмите «Загрузить распакованное расширение», вставьте путь Ctrl+V и нажмите «Выбор папки».%n4. Перезапустите браузер.%n%nПуть к папке расширения уже скопирован в буфер обмена.

[Files]
Source: "..\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs
Source: "{#AppDir}\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs
Source: "..\docs\guide\ru\*.png"; DestDir: "{app}\guide"; Flags: ignoreversion
Source: "guide.html"; DestDir: "{app}\guide"; DestName: "Инструкция.html"; Flags: ignoreversion

[Dirs]
Name: "{app}\downloads"

[Run]
; Both guide images on one page, in the default browser (no photo-viewer zooming).
Filename: "{app}\guide\Инструкция.html"; Description: "Открыть инструкцию"; Flags: postinstall shellexec nowait skipifsilent unchecked

[UninstallRun]
Filename: "{app}\app\grabber_host.exe"; Parameters: "--uninstall"; RunOnceId: "unregister"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\guide"
Type: filesandordirs; Name: "{app}\bin"
Type: files; Name: "{app}\host.log"
Type: files; Name: "{app}\install.log"
Type: files; Name: "{app}\app\com.grabber.host.json"

[Code]
// The browser keeps grabber_host.exe running while the extension is on, which locks app\ and bin\.
// Stop it (and the yt-dlp/ffmpeg it started, /T) before installing over it or uninstalling —
// the browser simply starts it again when it's needed.
procedure StopHelper;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM grabber_host.exe', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(500);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopHelper;
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  StopHelper;
  Result := True;
end;

// Check what's already on the PC and download only the missing parts (yt-dlp, ffmpeg, a JS runtime),
// then register the browsers — with no console window: the wizard shows a moving bar meanwhile,
// and a readable message if it fails.
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Проверяю компоненты и скачиваю недостающие (yt-dlp, ffmpeg)…';
    WizardForm.FilenameLabel.Caption := 'В первый раз это может занять пару минут.';
    WizardForm.ProgressGauge.Style := npbstMarquee;
    if not Exec(ExpandConstant('{app}\app\grabber_host.exe'), '--install --setup', '', SW_HIDE, ewWaitUntilTerminated, Code) or (Code <> 0) then
      MsgBox('Не получилось скачать компоненты Grabber.' + #13#10#13#10 +
             'Проверьте интернет и запустите установщик ещё раз.' + #13#10 +
             'Подробности: ' + ExpandConstant('{app}\install.log'), mbError, MB_OK);
    WizardForm.ProgressGauge.Style := npbstNormal;
  end;
end;
