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

## Keyboard/Language customization
- Keyboard layouts are defined through `.yml` files in `resources/keyboards/` (for example: `azerty_fr.yml`, `qwerty_us.yml`).
- UI strings are defined through `.yml` files in `resources/i18n/` (for example: `fr.yml`, `en.yml`, `pt.yml`).
- These options can be changed in **Settings** without changing dependencies or the current build workflow.

## Releases
Prebuilt versions (`.exe` files) are available in the repository's **Releases** section. Download a release if you do not want to build from source.

## License & contribution
See `LICENSE` for licensing details. Contributions are welcome through issues and pull requests.
