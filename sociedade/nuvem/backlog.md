# Backlog único da sessão em nuvem — rascunho do lote 1 (03/10/2026)


## Fila fora da nuvem, em ordem de prioridade (Odival, 03/10/2026)

| # | Etapa | Pedido ou itens | Notas |
|---|---|---|---|
| 0 | troca do perfil | Formação real no `sociedade/perfil.md` e desligar a chave `emulacao` | Primeiro passo da primeira etapa local |
| 1 | **d1-design** | "Quero que o app tenha uma cara moderna, sóbria e acolhedora, com uma referência visual que eu aprovo e que vale para todas as telas, começando por extratos, resultado e diagnóstico." | Q169: referência aprovada, Legolas, capturas em 360 px |
| 2 | **a2a** | Conferência individual (T10) e catálogo com fonte (seção 6); correções do teste de Odival com os extratos mensais | B17a (PDFs sintéticos, Q167), B17c |
| 3 | **a2b** | Entrevista (T03–T07: PGSI, complementares, financeiro, relato) | **B14**, **B15r** |
| 4 | a3 | Documentos e privacidade (B18–B20) | — |
| 5 | a4 | Publicação (B21–B23) | Só com o "vai" de Odival |
| 6 | final | Revisão completa da 4.0.0, CHANGELOG, devolução da cópia do pacote (C40) | Formação real |
| — | depois | B16, B17, resíduos da a1 e da fechamento-nuvem | — |

**B15r — resíduo da B15 (parecer da fechamento-nuvem):** atestado escrito à mão com hash recalculado ainda sai "feito" no `conferir` (o hash é SHA sem chave e o commit não é conferido); `sc_rodada fatia --fechar --prova` e `sc_passagem` gravam `exit_code=0` declarado; `_nome_do_perfil` por igualdade exata ("Revisor", "GPT", "Gemini" passam como pessoa); `verificar_workflows` só cobre `.github/workflows/`; o job `portao` não confere o hash. Correção: o `entregar` grava o hash no registro, ou o CI reexecuta o portão; evidência declarada marcada como tal. Também: uma lista só de termos de consumo (validador e portão); `sc.py revisar` com o projeto do repositório principal e com a regra de rede clara; script de contagem de linhas (Q168); grupo com total e 0 linhas; banco nulo num mês.

**Fontes:**
- revisão de 25–27/09 (`docs/revisao-claude/`): achados DG-01 a DG-36, etapas G0, E1–E18 e S0, decisões P01–P29;
- entrevista C01–C61 (`sociedade/entrevista-nuvem-2026-10-03.md`).

**Onde cada item entra:**

| Sigla | Momento |
|---|---|
| **P** | Preparo local |
| **E0** | Etapa 0, que destrava o método |
| **A1–A4** | Junto com a etapa do app |
| **F** | Sessão final |
| **S** | Se sobrar |
| **X** | Fora, com motivo |

**Regras de uso:**
- Na nuvem, um item só é antecipado se travar a etapa corrente, com o motivo registrado (C39).
- Se o saldo apertar, cortam-se as etapas do app antes dos itens do pacote (C31). Com o saldo em US$ 10, roda só a sessão final (C60).
- "Alto impacto" significa que a Galadriel revisa a fatia antes do portão (C17).
- O especialista indicado é uma sugestão; quem decide a fatia é a ordem.

**Cobertura do critério máximo (C05):**

| Achado | Item que resolve |
|---|---|
| DG-01 | B01 |
| DG-02 | B01 e B15 |
| DG-03 | B11 e B14 |
| DG-04 | B02, com a marca de emulação (independência real fica para a produção, R6) |
| DG-05 | B04 |
| DG-06 | B19 |
| DG-07 | B15 |
| DG-08 | B18 |
| DG-09 | B11 |
| DG-10 | B14 |
| DG-11 | B11 |
| DG-12 | B06 e B14 |
| DG-13 | B07 |
| DG-14 | X1 |
| DG-15 | B21 |
| DG-16 | B02 e B16 |
| DG-17 | B14 e B23 |
| DG-18 | X2 |
| DG-19 | B22, com a instalação local (C53) |

---

## Preparo local (P), nesta conversa, lote 3

| ID | Item | Origem | Aceite verificável |
|---|---|---|---|
| P1 | Encerrar a ARR sem aceite, ensaiando antes numa cópia | P13, G0, DG-01, C21 | Evento de encerramento com exceção Q146 no registro; o painel mostra "encerrada sem aceite" |
| P2 | Conter o DG-36 no projeto de campo privado (fora deste repositório) | C54, G0 passo 0(a) | Tratado por Odival; nenhum arquivo de dados aberto |
| P3 | Arquivar a governança antiga (R5) | R5, DG-21 | `sociedade/arquivo/` com histórico, `rm`, diagnóstico, planejamentos, `decisoes.md` Q01–Q145 e `regras-vigentes`; novo `decisoes.md` a partir da Q146 |
| P4 | Transcrever as decisões Q146+ (arquivo `decisoes-q146.md` deste lote) | C50 | Q146 em diante no `decisoes.md` enxuto |
| P5 | Versionar `docs/revisao-claude/` e a entrevista | G0 passo 0(b) | Commit na `main`; push só com confirmação |
| P6 | Repositório `aposte-em-voce` com cópia do pacote 3.0.0, `sc_init`, 9 agentes, `settings.json`, CI com `pipefail` e testes do pacote, e prompts | C10, C14, C20, C34 | Projeto instalado sem erro; agentes válidos; CI verde no primeiro PR |

## Etapa 0 — m0-destravar: só o que impede uma etapa de fechar (C06, C33)

A etapa 0 roda pela formação emulada. Seu último passo é fechar a si mesma com o comando que ela criou.

| ID | Item | Origem | Aceite verificável | Especialista | Alto impacto |
|---|---|---|---|---|---|
| B01 | **Ciclo da etapa no `sc.py`.** `sc.py abrir` (a partir da ordem aprovada) e `sc.py decidir aceitar\|corrigir\|rejeitar\|sem-aceite`. O encerramento sai do `sc_rodada`. A decisão grava o usuário real, nunca um nome padrão. SKILL e papéis citam só o ciclo novo | DG-01, DG-02 (parte), E4 F1, C28 | Teste de fumaça: uma etapa trivial fecha só com os comandos do README. A etapa 0 fecha por ele | Elrond | sim |
| B02 | **Modo emulação.** Chave `emulacao` no perfil. Com ela, o parecer do Barbárvore do mesmo fornecedor vale como aceite, marcado "aceite em emulação" no registro e no painel; R1–R3 aceitam um fornecedor só, com aviso, e a troca é gravada com motivo "emulação" (R4). Nunca conta como revisão independente | C12, C13, C43, C44, DG-04, DG-16 (parte) | Testes: com a chave desligada, D-RT-001 e R1–R3 como hoje; com ela ligada, aceite marcado e independência "não" | Elrond | sim |
| B03 | **Delegação conferida pelo log do Claude.** `sc.py sessao claude` lê `~/.claude/projects/…/subagents/agent-*.jsonl`. As entregas `delegacoes claude` e `conversa_nova claude` entram no `conferir`. Se não conseguir ler o log, a conferência falha fechada | C19, DG-22 (parte), DG-30 (parte) | Teste com transcrições sintéticas; log ausente reprova | Aragorn | não |
| B04 | **Estação 5 de ponta a ponta.** O modelo de parecer passa no `lint_parecer`. Teste de contrato: todo `*-modelo.md` preenchido passa no seu analisador. `revisar`, parecer e registro funcionam sem passo manual | DG-05, E1 F3 | Teste de contrato verde; revisão da própria etapa 0 registrada sem edição manual | Galadriel | não |
| B05 | **Status no GitHub.** O portão publica o status `portao` no SHA, com o hash do atestado. O `decidir` publica `aceite`. A proteção da `main` exige `ci`, `portao` e `aceite` | C42, C30, R3 | Teste com `gh` simulado; PR de teste bloqueado enquanto faltar algum dos três | Aragorn | sim |
| B06 | **Cauda de governança.** Commits posteriores ao SHA revisado só passam se tocarem apenas `sociedade/` (automatiza a Q145 `sem_alto`) | C41, DG-12 (parte) | Teste: commit de produto depois do parecer derruba o parecer; commit só de `sociedade/` não derruba | Elrond | sim |
| B07 | **CI honesto.** `pipefail` em todos os passos e um teste que reprova pipe sem `pipefail`. O CI do app roda também os testes e o validador do pacote copiado | DG-13, E1 F2, C20 | Um commit de demonstração com o validador falhando deixa o job vermelho | Galadriel | não |
| B08 | **ID de etapa validado** (`^[a-z0-9][a-z0-9-]{0,39}$`), só para etapas novas | DG-23, E1 F4 | Sonda verde | Elrond | não |
| B09 | **Sondas dos críticos.** Um teste por DG-01 a DG-05: verdes os que a E0 fecha; os demais com `expectedFailure` até a etapa deles | E1 F1 (parte), CR6 | Pelo menos 5 sondas com o número do DG no nome | Galadriel | não |
| B10 | **Métricas por etapa.** Comandos do método, erros, edições manuais em arquivos de controle, intervenções e minutos de Odival. O `decidir` resume no evento, com uma linha em `evolucao.md` | C35, C51, E4 F4, E15 (parte) | Linha da própria etapa 0 gravada pelo script | Aragorn | não |

## Junto com A1 — base e parser

| ID | Item | Origem | Aceite verificável | Especialista | Alto impacto |
|---|---|---|---|---|---|
| B11 | **Portão amarrado.** Comando e timeout só do perfil canônico (recusa `--comando-teste`). Árvore suja, 0 testes ou todos pulados reprovam. Hash do perfil e commit no atestado. Caminhos com `core.quotepath=off -z` e normalização NFC | DG-03 (árvore suja), DG-09, DG-11, E2 F1–F3, C30 | Sondas DG-09 (3 casos), DG-11 e árvore suja verdes | Galadriel e Aragorn | sim |
| B12 | **Simulação "3 tentativas" (Q12).** O Círdan planta um problema numa fatia; o executor deve parar e devolver depois da 3ª hipótese | C18 | Comportamento registrado como atrito ou acerto | Círdan planta | não |
| B13 | **Primeiro uso do Jules emulado** (teto 3, janela de 45 min, portão do Jules) em tarefa mecânica: gerar os PDFs sintéticos | C15 | Tarefas registradas; o portão do Jules aprova ou reprova com motivo | Jules (Haiku) | não |

**Antecipados da m0 para a A1 (C39, Odival em 03/10/2026; o contorno se repetiria em toda etapa):**

| ID | Item | Origem | Aceite verificável | Especialista | Alto impacto |
|---|---|---|---|---|---|
| B11a | **`sociedade/` canônica no worktree da etapa.** Durante a etapa, `decidir`, `revisar --parecer`, `conferir --registrar` e `estado` gravam e leem a `sociedade/` do worktree da etapa; o `sc.py conferir` expõe `--pasta-sociedade`; nenhum comando grava no checkout principal | Achado R-2 da m0, atrito do `conferir --registrar`, proposta 3 aceita | Teste: etapa em worktree fecha sem cópia manual; conferência gravada no registro do ramo | Elrond | sim |
| B11b | **Textos do ciclo novo.** `sc-revisao/SKILL.md` registra o parecer por `sc.py revisar --parecer`, não por `sc_rodada parecer` | Achado R-6 da m0 | Nenhuma skill cita `sc_rodada parecer` | Galadriel | não |
| B11c | **Portão por área** (app e pacote) no perfil, junto com a B11, quando o app ganhar `package.json` | Proposta 2 aceita na m0 | O portão roda o comando da área sem `--comando-teste` | Galadriel | não |
| B11d | **Modelo de PR** com a linha "conferi o diff de `.github/` e `sociedade/pareceres/`" | Proposta 5 rejeitada; substituta | Linha presente no `.github/pull_request_template.md` | Galadriel | não |

## Junto com A2 — catálogo, confirmação, PGSI e relato

| ID | Item | Origem | Aceite verificável | Especialista | Alto impacto |
|---|---|---|---|---|---|
| B14 | **Commit amarrado e ordem com hash.** `sc.py ordem aprovar` grava `ordem_aprovada` com SHA-256. O `revisar` clona o commit do atestado (não `git archive`), tira do pacote `AGENTS.md`, `.claude/`, `.codex/`, `.agents/` e `.gitattributes` do candidato e injeta o protocolo. O parecer exige `commit:` e `pacote:`. Trava temporal. **Da m0 (Odival, 03/10/2026):** `--head` que não resolve é recusado, sem cair no HEAD (achado R-4 do parecer da m0) | DG-03, DG-10, DG-12, DG-17 (parte), DG-30 (parte), E3 F1–F4, P14 | Sondas verdes; ordem alterada depois da aprovação é recusada; commit novo depois do parecer o derruba | Elrond, Aragorn e Galadriel | sim |
| B15 | **Aceite não forjável.** O `decidir` exige atestado oficial do SHA, parecer do mesmo SHA e os checks. Saem do legado os argumentos declarativos (`--exit-code`, `--veredito` sem arquivo, `--implementador`). O `sc_rodada encerrar` passa a exigir o evento `decisao`. A conferência verifica o hash dos atestados e recusa atestado escrito à mão. **Da m0 (Odival, 03/10/2026):** (a) `--implementador Nome:Fornecedor` não sobrepõe o fornecedor do perfil, e o fornecedor declarado pelo revisor é conferido (R-1); (b) o `aceite` confere o hash do atestado e recusa atestado alterado na cauda (R-3); (c) o `aceite` fica vermelho se o PR alterar `.github/workflows/` sem que a ordem o liste no escreva-só (R-3, no lugar da proposta 5 rejeitada); (d) o `decidir` recusa como decisor todos os nomes de papel e de modelo do perfil, não só "Claude" | DG-02, DG-07, E4 F5, E7 | Sondas AUD-01 e AUD-05 verdes; aceite forjado numa sessão só é recusado | Elrond | sim |
| B16 | **Simulação "cota do executor".** O Gandalf emulado fica sem cota no meio da etapa: troca pela tabela B4, modo reduzido (Q13, Q74) e substituição declarada (P18), com retomada pelo estado salvo | C18, P18, DG-16 | Evento de substituição no registro e no painel; a etapa continua | Círdan | não |
| B17 | **Executor local emulado uma vez** (Haiku), numa fatia mecânica | C16 | Módulo exercitado; o que não serve fica registrado | Executor local | não |
| B17a | **PDFs sintéticos (F3 da a1, pela Q167).** O Elrond desenha um layout de referência; o Jules replica nos 6 layouts e casos difíceis; esperado da tabela de origem, nunca da F2. Material de consulta: ramo `jules/a1-parser-pdfs` (`228d049`) | a1-parser, E5 não feita | Meta da seção 14 com `tests/leitura` verde | Elrond e Jules | não |
| B17b | **Resto do achado E3.** `atestado_aprovado` do `sc_conferir` aplica `forma_do_atestado` (recusa atestado avulso e `--area` parcial); `sc.py revisar` sem `--parecer` usa o worktree da etapa e leva ordem, atestado e perfil à cópia | a1-parser, parecer reduzido e atritos da estação 5 | Sondas verdes | Aragorn | sim |
| B17c | **Itens menores da a1** (revisões internas): prefixo D/C colado; valor sem marca com status `suficiente` sem saldo; "50,00 D" na coluna Crédito; razão de 95% em inteiro; erro interno como "corrompido"; testes de 30 MB e 200 páginas; build e lint com timeout; `sc_init` e `perfil-modelo` com "Portão por área"; `references/comandos.md` com a exigência do atestado 1.3.0 | a1-parser | Cada um com teste ou texto | Elrond, Aragorn | não |

## Junto com A3 — documentos, privacidade e CSP

| ID | Item | Origem | Aceite verificável | Especialista | Alto impacto |
|---|---|---|---|---|---|
| B18 | **Registro com cadeia de hash** (`seq`, `anterior`, `hash`), migração com teste de ida e volta e alerta no painel | DG-08, DG-33, E8, P15, C29 | Sonda de reescrita ingênua verde; 3.000 eventos em até 5 s; a migração do registro real dá o mesmo estado derivado | Elrond | sim |
| B19 | **Painel honesto.** O `sc_resumo` usa a mesma função de condições do `decidir`; registro ilegível vira alerta; bloco "decisões pedidas a você"; marcas de emulação e de substituição | DG-06, E5 | Sondas DG-06 (3 casos) verdes; teste de arquitetura | Legolas | não |
| B20 | **Aceite condicional e simulação "revisor indisponível".** Estado `aceite_condicional` com evento `revisao_devida`; integra, mas não publica; teto de 1 aberto; rejeição posterior reabre. Parecer marcado "revisor não calibrado" | C18, C62 (Q159), C63 (Q160), P24, E4 F2 | Simulação registrada; painel mostra a revisão devida e a idade; segundo aceite condicional recusado | Elrond | sim |

## Junto com A4 — pré-visualização e publicação

| ID | Item | Origem | Aceite verificável | Especialista | Alto impacto |
|---|---|---|---|---|---|
| B21 | **Regras de aceite protegidas por teste.** Mutação nas funções de aceite, com meta de 85% ou mais de mutantes mortos, e teste ponta a ponta das seis estações | DG-15, E13 (versão leve), CR6 | Relatório de mutação; teste das estações verde | Galadriel | não |
| B22 | **Instalação e versões.** O `sc_init` grava a versão certa, o `marketplace.json` fica no lugar certo e `instalar.py --verificar` funciona. A instalação em si é local (C53) | DG-19 (parte) | Teste do `sc_init` com a versão; verificação simulada | Aragorn | não |
| B23 | **Garantias restantes do tier formal.** Etapa encerrada pode ser reaberta (estado) e "HEAD igual à base" é detectado | DG-17 (resto), DG-32 (parte) | Testes de reabrir e de HEAD igual à base | Elrond | não |

## Sessão final (F) — reserva de US$ 10 (C60)

| ID | Item | Origem |
|---|---|---|
| F1 | Revisão do diff acumulado do pacote, com o protocolo completo | C47 |
| F2 | `regras.md` final e Q146+ finais | C38, C49 |
| F3 | Proposta de ajuste das regras de leitura (Q21, Q99, Q128), com os números medidos | C52 |
| F4 | Relatório final, manual de uma página, CHANGELOG 4.0.0 e `VERSION` 4.0.0 | C48, C49 |
| F5 | Avisos de depreciação em `sc_rodada`, `sc_passagem`, na calibração e nos níveis; nenhum documento os cita como caminho normal | C28, E10a (parte) |

## Se sobrar (S), nesta ordem

| ID | Item | Origem |
|---|---|---|
| S1 | Antitoken fora do portão de produto; lista única de segredos com `github_pat_`, `AKIA` e `sk_live_`, cobrindo também `.env.*` | DG-28, DG-29, E14 |
| S2 | Textos dos papéis que levam o Gandalf a errar (`--fatia`, `--registrar`, `push_feito`) | DG-22 |
| S3 | `except: pass` e subprocessos sem timeout | DG-26 |
| S4 | Projeções `.md` sem trava em fatias paralelas | DG-24 |
| S5 | Revisor contaminável; adaptador do revisor sem Bash; sonda de barreira no Claude Code | DG-30, DG-31, E6 (parte) |
| S6 | Duplicações (perfil, git, segredos, worktree, revisão, modelos) | DG-25 |
| S7 | Máquina de estados mínima | DG-32, E9 |
| S8 | Acoplamento ao autor e ao domínio | DG-27 |
| S9 | POSIX declarado e higiene | DG-34, DG-35 |

## Fora (X)

| ID | Item | Motivo |
|---|---|---|
| X1 | Calibração B2 do Sol (DG-14, E11) | R6 e C08: sem Sol nesta execução |
| X2 | Campo (DG-18; Marco 3, E17 e E18) | Fora do escopo; o DG-36 é contido no preparo (P2) |
| X3 | Remoção do legado (E10b) | C28 manda deprecar, não remover |
| X4 | Regras com mecanismo e teto (E12) | Substituída pela página única (R5) e pela F2 |
| X5 | Instalação nas ferramentas (E16) | Conversa local depois (C53) |
| X6 | Apostas H3 (canário, cerimônia proporcional, prova por terceiro) | Fora; a revisão proporcional (C27) cobre parte da cerimônia |
| X7 | Etapa real do painel (P1, P22) | Substituída pelas etapas do app (C04) |
| X8 | *Spike* S0 | Resolvido pelas decisões C30, C42 e R3 |
| X9 | Sondas de barreira no Antigravity e no Codex reais (E6) | R6: só Claude |
| X10 | Mudanças grandes, como a Sociedade "v4" | Revogadas em 03/10 |

## Notas

As duas pendências do rascunho foram decididas: **C62 → Q159** (aceite condicional com salvaguardas) e **C63 → Q160** (Q135 segue suspensa, com marca).
