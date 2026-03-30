@echo off
:: ============================================================
::  DOSOFT - Script de compilation PyInstaller
::  Prerequis : pip install pyinstaller pyinstaller-hooks-contrib
:: ============================================================
setlocal enabledelayedexpansion

set APP_NAME=Dosoft
set MAIN_FILE=main.py
set ICON_FILE=logo.ico
set OUT_DIR=dist

echo.
echo  ============================
echo   Compilation PyInstaller - DOSOFT
echo  ============================
echo.

:: --- Nettoyage ---
if exist "%OUT_DIR%" (
    echo [*] Nettoyage du dossier dist...
    rmdir /s /q "%OUT_DIR%"
)
if exist "build" (
    rmdir /s /q "build"
)
if exist "%APP_NAME%.spec" (
    del "%APP_NAME%.spec"
)

:: --- Compilation PyInstaller ---
echo [*] Lancement de PyInstaller...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --uac-admin ^
    --icon="%ICON_FILE%" ^
    --name="%APP_NAME%" ^
    --distpath="%OUT_DIR%" ^
    --add-data="skin;skin" ^
    --add-data="sounds;sounds" ^
    --add-data="logo.ico;." ^
    --add-data="locales;locales" ^
    --collect-all customtkinter ^
    --collect-all pystray ^
    --collect-all pygame ^
    --hidden-import=PIL ^
    --hidden-import=PIL._imagingtk ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=win32gui ^
    --hidden-import=win32process ^
    --hidden-import=win32com ^
    --hidden-import=pythoncom ^
    --hidden-import=pywintypes ^
    --hidden-import=keyboard ^
    --hidden-import=unicodedata ^
    --hidden-import=_overlapped ^
    --hidden-import=requests ^
    --hidden-import=idna ^
    --hidden-import=idna.core ^
    --hidden-import=idna.codec ^
    --hidden-import=charset_normalizer ^
    --hidden-import=certifi ^
    --hidden-import=urllib3 ^
    --hidden-import=yaml ^
    --hidden-import=pystray._win32 ^
    "%MAIN_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] La compilation a echoue. Verifiez les logs ci-dessus.
    pause
    exit /b 1
)

echo.
echo [OK] Compilation reussie !
echo [OK] Executable : %OUT_DIR%\%APP_NAME%.exe
echo.
pause