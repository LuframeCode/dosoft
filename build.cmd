@echo off
:: ============================================================
::  DOSOFT - Script de compilation PyInstaller
::  Prerequis : pip install pyinstaller
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
    --add-data="resources\\i18n;resources\\i18n" ^
    --add-data="resources\\keyboards;resources\\keyboards" ^
    --add-data="logo.ico;." ^
    --hidden-import=customtkinter ^
    --hidden-import=PIL ^
    --hidden-import=pygame ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=win32gui ^
    --hidden-import=win32process ^
    --hidden-import=keyboard ^
    --collect-all=customtkinter ^
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
