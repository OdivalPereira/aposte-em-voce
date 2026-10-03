# Retorno F1 (fechamento-nuvem) · Galadriel

Veredito: **pronto**. Sem commit, add, stash nem checkout. Base `dc35a59`.

## Comandos e contagens (da pasta `sociedade-do-codigo/`)
- `python3 -B -m unittest tests.test_sessao_consumo tests.test_metricas tests.test_sessao_claude`: 76 testes, OK.
- `python3 scripts/validar_pacote.py`: "pacote válido".
- `python3 -B -m unittest discover -s tests`: 710 testes, OK (1 pulado, 13 expectedFailure, como antes).
- Mutações feitas à mão em `consumo_claude` (dedup sempre substitui; `--desde` desligado; comparação de saída invertida): cada uma derrubou testes (1, 6 e 1 falhas). Restaurado.

## Linhas de produto em `S/` (`git diff --numstat`, adicionadas/removidas)
- `sc_sessao.py` 130/11, `sc_metricas.py` 49/9, `sc_ciclo.py` 7/2, `sc.py` 4/2, `sc_registro.py` 3/1. Soma 193 adicionadas (meta ~350).
- `scripts/validar_pacote.py` 13/2 (ampliação confirmada pelo Círdan).

## Arquivos
Criado: `T/test_sessao_consumo.py` (31 testes: soma com oráculo à mão, dedup no arquivo e entre principal e subagente, id divergente, sem id, `<synthetic>`, agente por `.meta.json` e por "Para: <Papel>", `--desde` com Z, offset, sem fuso e inválido, CLI, log ausente, `consumo_tolerante`, coluna nova, migração, `decidir aceitar` grava `consumo` no evento, sem log fica `n/d`, `--desde` inválido recusa antes de decidir, validador).
Alterados:
- Código: `sc_sessao.py`, `sc_metricas.py`, `sc_ciclo.py`, `sc.py` (parser e `cmd_` de `sessao` e `decidir`), `sc_registro.py` (só `registrar_decisao`, parâmetro `consumo=None`), `scripts/validar_pacote.py` (só `MEDICAO`).
- Teste existente: `T/test_metricas.py` (3 asserts por causa da 14ª coluna; teste do cabeçalho do projeto aceita também o cabeçalho antigo até o próximo `decidir` migrar o `sociedade/evolucao.md`, que é do Gandalf).
- Textos: `N/SKILL.md` (regras 8 a 11), `N/references/comandos.md`, `N/references/contrato-nucleo-projeto.md`, `N/assets/{ordem,rodada,avaliacao}-modelo.md`, `K/sc-execucao/SKILL.md`, `K/sc-papeis/SKILL.md`, `K/sc-papeis/references/papel-gandalf.md`, `K/sc-revisao/SKILL.md`, `P/README.md` (linha 115), `P/adapters/claude/CLAUDE.md.modelo`, `P/CHANGELOG.md` (entrada em "Não lançado"), `P/docs/decisoes.md` (só a frase de D8).

## Decisões de desenho
- `medir_claude(log, pasta=None, desde=None)` devolve `consumo = {desde, por_agente_e_modelo[{agente, modelo, mensagens, entrada, cache_escrito, cache_lido, saida}], total}`. `medir('claude', ...)` segue compatível (`desde` é o último parâmetro). Subagente avulso (`--sessao agent-x`) também ganha `consumo`.
- Nome do agente em minúsculas (`gandalf`), do `.meta.json`, senão de "Para: <Papel>", senão `agent-<id>`; principal = `principal`.
- Registro sem `timestamp` válido é descartado quando há `--desde` (não dá para provar que está no trecho).
- `decidir`: `desde` nomeado no fim da assinatura. Grava `consumo = {desde, por_agente_e_modelo, total, logs}` só no `aceitar` e só se houver log com registro de uso; senão a chave não existe e a coluna sai `n/d`. Log com zero registros de uso (ou `--desde` depois de tudo) também sai `n/d`, não 0.
- Comportamento preservado: `--log` ou `--sessao` apontando para log ausente continua erro (`não consegui medir a etapa`), porque `medir_logs` falha fechada para comandos, erros e edições. O `n/d` vale para "nenhum log informado" e para log sem uso. Se o Gandalf quiser que log ausente também vire `n/d` em tudo, é decisão de contrato (mudaria um teste existente).
- `acrescentar_linha` migra tabela antiga (coluna antes de "Dentro da meta?", separador `---`, `n/d` nas linhas antigas) e agora insere a linha **no fim da tabela**, não no fim do arquivo. Antes, com `sociedade/evolucao.md` do projeto (tem seção "Escaparam ao aceite" depois da tabela), a linha cairia depois do texto. Mudança de comportamento, coberta por teste.
- `sc.py sessao codex|antigravity --desde` recusa ("só vale para o Claude Code").

## Redações reescritas por causa do validador e dos limites
- Limite da carga do coordenador (12288 B; tinha 165 B de folga) e do Markdown das skills (60000 B): enxuguei texto existente para caber (`sc-execucao`: bullet do Jules duplicado da lista "Arquivos desta skill", frase do inventário local; `sc-papeis`: frase dos executores locais, regra da disjunção; núcleo: linha de referências). Nada de regra saiu. Folga atual do total: menos de 100 B; a próxima fatia de texto vai estourar o validador sem nova poda.
- `ordem-modelo.md`: `<ordem>-<fatia>` virou marcador não preenchido para `test_contrato_modelos`; a frase agora diz "arquivo de retorno em `sociedade/subordens/`".
- `avaliacao-modelo.md`: título "Proibição Absoluta" e proibições de estimar mantidos; ganhou a exceção "medir pelo log é permitido". Os dois testes de redação seguem verdes sem edição.
- Regra 8 do núcleo: "Medir o consumo pelo log é permitido; estimar é proibido." (a proibição na mesma linha também satisfaz o validador antigo).

## Divergências e pendências para o Círdan
- `sociedade/regras.md` §3 item 8 ainda diz "Retorno do coordenador até 8 KB (Q99)" e §8 item 3 "Nenhum agente estima ou relata consumo. Scripts medem só contagens objetivas pelos logs": divergem do pacote (2 KB; medir pelo log permitido). Arquivo é do Círdan; não editei.
- `sociedade/evolucao.md` do projeto ainda tem 13 colunas; o `decidir aceitar` seguinte migra sozinho (e o teste do cabeçalho aceita as duas formas até lá).
- `P/docs/decisoes.md`: troquei só a frase de D8 ("Estimar consumo foi expurgado ... Medir pelo log passou a ser permitido").
- `validar_pacote.py`: nova função `instrucao_de_medir(linha)`: `medi\w+` passa se a linha menciona log/logs/transcrição; estimar, calcular, relatar, registrar e contar seguem recusados. Limitação herdada: o regex não pega "Meça" (cedilha).

## Atritos com o método
- Limites de tamanho do validador (carga do coordenador com 165 B de folga) tornam qualquer regra nova um corte de outra; a subordem não avisava. Vale registrar em `sociedade/nuvem/atritos.md`.
- A subordem pedia "Q99 vira 2 KB" para o limite do coordenador na ordem ao Círdan também; só o `ordem-modelo.md` e as skills foram tocados, `regras.md` ficou para o Círdan.
- Nenhuma hipótese repetida; nenhum bloqueio de 3 tentativas.
