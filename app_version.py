import json
import os
import sys

APP_VERSION = "1.2.0"


def _candidate_paths(filename: str) -> list[str]:
    paths = []
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", "")
        if base_dir:
            paths.append(os.path.join(base_dir, filename))
        paths.append(os.path.join(os.path.dirname(sys.executable), filename))
    paths.append(os.path.join(os.path.dirname(__file__), filename))
    return paths


def _read_version_from_json(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except Exception:
        return None
    return None


def get_current_version() -> str:
    for path in _candidate_paths("version.json"):
        if os.path.exists(path):
            version = _read_version_from_json(path)
            if version:
                return version
    return APP_VERSION


CURRENT_VERSION = get_current_version()
APP_TITLE = f"DOSOFT v{CURRENT_VERSION}"