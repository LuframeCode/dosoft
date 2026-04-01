# Contribuer à Dosoft

**Disponible en :** [English](CONTRIBUTING.md) · [Español](CONTRIBUTING.es.md)

Merci de l'intérêt que tu portes à Dosoft ! Ce guide explique comment contribuer efficacement au projet, que ce soit pour signaler un bug, proposer une amélioration ou soumettre du code.

---

## Table des matières

1. [Avant de commencer](#avant-de-commencer)
2. [Signaler un bug](#signaler-un-bug)
3. [Proposer une fonctionnalité](#proposer-une-fonctionnalité)
4. [Contribuer du code](#contribuer-du-code)
5. [Convention de commits](#convention-de-commits)
6. [Style de code](#style-de-code)
7. [Build et test local](#build-et-test-local)

---

## Avant de commencer

- Vérifie qu'une issue ou pull request similaire n'existe pas déjà avant d'en ouvrir une nouvelle.
- Pour les changements importants, **ouvre d'abord une issue** pour discuter de l'approche. Ça évite d'investir du temps sur quelque chose qui ne serait pas mergé.
- Le projet cible **Windows uniquement** et les joueurs de **Dofus** (Unity et Rétro). Les contributions hors de ce périmètre ne seront pas acceptées.
- La langue officielle du projet est l'**anglais**. Le français est également accepté pour les issues, PRs et commentaires.

---

## Signaler un bug

Ouvre une [issue](https://github.com/LuframeCode/dosoft/issues) avec le template **Bug report** et inclus :

- **Version de Dosoft** (visible dans l'interface ou dans `version.json`)
- **Version du jeu** : Unity ou Rétro
- **Comportement observé** : ce qui se passe réellement
- **Comportement attendu** : ce qui devrait se passer
- **Étapes pour reproduire** : le plus précis possible
- **Logs ou captures d'écran** si applicable

---

## Proposer une fonctionnalité

Ouvre une [issue](https://github.com/LuframeCode/dosoft/issues) avec le template **Feature request** et explique :

- Le **problème** que ça résout ou le besoin que ça couvre
- La **solution envisagée**
- Les **alternatives** que tu as considérées

---

## Contribuer du code

### 1. Fork et clone

```bash
git clone https://github.com/<ton-pseudo>/dosoft
cd dosoft
```

### 2. Installe les dépendances

```bash
pip install -r requirements.txt
```

### 3. Crée une branche

Nomme ta branche de façon explicite, en lien avec ce que tu fais :

```bash
git checkout -b fix/detection-fenetres-retro
git checkout -b feat/raccourci-equipe-custom
```

Préfixes recommandés : `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`

### 4. Fais tes modifications

- Respecte la structure existante du projet (voir [Style de code](#style-de-code))
- Teste manuellement le comportement modifié
- Un seul sujet par pull request

### 5. Commite et pousse

Respecte la [convention de commits](#convention-de-commits) ci-dessous.

```bash
git push origin feat/raccourci-equipe-custom
```

### 6. Ouvre une Pull Request

- Titre clair et concis
- Description expliquant **pourquoi** ce changement et **comment** il a été testé
- Relie l'issue correspondante avec `Closes #42` si applicable

---

## Convention de commits

Le projet suit une convention inspirée de [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <description courte>

[corps optionnel]

[footer optionnel]
```

### Types

| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Refactorisation sans changement de comportement |
| `style` | Formatage, indentation (pas de logique modifiée) |
| `docs` | Modification de documentation uniquement |
| `chore` | Tâches de maintenance (build, dépendances, config…) |
| `perf` | Amélioration de performance |
| `revert` | Annulation d'un commit précédent |

### Scope (optionnel)

Indique le module concerné : `gui`, `logic`, `hotkeys`, `config`, `radial`, `build`, `installer`

### Règles

- La **description courte** est en anglais ou français, à l'impératif, sans majuscule, sans point final
- Maximum **72 caractères** pour la première ligne
- Le **corps** est facultatif mais recommandé pour les changements non triviaux
- Un commit = une unité logique de changement

### Exemples

```
feat(hotkeys): add MB4/MB5 support per team

fix(logic): corriger la détection des fenêtres en mode Rétro

refactor(gui): déplacer les paramètres d'affichage dans un panneau dédié

docs: mettre à jour le guide de build dans le README

chore(build): bump version to 1.2.0

fix: prevent crash on startup when settings.json is corrupted
```

---

## Style de code

- **Python 3**, compatible avec les versions supportées par les dépendances du projet
- Indentation : **4 espaces** (pas de tabulations)
- Nommage : `snake_case` pour les variables et fonctions, `PascalCase` pour les classes
- Commentaires en **anglais** ou français
- Pas de librairies externes supplémentaires sans discussion préalable en issue
- Évite les dépendances inutiles : le projet doit rester léger et installable simplement

---

## Build et test local

Lance l'application directement avec Python pour tester :

```bash
python main.py
```

Pour créer un build complet (`.exe` + installateur) :

```bash
build.cmd
```

> Requiert [PyInstaller](https://pyinstaller.org/) et [Inno Setup 6+](https://jrsoftware.org/isinfo.php) installés sur ta machine.

---

Pour toute question, ouvre une issue ou consulte le site [dosoft.fr](https://dosoft.fr).
