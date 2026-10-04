# Auditoria v0.2.0-alpha.1

Base oficial: `v0.1.0-alpha.1`, revisão `44f6cba`. Candidata: tag `v0.2.0-alpha.1` na branch `main`. A base é ancestral da candidata. Nenhum PR estava aberto durante a integração. As alterações pendentes relacionadas ao DuoOmarchy foram integradas; perfis locais, credenciais, sessões e binários compilados ficaram fora do commit.

## Entregas e evidências

| Resultado | Evidência | Situação |
| --- | --- | --- |
| Desktop completo, apps e nove workspaces próprios | Hyprland aninhado com shell oficial, 228 bindings, captura visual na bancada, validação no Samsung | Integrado e aplicado localmente |
| Kits, DPI, GPU, áudio e modos no configurador | Código de configurador/gerenciador, testes dos contratos de configuração e captura exclusiva do segundo kit | Integrado; jogos não foram retestados |
| Janela em tela cheia sem mudar foco principal | Teste de endereço específico e estado físico 1920×1080, fullscreen interno/cliente 2 | Integrado e aplicado localmente |
| Rede e CLI autenticados | DNS/HTTPS no namespace real; Codex respondeu OK, Claude autenticado retornou quota, Grok reconheceu SuperGrok Heavy | Integrado e aplicado localmente |
| Mesmos binários/configs e bypass nos harnesses | Wrappers, mounts e launchers; ajuda dos onze comandos sem flag inválida, teste de argumentos e ambiente | Integrado; não foram feitas chamadas pagas de todos os provedores |
| Maestri separado | App aberto em bancada, canvas próprio criado, licença ativa, perfil/socket próprios; hash das preferências e PIDs principais preservados | Integrado; SSH e remote companion começam desligados |
| Runtime privado de Gamescope/Aquamarine | Compilação local, aplicação dos patches nas revisões fixadas e smoke do compositor | Integrado; biblioteca do sistema preservada |

## Cobertura de agentes e sessões

| Harness | Fonte consultada | Cobertura e atribuição |
| --- | --- | --- |
| Codex | Histórico local e metadados de threads associados ao repositório | Sessão atual implementou desktop completo, fullscreen, DNS, compartilhamento de CLI/configs, wrappers e Maestri independente, além de validar e publicar. Dois IDs relacionados constavam do índice; não foi inferida autoria adicional apenas por essa associação. |
| Claude | `~/.claude/history.jsonl` | Nenhuma entrada relacionada encontrada no índice consultado. |
| Hermes | Índice de sessões local | Nenhuma sessão relacionada encontrada no índice consultado. |
| Grok | Índice de sessões ativas | Repositório ausente; histórico completo não estava indexado nessa fonte. |
| Pi | Diretórios de sessões por projeto | Nenhum diretório relacionado encontrado. |
| Orca | Fontes locais disponíveis | Metadados indisponíveis; contribuição não atribuída. |

O configurador, parte do gerenciador e a primeira adaptação do modo trabalho já estavam pendentes no início da rodada. Foram revisados e integrados porque pertencem ao objetivo; o agente de origem não foi identificado. Autoria de commit não foi tratada como prova do harness usado.

## Validação

- `python3 -m unittest discover -s tests -q`: 33 testes aprovados.
- `python3 -m compileall -q src scripts`: aprovado.
- `bash -n scripts/build-gamescope.sh scripts/build-work-runtime.sh`: aprovado.
- `git diff --check`: aprovado.
- Gamescope na revisão `17baf4abd1ab3353fb705e4d0d023f84e870f7e8`; Aquamarine 0.14.0. Builds e aplicação dos patches conferidos localmente.
- Bancada independente com GPU: shell, apps, clipboard, workspace 9, terminais e Maestri. A bancada de validação foi encerrada após o trabalho.
- Estação física: Samsung HDMI-A-1, Logitech G515 e AJAZZ. A configuração de dispositivos e o perfil existente foram preservados durante a atualização.
- CI do GitHub acompanha a revisão publicada, com os mesmos testes e verificações de sintaxe.

## Implantação e limites

Deploy aplicável: instalação local Omarchy, preservando os caminhos legados `jogarduo`, com backup anterior à atualização. Não existem migrations nem deploy de serviço em nuvem neste produto. O GitHub hospeda código, tag e assets do prerelease.

CPU, GPU, disco, rede e UID continuam compartilhados. A assinatura e suas quotas são comuns: Claude retornou o limite semanal, com reset em 5 de outubro às 15h, horário de São Paulo. Configurações e credenciais montadas somente para leitura podem exigir reabrir a estação após renovação no principal. Oh My Pi precisa de banco de autenticação gravável e recebe uma cópia inicial privada; o cache de licença do Maestri também é privado. Dependências e locks de instalação do Hermes são compartilhados para reutilizar suas bibliotecas.

Esta versão é experimental. Instalação do zero, outras GPUs, jogos/anti-cheat e todos os provedores dos onze harnesses não foram certificados nesta rodada. Nenhum binário proprietário, credencial, cookie ou perfil de navegador faz parte da distribuição.
