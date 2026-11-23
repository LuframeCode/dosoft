"""Auto-Focus Rétro sous macOS.

macOS n'offre pas d'API publique pour lire les notifications des autres
applications (équivalent du UserNotificationListener WinRT). DOSOFT lit donc
les bannières affichées par le Centre de notifications via l'API
d'Accessibilité (même permission que pour le reste de l'application).

Moteurs (sélectionnables dans les Paramètres, comme sous Windows) :
- v1 : lecture toutes les 0,5 s
- v2 : lecture toutes les 0,5 s + fermeture de la bannière Dofus reconnue
- v3 : lecture rapide toutes les 0,3 s, sans fermeture
"""
import threading
import time

import ApplicationServices as AX
from AppKit import NSWorkspace

NC_BUNDLE_IDS = ("com.apple.notificationcenterui",)
CLOSE_WORDS = ("close", "fermer", "fechar", "cerrar", "schließen", "chiudi", "clear", "effacer", "limpar", "borrar")
_MAX_DEPTH = 12


def _attr(el, name):
    try:
        err, val = AX.AXUIElementCopyAttributeValue(el, name, None)
        if err == 0:
            return val
    except Exception:
        pass
    return None


def _nc_pid():
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if (app.bundleIdentifier() or "") in NC_BUNDLE_IDS:
            return app.processIdentifier()
    return None


def _collect_texts(el, statics, others, depth=0):
    """Textes d'une bannière : les AXStaticText (titre, corps) d'abord, puis les
    descriptions agrégées (« App, Titre, Corps ») en dernier recours."""
    if depth > _MAX_DEPTH:
        return
    role = _attr(el, AX.kAXRoleAttribute)
    if role == "AXStaticText":
        val = _attr(el, AX.kAXValueAttribute)
        if val:
            statics.append(str(val))
    else:
        for name in (AX.kAXTitleAttribute, AX.kAXDescriptionAttribute):
            val = _attr(el, name)
            if val and isinstance(val, str):
                others.append(val)
    for child in _attr(el, AX.kAXChildrenAttribute) or []:
        _collect_texts(child, statics, others, depth + 1)


def _find_banners(el, out, depth=0):
    """Repère les groupes « notification » (subrole AXNotificationCenterBanner…)."""
    if depth > _MAX_DEPTH:
        return
    subrole = str(_attr(el, AX.kAXSubroleAttribute) or "")
    if subrole.startswith("AXNotificationCenter") or subrole.startswith("AXNotification"):
        out.append(el)
        return
    for child in _attr(el, AX.kAXChildrenAttribute) or []:
        _find_banners(child, out, depth + 1)


def _signature(texts):
    # Les libellés courts (« maintenant », « il y a 1 min »…) évoluent avec le
    # temps : on les exclut de la signature pour ne pas re-déclencher le focus.
    stable = tuple(t for t in texts if len(t.strip()) > 14)
    return stable or tuple(texts)


def read_banners(pid):
    """Retourne [(signature, textes, élément)] des bannières affichées."""
    app = AX.AXUIElementCreateApplication(pid)
    result = []
    for win in _attr(app, AX.kAXWindowsAttribute) or []:
        banners = []
        _find_banners(win, banners)
        fallback = not banners
        if fallback:
            banners = [win]  # structure inconnue : la fenêtre entière tient lieu de bannière
        win_title = _attr(win, AX.kAXTitleAttribute)
        for b in banners:
            statics, others = [], []
            _collect_texts(b, statics, others)
            texts = [t for t in statics + others if t.strip()]
            if fallback:
                texts = [t for t in texts if t != win_title]
            if texts:
                result.append((_signature(texts), texts, b))
    return result


def close_banner(el):
    try:
        err, actions = AX.AXUIElementCopyActionNames(el, None)
        if err != 0 or not actions:
            return False
        for action in actions:
            low = str(action).lower()
            if any(w in low for w in CLOSE_WORDS):
                return AX.AXUIElementPerformAction(el, action) == 0
    except Exception:
        pass
    return False


def _engine(mode, handle_texts):
    interval = 0.3 if mode == "v3" else 0.5
    cleanup = mode == "v2"
    while True:
        try:
            if not AX.AXIsProcessTrusted():
                time.sleep(5)
                continue
            pid = _nc_pid()
            if not pid:
                time.sleep(3)
                continue
            seen = set()
            first_pass = True
            while True:
                try:
                    banners = read_banners(pid)
                    current = {sig for sig, _, _ in banners}
                    new = [(sig, texts, el) for sig, texts, el in banners if sig not in seen]
                    seen.update(sig for sig, _, _ in new)
                    # Plusieurs « nouvelles » notifications d'un coup = ouverture du
                    # panneau du Centre de notifications (historique) : on ignore.
                    burst = len(new) > 2
                    for sig, texts, el in new:
                        if first_pass or burst:
                            continue
                        try:
                            if handle_texts(texts) and cleanup:
                                threading.Timer(1.0, close_banner, args=(el,)).start()
                        except Exception:
                            pass
                    seen.intersection_update(current)
                    first_pass = False
                except Exception:
                    break  # le Centre de notifications a pu redémarrer : on rescanne
                time.sleep(interval)
        except Exception:
            pass
        time.sleep(3)


def start(mode, handle_texts):
    threading.Thread(target=_engine, args=(mode, handle_texts), name="dosoft-notifications", daemon=True).start()
