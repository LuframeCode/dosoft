# README

Este repositório contém o código-fonte da ferramenta disponível em https://dosoft.fr.

## Descrição
O código-fonte presente aqui permite reconstruir a aplicação distribuída no site. O repositório inclui tudo o que é necessário para entender a lógica e recriar a ferramenta.

## Compilar a partir do código-fonte
1. Clone o repositório:
    ```
    git clone https://github.com/LuframeCode/dosoft
    ```
2. Abra o projeto e faça o build com PyInstaller:
    ```
    pyinstaller --onefile --windowed main.py
    ```
3. O binário compilado (`.exe`) normalmente fica em `dist/main.exe` ou na pasta definida pelo seu script de build.

## Compilar o instalador
Você pode compilar tudo via `build.cmd` e Inno Setup usando `setup.iss` para gerar um instalador `.exe`.

## Personalização de teclado/idioma
- Os layouts de teclado agora são definidos por arquivos `.yml` em `resources/keyboards/` (ex.: `azerty_fr.yml`, `qwerty_us.yml`).
- Os textos da interface são definidos por arquivos `.yml` em `resources/i18n/` (ex.: `fr.yml`, `en.yml`, `pt.yml`).
- Essas opções podem ser alteradas em **Configurações** sem mudar dependências nem o fluxo atual de build.

## Releases
Versões pré-compiladas (arquivos `.exe`) estão disponíveis na seção **Releases** do repositório. Baixe uma release se não quiser compilar manualmente.

## Licença & contribuição
Veja o arquivo `LICENSE` para detalhes de licença. Contribuições são bem-vindas via issues e pull requests.
