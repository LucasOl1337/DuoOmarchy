# Diagnóstico

## Não consigo usar Super no desktop principal

Execute `jogarduonao` no terminal principal. A versão atual não captura o primeiro kit. Confira `config.json`: o teclado/mouse principal não podem estar escolhidos como segundo kit. Nunca atribua todos os dispositivos de `/dev/input` à estação secundária.

## Steam fechada / quero abrir novamente

Abra o Gerenciador e use **Abrir Steam**. O serviço de controle continua vivo mesmo sem janela. Se a sessão inteira estiver desligada, use **Ligar sessão** primeiro. O modo não fornece um segundo Hyprland; gerencie os aplicativos pelo painel principal.

## Sessão não inicia

```sh
duoomarchy status
journalctl --user -u duoomarchy.service -n 60
```

Verifique caminhos USB, permissões, monitor e o log `~/.local/share/duoomarchy/logs/player2.log`. Monitores nos workspaces 6–11 são recusados. Se um dispositivo for removido, reconecte, confira o caminho estável e reabra a sessão. Não contorne a verificação de sobreposição dos kits.

## FPS alto, movimento irregular

Confirme o backend `wayland` na configuração. Verifique Hz físicos com `hyprctl -j monitors`, o alvo do jogo e se a GPU está saturada pelos dois jogadores. Deixe o processamento de shaders da Steam terminar; um perfil novo pode compilar muito conteúdo. Não atribua uma melhora a um único ajuste sem comparar os tempos entre quadros.

O perfil padrão usa 120 FPS no segundo jogo; a Steam principal mantém as configurações do usuário. Um jogo principal sem limite pode consumir a margem da GPU necessária ao segundo. Se quiser testar SDL, mude apenas o backend e compare; não altere vários parâmetros de uma vez.

## Battle.net conecta em uma conta, mas não na outra

Verifique antes se a Steam principal está online. A mensagem `Session Replaced` em `~/.local/share/Steam/logs/connection_log.txt` indica substituição de uma sessão Steam, não comprova falha do servidor Blizzard. Feche cópias concorrentes da mesma conta e reabra a Steam afetada. O DuoOmarchy atual recusa iniciar player1 isolado.

## Sem áudio

Conecte o dispositivo pelo Omarchy e escolha saída e microfone por aplicativo no Sonora. Verifique volume e mudo ali. O DuoOmarchy não controla esses dispositivos.

Ao atualizar uma sessão antiga ainda aberta, o processo pode conservar a saída virtual herdada no lançamento. Para interromper a regra antiga sem fechar os jogos, deixe `sink` e `source` vazios na configuração e reabra somente o gerenciador. A remoção completa das variáveis antigas entra em vigor na próxima abertura normal da segunda estação.

## Reportar problema

Informe versão do Omarchy, GPU/driver, backend, resolução/Hz e se o erro acontece no menu ou em jogo. Envie apenas trechos relevantes dos logs. Nunca anexe o home `player2`, arquivos de login Steam, tokens, saves privados ou dumps de memória completos a uma issue pública.
