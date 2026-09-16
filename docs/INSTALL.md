# Instalação

## 1. Dependências

Use uma sessão Omarchy com Hyprland Lua. O usuário deve ter acesso de leitura aos dispositivos escolhidos em `/dev/input`; o projeto não instala uma regra global que exponha todos os teclados.

Dependências de execução no Arch: `python`, `python-evdev`, `python-vdf`, `tk`, `bubblewrap`, `steam`, `libpulse`, `dbus`, `systemd`, `chromium` (opcional, para o botão de navegador). A Steam requer o repositório multilib do Arch.

Dependências de compilação: `base-devel`, `git`, `meson`, `ninja`, `glslang`, `vulkan-headers`, `vulkan-icd-loader`, `libdrm`, `libx11`, `libxcomposite`, `libxdamage`, `libxext`, `libxfixes`, `libxrender`, `libxres`, `libxtst`, `libxcb`, `libxkbcommon`, `wayland`, `wayland-protocols`, `xorg-xwayland`, `sdl2`, `libdecor`, `libinput`, `pixman`, `pipewire`, `libcap`, `seatd`, `hwdata`, `libdisplay-info`, `libliftoff`, `libei`, `luajit`, `glm`, `stb`, `libavif`, `libjxl`, `libpng`, `lcms2`. Meson informa bibliotecas adicionais exigidas pela versão instalada. Não é feito upgrade automático do sistema.

Instale pelos comandos de pacotes do seu Omarchy (`omarchy pkg add ...`) e confira a saída do Meson. A lista de pacotes pode evoluir com Arch/Omarchy.

## 2. Baixar e compilar

```sh
git clone https://github.com/LucasOl1337/DuoOmarchy.git
cd DuoOmarchy
./scripts/build-gamescope.sh
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

Escolha monitor, teclado e mouse de cada pessoa. O primeiro kit é usado para validação contra sobreposição e **nunca é capturado**. Use os caminhos estáveis `/dev/input/by-id/…` sempre que existirem. Os dois monitores devem estar em workspaces humanos 1–5; 6–11 continuam reservados às bancadas de agentes.

Fones podem ficar vazios: uma saída virtual silenciosa é usada até a seleção de um fone real. Para GPUs múltiplas, edite os campos opcionais `gpu` (`vendor:device`, como mostrado por `lspci -nn`) e `gpu_name` (nome Vulkan exato) do segundo jogador em `~/.config/duoomarchy/config.json`.

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

O segundo jogador pode usar Alt+Tab dentro da sessão, sujeito ao comportamento do Gamescope. Não existe um segundo Hyprland nem um desktop completo nessa estação.

Depois do primeiro login, reiniciar a sessão registra o wrapper opcional do Overwatch na Steam privada. Opções de inicialização personalizadas já existentes são preservadas. O alvo padrão é 120 FPS; escolha um limite adequado à GPU compartilhada. O projeto não modifica automaticamente as opções da Steam principal.

## Remover

Execute `jogarduonao`, feche o gerenciador e remova os três links de comandos, a entrada `duoomarchy-manager.desktop`, os arquivos `duoomarchy.service`/`duoomarchy.slice` e a linha `require("hypr.duoomarchy")` do seu Hyprland. Depois execute `systemctl --user daemon-reload` e valide o Hyprland.

Os dados de `player2` contêm login e arquivos pessoais: preserve-os ou remova-os conscientemente. Não há exclusão automática desses dados. Nenhum binário do sistema foi substituído.
