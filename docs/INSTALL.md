# Instalação

## 1. Dependências

Use uma sessão Omarchy com Hyprland Lua. O usuário deve ter acesso de leitura aos dispositivos escolhidos em `/dev/input`; o projeto não instala uma regra global que exponha todos os teclados.

Dependências de execução no Arch: `python`, `python-evdev`, `python-vdf`, `tk`, `bubblewrap`, `steam`, `libpulse`, `dbus`, `systemd`, `hyprland`, `quickshell`, `foot`, `xdg-terminal-exec`, `nautilus`, `chromium` (ou o navegador padrão). A Steam requer o repositório multilib do Arch.

Dependências de compilação: `base-devel`, `git`, `meson`, `ninja`, `glslang`, `vulkan-headers`, `vulkan-icd-loader`, `libdrm`, `libx11`, `libxcomposite`, `libxdamage`, `libxext`, `libxfixes`, `libxrender`, `libxres`, `libxtst`, `libxcb`, `libxkbcommon`, `wayland`, `wayland-protocols`, `xorg-xwayland`, `sdl2`, `libdecor`, `libinput`, `pixman`, `pipewire`, `libcap`, `seatd`, `hwdata`, `libdisplay-info`, `libliftoff`, `libei`, `luajit`, `glm`, `stb`, `libavif`, `libjxl`, `libpng`, `lcms2`. Meson informa bibliotecas adicionais exigidas pela versão instalada. Não é feito upgrade automático do sistema.

Instale pelos comandos de pacotes do seu Omarchy (`omarchy pkg add ...`) e confira a saída do Meson. A lista de pacotes pode evoluir com Arch/Omarchy.

## 2. Baixar e compilar

```sh
git clone https://github.com/LucasOl1337/DuoOmarchy.git
cd DuoOmarchy
./scripts/build-gamescope.sh
./scripts/build-work-runtime.sh
python scripts/install.py
```

O build usa Gamescope 3.16.25 no commit fixado no script, com submódulos e o patch deste repositório. Instala em `~/.local/share/duoomarchy/runtime`; não substitui `/usr/bin/gamescope`. `BUILD_JOBS=4` é o padrão para não ocupar todos os núcleos. O script recusa sobrescrever uma árvore de build existente; use `DUOOMARCHY_BUILD_DIR` para outro diretório se precisar repetir.

O instalador não captura dispositivos, não inicia jogos e preserva configurações existentes. Também recusa substituir comandos já existentes chamados `jogarduosim`/`jogarduonao`; revise instalações antigas antes de prosseguir. Ele acrescenta `require("hypr.duoomarchy")` ao `hyprland.lua` e guarda um backup. Leia esse trecho e valide:

```sh
hyprctl reload
hyprctl configerrors
```

## 3. Escolher os kits

```sh
duoomarchy devices
duoomarchy configurar
```

Escolha nome, monitor, workspace, reserva persistente, teclado, mouse, DPI físico e desejado, controle, entradas extras, saída, microfone, volumes, renderização e opções de trabalho de cada pessoa. O primeiro kit é usado para validação contra sobreposição e **nunca é capturado**. Use os caminhos estáveis `/dev/input/by-id/…` sempre que existirem. Os workspaces externos precisam ser distintos e ficar na faixa humana 1–5; 6–11 continuam reservados às bancadas de agentes.

Na estação isolada, a saída e o microfone escolhidos são passados à sessão; “Padrão / escolher no Sonora” herda o mixer do desktop. A estação principal continua sendo uma sessão Omarchy normal, então o Sonora pode ajustar seus aplicativos ao vivo. Para GPUs múltiplas, edite os campos opcionais `gpu` (`vendor:device`, como mostrado por `lspci -nn`) e `gpu_name` (nome Vulkan exato) do segundo jogador em `~/.config/duoomarchy/config.json`.

Se o comando informar falta de permissão num dispositivo, confirme primeiro a ACL de sessão com `getfacl /dev/input/eventN`. Uma regra de udev/ACL específica para os dispositivos do segundo kit deve ser administrada conscientemente pelo dono da máquina. Não use `chmod 666 /dev/input/*`; pertencer ao grupo `input` também dá acesso amplo à digitação de outros dispositivos. O instalador deixa essa decisão explícita.

## 4. Conta Steam separada

```sh
jogarduosim
```

O primeiro início usa um diretório vazio em `~/.local/share/duoomarchy/player2` (modo 0700). A Steam prepara seu cliente nesse diretório e pede o login da segunda pessoa. Instale o jogo e o Proton pela própria Steam. Não copie `loginusers.vdf`, `registry.vdf`, `local.vdf` nem pastas de credenciais da conta principal.

Se quiser copiar arquivos de um jogo já instalado, feche a segunda sessão e use:

```sh
python scripts/import-game.py 2357570
```

Por padrão, exige reflink: Btrfs suporta cópia CoW, que compartilha os blocos iniciais sem compartilhar futuras escritas. Em outro filesystem, `--allow-full-copy` permite uma cópia integral e consome o espaço completo do jogo. O script copia apenas a pasta do aplicativo e seu manifesto, retirando `LastOwner`; não copia credenciais nem o prefixo Proton. A Steam pode baixar runtimes/Proton e verificar os arquivos depois.

## 5. Gerenciador e retomada

```sh
duoomarchy manager
```

O menu também mostra **DuoOmarchy — Gerenciador**. A sessão deve estar ligada para os botões de aplicativos funcionarem. O navegador usa um perfil próprio dentro do segundo home, sem porta de depuração. Fechar Steam pode fechar um jogo aberto; o gerenciador pede confirmação. Encerrar a sessão fecha seus aplicativos e libera teclado/mouse.

Escolha **Trabalhar** para abrir o desktop privado. A quantidade de workspaces internos é configurável entre 1 e 9. Dentro dele: `Super+1…9` troca os workspaces habilitados, `Super+Shift+1…9` move janelas, `Super+Space` abre o launcher, `Super+Return` abre um terminal, `Super+C` copia, `Super+V` cola e `Super+Shift+Return` abre o navegador. Codex e Claude podem ser abertos pelo terminal ou pela lista de apps. O shell, os menus, a lista de apps e os atalhos são os do Omarchy instalado. `Super+K` mostra a lista completa. O tema, wallpaper e plugins são inicializados a partir das preferências existentes; alterações posteriores são privadas. Os arquivos comuns ficam em `~/Compartilhado`; Projects e Documents também apontam para os arquivos comuns quando essas pastas privadas estavam vazias. Codex, Claude e Grok da estação usam o login de terminal já configurado no PC. O navegador precisa de seu próprio login; cookies não são copiados.

Depois do primeiro login, reiniciar a sessão registra o wrapper opcional do Overwatch na Steam privada. Opções de inicialização personalizadas já existentes são preservadas. O alvo padrão é 120 FPS; escolha um limite adequado à GPU compartilhada. O projeto não modifica automaticamente as opções da Steam principal.

## Remover

Execute `jogarduonao`, feche o gerenciador e remova os três links de comandos, a entrada `duoomarchy-manager.desktop`, os arquivos `duoomarchy.service`/`duoomarchy.slice` e a linha `require("hypr.duoomarchy")` do seu Hyprland. Depois execute `systemctl --user daemon-reload` e valide o Hyprland.

Os dados de `player2` contêm login e arquivos pessoais: preserve-os ou remova-os conscientemente. Não há exclusão automática desses dados. Nenhum binário do sistema foi substituído.

## Atualizar uma instalação legada jogarduo

Com a estação encerrada, execute `python scripts/update-local.py`. A atualização preserva Steam, dispositivos e preferências existentes e cria backup do código e configuração do compositor privado. O Gamescope e Aquamarine privados precisam ser compilados com `DUOOMARCHY_DATA="$HOME/.local/share/jogarduo"`. Aquamarine 0.14.0 recebe uma correção de inicialização do backend Wayland, instalada somente em `runtime/lib`; a biblioteca do sistema não é substituída. Dependências de compilação adicionais: CMake e as bibliotecas de desenvolvimento do Hyprland/Aquamarine instaladas no Omarchy.

### Terminais e Maestri

Os harnesses reutilizam os binários instalados e as configs do PC: Codex, Claude Code, Grok, Hermes, Pi, Oh My Pi, OpenCode, Cursor Agent, Devin, jcode e Antigravity, quando presentes. Os wrappers da estação liberam as permissões de execução nos comandos que oferecem esse modo. Pi e jcode mantêm seu modelo nativo e as configurações existentes. Históricos, bancos de sessão e processos continuam na home privada. Os arquivos de configuração e autenticação são montados somente para leitura; o banco de autenticação do Oh My Pi recebe uma cópia inicial privada, porque precisa aceitar escritas do SQLite.

O launcher inclui cada harness disponível e **Maestri**. `maestri-abrir` reutiliza o bundle instalado, com perfil Electron, canvas, daemon, terminais e sockets próprios. A licença existente é acessível, sem compartilhar o perfil do navegador do app. Os presets de agentes são inicializados como no Maestri principal; não são importados canvases, workspaces nem terminais ativos. SSH e remote companion começam desligados, a porta reservada é 7434 e a instalação de CLI em hosts remotos fica desligada. `maestri` no terminal aponta apenas para a CLI da instância desta estação.
