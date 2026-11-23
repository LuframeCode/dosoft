# README

Ce dépôt contient le code source de l'outil disponible sur https://dosoft.fr.

## Langues disponibles
- Français: `README.md`
- English: `README.en.md`
- Português: `README.pt.md`

## Description
Le code source présent ici permet de reconstruire l'application fournie sur le site. Le dépôt contient tout le nécessaire pour comprendre la logique et recréer l'outil.

## Construire depuis les sources
1. Cloner le dépôt :
    ```
    git clone https://github.com/LuframeCode/dosoft
    ```
2. Ouvrir le projet et lancer le build via le script recommandé:
    ```
    build.cmd
    ```
3. Le binaire compilé (.exe) se trouvera typiquement dans `dist/main.exe` ou dans le dossier indiqué par le script de build.

## Construire l'installateur
Vous pouvez tout build via "build.cmd" et inno setup en utilisant setup.iss pour créer un installateur .exe.


## Version macOS
DOSOFT fonctionne aussi sur macOS 11+ (Apple Silicon et Intel), avec les mêmes fonctionnalités que sous Windows : détection des pages Unity/Rétro, raccourcis clavier/souris globaux, binds avancés, roue radiale, chef, teams, fermeture des pages, icône dans la barre des menus et Auto-Focus Rétro.

### Construire l'application
```
./build_mac.sh
```
Le script crée un environnement Python (`.venv-mac`), puis produit `dist/Dosoft.app` et `installer_output/Dosoft_macOS_v<version>.dmg`. Il faut un Python 3.10–3.13 avec Tkinter (le script utilise `uv` s'il est installé).

Pour lancer depuis les sources :
```
pip install -r requirements-mac.txt
python main.py
```

### Autorisation « Accessibilité »
Au premier lancement, macOS demande l'autorisation **Accessibilité** (Réglages Système → Confidentialité et sécurité → Accessibilité → cocher DOSOFT). Elle est nécessaire pour lire le nom des personnages, changer de fenêtre, capter les raccourcis et lire les notifications Rétro. Les raccourcis s'activent dès que l'autorisation est accordée, sans redémarrage. Pour que l'autorisation survive aux nouveaux builds, créez une fois un certificat de signature local avec `./create_mac_cert.sh` : `build_mac.sh` l'utilise ensuite automatiquement. Sans lui, l'app est signée « ad hoc » et doit être ré-autorisée après chaque build (retirer l'ancienne entrée DOSOFT de la liste Accessibilité, ou `tccutil reset Accessibility fr.dosoft.app`). Une autre identité peut être imposée via `DOSOFT_CODESIGN_IDENTITY`.

### Différences avec Windows
- Les réglages sont stockés dans `~/Library/Application Support/Dosoft/settings.json`.
- « Trier Barre Windows » devient **Trier les fenêtres** : le Dock ne peut pas être réordonné, DOSOFT empile donc les fenêtres et le sélecteur Cmd+Tab dans l'ordre de l'initiative.
- La touche **Cmd** est disponible comme modificateur (raccourcis et préfixe des binds avancés). `ctrl`, `alt` (Option) et `shift` gardent leur sens.
- L'Auto-Focus Rétro lit les bannières du Centre de notifications (les notifications de Dofus Retro doivent être autorisées en mode « Bannières »). Les moteurs v1/v2/v3 des Paramètres existent aussi : v2 ferme la bannière une fois traitée.
- La roue radiale s'affiche aussi au-dessus d'une fenêtre de jeu en plein écran.

## Personnalisation clavier/langue
- Les dispositions clavier sont maintenant définies via des fichiers `.yml` dans `resources/keyboards/` (ex: `azerty_fr.yml`, `qwerty_us.yml`).
- Les chaînes d'interface sont définies via des fichiers `.yml` dans `resources/i18n/` (ex: `fr.yml`, `en.yml`, `pt.yml`).
- Ces options sont modifiables dans **Paramètres** sans changer les dépendances ni la méthode de build actuelle.

## Releases
Les versions précompilées (fichiers .exe) sont disponibles dans la section "Releases" du dépôt. Téléchargez la release souhaitée si vous ne voulez pas compiler vous‑même.

## Licence & contribution
Voir le fichier `LICENSE` pour les détails de licence. Les contributions sont les bienvenues via des issues et des pull requests.
