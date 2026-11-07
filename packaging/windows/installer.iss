#define MyAppName "InvoiceFlow"
#define MyAppVersion "2.1.0"
[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\InvoiceFlow
DefaultGroupName={#MyAppName}
OutputBaseFilename=InvoiceFlow-Setup
Uninstallable=yes
[Files]
Source: "..\..\dist\InvoiceFlow\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{group}\InvoiceFlow"; Filename: "{app}\InvoiceFlow.exe"
Name: "{autodesktop}\InvoiceFlow"; Filename: "{app}\InvoiceFlow.exe"
