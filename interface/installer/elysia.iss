; Per-user Windows installer. Private data is deliberately outside {app}.
#ifndef AppSourceDir
  #error AppSourceDir must point to the verified PyInstaller directory
#endif
#ifndef AppOutputDir
  #define AppOutputDir "."
#endif
#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#ifdef AppWebView2Bootstrapper
  #ifndef AppWebView2Sha256
    #error AppWebView2Sha256 is required with AppWebView2Bootstrapper
  #endif
#endif

[Setup]
#ifdef AppIconFile
SetupIconFile={#AppIconFile}
#endif
AppId={{620794CC-B5EE-48C0-998D-045C155A2F87}
AppName=Elysia
AppVersion={#AppVersion}
AppPublisher=Projeto E.L.Y.S.I.A. 2.0
AppPublisherURL=https://github.com/Lorran1690/elysia-2.0
DefaultDirName={localappdata}\Programs\Elysia
DefaultGroupName=Elysia
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#AppOutputDir}
OutputBaseFilename=Elysia-Setup-x64
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Elysia.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
#ifdef AppWebView2Bootstrapper
; Keep this first so solid compression can extract it without unpacking the app.
Source: "{#AppWebView2Bootstrapper}"; DestName: "MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy
#endif
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Elysia"; Filename: "{app}\Elysia.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar Elysia"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Elysia"; Filename: "{app}\Elysia.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Elysia.exe"; Description: "Abrir Elysia"; Flags: nowait postinstall skipifsilent

; No [UninstallDelete] wildcard: never delete the owner's Vault, media or backups.

#ifdef AppWebView2Bootstrapper
[Code]
const
  WebView2ClientKey = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2Version(const RootKey: Integer): Boolean;
var
  Value: String;
  Version: Int64;
begin
  Result := False;
  if RegQueryStringValue(RootKey, WebView2ClientKey, 'pv', Value) then
    if StrToVersion(Trim(Value), Version) then
      Result := Version > 0;
end;

function WebView2Installed(): Boolean;
begin
  { HKLM32 reads WOW6432Node on x64 Windows. Check both user views as well. }
  Result := HasWebView2Version(HKLM32) or HasWebView2Version(HKCU32) or
    HasWebView2Version(HKCU64);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Bootstrapper: String;
  ResultCode: Integer;
  Attempt: Integer;
begin
  Result := '';
  if WebView2Installed() then
  begin
    Log('Microsoft Edge WebView2 Runtime already installed; prerequisite skipped.');
    Exit;
  end;

  try
    Log('WebView2 Runtime absent; preparing the verified Microsoft bootstrapper.');
    ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
    Bootstrapper := ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe');
    { Authenticode is checked in the Windows build. Match those exact bytes here. }
    if CompareText(GetSHA256OfFile(Bootstrapper), '{#AppWebView2Sha256}') <> 0 then
    begin
      Result := 'A verificação de integridade do instalador Microsoft WebView2 falhou. ' +
        'Baixe novamente o instalador da Elysia e tente de novo.';
      Exit;
    end;

    WizardForm.StatusLabel.Caption := 'Preparando o Microsoft Edge WebView2 Runtime...';
    if not Exec(Bootstrapper, '/silent /install', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode) then
    begin
      Result := Format('Não foi possível iniciar a instalação do Microsoft WebView2 (erro %d). ', [ResultCode]) +
        'Verifique sua conexão com a internet e tente novamente.';
      Exit;
    end;
    Log(Format('Microsoft WebView2 bootstrapper exited with code %d.', [ResultCode]));

    { The updater may finish in a helper process. Never start Elysia before detection. }
    for Attempt := 0 to 120 do
    begin
      if WebView2Installed() then
      begin
        if ResultCode = 3010 then
          NeedsRestart := True;
        Log('Microsoft Edge WebView2 Runtime detected after prerequisite installation.');
        Exit;
      end;
      if Attempt < 120 then
        Sleep(250);
    end;
    Result := Format('Não foi possível concluir a instalação do Microsoft WebView2 (código %d). ', [ResultCode]) +
      'É necessário acesso à internet quando o Runtime ainda não está instalado. ' +
      'Verifique a conexão e execute novamente o instalador da Elysia. ' +
      'Você também pode instalar o Runtime em https://developer.microsoft.com/microsoft-edge/webview2/consumer/';
  except
    Result := 'Não foi possível preparar o Microsoft WebView2: ' + GetExceptionMessage + '. ' +
      'Verifique a conexão e tente novamente.';
  end;
end;
#endif
