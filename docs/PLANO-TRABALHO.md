# Segunda estação pra trabalhar

Pedido de 04/10/2026: escolher monitor e kit, dar à segunda pessoa o controle de um desktop Omarchy com workspaces próprios de 1 a 9, mantendo recursos, arquivos e acessos compartilhados.

## Implementação

1. Preservar o desktop principal e capturar só as interfaces USB do segundo kit, com o Gamescope que já foi validado fisicamente. Uma janela em tela cheia ocupa o monitor escolhido.
2. Dentro dela, iniciar uma sessão completa do Omarchy instalado: Hyprland 0.56, shell oficial Quickshell, menus e lista de aplicativos completa, módulos oficiais de atalhos, wallpaper e tema. Configurações próprias e nove workspaces. Preferências visuais começam iguais às do Lucas e podem ser alteradas separadamente. Mouse, teclado, XWayland, clipboard, D-Bus e runtime pertencem à estação.
3. Iniciar o endpoint de ações dentro do ambiente já criado pelo Hyprland. Os botões do gerenciador precisam abrir apps nela, sem herdar o display do Gamescope.
4. Manter a home privada existente, incluindo Steam. Expor a home original em `~/Compartilhado`; a pasta Projetos compartilhados e as ferramentas instaladas ficam acessíveis sem duplicar arquivos. Não montar login de CLI. Skills e repositórios são compartilhados; navegador mantém perfil separado.
5. Atualizar a instalação local `jogarduo` sem apagar perfis ou exigir reinstalação. Guardar backup dos arquivos alterados, deixar diagnóstico e encerramento disponíveis.
6. Validar configuração, namespace, abertura de aplicativos, workspaces, clipboard e compartilhamento numa bancada com entrada virtual. Ativar a estação física só depois dessas verificações. O teste de conforto dos dois kits continua sendo humano.

## Limites do modelo

A separação é da experiência de desktop. CPU, RAM, GPU, disco, rede e UID são compartilhados. Um navegador com login próprio pode usar a mesma conta/assinatura, mas não se abre o mesmo diretório de perfil nos dois desktops nem se copia cookies. Login de CLI fica fora da estação. Nenhum segredo vai pra logs ou Git.

## Entrega

`duoomarchy work` ou botão Trabalhar; `duoomarchy off` ou Ctrl+Alt+F12 no kit dela para encerrar. Configurar tudo escolhe o monitor e os dispositivos. O desktop principal continua usando seus próprios workspaces; 1 a 9 internos não disputam os workspaces externos.

## Correção de escopo

O Lucas rejeitou o desktop simplificado com barra própria e launcher de cinco aplicativos. A implementação usa agora o shell oficial e os módulos do Omarchy instalado, com a experiência normal de menus e atalhos. A inicialização local evita importar a sessão dela para o systemd do desktop principal. A adaptação é dos lançadores de processos; a interface e os aplicativos vêm do Omarchy.

O Samsung fica em tela cheia, sem barra externa. O supervisor endereça apenas a janela da estação para manter esse estado; a barra privada recebe os dados de seu próprio compositor e mostra somente 1–9. Verificado fisicamente em 04/10/2026 com G515/AJAZZ.
