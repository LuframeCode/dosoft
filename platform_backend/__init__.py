"""Couche d'abstraction plateforme de DOSOFT.

Tout le code spécifique au système (fenêtres, clavier/souris globaux,
notifications, icône de la barre système, instance unique, droits) vit ici.
Le reste de l'application (main.py, gui.py, logic.py, radial_menu.py)
n'appelle que les fonctions exposées par ce module.

- Windows : platform_backend/windows.py (win32 + keyboard + WinRT)
- macOS   : platform_backend/macos.py   (Quartz + Accessibility + AppKit)
"""
import sys

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform.startswith("win")

if IS_MAC:
    from .macos import *  # noqa: F401,F403
    from .macos import __all__  # noqa: F401
else:
    from .windows import *  # noqa: F401,F403
    from .windows import __all__  # noqa: F401
