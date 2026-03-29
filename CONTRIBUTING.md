# Contributing to Dosoft

**Available in:** [Français](CONTRIBUTING.fr.md) · [Español](CONTRIBUTING.es.md)

Thank you for your interest in Dosoft! This guide explains how to contribute effectively — whether you're reporting a bug, suggesting a feature, or submitting code.

---

## Table of contents

1. [Before you start](#before-you-start)
2. [Report a bug](#report-a-bug)
3. [Suggest a feature](#suggest-a-feature)
4. [Contribute code](#contribute-code)
5. [Commit convention](#commit-convention)
6. [Code style](#code-style)
7. [Local build & testing](#local-build--testing)

---

## Before you start

- Check that a similar issue or pull request doesn't already exist before opening a new one.
- For significant changes, **open an issue first** to discuss your approach. It avoids investing time on something that might not be merged.
- The project targets **Windows only** and **Dofus players** (Unity and Rétro). Contributions outside this scope won't be accepted.
- The project language for code, comments, issues, and PRs is **English**. French is also accepted.

---

## Report a bug

Open an [issue](https://github.com/LuframeCode/dosoft/issues) using the **Bug report** template and include:

- **Dosoft version** (visible in the UI or in `version.json`)
- **Game version**: Unity or Rétro
- **Observed behavior**: what actually happens
- **Expected behavior**: what should happen
- **Steps to reproduce**: as precise as possible
- **Logs or screenshots** if applicable

---

## Suggest a feature

Open an [issue](https://github.com/LuframeCode/dosoft/issues) using the **Feature request** template and describe:

- The **problem** it solves or the need it covers
- The **solution you have in mind**
- Any **alternatives** you considered

---

## Contribute code

### 1. Fork & clone

```bash
git clone https://github.com/<your-username>/dosoft
cd dosoft
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a branch

Name your branch clearly, reflecting what you're working on:

```bash
git checkout -b fix/retro-window-detection
git checkout -b feat/custom-team-shortcut
```

Recommended prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`

### 4. Make your changes

- Follow the existing project structure (see [Code style](#code-style))
- Manually test the modified behavior
- One topic per pull request

### 5. Commit & push

Follow the [commit convention](#commit-convention) below.

```bash
git push origin feat/custom-team-shortcut
```

### 6. Open a Pull Request

- Clear and concise title
- Description explaining **why** this change and **how** it was tested
- Link the related issue with `Closes #42` if applicable

---

## Commit convention

The project follows a convention inspired by [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without behavior change |
| `style` | Formatting, indentation (no logic change) |
| `docs` | Documentation only |
| `chore` | Maintenance tasks (build, deps, config…) |
| `perf` | Performance improvement |
| `revert` | Revert a previous commit |

### Scope (optional)

Refers to the affected module: `gui`, `logic`, `hotkeys`, `config`, `radial`, `build`, `installer`

### Rules

- The **short description** is in English (or French), imperative mood, no capital letter, no trailing period
- Maximum **72 characters** for the first line
- The **body** is optional but recommended for non-trivial changes
- One commit = one logical unit of change

### Examples

```
feat(hotkeys): add MB4/MB5 support per team

fix(logic): fix window detection in Rétro mode

refactor(gui): move display settings into a dedicated panel

docs: update build instructions in README

chore(build): bump version to 1.2.0

fix: prevent crash on startup when settings.json is corrupted
```

---

## Code style

- **Python 3**, compatible with the versions supported by the project's dependencies
- Indentation: **4 spaces** (no tabs)
- Naming: `snake_case` for variables and functions, `PascalCase` for classes
- Comments in **English** or French
- No additional external libraries without prior discussion in an issue
- Keep the project lightweight: it must remain simple to install and run

---

## Local build & testing

Run the app directly with Python for quick testing:

```bash
python main.py
```

To create a full build (`.exe` + installer):

```bash
build.cmd
```

> Requires [PyInstaller](https://pyinstaller.org/) and [Inno Setup 6+](https://jrsoftware.org/isinfo.php) installed on your machine.

---

For any questions, open an issue or visit [dosoft.fr](https://dosoft.fr).
