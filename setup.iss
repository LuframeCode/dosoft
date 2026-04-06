; ============================================================
;  DOSOFT - Script Inno Setup
;  Prerequis : Inno Setup 6+
; ============================================================

#define AppName      "Dosoft"
#define AppVersion   "1.1.1"
#define AppPublisher "Dosoft"
#define AppExeName   "Dosoft.exe"
#define SourceDir    "dist"
<<<<<<< Updated upstream
=======
; Renseigne simplement ta version ici à chaque mise à jour :
#define AppVersion   "1.2.2" 
>>>>>>> Stashed changes

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
VersionInfoDescription=Gestionnaire multi-compte Dofus - {#AppName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"
Name: "startmenuicon"; Description: "Créer un raccourci dans le Menu Démarrer"; GroupDescription: "Raccourcis :"

[Files]
; --- Executable principal ---
Source: "{#SourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; --- Ressources ---
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "skin\*"; DestDir: "{app}\skin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "sounds\*"; DestDir: "{app}\sounds"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; --- Raccourcis ---
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: startmenuicon

; CORRECTION ICI : On ajoute "Tasks: startmenuicon" à la fin de la ligne
Name: "{group}\Désinstaller {#AppName}"; Filename: "{uninstallexe}"; Tasks: startmenuicon

[Run]
; --- Lancement après installation ---
Filename: "{app}\{#AppExeName}"; Description: "Lancer {#AppName} maintenant"; Flags: nowait postinstall skipifsilent runascurrentuser

[Code]
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  // Chemin de désinstallation écrit en dur pour éviter les bugs d'accolades avec ExpandConstant
  sUnInstPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1';
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
    // 1. Sauvegarde du settings.json de l'ancienne version
    if FileExists(SettingsPath) then begin
      FileCopy(SettingsPath, BackupPath, False);
    end;

    // Désinstallation silencieuse
    if (IsUpgrade()) then
      UnInstallOldVersion();
  end;

  if (CurStep = ssPostInstall) then begin
    // 2. Restauration du settings.json
    if FileExists(BackupPath) then begin
      FileCopy(BackupPath, SettingsPath, False);
    end;

    // Exclusion Windows Defender
    ExePath := ExpandConstant('{app}\{#AppExeName}');
    Exec('powershell.exe',
      '-ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + ExePath + '''"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;