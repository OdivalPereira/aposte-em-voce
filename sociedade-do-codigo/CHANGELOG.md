# Changelog

Versionamento semântico. Major: muda o comportamento a ponto de exigir ajuste nos projetos.

## Não lançado

Etapa `m0-destravar`: uma etapa fecha só com comandos documentados.

**Entrou**

- **B01 · ciclo da etapa no `sc.py`** (`sc_ciclo.py`): `abrir` (a partir da ordem, com base que resolve), `revisar --parecer` (registra o parecer sem passo manual) e `decidir aceitar|corrigir|rejeitar|sem-aceite`. O encerramento não passa mais pelo `sc_rodada`. O `decidir aceitar` exige atestado aprovado e parecer válido do mesmo SHA, grava o nome de quem decide (`--por` ou `git config user.name`, nunca um nome padrão), a marca "aceite em emulação", as métricas e a linha de `evolucao.md`. `rejeitar` e `sem-aceite` encerram sem aceite; `corrigir` deixa a etapa aberta.
- **B06 · cauda de governança**: `parecer_vale`; commit de produto depois do SHA do parecer derruba o parecer, e commits só de `sociedade/` não.
- **B08 · ID de etapa validado** (`^[a-z0-9][a-z0-9-]{0,39}$`) em `abrir`, só para etapas novas; o ID legado segue nos demais comandos.
- **Ligações**: `sc.py sessao` repassa `--sessao` e `--projetos`; o `conferir` aceita `delegacoes | claude` e `conversa_nova | claude` ponta a ponta; o registro grava `commit` no parecer e na decisão, e `desfecho` no encerramento sem aceite; o parecer do `sc_passagem exportar-revisao` traz `- commit:` e passa no `lint_parecer`; teste de fumaça com uma etapa trivial.

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
