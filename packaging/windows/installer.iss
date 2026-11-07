#define MyAppName "InvoiceFlow"
#define MyAppPublisher "InvoiceFlow"
#ifndef MyAppVersion
  #define MyAppVersion "3.0.0"
#endif
#define MyAppExeName "InvoiceFlow.exe"
#ifndef DistributionDir
  #define DistributionDir "..\..\dist\InvoiceFlow_3.0.0\InvoiceFlow"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist\InvoiceFlow_3.0.0"
#endif
#ifndef InstallerName
  #define InstallerName "InvoiceFlow_Setup_3.0.0.exe"
#endif

[Setup]
AppId={{B1A1F0A5-5B39-4F2E-8D4B-7E3B0E8A2510}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/
DefaultDirName={autopf}\InvoiceFlow
DefaultGroupName={#MyAppName}
OutputDir={#OutputDir}
OutputBaseFilename={#InstallerName}
SetupIconFile=..\..\assets\brand\invoiceflow-if-logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
Uninstallable=yes
DisableProgramGroupPage=yes
AllowNoIcons=yes
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Windows installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Files]
Source: "{#DistributionDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion restartreplace

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
