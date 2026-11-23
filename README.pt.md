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

## Versão macOS
O DOSOFT também funciona no macOS 11+ (Apple Silicon e Intel), com as mesmas funcionalidades do Windows: detecção das janelas Unity/Retro, atalhos globais de teclado/mouse, binds avançados, roda radial, líder, times, fechamento das janelas, ícone na barra de menus e Auto-Focus Retro.

### Compilar o aplicativo
```
./build_mac.sh
```
O script cria um ambiente Python (`.venv-mac`) e gera `dist/Dosoft.app` e `installer_output/Dosoft_macOS_v<versão>.dmg`. É necessário Python 3.10–3.13 com Tkinter (usa `uv` se estiver instalado).

Para executar a partir do código-fonte:
```
pip install -r requirements-mac.txt
python main.py
```

### Permissão "Acessibilidade"
Na primeira execução, o macOS pede a permissão de **Acessibilidade** (Ajustes do Sistema → Privacidade e Segurança → Acessibilidade → ativar o DOSOFT). Ela é necessária para ler o nome dos personagens, alternar janelas, capturar atalhos e ler as notificações do Retro. Os atalhos passam a funcionar assim que a permissão é concedida, sem reiniciar. Para manter a permissão entre builds, crie uma vez um certificado de assinatura local com `./create_mac_cert.sh`: o `build_mac.sh` passa a usá-lo automaticamente. Sem ele, o app é assinado "ad hoc" e precisa ser autorizado novamente após cada build (remova a entrada antiga do DOSOFT da lista de Acessibilidade, ou execute `tccutil reset Accessibility fr.dosoft.app`). Outra identidade pode ser imposta com `DOSOFT_CODESIGN_IDENTITY`.

### Diferenças em relação ao Windows
- As configurações ficam em `~/Library/Application Support/Dosoft/settings.json`.
- "Ordenar barra do Windows" passa a ser **Ordenar janelas**: o Dock não pode ser reordenado, então o DOSOFT empilha as janelas e o seletor Cmd+Tab na ordem da iniciativa.
- A tecla **Cmd** está disponível como modificador (atalhos e prefixo dos binds avançados). `ctrl`, `alt` (Option) e `shift` mantêm o mesmo significado.
- O Auto-Focus Retro lê os banners da Central de Notificações (as notificações do Dofus Retro devem estar no modo "Banners"). Os motores v1/v2/v3 das Configurações também existem: o v2 fecha o banner depois de tratado.
- A roda radial também aparece sobre uma janela de jogo em tela cheia.

## Personalização de teclado/idioma
- Os layouts de teclado agora são definidos por arquivos `.yml` em `resources/keyboards/` (ex.: `azerty_fr.yml`, `qwerty_us.yml`).
- Os textos da interface são definidos por arquivos `.yml` em `resources/i18n/` (ex.: `fr.yml`, `en.yml`, `pt.yml`).
- Essas opções podem ser alteradas em **Configurações** sem mudar dependências nem o fluxo atual de build.

## Releases
Versões pré-compiladas (arquivos `.exe`) estão disponíveis na seção **Releases** do repositório. Baixe uma release se não quiser compilar manualmente.

## Licença & contribuição
Veja o arquivo `LICENSE` para detalhes de licença. Contribuições são bem-vindas via issues e pull requests.
