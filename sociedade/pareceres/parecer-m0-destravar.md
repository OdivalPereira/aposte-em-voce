## Parecer do Revisor Independente
- etapa: m0-destravar
- entrega: commit fb3ae42 do ramo etapa/m0-destravar (cópia preparada por sc.py revisar)
- commit: fb3ae4265da0fc5fdd1e327d8320b579c640d3b5
- base..head: 3bff553..fb3ae42
- revisor: Barbárvore (Claude Code, subagente barbarvore, protocolo completo) · fornecedor: Anthropic · sessão: subagente da sessão session_01Sc8Uybhu6Ku6oeUkYMZ8b2 (id do agente não exposto)
- modelo: Claude Opus 5.5 (claude-opus-5-5) · esforço: não exposto
- independência: Nível C (mesmo fornecedor; aceite em emulação, Q147; revisor não calibrado, Q160)
- veredito: aceitar com ressalvas
- data: 03/10/2026 17:13

### Independência
Não implementei nem corrigi nada desta entrega. Implementação feita pelo fornecedor Anthropic (Gandalf, Elrond, Aragorn e Galadriel emulados por modelos Claude); minha revisão é de fornecedor igual: revisão interna. Este parecer vale só como "aceite em emulação" (Q147), nunca como revisão independente (D-RT-001), e o revisor é "não calibrado" (Q160). Trabalhei só na cópia descartável e no diretório temporário das sondas; li fora dela apenas o atestado indicado na ordem, para conferi-lo pelo hash. Não consultei memória da ferramenta.

### Mapa da entrega
- Motivo da etapa: pedido de Odival (linha m0-destravar de sociedade/nuvem/pedidos.md, ordem sociedade/ordens/m0-destravar.md): uma etapa fecha pela formação emulada só com comandos documentados, com prova dupla, parecer ligado ao commit e decisão registrada; esta etapa fecha assim (C33). Achados de origem: DG-01 a DG-05 e DG-13, DG-22, DG-23.
- Critérios de aceite: B01 a B10 da seção "Etapa 0" do backlog e os aceites das fatias F1 a F5 da ordem (escopo só sociedade-do-codigo/ e .github/; teto de cerca de 1.500 linhas de produto).
- Superfícies de entrada: sc.py abrir (etapa, ordem, base, bastao); sc.py revisar --parecer (parecer, head, implementador); sc.py decidir (acao, por, head, motivo, minutos, intervencoes, escaparam, log, sessao, projetos); sc.py sessao claude (sessao, projetos); sc_conferir tipos delegacoes claude e conversa_nova claude (SC_CLAUDE_PROJETOS); sc_status.py portao e aceite (ramo, head, raiz); sc_metricas.py; lint_parecer.py; sc_perfil (chave Emulação, nome_de_agente); sc_rodada papel trocar em emulação; workflows ci.yml e status.yml.
- Estados e transições: etapa aberta (abrir) para encerrada (decidir aceitar, rejeitar ou sem-aceite); corrigir mantém aberta; parecer registrado por SHA (níveis A, B, C e E de emulação); decisão aceitar exige atestado APROVADO e parecer do mesmo SHA com cauda só de sociedade/; quem muda é a pessoa que decide (por ou git config user.name, nunca nome de agente).
- Fontes de verdade e derivados: fonte é sociedade/registro.json (eventos); derivados são estado.md e estado.html, a linha de evolucao.md, a cópia pareceres/parecer-ID.md e os status portao e aceite (calculados no PR a partir do registro e do atestado do head). O atestado do portão é fonte da prova local.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| Motivo C33: etapa trivial fecha só com os comandos do README | S2: `sc_init.py`, `sc.py ordem`, `abrir`, `entregar`, `revisar`, `revisar --parecer`, `decidir aceitar --por`, `estado` num repositório temporário: etapa encerrada, marca de emulação, linha em evolucao.md. S17: no arranjo com worktree a instrução do decidir não fecha (achado R-2) | executada |
| B01 ciclo abrir, revisar --parecer e decidir; sem nome padrão | S2 (recusa sem por, com Claude e com Gandalf), S5, S7, S14, S17; `python3 -B -m unittest tests.test_ciclo` verde | executada |
| B02 modo emulação | S2 e S4 (marca e independência não), S11 (chave desligada), S16 (leitura da chave no perfil real e variações); `tests.test_emulacao` e sondas DG-04 verdes | executada |
| B03 delegação conferida pelo log do Claude, falha fechada | S3: `sc.py conferir` e `sc.py sessao claude --sessao` com transcrições sintéticas (ausente, ilegível, subagente, mínimo) | executada |
| B04 estação 5 sem passo manual | S2: `lint_parecer.py` e `sc.py revisar --parecer` registram e copiam o parecer; `tests.test_contrato_modelos` verde | executada |
| B05 status portao e aceite calculados | S1 (script da base isolado), S13 (ramos, heads, atestado adulterado), S17b (verde no fluxo com worktree e pasta da etapa); `tests.test_status` verde | executada |
| B05 proteção da main exige ci, portao e aceite; PR de teste bloqueado | sem rede e sem acesso ao GitHub; nenhum verificador somente-leitura no candidato (achado R-5) | não verificada |
| B06 cauda de governança | S5a (produto depois do parecer recusa), S13 e S17b (cauda só de sociedade/ passa); `tests.test_cauda` verde | executada |
| B07 CI honesto com pipefail | S12: passo real do validador do ci.yml rodado com `bash -eo pipefail` e validador falhando sai 1; controle sem pipefail sai 0; `tests.test_ci_pipefail` verde | executada |
| B08 ID de etapa validado só para etapas novas | S9: `sc.py abrir` recusa Soma, quebra de linha, hífen inicial, 41 caracteres, acento, sublinhado, ponto, espaço, vazio e E1; aceita 40 caracteres | executada |
| B09 sondas DG-01 a DG-05 | `python3 -B -m unittest discover -s tests/adversarial -t .`: 66 testes, 15 expectedFailure (DG-02 resto e DG-03), nomes com DG0N, A-1 a A-7 verdes | executada |
| B10 métricas e linha de evolucao.md | S2 (linha com as 13 colunas da tabela atual), S15; `tests.test_metricas` verde | executada |
| B10 linha da própria etapa 0 gravada pelo script | só acontece na decisão de Odival, depois deste parecer | não verificada |
| Atestado e números declarados | A: `sha256sum` e recálculo do atestado_hash conferem; 46 artefatos idênticos ao HEAD; 610 testes pelo carregador do unittest; produto +1379 linhas; `validar_pacote.py` válido | executada |

### Matriz de cobertura
| Critério | L1 motivo | L2 ponta a ponta | L3 estados | L4 escape | L5 entradas | L6 concorrência | L7 fontes | L8 retorno |
|---|---|---|---|---|---|---|---|---|
| Motivo C33 | S2, S17 | S2, S17b | S14 | S5 | S9 | S8 | S17 | A, T |
| B01 ciclo | S2, S14 | S2 | S7, S8c, S14 | S5, S10 | S6, S9 | S8, S8b, S8c | S6, S17 | T (test_ciclo, fumaça lida e rodada) |
| B02 emulação | S2, S4 | S2 | S4, S11 | S4, S16 | S16 | n/a (só leitura do perfil) | S2 (painel), S11 | T (test_emulacao, DG-04) |
| B03 log do Claude | S3 | S3 | n/a (sem estados) | S3 (subagente no lugar da sessão, id inválido) | S3 (ausente, ilegível) | n/a (só leitura) | lida (conferir --registrar não exercitado) | T (test_sessao_claude) |
| B04 estação 5 | S2 | S2 | S7 | lida (lint_parecer) | T (A-7, DG-05) | n/a (um arquivo, sem trava própria) | S2 (cópia em pareceres) | T (test_contrato_modelos) |
| B05 status | S1, S13 | S17b | S13 | S13, lida (status.yml) | S13 (head inválido, ramo inválido) | n/a (jobs sem escrita) | S17 | lida (sem gh api, sem verificador da proteção) |
| B06 cauda | S5a | S17b | S13 | S5 | S13 | n/a (git somente leitura) | S13 | T (test_cauda, DG-02) |
| B07 CI | S12 | lida (CI real fora de alcance) | n/a (sem estados) | S12 (controle sem pipefail) | n/a (sem entradas) | n/a (passos sequenciais) | lida (passo Resumo) | T (test_ci_pipefail) |
| B08 ID | S9 | S9 | n/a (validação pura) | S9 | S9 | n/a (sem escrita) | n/a (sem derivados) | T (test_id_etapa) |
| B09 sondas | T-adv | T-adv | lida | lida | lida | n/a (testes isolados) | n/a (sem fontes) | T-adv |
| B10 métricas | S2 | S2 | n/a (cálculo puro) | S15 | lida (ler_jsonl_estrito) | n/a (gravação única no decidir) | S2 | T (test_metricas) |
| Atestado e números | A | n/a (não é fluxo) | n/a (sem estados) | n/a (sem opções) | A | n/a (arquivo congelado) | A | A |

### Sondas executadas
Todas com dados sintéticos, em repositórios temporários fora da cópia; nenhuma alterou a cópia.
- S1: sc_status.py e sc_registro.py copiados sozinhos para uma pasta, como o passo "script da base" do status.yml, rodados contra a cópia: funcionam (vermelho esperado, sem decisão no candidato).
- S2: fluxo do README do zero (sc_init, ordem, abrir, entregar, revisar, revisar --parecer, decidir, estado). Aceite marcado em emulação, independência não, não elegível, painel marcado.
- S3: transcrições sintéticas em SC_CLAUDE_PROJETOS; conferir marca feito com 2 delegações e mínimo 2, não feito com mínimo 3, log corrompido, sessão ausente, subagente no lugar da sessão e id com barra.
- S4: fornecedor do implementador sobreposto por --implementador e fornecedor autodeclarado do revisor, com emulação ligada e desligada (achado R-1).
- S5: decidir com head que tem produto depois do parecer (recusa) e com head digitado errado (aceita contra o HEAD; achado R-4).
- S6: aceitar recusado por achado bloqueador aberto deixa evidência gravada (O-1).
- S7: corrigir e depois aceitar o mesmo SHA sem nova revisão: aceito (decisão legítima de Odival; não é achado).
- S8, S8b, S8c: dois aceitar simultâneos (decisão duplicada em 2 de 4 rodadas, O-2); corrida aceitar e rejeitar em 6 rodadas sem estado incoerente; intercalação forçada: o registro recusa decisão em etapa encerrada.
- S9: IDs de etapa. S10: nomes de decisor. S11: Nível C com emulação desligada. S12: passo do validador do CI com pipefail. S13: status por ramo, head e atestado adulterado. S14: etapa aberta pelo legado fechada por decidir (recusa até haver evidências, como prevê a abertura da sessão 1). S15: métricas negativas. S16: chave Emulação no perfil real e em variações; validar_perfil. S17 e S17b: fluxo com worktree, com a pasta canônica e com a pasta do worktree.
- T: `python3 -B -m unittest` dos módulos novos (test_ciclo, test_cauda, test_id_etapa, test_status, test_emulacao, test_sessao_claude, test_metricas, test_contrato_modelos, test_ci_pipefail): 212 testes OK. T-adv: sondas adversariais, 66 testes OK com 15 expectedFailure.
- A: atestado conferido pelo hash (sha256 do arquivo be6c7be9...; atestado_hash recalculado confere; 46 hashes de artefatos iguais aos arquivos do HEAD da cópia; commit e base do atestado iguais aos da ordem de revisão). A suíte completa não foi repetida (Q70): o atestado existe e não diverge.
- Só lidos, sem execução: os diffs de sc.py, sc_ciclo.py, sc_status.py, sc_metricas.py, sc_sessao.py, sc_conferir.py, sc_registro.py, sc_resumo.py, sc_rodada.py, sc_perfil.py, validar_perfil.py, lint_parecer.py, sc_passagem.py, SKILL.md, references, README, CHANGELOG, adapters e os workflows; a semântica do evento pull_request do GitHub Actions (achado R-3).

### Itens deixados para Odival, graduados
- O PR pode alterar o próprio status.yml: confirmado por leitura (o evento pull_request usa o workflow do próprio PR), não executado no GitHub; relevante, achado R-3.
- Ramos jules/* ficam vermelhos: confirmado por S13 (também claude/*); opcional, achado O-5.
- Nível C fora da emulação: confirmado por S11; não elegível, como manda a D-RT-001; opcional, achado O-3.
- Recorte Claude* do decisor: confirmado por S10; opcional, achado O-4.
- Head que não resolve cai no HEAD: confirmado por S5b; relevante, achado R-4.

### Achados
- [relevante] L4 e L1 · R-1 · Condição: no caminho novo, `sc.py revisar --parecer --implementador Gandalf:OutraEmpresa` sobrepõe o fornecedor que o perfil dá ao implementador, e o fornecedor que o revisor declara no próprio parecer não é conferido com o perfil. Efeito (S4): com emulação desligada, revisor Anthropic contra implementador Anthropic sai Nível A, independência sim e etapa elegível à publicação (D-RT-001 burlada por comando documentado); com emulação ligada, a etapa sai marcada "aceite em emulação", mas com elegivel_publicacao true, contrariando o "nunca elegível" da sonda DG-04 e do comentário do registro. Critérios: B02 e DG-02 (parte B01). Evidência: S4. Correção esperada: fornecedor do implementador só pelo perfil (ou recusa da divergência), encerramento nunca elegível com a chave ligada e sonda do caminho novo no B09 (sc_ciclo.py:171-173; sc.py:225; sc_registro.py:580; sc_ciclo.py:308-313).
- [relevante] L1, L2 e L7 · R-2 · Condição: arranjo com worktree, o da própria m0 (sc_worktree e pasta-sociedade canônica). Efeito (S17): abrir, entregar, revisar e decidir gravam registro, atestado, parecer e evolucao.md na sociedade/ do checkout principal, mas o decidir manda `git add sociedade/` no worktree da etapa, onde não há nada a commitar; o job aceite fica vermelho ("sem sociedade/registro.json no head"). Só fecha com cópia manual (que a B10 conta como edição manual) ou com `--pasta-sociedade` do worktree nos quatro comandos (S17b, verde), o que nem o README nem a ordem dizem. Ficam duas cópias do registro, a canônica e a do PR (fonte dupla, DG-01). Critérios: motivo C33, B01 e B04. Correção esperada: o decidir leva o estado para o ramo da etapa, ou a instrução e o README documentam a pasta certa, com teste de fumaça em worktree (sc_ciclo.py:329-332; sc_status.py:119-128).
- [relevante] L4 e L3 · R-3 · Condição: o status.yml roda no evento pull_request, cuja definição vem do próprio PR (que pode editar o workflow e o passo "script da base"); portao e aceite leem atestado e registro do head sem conferir o atestado_hash nem cadeia do registro. Efeito: S13 mostra portao verde com o commit do atestado trocado num commit só de sociedade/; a sonda DG-02 já registra a decisão forjada (expectedFailure, B15 e B18). Critério: B05. Correção esperada: B15 e B18 incluírem o status.yml e o hash do atestado; Odival exigir revisão de CODEOWNERS em .github/ e sociedade/ na proteção (.github/workflows/status.yml:7-8 e 31-43; sc_status.py:95-112).
- [relevante] L5 · R-4 · Condição: `decidir --head` com referência que não resolve. Efeito (S5b): a decisão é tomada contra o HEAD sem aviso; com o head pretendido (main com produto depois do parecer) a recusa viria (S5a). O job aceite reconfere no PR, o que atenua. Critério: B01 e B06. Correção esperada: head informado e não resolvido vira erro (sc_ciclo.py:276).
- [relevante] L8 · R-5 · Condição: a ordem (F2 e F4) pede função que publica portao e aceite via gh api statuses, com gh simulado, um verificador somente-leitura da proteção da main e o decidir publicando aceite. Efeito: o candidato entrega jobs do Actions ("caso B"), não traz verificador da proteção e o decidir não publica; não há na cópia decisão de Odival ou do Círdan aprovando a troca de contrato, que a ordem manda devolver a eles. Critério: B05. Correção esperada: registrar a decisão da troca (o desenho em Actions funciona, S17b) e entregar ou adiar formalmente o verificador da proteção (sc_status.py:1-18; sc_ciclo.py:10; README.md:78).
- [relevante] L8 · R-6 · Condição: a skill sc-revisao manda registrar o parecer com sc_rodada.py parecer e diz que ele recusa revisor do mesmo fornecedor. Efeito: contradiz o ciclo novo (o papel barbarvore.md cita sc.py revisar --parecer) e o modo emulação, e aponta para o caminho legado declarativo (DG-02). Critério: B01 (skills e papéis citam só o ciclo novo). Correção esperada: trocar a linha pelo comando novo (sc-revisao/SKILL.md:46).
- [opcional] L7 · O-1 · aceitar recusado por achado bloqueador aberto deixa evidencia_registrada gravada, com o decisor como verificador (S6); checar as condições antes de gravar (sc_ciclo.py:298-305).
- [opcional] L6 · O-2 · dois decidir aceitar simultâneos gravam duas decisões em 2 de 4 rodadas (S8); o registro recusa decisão em etapa encerrada (S8c), então o efeito é só duplicata; decisão e encerramento numa mutação só (sc_ciclo.py:309-315).
- [opcional] L3 · O-3 · com emulação desligada, parecer Nível C do mesmo fornecedor fecha a etapa não elegível (correto), mas o painel mostra só "aceitar", sem "independência: não" (S11); vai para a B19 (sc_resumo.py:105-109).
- [opcional] L4 · O-4 · recorte do decisor inconsistente: "Claude Monet" e "Cláude" recusados, "Gandalf Silva" e "Bilbo Bolseiro" aceitos; bloqueia pessoa real chamada Claude (S10) (sc_perfil.py:167).
- [opcional] L4 · O-5 · PRs de ramos jules/* e claude/* ficam vermelhos em portao e aceite (S13); só bloqueia se mirarem a main protegida; restringir o workflow a etapa/* ou à base main (sc_status.py:41-44).
- [opcional] L5 · O-6 · minutos e intervenções negativos são aceitos e gravados em evolucao.md (S15) (sc.py:235-237).
- [opcional] L2 · O-7 · o sc_init sugere `sc.py ordem --etapa E1`, ID que o abrir agora recusa pela B08 (S9) (sc_init.py:240).
- [opcional] L2 · O-8 · nem o perfil-modelo nem a SKILL documentam a seção "Modo emulação" e a linha da chave; só o código a descreve (assets/perfil-modelo.md).

### O que não verifiquei
- O CI no GitHub para o SHA fb3ae42 e o resultado real dos jobs portao e aceite: a ordem de revisão proíbe rede.
- A proteção da main (ci, portao, aceite) e se um PR de teste fica bloqueado: configuração do repositório, fora da cópia.
- O registro canônico da etapa m0-destravar e como ela foi aberta: fica fora da cópia; S14 só simula a abertura pelo legado.
- A linha da própria etapa 0 em evolucao.md e o status aceite no SHA final: acontecem depois deste parecer, na decisão de Odival.
- A B03 com transcrições reais do Claude Code: usei só transcrições sintéticas (ler ~/.claude ficaria fora da pasta permitida).
- A suíte completa do pacote: não repetida (Q70), porque o atestado existe, confere pelo hash e não diverge do HEAD.
- Os testes do legado alterados (test_rodada, test_parecer e outros com uma linha) foram só lidos no diff.
