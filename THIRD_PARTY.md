# Créditos e licenças

DuoOmarchy integra software existente; não implementa um compositor, Vulkan ou Proton do zero.

- [Valve Gamescope](https://github.com/ValveSoftware/gamescope): compositor usado na segunda sessão. Base fixada no commit `17baf4abd1ab3353fb705e4d0d023f84e870f7e8` (3.16.25). Licença e avisos upstream preservados em [licenses/Gamescope-LICENSE](licenses/Gamescope-LICENSE).
- [Gamescope PR #1897](https://github.com/ValveSoftware/gamescope/pull/1897): proposta pública que serviu de base à captura seletiva de dispositivos. O patch deste repositório porta esse trabalho e adiciona correções de exclusividade, inicialização, desconexão, saída de emergência, clipboard e backends. Não é código integralmente original do DuoOmarchy e não implica aprovação do upstream.
- [Bubblewrap](https://github.com/containers/bubblewrap): namespaces e montagem do diretório privado.
- [Proton](https://github.com/ValveSoftware/Proton) e [DXVK](https://github.com/doitsujin/dxvk): execução dos jogos e tradução gráfica, instalados pela Steam.
- [Omarchy](https://github.com/basecamp/omarchy), [Hyprland](https://github.com/hyprwm/Hyprland), libinput, systemd e PipeWire: desktop, entrada, supervisão e áudio.

O código de integração original usa MIT. O patch do Gamescope mantém as condições e avisos do código upstream que modifica. Componentes instalados ou compilados conservam suas próprias licenças; o repositório não redistribui a Steam, Proton, jogos nem credenciais.

As capturas documentam uma sessão real autorizada. Overwatch e seus elementos visuais pertencem à Blizzard Entertainment; as imagens não são relicenciadas pela licença MIT do código. Projeto independente, sem afiliação com Blizzard, Valve ou Omarchy.
