# README

This repository contains the source code for the tool available at https://dosoft.fr.

## Description
The source code here allows you to rebuild the application distributed on the website. The repository includes everything needed to understand the logic and recreate the tool.

## Build from source
1. Clone the repository:
    ```
    git clone https://github.com/LuframeCode/dosoft
    ```
2. Open the project and build with PyInstaller:
    ```
    pyinstaller --onefile --windowed main.py
    ```
3. The compiled binary (`.exe`) is typically generated in `dist/main.exe` or in the folder configured by your build script.

## Build the installer
You can build everything through `build.cmd` and Inno Setup using `setup.iss` to create an installer `.exe`.

## macOS version
DOSOFT also runs on macOS 11+ (Apple Silicon and Intel) with the same features as on Windows: Unity/Retro window detection, global keyboard/mouse shortcuts, advanced binds, radial wheel, leader, teams, closing game windows, menu bar icon and Retro Auto-Focus.

### Build the app
```
./build_mac.sh
```
The script creates a Python environment (`.venv-mac`) and produces `dist/Dosoft.app` and `installer_output/Dosoft_macOS_v<version>.dmg`. It needs Python 3.10–3.13 with Tkinter (it uses `uv` when available).

To run from source:
```
pip install -r requirements-mac.txt
python main.py
```

### "Accessibility" permission
On first launch, macOS asks for the **Accessibility** permission (System Settings → Privacy & Security → Accessibility → enable DOSOFT). It is required to read character names, switch windows, catch shortcuts and read Retro notifications. Shortcuts start working as soon as it is granted, without restarting. To keep the permission across new builds, create a local signing certificate once with `./create_mac_cert.sh`: `build_mac.sh` then uses it automatically. Without it, the app is signed "ad hoc" and must be re-authorized after each build (remove the old DOSOFT entry from the Accessibility list, or run `tccutil reset Accessibility fr.dosoft.app`). Another identity can be forced with `DOSOFT_CODESIGN_IDENTITY`.

### Differences from Windows
- Settings are stored in `~/Library/Application Support/Dosoft/settings.json`.
- "Sort Windows taskbar" becomes **Sort windows**: the Dock cannot be reordered, so DOSOFT stacks the windows and the Cmd+Tab switcher in initiative order.
- The **Cmd** key is available as a modifier (shortcuts and advanced bind prefix). `ctrl`, `alt` (Option) and `shift` keep their meaning.
- Retro Auto-Focus reads Notification Center banners (Dofus Retro notifications must be allowed as "Banners"). The v1/v2/v3 engines in Settings also exist: v2 closes the banner once handled.
- The radial wheel also shows on top of a full-screen game window.

## Keyboard/Language customization
- Keyboard layouts are defined through `.yml` files in `resources/keyboards/` (for example: `azerty_fr.yml`, `qwerty_us.yml`).
- UI strings are defined through `.yml` files in `resources/i18n/` (for example: `fr.yml`, `en.yml`, `pt.yml`).
- These options can be changed in **Settings** without changing dependencies or the current build workflow.

## Releases
Prebuilt versions (`.exe` files) are available in the repository's **Releases** section. Download a release if you do not want to build from source.

## License & contribution
See `LICENSE` for licensing details. Contributions are welcome through issues and pull requests.
