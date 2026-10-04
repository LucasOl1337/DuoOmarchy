# DuoOmarchy v0.2.0-alpha.1

4 de outubro de 2026. Duas pessoas passam a trabalhar no mesmo PC com a experiência do Omarchy, cada uma usando seu monitor e kit de entrada.

## Novidades

- **Omarchy completo na segunda estação:** shell oficial, barra, wallpaper, lista completa de apps, menus e atalhos padrão. A segunda pessoa tem workspaces próprios de 1 a 9, mouse, teclado e clipboard independentes.
- **Arquivos e ferramentas compartilhados:** `~/Compartilhado` dá acesso aos arquivos comuns. Codex, Claude Code e Grok CLI reconhecem as autenticações existentes; históricos e processos ficam separados. Navegadores e apps com janela mantêm seus próprios perfis.

- **Mesmos harnesses e configs:** terminais para os CLIs instalados, usando os mesmos binários, modelos, integrações e configurações, com permissões liberadas nos harnesses que oferecem esse modo.
- **Outro Maestri:** a segunda estação abre o app instalado com canvas, perfil, daemon, terminais e sockets próprios. Os presets começam como no principal, sem disputar sua janela ou túnel.

## Melhorias

- **Configuração dos dois kits:** o configurador reúne monitor, teclado, mouse, DPI, controle, áudio, microfone, volume, FPS, resolução, escala, filtro e GPU. O gerenciador permite escolher Jogar ou Trabalhar e abrir os aplicativos da estação.
- **Preferências próprias:** tema, wallpaper e plugins começam com as preferências do desktop principal. Depois, cada estação guarda suas alterações.

## Correções

- **Rede funcionando no desktop privado:** DNS, HTTPS e o indicador de rede continuam acessíveis depois da separação do runtime.
- **Samsung em tela cheia:** a segunda estação cobre a barra externa. Sua barra mostra somente seus próprios workspaces; o supervisor mantém a janela no monitor reservado sem trocar o foco do desktop principal.
- **Inicialização sem queda durante o carregamento:** o controle da estação continua respondendo enquanto o shell abre. Clientes que encerram a conexão cedo não derrubam o serviço.

## Sistemas

- **Runtime privado do compositor:** Gamescope e Aquamarine recebem correções para iniciar o Hyprland aninhado, manter a entrada separada e preservar o clipboard privado. A biblioteca Aquamarine do sistema não é substituída.

## Atualizar e usar

A distribuição continua sendo em código-fonte. Consulte o [guia de instalação](https://github.com/LucasOl1337/DuoOmarchy/blob/v0.2.0-alpha.1/docs/INSTALL.md), incluindo a compilação do Gamescope e do Aquamarine privados.

Na instalação existente `jogarduo`, encerre a estação e rode `python scripts/update-local.py` depois de compilar os runtimes no prefixo correto. Os perfis, dispositivos e preferências existentes são preservados, com backup do código e configuração.

Inicie com `duoomarchy work` ou Trabalhar no gerenciador. Para encerrar, use `duoomarchy off` ou Ctrl+Alt+F12 no teclado secundário.

## Validação e limites

33 testes unitários passaram, assim como compilação Python e sintaxe dos scripts. Os patches de Gamescope e Aquamarine foram compilados e sua aplicação foi conferida nas revisões de origem. Na bancada foram verificados o shell oficial, 228 atalhos carregados, terminal, navegador, arquivos, workspace 9 e clipboard separado. Na estação física Samsung + Logitech G515 + AJAZZ foram conferidos tela cheia 1920×1080, nove workspaces privados, rede e captura exclusiva do segundo kit. O usuário aprovou o visual e o uso da estação nesta sessão. A segunda instância do Maestri foi aberta na bancada com perfil e daemon independentes; os wrappers dos onze harnesses foram verificados.

Codex respondeu a uma chamada real; Claude reconheceu a autenticação e retornou o limite da assinatura; Grok CLI reconheceu o plano SuperGrok Heavy. Quotas dos provedores continuam sendo as da conta compartilhada. A renovação de credenciais montadas somente para leitura pode exigir reabrir a estação após renovar no desktop principal.

Esta versão permanece experimental e foi validada em uma configuração AMD/NVIDIA. Recursos de CPU, GPU, disco, rede e UID são compartilhados; a separação é da experiência de desktop. Não foram repetidos testes de jogos, anti-cheat ou outras GPUs neste release.

[Comparar com a versão anterior](https://github.com/LucasOl1337/DuoOmarchy/compare/v0.1.0-alpha.1...v0.2.0-alpha.1)

![Notas da atualização](https://github.com/LucasOl1337/DuoOmarchy/releases/download/v0.2.0-alpha.1/v0.2.0-alpha.1-card.png)

[Auditoria e cobertura de sessões](https://github.com/LucasOl1337/DuoOmarchy/blob/v0.2.0-alpha.1/docs/releases/v0.2.0-alpha.1/AUDIT.md)
