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
2. Ouvrir le projet et lancer le build via pyinstaller:
    ```
    pyinstaller --onefile --windowed main.py
    ```
3. Le binaire compilé (.exe) se trouvera typiquement dans `dist/main.exe` ou dans le dossier indiqué par le script de build.

## Construire l'installateur
Vous pouvez tout build via "build.cmd" et inno setup en utilisant setup.iss pour créer un installateur .exe.


## Personnalisation clavier/langue
- Les dispositions clavier sont maintenant définies via des fichiers `.yml` dans `resources/keyboards/` (ex: `azerty_fr.yml`, `qwerty_us.yml`).
- Les chaînes d'interface sont définies via des fichiers `.yml` dans `resources/i18n/` (ex: `fr.yml`, `en.yml`, `pt.yml`).
- Ces options sont modifiables dans **Paramètres** sans changer les dépendances ni la méthode de build actuelle.

## Releases
Les versions précompilées (fichiers .exe) sont disponibles dans la section "Releases" du dépôt. Téléchargez la release souhaitée si vous ne voulez pas compiler vous‑même.

## Licence & contribution
Voir le fichier `LICENSE` pour les détails de licence. Les contributions sont les bienvenues via des issues et des pull requests.
