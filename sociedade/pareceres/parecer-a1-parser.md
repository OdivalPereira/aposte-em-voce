## Parecer do Revisor Independente
- etapa: a1-parser
- entrega: candidato congelado 6f2c4fd (na cópia: commit "candidato (6f2c4fd)", HEAD; base "base (d86e90c)")
- commit: 6f2c4fd
- base..head: d86e90c..6f2c4fd
- revisor: Barbárvore, revisão reduzida (Q150), subagente barbarvore-reduzida no Claude Code (nuvem) · fornecedor: Anthropic (papel emulado, Q147; o registro declara Anthropic, C12) · sessão: 8c54e58c-9f4a-56c4-a2da-c8f92be280dc (conversa nova)
- modelo: claude-opus-5-5 · esforço: não exposto
- independência: Nível C (mesmo fornecedor), sessão distinta; **aceite em emulação** · **revisor não calibrado**
- veredito: aceitar com ressalvas
- data: 03/10/2026 19:25

### Independência
Não implementei nem corrigi nada desta entrega. Implementação feita pelo fornecedor Anthropic (Aragorn na F1, Elrond na F2, emulados); minha revisão é de fornecedor igual: revisão interna em emulação, numa sessão nova e só sobre a cópia. Por isso o aceite que dela decorrer é **aceite em emulação** e este revisor é **não calibrado**. Modo reduzido (Q150): passo 0 e as lentes pertinentes; as demais ficam marcadas "n/a" com o motivo.

Registro de execução (Q29). Executado por mim nesta cópia: `npm ci`, `npm run lint`, `npm run build`, `CI=1 npm test` (Vitest e Playwright), `python3 -B -m unittest discover -s tests` e `python3 -B scripts/validar_pacote.py` (em `sociedade-do-codigo/`), as sondas `revisao-saida/sondas/app.sonda.ts` (SA1 a SA12, via `npx vitest run --config revisao-saida/sondas/vitest.sondas.config.ts`) e `revisao-saida/sondas/pacote_sondas.py` (SP1 a SP7, repositórios temporários), `git diff` de escopo e contagens. Só lido: o resto do código citado abaixo, a ordem, as seções pedidas de `docs/onda-1.md`, o backlog (B11 a B13) e o perfil. Atestado: `sociedade/pareceres/atestado-a1-parser.json` não está na cópia (fica na `sociedade/` do worktree e não faz parte do commit do candidato), então rodei as suítes (Q70). CI pelo hash: não conferido (sem rede). Efeitos colaterais na cópia: só `node_modules/`, `dist/` e `test-results/`, todos ignorados pelo `.gitignore`; nada rastreado mudou.

### Mapa da entrega
- Motivo da etapa: pedido de Odival (`sociedade/nuvem/pedidos.md`, linha a1-parser): abrir no celular extratos em PDF de vários bancos e ver, sem nada sair do aparelho, quantas movimentações foram lidas e se os saldos fecham (onda-1 §15, linha a1-parser). No pacote: B11 (portão amarrado ao perfil; DG-03, DG-09, DG-11), B11a a B11d; B12 (simulação "3 tentativas", plantada no caso colunas-trocadas); B13 (Jules, PDFs sintéticos).
- Critérios de aceite: os da ordem `sociedade/ordens/a1-parser.md` (F1, F2, F3 e entregas E1 a E10) e os da onda-1 §15 (CI e portão verdes; testes de leitura com a meta da §14; ponta a ponta de rede verde; teste de Odival na pré-visualização). Lista completa na matriz.
- Superfícies de entrada: `sc.py entregar` (`--etapa`, `--base`, `--fatia`, `--area`, `--pasta-projeto`, `--pasta-sociedade`, `--papel`; `--comando-teste` oculto e recusado); `sc_pre_devolucao.py` (`--portao-por-area`, `--area`; avulso mantém `--comando-teste`); `sc.py conferir` (`--pasta-sociedade`), `revisar --parecer`, `decidir`, `estado --etapa`; `sc_perfil.ler_portao_por_area`, `areas_do_caminho`, `areas_tocadas`; `sc_status.forma_do_atestado`. App: `lerExtrato(bytes, senha?)`, `analisarPaginas`, `consolidar`, `diagnosticar`, `lerNoWorker`; telas T08 (input de arquivo e senha), T09 e T99.
- Estados e transições: atestado APROVADO ou REPROVADO (só o portão grava; `decidir` e o status `portao` exigem a forma 1.3.0 com cobertura completa e o SHA-256 do perfil); etapa aberta, entregue, revisada, decidida (scripts do ciclo). No app, item de arquivo: lendo, senha, pronto; status do arquivo: suficiente, parcial, ambígua, não suportado (decidido no pipeline).
- Fontes de verdade e derivados: perfil canônico (`sociedade/perfil.md`, seção "Portão por área") é a fonte do comando e do timeout; o atestado é derivado (grava `perfil_sha256`, commit, áreas). No app, os bytes do PDF são a fonte; `ResultadoArquivo`, o consolidado e o diagnóstico são derivados, só na memória da página; `vercel.json` é a fonte dos cabeçalhos, repetidos pelo `vite preview` no teste.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| F1 B11: `entregar` recusa `--comando-teste`; comando e timeout só do perfil | SP1: `sc.py entregar --comando-teste ''`, `--comando-teste=echo`, abreviação `--comando-t echo` e o comando legítimo: todos rc 2, sem atestado gravado | executada |
| F1 B11: árvore suja, 0 testes, todos pulados e timeout reprovam | SP6a (mudança só no índice) e SP6b (rastreado dentro de `dist/`) REPROVADO; SP5 timeout de 2 s com processo neto: REPROVADO em 2,1 s; SP7 teste que cria arquivo: REPROVADO; SP4 `contar_testes` em 8 saídas (Vitest e unittest vazios dão 0; só pulados dão total = pulados) | executada |
| F1 B11: atestado com comando, timeout, contagem, SHA-256 do perfil e commit; `-z`, `core.quotepath=off`, NFC | `python3 -B -m unittest discover -s tests` (679 testes, OK, 1 pulado, 13 falhas esperadas), incluindo `test_portao_amarrado.py` (44 testes) e DG-11; código lido em `sc_pre_devolucao.py` | executada |
| F1: `node_modules/` presente e ignorado, portão aprovando | `test_aprova_com_node_modules_presente_e_ignorado` na suíte do pacote; SP6b com `node_modules/` presente só reprova pelo rastreado em `dist/` | executada |
| F1 B11c: portão por área, prefixo mais longo, `.github/` nas duas | suíte do pacote (`TestLeituraDoPerfil` e afins); SP2: `entregar --area app` com app e pacote tocados grava `areas_tocadas` = app, pacote e `cobertura_completa` falso | executada |
| F1: sondas DG-03 (árvore suja, sem `expectedFailure`), DG-09 (3 casos), DG-11 verdes | suíte do pacote verde; diff de `test_dg03_commit_amarrado.py` tira os dois decoradores da B11 | executada |
| F1 B11a: `sociedade/` do worktree da etapa; `conferir --pasta-sociedade` | `test_sociedade_worktree.py` (11 testes) na suíte; código lido em `sc_registro.localizar_sociedade_da_etapa` e `sc.py` | executada |
| F1 B11b: nenhuma skill cita `sc_rodada parecer` | `grep -rn "sc_rodada parecer"` nos plugins: nenhuma ocorrência | executada |
| F1 B11d: linha no modelo de PR | `.github/pull_request_template.md` lido: "Conferi o diff de `.github/` e `sociedade/pareceres/`" | lida |
| F1: suíte do pacote e `validar_pacote.py` verdes | `python3 -B scripts/validar_pacote.py`: "pacote válido"; suíte OK | executada |
| F2: stack da §3; `npm test`, `npm run lint`, `npm run build` passam; licenças | `npm run lint` rc 0; `npm run build` rc 0 (PDF.js em chunk e worker próprios); `CI=1 npm test`: Vitest 110 de 110, Playwright 9 de 9; licenças do lockfile: produção só MIT e Apache-2.0 | executada |
| F2: pipeline 5.1 a 5.5, genérico, em centavos, sem tolerância; função pública para a F3 | SA1 a SA12 (ordem decrescente, C/D, saldo D, virada de ano, "12 SET", parênteses, 1 centavo, fatura, 95%); código lido em `src/leitura/` | executada |
| F2: caso colunas-trocadas | SA1 (`npx vitest run --config revisao-saida/sondas/vitest.sondas.config.ts`): 3 lançamentos certos; pela §5.2 o saldo da ordem (1.119,91) não fecha por 1 centavo e o status é Parcial; o teste da entrega documenta a contradição e a correção pelo ajuste 4 (B12) | executada |
| F2: unidade com texto posicionado (datas, valores, direção, saldo, consolidação, duplicidade) | `npx vitest run`: 5 arquivos, 110 testes; nomes lidos em `tests/unit/` | executada |
| F2: telas T08, T09, T99; T99 sem valores, nomes nem descrições; nada guardado | ponta a ponta (`npx playwright test`) confere T99 sem PIX, nome, valores ou R$, e `localStorage`, `sessionStorage`, cookies e IndexedDB vazios; SA8 `diagnosticar` sem texto livre | executada |
| F2: ponta a ponta em perfil de celular; rede só GET do mesmo domínio | `CI=1 npm test`: 9 testes Playwright (Pixel 7) sob a CSP de `vercel.json`, sem violação de CSP | executada |
| F2: `vercel.json` com CSP e cabeçalhos; `ci.yml` com lint, build e testes do app | arquivos lidos; o teste ponta a ponta confere os cabeçalhos servidos | lida |
| F3 (E5): gerador de PDFs sintéticos e meta de leitura da §14 (6 layouts e 8 casos difíceis em PDF) | não integrada por decisão do coordenador (Q12); `scripts/`, `tests/leitura/` e `tests/fixtures/` não existem na cópia | não verificada |
| Escopo: candidato não altera `sociedade/`, `docs/` nem `.claude/`; E2 nos prefixos | `git diff --name-only HEAD~1 HEAD`: nenhum caminho nessas pastas e nenhum fora dos prefixos de E2 | executada |
| Teto de cerca de 1.500 linhas de produto | `git diff --numstat`: `src/` 1.824 linhas (1.428 sem comentários e linhas vazias) e scripts do pacote +590/−53 | executada |

### Matriz de cobertura
| Critério | L1 motivo | L2 ponta a ponta | L3 estados | L4 escape | L5 entradas | L6 concorrência | L7 fontes | L8 retorno |
|---|---|---|---|---|---|---|---|---|
| B11 portão amarrado | SP1, SP6a | suíte do pacote (fluxo `entregar`, `decidir`) | SP2 (forma do atestado) | SP1, SP2, SP3 | SP4, SP5 | SP7 (árvore muda durante o portão) | DG-09 perfil trocado (suíte) | SP3 achado 1 |
| node_modules ignorado | n/a (não é motivo) | SP6b | n/a (sem estado) | SP6b | SP6b | n/a (sem escrita concorrente) | n/a (sem derivado) | suíte do pacote |
| B11c por área | SP2 | suíte do pacote | SP2 | SP2 | lida (prefixos repetidos e pasta fora do repositório recusados) | n/a (execução sequencial por área) | SP2 | SP2 |
| Sondas DG-03, DG-09, DG-11 | suíte do pacote | suíte do pacote | n/a (são as sondas) | n/a (são as sondas) | n/a (são as sondas) | n/a (fora do reduzido) | n/a (fora do reduzido) | diff lido e suíte |
| B11a worktree | lida | suíte do pacote | n/a (fora do reduzido) | lida (`--pasta-sociedade` antes do worktree) | lida (nome de etapa inválido cai na canônica) | n/a (fora do reduzido) | suíte do pacote | suíte do pacote |
| B11b e B11d textos | grep executado | n/a (texto) | n/a (texto) | n/a (texto) | n/a (texto) | n/a (texto) | lida | lida |
| Suíte e validador do pacote | n/a (verificação) | suíte e validador executados | n/a | n/a | n/a | n/a | n/a | suíte e validador executados |
| Stack, lint, build, testes | n/a (infraestrutura) | lint, build e testes executados | n/a | n/a | n/a | n/a | lida (licenças) | lint, build e testes executados |
| Pipeline 5.1 a 5.5 | ponta a ponta do app | ponta a ponta do app | SA12 (fronteira de 95%), SA10 | SA9 (direção por convenção) | SA2 a SA6, SA11 | n/a (função pura) | SA2 (ordem inversa) | SA1 a SA12 |
| colunas-trocadas | SA1 | n/a (unidade) | SA1 | n/a | SA1 | n/a | n/a | SA1 |
| Unidade | n/a | testes do app executados | n/a | n/a | lida | n/a | n/a | testes do app executados |
| Telas T08, T09, T99 | ponta a ponta do app | ponta a ponta do app | lida (estado do item: lendo, senha, pronto) | lida (pular arquivo) | ponta a ponta do app (senha errada, imagem, corrompido) | lida (worker único, respostas por id) | SA8 | ponta a ponta do app |
| Ponta a ponta e rede | ponta a ponta do app | ponta a ponta do app | n/a | n/a | n/a | n/a | lida (cabeçalhos de `vercel.json` no preview) | ponta a ponta do app |
| vercel.json e ci.yml | lida | lida | n/a | n/a | n/a | n/a | lida | lida (CI não conferido pelo hash, sem rede) |
| F3 (E5) e meta da §14 | não verificada (não entregue) | não verificada | não verificada | não verificada | não verificada | não verificada | não verificada | não verificada |
| Escopo e teto | n/a | n/a | n/a | n/a | n/a | n/a | diff de escopo executado | contagem executada |

### Achados
- [relevante] L4, L8 · `sc_conferir` (`atestado_aprovado`, a entrega E3 desta ordem) marca "feito" um atestado que o `decidir` e o status `portao` recusam: o avulso, sem bloco `portao` (SP3: `sc_pre_devolucao.py --comando-teste` com saída forjada; status APROVADO, E3 feito) e o de `--area app` com a área pacote tocada e não rodada (SP2: `cobertura_completa` falso, `forma_do_atestado` recusa, E3 feito). Efeito: a conferência por script, que o arquiteto usa, pode dar o portão por cumprido sem a forma 1.3.0; o aceite em si continua protegido pelo `decidir` e pelo status. Correção esperada: `atestado_aprovado` aplica `sc_status.forma_do_atestado` com o SHA-256 do perfil da `sociedade/` da etapa, e um teste cobre os dois casos (`sc_conferir.py:108-126`).
- [relevante] Etapa, L1 · E5 "não feito" (F3/B13 não integrada, Q12): o critério da onda-1 §15 "testes de leitura com a meta da seção 14" fica sem evidência. Nenhum dos 6 layouts imitados (Nubank, Mercado Pago, PicPay, Inter, Caixa Tem, Caixa) é testado; dos casos difíceis, a unidade cobre quase todos com texto posicionado e o ponta a ponta cobre senha, imagem, mesmo arquivo e períodos sobrepostos com PDFs gerados no teste, mas não há a suíte `tests/leitura/` sobre PDFs com JSON esperado. Efeito: o aceite não pode declarar a meta de leitura cumprida, e o teste de Odival com extratos reais passa a ser a única prova por layout. Correção esperada: registrar a B13 e a meta da §14 como pendência explícita (a2 ou etapa própria), com E5 "não feito" no registro, sem tratá-las como entregues (`sociedade/ordens/a1-parser.md`, F3 e E5).
- [opcional] Escopo · o teto de cerca de 1.500 linhas de produto foi passado: `src/` tem 1.824 linhas novas (1.428 sem comentários nem linhas vazias) e os scripts do pacote, +590/−53. O ajuste 5 manda o excedente para a a2; a cópia não mostra esse registro, que fica na `sociedade/` do worktree (não verificado aqui).
- [opcional] L4 · `contar_testes` soma os executores de uma área: com `vitest run && playwright test`, se todos os testes do Playwright forem pulados e o Vitest tiver testes, a área aprova (SP4, "vitest_ok_mais_pw_pulados": total 9, pulados 4). Fica a critério do método exigir "nem todos pulados" por executor (`sc_pre_devolucao.py`, `contar_testes` e `_rodar_areas`).
- [opcional] L5 · datas sem ano num documento sem período: as linhas ficam não lidas (não inventa ano, como manda a §5.2). Sem nenhum lançamento, porém, o arquivo vira "Não suportado" com a mensagem "Ele pode não ser um extrato de conta", embora tenha linhas candidatas (SA4: 2 candidatas, 0 lançamentos). Uma mensagem que diga que faltou o ano ajudaria no teste de Odival (`src/leitura/conferir.ts`, `decidirStatus`).
- [opcional] L5 · o limite de 30 MB só é conferido depois de ler o arquivo inteiro para a memória e calcular o hash (`src/app.tsx`, `escolher`; `src/leitura/index.ts`, `lerExtrato`). Conferir `File.size` antes do `arrayBuffer()` evita estourar a memória do celular com um arquivo enorme.
- [opcional] L4 · direção por convenção do documento: se há valores com "-" e nenhum com "+", os valores sem sinal viram entrada (`reconstruir.ts`, `semMarca`). Com saldo, o erro aparece (SA9: Parcial, saldo não fecha); sem saldo, o arquivo sai "Leitura suficiente" sem confirmação. É uma leitura razoável da §5.1, passo 7, já coberta por teste da entrega; vale observar no teste de Odival.
- [opcional] Texto · T09 com a concordância "1 aparecem em dois extratos" (`src/telas/ResultadoLeitura.tsx`).

### O que não verifiquei
- O atestado da etapa (`atestado-a1-parser.json`) e o SHA-256 do perfil com a seção "Portão por área": ficam na `sociedade/` do worktree, fora do commit e da cópia. O perfil desta cópia não tem a seção. Rodei as suítes no lugar dele (Q70).
- O CI e o status `portao` no GitHub para o hash 6f2c4fd: sem rede.
- E1, E7, E8, E9 e E10 (commit no ramo, delegações, conversa nova, push, parecer registrado): dependem do repositório real e dos logs da sessão, fora da cópia.
- A F3 (gerador, fixtures, `tests/leitura/`), não entregue por decisão do coordenador; e a pré-visualização na Vercel com os cabeçalhos reais, além do teste de Odival com extratos reais (C45).
- Quem fez a correção do esperado do caso colunas-trocadas (o ajuste 4 reserva isso ao Gandalf): a cópia tem um commit só e não mostra a autoria por fatia. A revisão interna da Galadriel também não foi conferida.
- Lentes fora do modo reduzido: L6 (concorrência) só lida no cliente do worker; L3 e L7 do B11a só pela suíte da entrega, sem sondas próprias.
- Desempenho e acessibilidade além dos alvos de toque de 44 px que o ponta a ponta confere (são da a4).
