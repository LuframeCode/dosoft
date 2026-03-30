import os
import sys


def resource_path(*parts: str) -> str:
    """
    Retorna o caminho absoluto para um recurso.
    - Em desenvolvimento: relativo ao diretório do script
    - No .exe (--onefile): relativo ao sys._MEIPASS (pasta temporária extraída)
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)