## Parecer do Revisor Independente
- etapa: fechamento-nuvem
- entrega: commit congelado 12ba867 (ramo etapa/fechamento-nuvem; na cópia, "candidato (12ba867)")
- commit: 12ba867
- base..head: dc35a59..12ba867
- revisor: Barbárvore (revisão reduzida, Q150) · Claude Code em nuvem · fornecedor: Anthropic · sessão: subagente barbarvore-reduzida, conversa nova, da sessão 8c54e58c-9f4a-56c4-a2da-c8f92be280dc
- modelo: Claude Opus 5.5 · esforço: não exposto
- independência: Nível B (sessão distinta e modelo distinto, mesmo fornecedor dos implementadores; aceite em emulação, Q147; revisor não calibrado)
- veredito: aceitar com ressalvas
- data: 03/10/2026 21:06

**Marcas:** aceite em emulação · revisor não calibrado · revisão reduzida (passo 0 e lentes pertinentes).

### Independência
Não implementei nem corrigi nada desta entrega. Implementação feita pelo fornecedor Anthropic (Gandalf, Galadriel e Elrond, Claude Sonnet 5.5); minha revisão é de fornecedor igual: revisão em emulação (Q147). Pela D-RT-001 ela não conta como revisão independente; vale só como aceite em emulação.

### Mapa da entrega
- Motivo da etapa: pedido de Odival (ordem `sociedade/ordens/fechamento-nuvem.md`, seção "Objetivo"): menos releitura de contexto (F1), vários extratos mensais como um histórico só, com o layout no estilo Nubank (F2), e aceite mais firme, com os itens B15 e B17b do backlog (F3).
- Critérios de aceite: F1 (consumo pelo log por agente e modelo, com deduplicação e `--desde`; `decidir` grava o consumo e a coluna "Consumo (cache lido)", com "n/d" sem log; regras de economia nos textos; suíte e `validar_pacote.py` verdes). F2 (histórico contínuo por banco e identificador estrutural; encadeamento de saldo exato com aviso; acrescentar arquivos sem duplicar pelo hash; T99, a assinatura do layout sem dígitos nem descrições; layout agrupado por dia com variante ambígua; `npm test`, lint e build verdes). F3 (B15 a-d, B17b, as sondas DG-02 e E3 verdes).
- Superfícies de entrada: `sc.py sessao claude [--desde]`, `sc.py decidir [--desde]`, `sc.py revisar` (sem `--parecer`, worktree da etapa), `sc_rodada evidencia|parecer|encerrar`, `sc_conferir atestado_aprovado`, `sc_status aceite`, `sc_status.hash_do_atestado_confere`, `sc_ciclo._nome_do_perfil`, `Registro.registrar_parecer` (fornecedor do perfil); app: `agruparHistoricos`, `assinaturaDoLayout`, `contaDoTexto`, `formatoDeValor`, `formatoDeData`, telas Extratos, ResultadoLeitura e Diagnostico.
- Estados e transições: etapa aberta → decisão (`decidir`, só pessoa, exige atestado 1.3.0 com hash e parecer do SHA) → encerrada; `sc_rodada encerrar` agora exige o evento de decisão, também com `--forcar`. Atestado: gerado só pelo `entregar`, mas o hash é SHA-256 sem chave, refeito por qualquer um.
- Fontes de verdade e derivados: `registro.json` (fonte) → `evolucao.md` e o histórico (derivados); atestado (fonte do portão) → `atestado_hash` na decisão; logs JSONL da sessão → consumo.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| Atestado do commit (Q70) | 52 hashes de `hashes_artefatos` conferidos com os arquivos da cópia, sem divergência; commit 12ba867, áreas app (154 testes) e pacote (734 testes, 1 pulado) ok | executada |
| F1 consumo por agente e modelo, deduplicação, `--desde`, log ausente | sondas P9 a P13 (`revisao-saida/sondas/s2_nomes_sessao.py`) e testes `test_sessao_consumo` e `test_metricas` rodados (OK) | executada |
| F1 regras de economia nos textos e `validar_pacote.py` | grep nos SKILL.md (2 KB, por trecho, estado em arquivo); `validar_pacote.py`: "pacote válido" | executada |
| F2 histórico, meses faltando, encadeamento exato, mesmo hash não duplica | sonda P17 (`sondas/ts/h.ts`, node com strip-types): 1 centavo de diferença dá aviso no mês certo; o mês com lacuna não é encadeado; a cópia repetida vai para `repetidos`; sem identificador, os arquivos juntam com aviso | executada |
| F2 T99, assinatura sem dígitos nem descrição | sondas P14 a P16 (`sondas/ts/p.ts`) e leitura de `tests/unit/assinatura.test.ts` | executada |
| F2 layout agrupado por dia e variante ambígua | `tests/unit/agrupado-por-dia.test.ts` lido; o atestado traz `npm test` verde | lida |
| F3 B15 (b) hash do atestado e B17b avulso e `--area` parcial | sondas P1 a P7 (`sondas/s1_atestado.py`): sem hash, cauda alterada, avulso, parcial e total alterado são recusados; **forjado com hash refeito é aceito (P6)** | executada |
| F3 B15 (d) decisor não é papel nem modelo | `python3 -B revisao-saida/sondas/s2_nomes_sessao.py` (P8): Gandalf, Coordenador e os modelos do perfil são recusados; Odival é aceito | executada |
| F3 B15 (a), (c), legado `evidencia`, `parecer`, `encerrar`; DG-02 verde | `test_aceite_nao_forjavel` e `adversarial.test_dg02_aceite_forjavel` rodados (96 testes com os de F1, OK); nenhum `expectedFailure` resta no DG-02 | executada |
| F3 B17b `revisar` leva ordem, atestado e perfil | esta cópia: `sociedade/ordens/fechamento-nuvem.md`, os atestados e `perfil.md` presentes | executada |

### Matriz de cobertura
| Critério | L1 motivo | L2 ponta a ponta | L3 estados | L4 escape | L5 entradas | L6 concorrência | L7 fontes | L8 retorno |
|---|---|---|---|---|---|---|---|---|
| F1 consumo | P9 | n/a (redução Q150) | n/a (sem estado) | P11 | P12, P13 | n/a (redução Q150) | lida (`decidir` grava `consumo` no evento) | testes F1 |
| F1 textos | lida | n/a (texto) | n/a (texto) | n/a (texto) | n/a (texto) | n/a (texto) | `validar_pacote` | grep |
| F2 histórico e encadeamento | P17 | atestado (e2e `historico.spec.ts`) | n/a (sem estado) | n/a (sem opção) | P17 (sem id, repetido, lacuna) | n/a (redução Q150) | n/a (sem fonte gravada) | lida |
| F2 T99 assinatura | P14 a P16 | atestado | n/a | n/a | P15 | n/a | n/a | lida |
| F2 agrupado por dia | lida | atestado | n/a | n/a | lida (variante) | n/a | n/a | lida |
| F3 B15 hash e B17b forma | P1 a P7 | n/a (redução Q150) | lida (`exigir_decisao`) | P6 | P2, P3, P7 | n/a (redução Q150) | lida (`atestado_hash` na decisão e no `aceite`) | testes F3 |
| F3 B15 (d) decisor | P8 | n/a | P8 | P8 | P8 | n/a | n/a | teste B15_d |
| F3 declarativos do legado | lida | n/a | lida | lida (F3-2) | n/a | n/a | lida | testes B15 legado |

### Achados
- [relevante] L4 · F3-1, que a Galadriel deixou em aberto: o `atestado_hash` é um SHA-256 sem chave dos campos do próprio atestado. A sonda P6 escreve à mão um atestado para um commit inexistente (`ffff…`), com um único hash de artefato inventado, e refaz o hash com `sc_status.hash_do_atestado`; o resultado de `sc_conferir atestado_aprovado` é "feito". A conferência não verifica se o commit existe nem compara `hashes_artefatos` com a árvore do commit, e o status `portao` não confere o hash. Efeito: os textos "recusa atestado escrito à mão" e "aceite forjado numa sessão só é recusado" da B15 não estão cumpridos; só a adulteração sem refazer o hash é detectada. O CHANGELOG declara esse limite. Correção esperada: manter um resíduo da B15 aberto no backlog (reexecutar `sc.py entregar` no CI e comparar, ou conferir `hashes_artefatos` contra `git show <commit>:<arquivo>`), e no `atestado_aprovado` exigir que o commit exista e aplicar o hash também no status `portao` (`sc_conferir.py:120-131`, `sc_status.py:112-130`).
- [relevante] L4 · F3-2, o declarativo que sobra: `sc_rodada fatia --fechar --prova <texto>` grava evidência com `exit_code=0` tirado do texto livre, e nenhum comando é executado (`sc_rodada.py:571-588`). O `sc_passagem` grava `exit_code=0` com `comando=comando_teste` mesmo quando o portão avulso rodou com `--ignorar-testes` e um motivo (`sc_passagem.py:1020-1031`). Efeito limitado: o aceite continua exigindo atestado por área, parecer e decisão de uma pessoa. Mesmo assim, o registro mostra como medido um resultado declarado, ao contrário da regra da B15 ("saem do legado os declarativos"). Correção esperada: marcar essas evidências como declaradas (código nulo ou tipo próprio) ou removê-las.
- [opcional] L3 · `_nome_do_perfil` exige igualdade exata: "Revisor", "GPT" e "Gemini" passam como pessoa (P8). Isso cumpre a letra da B15 (d); variantes parciais de papel e de modelo ficam de fora (`sc_ciclo.py:264-275`).
- [opcional] L5 · `_escreva_so` conta todo caminho entre crases de uma linha com "escreva só", salvo o que vem depois de "proibid". Uma linha como "escreva só: `x`; não toque em `.github/workflows/`" libera o workflow (lida, não executada; `sc_status.py:279-287`).
- [opcional] L8 · A B15 do backlog cita as "Sondas AUD-01 e AUD-05", mas nenhum teste da cópia tem esse identificador. O rastreio do critério fica só pelos nomes `test_B15_*`.
- [opcional] L5 · `contaDoTexto("conta final 4821")` retorna nulo (P15): um final curto sem máscara é recusado, e o extrato cai em "sem identificador", com aviso. A escolha é conservadora e não vaza dado (`src/leitura/layout.ts:64-80`).

### O que não verifiquei
- Não reexecutei a suíte do pacote nem `npm test`, lint e build (Q70): o atestado confere pelo hash com o commit 12ba867 e com os 52 arquivos.
- Não executei o layout agrupado por dia nem o e2e de histórico: não há `node_modules`, e a ordem de revisão proíbe rede. Ficam como lidos e cobertos pelo atestado.
- Não executei as lentes L2 e L6 nem a parte de L7 do pacote (revisão reduzida, Q150). Não executei o `decidir` ponta a ponta com o consumo gravado em `evolucao.md`; só li o código e rodei `test_metricas`.
- Não conferi por script o teto de 1.500 linhas de produto (Q168).
- Não executei a sonda F3-2: o caminho `fatia --fechar` e o do `sc_passagem` foram lidos.
- Não verifiquei o CI do PR (sem rede).
