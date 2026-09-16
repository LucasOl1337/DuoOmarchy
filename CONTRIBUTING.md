# Contribuir

Comece com uma issue descrevendo o hardware, o comportamento esperado e observado. Relatos reproduzíveis de outras GPUs, monitores e jogos ajudam mais que promessas de FPS.

```sh
python -m pip install vdf
python -m unittest discover -s tests -v
python -m compileall -q src scripts
bash -n scripts/build-gamescope.sh
```

Os testes unitários não capturam entrada, não abrem jogos e não modificam a sessão real. Testes físicos devem ser feitos conscientemente pelo dono da máquina, com um teclado principal livre e uma rota de saída.

Preserve os invariantes: nunca capturar o kit principal; nunca abrir a conta principal em uma segunda Steam; não substituir dados pessoais; não adicionar execução arbitrária de shell ao protocolo; não usar mouse/foco globais no gerenciador; manter um caminho de encerramento.

Para alterar Gamescope, reproduza o build a partir do commit fixado e atualize o patch, os créditos e os testes relevantes. Não envie binários de jogos, credenciais ou diretórios Steam ao repositório.
