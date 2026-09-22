; Per-user installer for the PyIncucyte desktop application.

#define AppName "PyIncucyte"
#define AppPublisher "Brancaccio Lab"
#define AppExeName "PyIncucyte.exe"
#ifndef SourceDir
  #define SourceDir GetEnv("PYINCUCYTE_INSTALL_SOURCE_DIR")
  #if SourceDir == ""
    #define SourceDir "dist\PyIncucyte"
  #endif
#endif
#ifndef InstallerOutputDir
  #define InstallerOutputDir GetEnv("PYINCUCYTE_INSTALL_OUTPUT_DIR")
  #if InstallerOutputDir == ""
    #define InstallerOutputDir "installer"
  #endif
#endif
#ifndef AppVersion
  #define AppVersion GetEnv("PYINCUCYTE_INSTALL_VERSION")
  #if AppVersion == ""
    #define AppVersion GetStringFileInfo(SourceDir + "\" + AppExeName, "FileVersion")
  #endif
#endif
#if AppVersion == ""
  #error "Set PYINCUCYTE_INSTALL_VERSION or build an executable with version metadata."
#endif

[Setup]
AppId={{B0A8FD95-CE51-4BAA-9B11-11A1B7C3D60A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir={#InstallerOutputDir}
OutputBaseFilename=PyIncucyte-{#AppVersion}-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Open {#AppName}"; Flags: nowait postinstall skipifsilent
