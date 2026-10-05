# Changelog

Versionamento semântico. Major: muda o comportamento a ponto de exigir ajuste nos projetos.

## 3.3.0 (05/10/2026)

Etapa `d1b-robustez`: fechamento dos resíduos da d1 no pacote, integridade estrita e processo honesto (Q176–Q182).

**Entrou**

- **A01 (@etapa estruturado e exclusão de self):** `sc_conferir.py` resolve pasta exclusivamente por metadados estruturados de workspace; descarta menções no corpo e exige `TypeName` de especialista ativo (Q182).
- **A02 (Cadeia de registro estrita):** `sc_registro.py` estabelece corte explícito gravado; eventos subsequentes sem `hash` ou `prev_hash` são corrompidos, inclusive na cauda.
- **A03 e A05 (Trava da troca e rollback):** `sc_rodada.py` serializa leitura, validação e escrita sob trava comum em `papel trocar` e `papel emulacao`, garantindo rollback e impedindo estado inconsistente.
- **A06 (Permissões de merge delimitadas):** `.claude/settings.json` e modelo delimitam `-s` e `-r` para negar apenas argumentos curtos sem afetar `--subject`, `--repo` e merges legítimos.
- **P1 (Passagem com autor e hora):** `sc.py passar` exige `--por`, carimba timestamp atual e exige `--nova-rodada --motivo` para repetições.
- **P2 (Ambiente honesto de revisão):** `sc.py revisar` valida `perfil.md` e `regras.md` contra HEAD (Q178), symlinka dependências e testa áreas sem rede.
- **P3 (Decisão e reconferência sem sobrescrita):** `sc.py decidir` exige `--motivo` para `corrigir|rejeitar`. Reconferência grava em arquivo próprio (`parecer-<etapa>-reconferencia.md`) e encadeia registros.

## 3.2.0 (04/10/2026)

Etapa `d1-design`: prontidão para a formação real e resolução das lacunas L1–L8.

**Entrou**

- **L1 (Emulação):** `sc_rodada.py papel emulacao ligar|desligar` com conferência estrita de R1–R3 e evento em cadeia de hash.
- **L2 (Execução):** `papel trocar --papel execucao` altera todos os especialistas ativos; alcança Jules e executores em espera.
- **L3 (Passagem):** `sc.py passar --etapa <ID> --para gandalf|barbarvore` imprime ferramenta, caminho e comando exato, gravando evento `passagem`.
- **L4 (Sessão):** `sc.py sessao codex` mede logs do Codex; `sc.py sessao antigravity` informa estado sem quebrar.
- **L5 e L6 (Formação real):** adaptadores e documentação alinhados a merge commit com autorização de Odival (Q174) e passagem entre ferramentas (Q175).
- **L7 (Ordem em worktree):** `sc.py ordem` grava no worktree da etapa quando ele existir.
- **L8 (@etapa no Antigravity):** resolução unívoca da conversa da etapa para conferência de delegações e conversa nova.

## 3.1.0 (03/10/2026)

Versão de transição: o que as sessões em nuvem de 03/10/2026 mudaram no método. A 4.0.0 sai depois da revisão do diff acumulado e das regras finais (F1–F5).

Etapa `fechamento-nuvem`, fatia 1: economia de contexto; o uso sai do log da sessão.

**Entrou**

- **Consumo pelo log** (`sc_sessao.py`): `sc.py sessao claude` soma, por agente e por modelo, entrada, cache escrito, cache lido e saída, no log principal e em `subagents/`. Deduplica por id de mensagem (também entre arquivos; com valores divergentes, fica o de maior saída), ignora `<synthetic>` e registro sem uso. O agente vem do `.meta.json` ou de "Para: <Papel>" no primeiro pedido. `--desde <ISO 8601>` mede só o trecho (fuso `Z` ou offset; sem fuso, UTC; inválido é erro). `--json` traz tudo.
- **`decidir` grava o consumo** (`sc_ciclo.py`, `sc_registro.py`, `sc_metricas.py`): `decidir aceitar` aceita `--desde`, grava `consumo` no evento `decisao_registrada` e acrescenta a coluna "Consumo (cache lido)" a `evolucao.md`, que ganha a coluna sozinha nas tabelas antigas (linhas antigas com `n/d`). Sem log, `n/d`. A linha nova entra na tabela, não no fim do arquivo.
- **Regras de economia** nos textos do núcleo e das skills: conversa curta com estado em arquivo e agente novo; saída curta (resumo e falhas) e leitura por trecho; retorno de até 2 KB no chat, com o detalhe em arquivo (revisa a Q99, antes 8 KB); cada agente lê só o que a ordem ou a subordem indicou (Q21).
- **Medir pelo log é permitido; estimar continua proibido** (ajusta a regra 8): o `validar_pacote.py` aceita "medir" com menção ao log e recusa estimar, calcular e relatar; `avaliacao-modelo.md` mantém a "Proibição Absoluta" e ganha a exceção.

Etapa `fechamento-nuvem`, fatia 3: integridade do aceite (B15 e B17b). **Adulteração detectada, não aceite à prova de forja.**

**Entrou**

- **`atestado_hash` conferido** (`sc_status.py`, `sc_ciclo.py`, `sc_conferir.py`): o `decidir`, a conferência (`atestado_aprovado`, que também aplica `forma_do_atestado`: recusa atestado avulso e `--area` parcial) e o status `aceite` recalculam o hash e recusam atestado sem hash ou com conteúdo alterado. O `decidir` grava o `atestado_hash` na decisão e o `aceite` confere que o atestado do head é esse.
- **Limite**: o hash é um SHA-256 sem chave. Um atestado reescrito à mão com o hash recalculado **continua aceito** até a reexecução do portão (o `sc.py entregar` no CI); só a adulteração por descuido ou sem refazer o hash é detectada. O status `portao` ainda não confere o hash.
- **`aceite` e `.github/workflows/`**: fica vermelho se o PR altera workflows sem que a ordem, com o hash da abertura, os liste no escreva-só.
- **Legado `sc_rodada`**: `evidencia` executa o comando e grava o código de saída medido (saem `--exit-code` e `--saida`); `parecer` vem de `--arquivo` com lint (saem `--veredito`, `--implementador`, `--revisor`, `--fornecedor`, `--criterio-ok`, `--nivel-independencia`); `encerrar` exige o evento de decisão, também com `--forcar`.
- **Independência**: o fornecedor do perfil prevalece sobre `--implementador Nome:Fornecedor` (declaração contrária é recusada) e o fornecedor declarado pelo revisor é conferido com o perfil. O `decidir` recusa como decisor papel, agente e modelo do perfil.
- **`sc.py revisar`** sem `--parecer` usa o worktree da etapa e leva ordem, atestado e perfil à cópia do revisor.

Etapa `m0-destravar`: uma etapa fecha só com comandos documentados.

**Entrou**

- **B01 · ciclo da etapa no `sc.py`** (`sc_ciclo.py`): `abrir` (a partir da ordem, com base que resolve), `revisar --parecer` (registra o parecer sem passo manual) e `decidir aceitar|corrigir|rejeitar|sem-aceite`. O encerramento não passa mais pelo `sc_rodada`. O `decidir aceitar` exige atestado aprovado e parecer válido do mesmo SHA, grava o nome de quem decide (`--por` ou `git config user.name`, nunca um nome padrão), a marca "aceite em emulação", as métricas e a linha de `evolucao.md`. `rejeitar` e `sem-aceite` encerram sem aceite; `corrigir` deixa a etapa aberta.
- **B06 · cauda de governança**: `parecer_vale`; commit de produto depois do SHA do parecer derruba o parecer, e commits só de `sociedade/` não.
- **B08 · ID de etapa validado** (`^[a-z0-9][a-z0-9-]{0,39}$`) em `abrir`, só para etapas novas; o ID legado segue nos demais comandos.
- **Ligações**: `sc.py sessao` repassa `--sessao` e `--projetos`; o `conferir` aceita `delegacoes | claude` e `conversa_nova | claude` ponta a ponta; o registro grava `commit` no parecer e na decisão, e `desfecho` no encerramento sem aceite; o parecer do `sc_passagem exportar-revisao` traz `- commit:` e passa no `lint_parecer`; teste de fumaça com uma etapa trivial.
- **Correção da revisão interna (F6)**: a chave `Emulação` falha fechada (só o valor único `sim` liga; comentário HTML, código indentado e títulos que só citam o modo são ignorados); o `decidir` recusa como decisor nome de agente do perfil e "Claude" (`--por` ou `git config user.name`), recusa `--head` anterior à ponta de `etapa/<ID>` e manda commitar `sociedade/` no ramo da etapa; o `revisar --parecer` recusa parecer de outra etapa ou de outra base.

Etapa `a1-parser`, fatia 1 (pacote "portão amarrado"): B11, B11a, B11b, B11c, B11d.

**Entrou**

- **B11 · portão amarrado ao perfil** (`sc_pre_devolucao.py`, `sc_perfil.py`, `sc.py`): `sc.py entregar` recusa `--comando-teste`; o comando e o timeout vêm só da seção "Portão por área" do perfil canônico. Reprovam árvore suja (qualquer mudança fora de `sociedade/`, rastreada ou não; ignorados pelo `.gitignore` não contam), a árvore mudar durante o portão, timeout, 0 testes e todos pulados. A contagem de testes é lida do `unittest`, do Vitest e do Playwright. O atestado (1.3.0) grava, por área, comando, timeout e contagem, e o SHA-256 do perfil e o commit. Caminhos com `git -c core.quotepath=off ... -z`, em NFC (também no `arquivos_em` do `conferir`).
- **B11c · portão por área**: sem `--area`, roda as áreas que base..HEAD toca; com `--area <nome>`, só aquela. Área do caminho = prefixo mais longo da tabela; `.github/` conta para todas.
- **B11a · `sociedade/` do worktree da etapa** (`sc_registro.localizar_sociedade_da_etapa`): `abrir`, `entregar`, `conferir --registrar`, `revisar --parecer`, `decidir` e `estado` leem e gravam a `sociedade/` do worktree da etapa, se existir, sem cópia manual; `--pasta-sociedade` vale antes. `sc.py conferir` aceita `--pasta-sociedade` e `sc.py estado`, `--etapa`.
- **B11b**: o `sc-revisao` manda registrar o parecer por `sc.py revisar --parecer`; nenhuma skill cita `sc_rodada parecer`.
- **B11d**: o modelo de PR ganha a linha "Conferi o diff de `.github/` e `sociedade/pareceres/`".
- **Sondas**: DG-03 (árvore suja) e DG-09 (3 casos) e DG-11 (NFD com espaço) verdes; as demais do DG-03 seguem `expectedFailure` até a B14.

**Correções da F1 (revisão interna, F1c)**

- O `decidir aceitar` e o status `portao` só aceitam o atestado do `sc.py entregar` (1.3.0: `portao.modo == por_area`, `portao.commit` igual ao `commit`, áreas rodadas e todas ok); um atestado avulso do `sc_pre_devolucao.py` com `--comando-teste` é recusado (`sc_status.forma_do_atestado`).
- O atestado grava `areas_tocadas` e `cobertura_completa`; `--area` roda uma área só, mas o atestado resultante não aceita decisão nem fica verde no status se faltar área tocada.
- `--no-renames` em `sc_pre_devolucao.py` e `sc_conferir.py`: na renomeação contam a origem e o destino (área da origem rodada; mover de `sociedade/` para fora acusa a governança).
- O `decidir` e o status exigem `portao.perfil_sha256` igual ao SHA-256 de `sociedade/perfil.md` julgado (disco no `decidir`, head do PR no status); perfil trocado só para rodar o portão é recusado. O portão não compara com o HEAD: durante a etapa o perfil do worktree fica sem commit.
- Testes que falham com código 0 reprovam; arquivo `assume-unchanged` ou `skip-worktree` (`git ls-files -v`) conta como árvore suja.

**Mudou**

- `sc.py entregar` não aceita mais `--comando-teste` (quebra: ajuste a seção "Portão por área" do perfil). O `sc_pre_devolucao.py` avulso mantém o comportamento antigo, salvo com `--portao-por-area`.

## 3.0.0 (25/09/2026)

Arrumação a partir do diagnóstico de 25/09/2026 (Q130–Q143): o método passa a ser curto, sem contradições com as decisões e conferido por script. Quebra compatibilidade (Q72).

**Entrou**

- **Pipeline de seis estações** (pedido, ordem, execução, conferência, revisão, decisão) no núcleo e no README.
- **`sc.py`**, um comando por estação: `ordem`, `entregar`, `conferir`, `sessao`, `revisar`, `estado`.
- **Conferência da ordem verificável** (`sc_conferir.py`, Q119): bloco ```entregas na ordem; cada entrega marcada como feita ou não feita, com o resultado gravado no `registro.json`.
- **Medição objetiva de sessão** (`sc_sessao.py`, Q141): Antigravity, Codex e Claude Code; passos, delegações, releituras e testes, sem conteúdo e sem estimativa de consumo.
- **Estado de uma tela** (`sc_resumo.py`): `sociedade/estado.md` e `estado.html`, que servem de painel no celular.
- **Portão por commit** (D01): inspeciona `base..HEAD` pela raiz do Git; atestado 1.2.0 com commit, base, arquivos e totais; reprova quando não há nada a inspecionar; compila em memória.
- **Papéis curtos**: um arquivo por papel, de até 2,5 KB, incluindo `papel-cirdan` e `papel-barbarvore` (Q116); protocolo de revisão com oito lentes e matriz de cobertura na skill `sc-revisao` (Q126); modelo de ordem com lista de entregas.
- **Checagens estruturais no validador** (Q102): tamanho de papéis e skills, carga de leitura do coordenador (até 12 KB), caminhos absolutos, links e termos de regras revogadas.
- `sc_sync_agents_md.py --ponteiros`: `CLAUDE.md` e `GEMINI.md` apontam para o `AGENTS.md` (Q62).
- CI no GitHub (`.github/workflows/testes.yml`, Q70).
- Correções da RM-1a (D02–D09): worktree preso à raiz e sem remoção de pasta alheia; R2 e R3 sem contorno; troca de papel sem modelos fixos, com autor e alteração de uma só linha; parecer com implementadores do registro; leitor do perfil tolerante.

**Saiu**

- Os 210 testes que só conferiam frases de documentos (Q102).
- As cópias das regras de cada papel: camadas "essencial" e "aprofundada", orquestração, seções do `LEIA-ME` do Antigravity (de 47 KB para 2 KB) e `papel-revisor.md` duplicado.
- Níveis numéricos, revisão externa por fatia e "escala tripartite" dos textos (Q17, Q84, D-RT-001).
- Revisor e modelos fixos nos scripts e adaptadores (M5).
- Agente revisor do Antigravity: revisão por outro modelo Google é interna (D-RT-001).

**Mudou**

- Executores locais viram módulo opcional (`modulos/executores-locais/`), fora do caminho de leitura (Q140).
- Teto de tarefas abertas do Jules: 3 (Q93, Q129).
- `sc_init.py` grava o perfil em `sociedade/perfil.md` (Q31), a partir do modelo único.
- Regra de medição: agente continua sem estimar; scripts medem contagens objetivas (Q141).

## 2.1.0 (24/09/2026)

Aceite formal da Fase A com ressalvas pelo Revisor Independente (Barbárvore, parecer A3) e autorização do usuário (Q65, Q68, Q72).

**Entrou**

- **Aceite da Fase A com ressalvas:** encerramento da Fase A após resolução da regressão A2-REG-01 no candidato `f4b6fe1` com suíte de 493 testes aprovados (1 ignorado justificado) e portão físico `sc_pre_devolucao.py` validado.
- **Marcação Experimental de Recursos Não Homologados (Q65):** identificação explícita de recursos não homologados no README e na documentação de cada recurso ("Experimental, não homologado (Q65)"): adaptadores (Antigravity, Antigravity CLI, Claude, Codex, Jules), portão do Jules, fatias paralelas, calibração de gatilho, simulação contábil da SC-E4 e executores locais.
- **Pendências Encaminhadas para a SC-RM:**
  - R03-006 (opcional) adiado formalmente para a rodada SC-RM (Q118).
  - Pendências A2-P01 a A2-P13 e apontamentos A3 consolidados para tratamento no ciclo seguinte de governança e arquitetura (SC-RM / Fase B).

## Etapas SC-E1 a SC-E5 e 2.0.0 a 1.0.0 (resumo)

O texto completo dessas entradas está no histórico do Git (tag `v2.1.0`, arquivo `sociedade-do-codigo-2.0.0/CHANGELOG.md`).

- **SC-E1 (21–22/09):** registro de eventos atômico (`registro.json`), continuidade, critérios e evidências, pareceres, exceções e encerramento; correções REV-001 a REV-017 e N1 a N11.
- **SC-E2 a SC-E5 (22/09):** regras gerais e acionamento natural, adaptadores, piloto simulado de conciliação, automação de passagens (`sc_passagem.py`).
- **Pacotes 1 a 4 e papéis (22–23/09):** portão pré-devolução, papéis em duas camadas, calibração do gatilho, portão do Jules, fatias paralelas, onboarding (`sc_init.py`).
- **2.0.0 (20/09):** reescrita a partir de 55 respostas do usuário: ativação explícita, rodada em fatias, independência por fornecedor, três severidades, regra de privacidade.
- **1.1.0 e 1.0.0 (19/09):** primeira versão e módulo de executores locais.
