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

[Setup]
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
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Elysia"; Filename: "{app}\Elysia.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar Elysia"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Elysia"; Filename: "{app}\Elysia.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Elysia.exe"; Description: "Abrir Elysia"; Flags: nowait postinstall skipifsilent

; No [UninstallDelete] wildcard: never delete the owner's Vault, media or backups.
