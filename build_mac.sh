#!/usr/bin/env bash
# ============================================================
#  DOSOFT - Compilation macOS (bundle .app + image disque .dmg)
#  Prérequis : macOS 11+, Python 3.10-3.13 avec Tkinter
#  Usage     : ./build_mac.sh
#  Variables : PYTHON=python3.12  DOSOFT_CODESIGN_IDENTITY="Developer ID Application: ..."
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="Dosoft"
VENV=".venv-mac"
VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' version.json)
OUT_DIR="installer_output"
DMG="$OUT_DIR/${APP_NAME}_macOS_v${VERSION}.dmg"

echo
echo " ============================"
echo "  Compilation macOS - DOSOFT v$VERSION"
echo " ============================"
echo

# --- Environnement Python ---
if [ ! -x "$VENV/bin/python" ]; then
    echo "[*] Création de l'environnement $VENV..."
    if command -v uv >/dev/null 2>&1; then
        uv venv --python "${PYTHON:-3.12}" "$VENV"
    else
        "${PYTHON:-python3}" -m venv "$VENV"
    fi
fi
echo "[*] Installation des dépendances..."
if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$VENV/bin/python" -q -r requirements-mac.txt pyinstaller
else
    "$VENV/bin/python" -m pip install -q -r requirements-mac.txt pyinstaller
fi
"$VENV/bin/python" -c "import tkinter" || { echo "[ERREUR] Ce Python n'a pas Tkinter."; exit 1; }

# --- Icônes (.icns pour le bundle) ---
echo "[*] Génération de l'icône..."
mkdir -p build/mac/Dosoft.iconset
"$VENV/bin/python" - <<'EOF'
from PIL import Image
src = Image.open("logo.ico").convert("RGBA")
for size in (16, 32, 64, 128, 256, 512):
    src.resize((size, size), Image.LANCZOS).save(f"build/mac/Dosoft.iconset/icon_{size}x{size}.png")
    src.resize((size * 2, size * 2), Image.LANCZOS).save(f"build/mac/Dosoft.iconset/icon_{size}x{size}@2x.png")
EOF
iconutil -c icns build/mac/Dosoft.iconset -o build/mac/Dosoft.icns

# --- PyInstaller ---
echo "[*] Lancement de PyInstaller..."
rm -rf "dist/$APP_NAME" "dist/$APP_NAME.app"
"$VENV/bin/python" -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller Dosoft-mac.spec

# --- Signature ---
# Signature ad hoc par défaut. macOS rattache l'autorisation « Accessibilité » à la
# signature : avec une signature ad hoc, il faut ré-autoriser DOSOFT après chaque build.
IDENTITY="${DOSOFT_CODESIGN_IDENTITY:--}"
echo "[*] Signature ($IDENTITY)..."
codesign --force --deep --sign "$IDENTITY" "dist/$APP_NAME.app"
codesign --verify --deep "dist/$APP_NAME.app"

# --- Image disque ---
echo "[*] Création du DMG..."
mkdir -p "$OUT_DIR" build/mac/dmg
rm -rf build/mac/dmg/* "$DMG"
cp -R "dist/$APP_NAME.app" build/mac/dmg/
ln -s /Applications build/mac/dmg/Applications
hdiutil create -volname "$APP_NAME" -srcfolder build/mac/dmg -ov -format UDZO "$DMG" >/dev/null

echo
echo "[OK] Application : dist/$APP_NAME.app"
echo "[OK] Installeur  : $DMG"
echo
