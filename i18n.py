from __future__ import annotations
import json
import os
from typing import Any

DEFAULT_LANGUAGE = "pt"
DEFAULT_KEYBOARD_LAYOUT = "qwerty"


LANGUAGE_NAMES = {
    "pt": "Português",
    "en": "English",
    "fr": "Français",
}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "pt": {
        "⚙️ Gestionnaire de Binds Avancé DOSOFT": "⚙️ Gerenciador de Atalhos Avançado DOSOFT",
        "⚙️ Paramètres": "⚙️ Configurações",
        "Roue de Focus (Radiale)": "Roda de foco (radial)",
        "Activer la roue": "Ativar roda",
        "Raccourci :": "Atalho:",
        "Aucun": "Nenhum",
        "Fermer & Sauvegarder": "Fechar e salvar",
        "Ouvrir l'interface principale": "Abrir interface principal",
        "Rafraîchir les pages Dofus": "Atualizar janelas do Dofus",
        "🎓 Tuto": "🎓 Tutorial",
        "Contrôler :": "Controlar:",
        "Raccourcis Clavier": "Atalhos do teclado",
        "Options Globales": "Opções globais",
        "🔙 Focus Chef": "🔙 Voltar ao líder",
        "Fermer Team": "Fechar time",
        "Reset Settings": "Redefinir configurações",
        "🔊 Volume Roulette :": "🔊 Roda de volume:",
        "Comptes actifs": "Contas ativas",
        "Rafraîchir": "Atualizar",
        "Trier Barre Windows": "Ordenar janelas do Windows",
        "Bulles": "Dicas",
        "Cacher l'UI": "Ocultar interface",
        "Tutoriel Vidéo": "Tutorial em vídeo",
        "Voulez-vous ouvrir la vidéo de présentation sur YouTube ?": "Deseja abrir o vídeo de apresentação no YouTube?",
        "🚀 Les pages ont été rangées avec succès !": "🚀 As janelas foram organizadas com sucesso!",
        "💥 La team a été fermée !": "💥 O time foi fechado!",
        "Confirmation": "Confirmação",
        "Êtes-vous sûr de vouloir tout réinitialiser ?\n\nToutes vos touches seront perdues.": "Tem certeza de que deseja redefinir tudo?\n\nTodos os seus atalhos serão perdidos.",
        "Fermer la fenêtre": "Fechar janela",
        "Définir comme Chef": "Definir como líder",
        "Changer l'équipe": "Trocar equipe",
        "Descendre": "Mover para baixo",
        "Monter": "Mover para cima",
        "Position exacte": "Posição exata",
        "Effacer le raccourci": "Limpar atalho",
        "Mode :": "Modo:",
        "Préfixe Global :": "Prefixo global:",
        "aucun": "nenhum",
        "💾 Enregistrer les raccourcis": "💾 Salvar atalhos",
        "Target immuable par place. (ex: Ligne 1 focus le 1er de l'initiative)": "Alvo fixo por posição. (ex.: Linha 1 foca o 1º da iniciativa)",
        "Place n°{index}": "Posição nº{index}",
        "Target fixe par pseudo (Même s'ils changent d'ordre)": "Alvo fixo por personagem (mesmo se a ordem mudar)",
        "Aucun personnage connecté détecté.": "Nenhum personagem conectado detectado.",
        "✅ Raccourcis enregistrés avec succès !": "✅ Atalhos salvos com sucesso!",
        "⚠️ Personnage '{identifier}' non trouvé.": "⚠️ Personagem '{identifier}' não encontrado.",
        "Erreur d'initialisation du son : {error}": "Erro ao inicializar o som: {error}",
        "Activer ou désactiver complètement la roue de sélection": "Ativar ou desativar totalmente a roda de seleção",
        "Voir la vidéo de présentation sur YouTube": "Ver o vídeo de apresentação no YouTube",
        "Paramètres du jeu et de la roue": "Configurações do jogo e da roda",
        "Cible du focus (Tout le monde ou équipe spécifique)": "Alvo do foco (todos ou equipe específica)",
        "Focus perso précédent": "Focar personagem anterior",
        "Focus perso suivant": "Focar próximo personagem",
        "Reprendre focus sur le Chef": "Retomar foco no líder",
        "Ne plus m'afficher cet avertissement": "Não mostrar este aviso novamente",
        "Fermer Organizer": "Fechar Organizer",
        "Conserver": "Manter",
        "✅ Organizer fermé avec succès !": "✅ Organizer fechado com sucesso!",
        "Action Impossible": "Ação impossível",
        "Afficher/Cacher": "Mostrar/Ocultar",
        "Quitter": "Sair",
        "Instance détectée": "Instância detectada",
        "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?": "Uma instância do DOSOFT já está em execução!\n\nDeseja fechar a instância antiga para abrir esta?",
        "Language": "Idioma",
        "Keyboard layout": "Layout do teclado",
        "Layout change saved. Hotkeys were converted to the selected keyboard layout.": "Alteração de layout salva. Os atalhos foram convertidos para o layout de teclado selecionado.",
        "Language change saved. Restart the app to apply it everywhere.": "Alteração de idioma salva.",
        "Information": "Informação",
        "Précédent": "Anterior",
        "Suivant": "Próximo",
        "Chef": "Líder",
        "📌 Overlay": "📌 Overlay",
        "🖱️ Spam Clic": "🖱️ Spam clique",
        "Auto-invitation de l'équipe via le chat": "Convite automático do grupo pelo chat",
        "Kill instantané de toutes les fenêtres Dofus actives": "Fechamento instantâneo de todas as janelas ativas do Dofus",
        "Remise à zéro de tous les paramètres et raccourcis": "Redefinir todos os parâmetros e atalhos",
        "Gérer les raccourcis avancés par personnage": "Gerenciar atalhos avançados por personagem",
        "Actualiser la liste des comptes": "Atualizar a lista de contas",
        "Organise les fenêtres dans la barre des tâches": "Organizar janelas na barra de tarefas",
        "Erreur de raccourci : {error}": "Erro de atalho: {error}",
        "Versions :": "Versões:",
        "Afficher UI": "Mostrar UI",
        "Auto-Focus 🔔": "Auto-Focus 🔔",
        "Une mise à jour est requise pour utiliser le logiciel.\n\nVotre version : {current_version}\nVersion disponible : {latest_version}\n\nMise à jour dispo sur Dosoft.fr": "É necessário atualizar para usar o programa.\n\nSua versão: {current_version}\nVersão disponível: {latest_version}\n\nAtualização disponível em Dosoft.fr",
        "Mise à jour requise": "Atualização obrigatória",
        "Impossible de vérifier la version.": "Não foi possível verificar a versão.",
        "Erreur réseau": "Erro de rede",
    },
    "en": {
        "⚙️ Gestionnaire de Binds Avancé DOSOFT": "⚙️ Advanced Bind Manager DOSOFT",
        "⚙️ Paramètres": "⚙️ Settings",
        "Roue de Focus (Radiale)": "Focus Wheel (Radial)",
        "Activer la roue": "Enable wheel",
        "Raccourci :": "Shortcut:",
        "Aucun": "None",
        "Fermer & Sauvegarder": "Close & Save",
        "Ouvrir l'interface principale": "Open main interface",
        "Rafraîchir les pages Dofus": "Refresh Dofus windows",
        "🎓 Tuto": "🎓 Tutorial",
        "Contrôler :": "Control:",
        "Raccourcis Clavier": "Keyboard shortcuts",
        "Options Globales": "Global options",
        "🔙 Focus Chef": "🔙 Back to leader",
        "Fermer Team": "Close team",
        "Reset Settings": "Reset settings",
        "🔊 Volume Roulette :": "🔊 Wheel volume:",
        "Comptes actifs": "Active accounts",
        "Rafraîchir": "Refresh",
        "Trier Barre Windows": "Sort Windows taskbar",
        "Bulles": "Tooltips",
        "Cacher l'UI": "Hide UI",
        "Tutoriel Vidéo": "Video tutorial",
        "Voulez-vous ouvrir la vidéo de présentation sur YouTube ?": "Do you want to open the presentation video on YouTube?",
        "🚀 Les pages ont été rangées avec succès !": "🚀 The windows have been organized successfully!",
        "💥 La team a été fermée !": "💥 The team has been closed!",
        "Confirmation": "Confirmation",
        "Êtes-vous sûr de vouloir tout réinitialiser ?\n\nToutes vos touches seront perdues.": "Are you sure you want to reset everything?\n\nAll your shortcuts will be lost.",
        "Fermer la fenêtre": "Close window",
        "Définir comme Chef": "Set as leader",
        "Changer l'équipe": "Change team",
        "Descendre": "Move down",
        "Monter": "Move up",
        "Position exacte": "Exact position",
        "Effacer le raccourci": "Clear shortcut",
        "Mode :": "Mode:",
        "Préfixe Global :": "Global prefix:",
        "aucun": "none",
        "💾 Enregistrer les raccourcis": "💾 Save shortcuts",
        "Target immuable par place. (ex: Ligne 1 focus le 1er de l'initiative)": "Fixed target by position. (e.g.: Row 1 focuses the 1st in initiative order)",
        "Place n°{index}": "Position #{index}",
        "Target fixe par pseudo (Même s'ils changent d'ordre)": "Fixed target by character name (even if their order changes)",
        "Aucun personnage connecté détecté.": "No connected character detected.",
        "✅ Raccourcis enregistrés avec succès !": "✅ Shortcuts saved successfully!",
        "⚠️ Personnage '{identifier}' non trouvé.": "⚠️ Character '{identifier}' not found.",
        "Erreur d'initialisation du son : {error}": "Sound initialization error: {error}",
        "Activer ou désactiver complètement la roue de sélection": "Enable or completely disable the selection wheel",
        "Voir la vidéo de présentation sur YouTube": "Watch the presentation video on YouTube",
        "Paramètres du jeu et de la roue": "Game and wheel settings",
        "Cible du focus (Tout le monde ou équipe spécifique)": "Focus target (everyone or a specific team)",
        "Focus perso précédent": "Focus previous character",
        "Focus perso suivant": "Focus next character",
        "Reprendre focus sur le Chef": "Return focus to the leader",
        "Ne plus m'afficher cet avertissement": "Do not show this warning again",
        "Fermer Organizer": "Close Organizer",
        "Conserver": "Keep",
        "✅ Organizer fermé avec succès !": "✅ Organizer closed successfully!",
        "Action Impossible": "Action impossible",
        "Afficher/Cacher": "Show/Hide",
        "Quitter": "Exit",
        "Instance détectée": "Instance detected",
        "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?": "A DOSOFT instance is already running!\n\nDo you want to close the old instance to open this one?",
        "Language": "Language",
        "Keyboard layout": "Keyboard layout",
        "Layout change saved. Hotkeys were converted to the selected keyboard layout.": "Layout change saved. Hotkeys were converted to the selected keyboard layout.",
        "Language change saved. Restart the app to apply it everywhere.": "Language change saved. Restart the app to apply it everywhere.",
        "Information": "Information",
        "Précédent": "Previous",
        "Suivant": "Next",
        "Chef": "Leader",
        "📌 Overlay": "📌 Overlay",
        "🖱️ Spam Clic": "🖱️ Click spam",
        "Auto-invitation de l'équipe via le chat": "Automatic team invitation via chat",
        "Kill instantané de toutes les fenêtres Dofus actives": "Instantly close all active Dofus windows",
        "Remise à zéro de tous les paramètres et raccourcis": "Reset all settings and shortcuts",
        "Gérer les raccourcis avancés par personnage": "Manage advanced shortcuts per character",
        "Actualiser la liste des comptes": "Refresh account list",
        "Organise les fenêtres dans la barre des tâches": "Organize windows in the taskbar",
        "Erreur de raccourci : {error}": "Shortcut error: {error}",
        "Versions :": "Versions:",
        "Afficher UI": "Show UI",
        "Auto-Focus 🔔": "Auto-Focus 🔔",
        "Une mise à jour est requise pour utiliser le logiciel.\n\nVotre version : {current_version}\nVersion disponible : {latest_version}\n\nMise à jour dispo sur Dosoft.fr": "An update is required to use the software.\n\nYour version: {current_version}\nAvailable version: {latest_version}\n\nUpdate available on Dosoft.fr",
        "Mise à jour requise": "Update required",
        "Impossible de vérifier la version.": "Unable to check the version.",
        "Erreur réseau": "Network error",
},

"fr": {
    "⚙️ Gestionnaire de Binds Avancé DOSOFT": "⚙️ Gerenciador de Atalhos Avançado DOSOFT",
    "⚙️ Paramètres": "⚙️ Paramètres",
    "Roue de Focus (Radiale)": "Roue de Focus (Radiale)",
    "Activer la roue": "Activer la roue",
    "Raccourci :": "Raccourci :",
    "Aucun": "Aucun",
    "Fermer & Sauvegarder": "Fermer & Sauvegarder",
    "Ouvrir l'interface principale": "Ouvrir l'interface principale",
    "Rafraîchir les pages Dofus": "Rafraîchir les fenêtres Dofus",
    "🎓 Tuto": "🎓 Tuto",
    "Contrôler :": "Contrôler :",
    "Raccourcis Clavier": "Raccourcis Clavier",
    "Options Globales": "Options Globales",
    "🔙 Focus Chef": "🔙 Focus Chef",
    "Fermer Team": "Fermer l'équipe",
    "Reset Settings": "Réinitialiser les paramètres",
    "🔊 Volume Roulette :": "🔊 Volume de la roulette :",
    "Comptes actifs": "Comptes actifs",
    "Rafraîchir": "Rafraîchir",
    "Trier Barre Windows": "Trier la barre Windows",
    "Bulles": "Bulles",
    "Cacher l'UI": "Cacher l'UI",
    "Tutoriel Vidéo": "Tutoriel Vidéo",
    "Voulez-vous ouvrir la vidéo de présentation sur YouTube ?": "Voulez-vous ouvrir la vidéo de présentation sur YouTube ?",
    "🚀 Les pages ont été rangées avec succès !": "🚀 Les fenêtres ont été rangées avec succès !",
    "💥 La team a été fermée !": "💥 L'équipe a été fermée !",
    "Confirmation": "Confirmation",
    "Êtes-vous sûr de vouloir tout réinitialiser ?\n\nToutes vos touches seront perdues.": "Êtes-vous sûr de vouloir tout réinitialiser ?\n\nTous vos raccourcis seront perdus.",
    "Fermer la fenêtre": "Fermer la fenêtre",
    "Définir comme Chef": "Définir comme Chef",
    "Changer l'équipe": "Changer l'équipe",
    "Descendre": "Descendre",
    "Monter": "Monter",
    "Position exacte": "Position exacte",
    "Effacer le raccourci": "Effacer le raccourci",
    "Mode :": "Mode :",
    "Préfixe Global :": "Préfixe Global :",
    "aucun": "aucun",
    "💾 Enregistrer les raccourcis": "💾 Enregistrer les raccourcis",
    "Target immuable par place. (ex: Ligne 1 focus le 1er de l'initiative)": "Cible immuable par position. (ex. : Ligne 1 focus le 1er de l'initiative)",
    "Place n°{index}": "Place n°{index}",
    "Target fixe par pseudo (Même s'ils changent d'ordre)": "Cible fixe par pseudo (même s'ils changent d'ordre)",
    "Aucun personnage connecté détecté.": "Aucun personnage connecté détecté.",
    "✅ Raccourcis enregistrés avec succès !": "✅ Raccourcis enregistrés avec succès !",
    "⚠️ Personnage '{identifier}' non trouvé.": "⚠️ Personnage '{identifier}' non trouvé.",
    "Erreur d'initialisation du son : {error}": "Erreur d'initialisation du son : {error}",
    "Activer ou désactiver complètement la roue de sélection": "Activer ou désactiver complètement la roue de sélection",
    "Voir la vidéo de présentation sur YouTube": "Voir la vidéo de présentation sur YouTube",
    "Paramètres du jeu et de la roue": "Paramètres du jeu et de la roue",
    "Cible du focus (Tout le monde ou équipe spécifique)": "Cible du focus (tout le monde ou équipe spécifique)",
    "Focus perso précédent": "Focus perso précédent",
    "Focus perso suivant": "Focus perso suivant",
    "Reprendre focus sur le Chef": "Reprendre focus sur le Chef",
    "Ne plus m'afficher cet avertissement": "Ne plus m'afficher cet avertissement",
    "Fermer Organizer": "Fermer Organizer",
    "Conserver": "Conserver",
    "✅ Organizer fermé avec succès !": "✅ Organizer fermé avec succès !",
    "Action Impossible": "Action impossible",
    "Afficher/Cacher": "Afficher/Cacher",
    "Quitter": "Quitter",
    "Instance détectée": "Instance détectée",
    "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?": "Une instance de DOSOFT est déjà en cours d'exécution !\n\nVoulez-vous fermer l'ancienne instance pour ouvrir celle-ci ?",
    "Language": "Langue",
    "Keyboard layout": "Disposition du clavier",
    "Layout change saved. Hotkeys were converted to the selected keyboard layout.": "Le changement de disposition a été enregistré. Les raccourcis ont été convertis vers la disposition de clavier sélectionnée.",
    "Language change saved. Restart the app to apply it everywhere.": "Le changement de langue a été enregistré. Redémarrez l'application pour l'appliquer partout.",
    "Information": "Information",
    "Précédent": "Précédent",
    "Suivant": "Suivant",
    "Chef": "Chef",
    "📌 Overlay": "📌 Overlay",
    "🖱️ Spam Clic": "🖱️ Spam clic",
    "Auto-invitation de l'équipe via le chat": "Auto-invitation de l'équipe via le chat",
    "Kill instantané de toutes les fenêtres Dofus actives": "Fermeture instantanée de toutes les fenêtres Dofus actives",
    "Remise à zéro de tous les paramètres et raccourcis": "Remise à zéro de tous les paramètres et raccourcis",
    "Gérer les raccourcis avancés par personnage": "Gérer les raccourcis avancés par personnage",
    "Actualiser la liste des comptes": "Actualiser la liste des comptes",
    "Organise les fenêtres dans la barre des tâches": "Organiser les fenêtres dans la barre des tâches",
    "Erreur de raccourci : {error}": "Erreur de raccourci : {error}",
    "Versions :": "Versions :",
    "Afficher UI": "Afficher l'UI",
    "Auto-Focus 🔔": "Auto-Focus 🔔",
    "Une mise à jour est requise pour utiliser le logiciel.\n\nVotre version : {current_version}\nVersion disponible : {latest_version}\n\nMise à jour dispo sur Dosoft.fr": "Une mise à jour est requise pour utiliser le logiciel.\n\nVotre version : {current_version}\nVersion disponible : {latest_version}\n\nMise à jour disponible sur Dosoft.fr",
    "Mise à jour requise": "Mise à jour requise",
    "Impossible de vérifier la version.": "Impossible de vérifier la version.",
    "Erreur réseau": "Erreur réseau",
},
}


CLICK_SPEED_LABELS = {
    "fast": {"pt": "Rápido", "en": "Fast", "fr": "Rapide"},
    "medium": {"pt": "Médio", "en": "Medium", "fr": "Moyen"},
    "slow": {"pt": "Lento", "en": "Slow", "fr": "Lent"},
}


LEGACY_SPEED_VALUES = {
    "rapide": "fast",
    "moyen": "medium",
    "lent": "slow",
    "rápido": "fast",
    "rapido": "fast",
    "medio": "medium",
    "médio": "medium",
    "lento": "slow",
    "fast": "fast",
    "medium": "medium",
    "slow": "slow",
}


KEYBOARD_LAYOUT_LABELS = {
    "qwerty": {
        "pt": "QWERTY (US/Internacional)",
        "en": "QWERTY (US/International)",
        "fr": "QWERTY (US/International)",
    },
    "azerty": {
        "pt": "AZERTY (Francês)",
        "en": "AZERTY (French)",
        "fr": "AZERTY (Français)",
    },
}


def _normalize_lang(value: Any) -> str:
    lang = str(value or DEFAULT_LANGUAGE).strip().lower()
    return lang if lang in LANGUAGE_NAMES else DEFAULT_LANGUAGE


def _extract_lang(config_or_lang: Any) -> str:
    if hasattr(config_or_lang, "data"):
        return _normalize_lang(config_or_lang.data.get("language", DEFAULT_LANGUAGE))
    if isinstance(config_or_lang, dict):
        return _normalize_lang(config_or_lang.get("language", DEFAULT_LANGUAGE))
    return _normalize_lang(config_or_lang)


def _normalize_label(value: str | None) -> str:
    return (value or "").strip().lower()


def get_language_from_settings(settings_path: str = "settings.json") -> str:
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return _normalize_lang(data.get("language", DEFAULT_LANGUAGE))
        except Exception:
            pass
    return DEFAULT_LANGUAGE


def tr(config_or_lang: Any, text: str, **kwargs) -> str:
    lang = _extract_lang(config_or_lang)
    translated = TRANSLATIONS.get(lang, {}).get(text, text)
    if kwargs:
        try:
            return translated.format(**kwargs)
        except Exception:
            return translated
    return translated


def get_language_options() -> list[str]:
    return [LANGUAGE_NAMES["pt"], LANGUAGE_NAMES["en"], LANGUAGE_NAMES["fr"]]


def language_code_from_label(label: str) -> str:
    normalized = _normalize_label(label)
    for code, name in LANGUAGE_NAMES.items():
        if normalized == name.lower():
            return code
    return DEFAULT_LANGUAGE


def language_label(code: str) -> str:
    return LANGUAGE_NAMES.get(_normalize_lang(code), LANGUAGE_NAMES[DEFAULT_LANGUAGE])


def keyboard_layout_label(lang: str, layout: str) -> str:
    normalized_lang = _normalize_lang(lang)
    normalized_layout = _normalize_label(layout) or DEFAULT_KEYBOARD_LAYOUT
    labels = KEYBOARD_LAYOUT_LABELS.get(normalized_layout, KEYBOARD_LAYOUT_LABELS[DEFAULT_KEYBOARD_LAYOUT])
    return labels.get(normalized_lang, labels["en"])


def get_keyboard_layout_options(lang: str) -> list[str]:
    return [
        keyboard_layout_label(lang, "qwerty"),
        keyboard_layout_label(lang, "azerty"),
    ]


def keyboard_layout_from_label(label: str) -> str:
    normalized = _normalize_label(label)
    for layout, labels in KEYBOARD_LAYOUT_LABELS.items():
        if normalized in {labels["pt"].lower(), labels["en"].lower(), labels["fr"].lower()}:
            return layout
    return DEFAULT_KEYBOARD_LAYOUT