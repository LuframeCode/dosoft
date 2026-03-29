# README

Ce dépôt contient le code source de l'outil disponible sur https://dosoft.fr.

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

## Releases
Les versions précompilées (fichiers .exe) sont disponibles dans la section "Releases" du dépôt. Téléchargez la release souhaitée si vous ne voulez pas compiler vous‑même.

## Licence & contribution
Voir le fichier `LICENSE` pour les détails de licence. Les contributions sont les bienvenues via des issues et des pull requests.

---------------------------------

# README (ENG)

This repository contains the source code for the tool available at https://dosoft.fr.

## Description
The source code here allows you to rebuild the application provided on the website. The repository contains everything you need to understand the logic and recreate the tool.

## Building from Source
1. Clone the repository:

```
git clone https://github.com/LuframeCode/dosoft

```
2. Open the project and run the build using pyinstaller:

```
pyinstaller --onefile --windowed main.py

```
1. The compiled binary (.exe) will typically be located in `dist/main.exe` or in the folder specified by the build script.

## Building the Installer
You can build everything using "build.cmd" and inno setup using setup.iss to create an .exe installer.

## Releases
Pre-compiled versions (.exe files) are available in the "Releases" section of the repository. Download the desired release if you don't want to compile it yourself.

## License & Contributions
See the `LICENSE` file for license details. Contributions are welcome via issues and pull requests.

---------------------------------

# README (PTBR)

Este repositório contém o código-fonte da ferramenta disponível em https://dosoft.fr.

## Descrição
O código-fonte aqui permite que você reconstrua o aplicativo fornecido no site. O repositório contém tudo o que você precisa para entender a lógica e recriar a ferramenta.

## Compilando a partir do código-fonte
1. Clone o repositório:

```
git clone https://github.com/LuframeCode/dosoft

```
2. Abra o projeto e execute a compilação usando o PyInstaller:

```
pyinstaller --onefile --windowed main.py

```
3. O binário compilado (.exe) geralmente estará localizado em `dist/main.exe` ou na pasta especificada pelo script de compilação.

## Criando o instalador
Você pode compilar tudo usando o "build.cmd" e o Inno Setup usando o setup.iss para criar um instalador .exe.

## Versões
Versões pré-compiladas (arquivos .exe) estão disponíveis na seção "Versões" do repositório. Baixe a versão desejada se não quiser compilá-la você mesmo.

## Licença e Contribuições
Consulte o arquivo `LICENSE` para obter detalhes da licença. Contribuições são bem-vindas por meio de issues e pull requests.
