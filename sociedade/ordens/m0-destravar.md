# Ordem m0-destravar — uma etapa fecha pela formação emulada só com comandos documentados

Para: Gandalf (Claude Code em nuvem, subagente `gandalf`, esforço high) · CONVERSA NOVA
Etapa: m0-destravar · Base: `3bff553` · Worktree: `~/.sociedade/trabalho/aposte-em-voce/m0-destravar` (já criado pelo Círdan com `sc_worktree.py criar`) · Ramo: `etapa/m0-destravar`
Aprovada por Odival em 03/10/2026, com os ajustes da seção "Ajustes da aprovação".
Especialistas: Elrond (F1, F4), Aragorn (F2), Galadriel (F3, F5) · Revisão interna (Galadriel): F1 (B02), F2 só a parte B05, F4 (B01 e B06) · Jules: nenhuma
Revisão independente: **completa** (`barbarvore`), marcada "aceite em emulação" e "revisor não calibrado"

## Objetivo
Pedido de Odival (`sociedade/nuvem/pedidos.md`, linha `m0-destravar`): "Quero que uma etapa da Sociedade feche pela formação emulada só com comandos documentados, com prova dupla, parecer ligado ao commit e a minha decisão registrada, e que esta própria etapa feche assim."

Como Odival percebe: a etapa trivial do teste de fumaça fecha só com os comandos do README do pacote, e **esta etapa** fecha com `sc.py decidir aceitar`, gravando o nome dele, a marca "aceite em emulação", as métricas e a linha de `sociedade/evolucao.md`, e publicando o status `aceite` no SHA.

## Leia só
1. Esta ordem.
2. `sociedade/nuvem/backlog.md`, seção "Etapa 0" (B01 a B10) e a tabela "Cobertura do critério máximo".
3. `sociedade/regras.md` (seções 2, 4, 5 e 7).
4. `sociedade/perfil.md` (seções "Modo emulação" e "Comandos").
5. `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/SKILL.md`.

Cada especialista lê, além disso, só os scripts e testes do seu escreva-só.

## Onde se mexe
Só em `sociedade-do-codigo/` e em `.github/`. O candidato **não altera** `sociedade/` (Q60), `docs/` nem `.claude/`. Prefixo abaixo: `S = sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`; `T = sociedade-do-codigo/tests`.

## Fatias (escreva-só disjuntos)
Ordem de execução: F1, F2 e F3 em paralelo (no máximo 3 subagentes ao mesmo tempo); F4 depois delas (integra os módulos); F5 por último.

1. **F1 · B02 modo emulação** · Elrond · **alto impacto** · escreva só: `S/sc_perfil.py`, `S/sc_rodada.py` (só a troca de papel e a conferência R1–R4), `S/sc_registro.py`, `S/sc_resumo.py`, `S/validar_perfil.py`, `T/test_emulacao.py` · aceite: com a chave `emulacao` desligada, D-RT-001 e R1–R3 como hoje (testes atuais verdes); ligada, R1–R3 viram aviso, a troca grava motivo "emulação", o parecer do mesmo fornecedor vale como aceite marcado "aceite em emulação" no registro e no painel, e independência = "não". A chave é lida da seção "Modo emulação" do perfil (`- **Emulação:** sim`).
2. **F2 · B03, B05 e B10 como módulos** · Aragorn · B05 de **alto impacto** · escreva só: `S/sc_sessao.py`, `S/sc_conferir.py`, `S/sc_status.py` (novo), `S/sc_metricas.py` (novo), `.github/workflows/` exceto `ci.yml` (só no caso B abaixo), `T/test_sessao_claude.py`, `T/test_status.py`, `T/test_metricas.py` · aceite:
   - B03: `sc.py sessao claude` lê também `~/.claude/projects/<projeto>/<sessão>/subagents/agent-*.jsonl`; as entregas `delegacoes | claude | <sessão> | <mínimo>` e `conversa_nova | claude | <sessão ou agente>` entram no `conferir`; log ausente ou ilegível reprova (falha fechada). Teste com transcrições sintéticas.
   - B05, **primeiro passo da F2:** teste se a sessão publica status de commit: `gh api repos/OdivalPereira/aposte-em-voce/statuses/da38273 -f state=success -f context=teste-status`.
     - **Caso A (funciona):** função que publica o status `portao` (com o hash do atestado na descrição) e `aceite` no SHA via `gh api …/statuses/<sha>`, com `gh` simulado nos testes; falha do `gh` é relatada, nunca engolida.
     - **Caso B (403):** `portao` e `aceite` viram jobs do GitHub Actions com exatamente esses nomes, rodando no PR. `portao` lê no head do PR o atestado da etapa (`sociedade/pareceres/atestado-<ID>.json`, ID tirado do ramo `etapa/<ID>`), exige aprovado, commit do atestado ancestral do head e, depois dele, só commits de `sociedade/`. `aceite` lê no registro a decisão `aceitar` da etapa para o SHA revisado. Os dois falham fechados (sem atestado ou sem decisão = vermelho). A lógica fica em `S/sc_status.py`, testada com registro e atestado sintéticos.
     - Sem verificador da proteção da `main`: a regra já está ativa (ajuste 2).
   - B10: função que mede, pelo registro e pelo log da sessão, comandos do método, erros, edições manuais em arquivos de controle, intervenções e minutos de Odival, e devolve a linha de `evolucao.md` no formato da tabela atual.
3. **F3 · B04 e B07** · Galadriel · escreva só: `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sc-revisao/` (modelo, `lint_parecer.py`, referências), os demais `*-modelo.md` do pacote só se o teste de contrato exigir, `.github/workflows/ci.yml`, `T/test_contrato_modelos.py`, `T/test_ci_pipefail.py` · aceite: todo `*-modelo.md` preenchido com dados sintéticos passa no seu analisador; o modelo de parecer exige `commit:` e passa no `lint_parecer`; todo passo `run` do CI tem `pipefail` e o teste reprova um passo com pipe sem `pipefail`; o CI roda a suíte e o validador do pacote copiado.
4. **F4 · B01, B06 e B08, e a ligação dos módulos** · Elrond · **alto impacto** · escreva só: `S/sc.py`, `S/sc_ciclo.py` (novo), `T/test_ciclo.py`, `T/test_cauda.py`, `T/test_id_etapa.py`, `SKILL.md` e `references/` do núcleo, `sociedade-do-codigo/README.md`, `sociedade-do-codigo/adapters/` (só textos dos papéis), `sociedade-do-codigo/CHANGELOG.md` (entrada "não lançado") · aceite:
   - `sc.py abrir --etapa <ID> --ordem <arquivo> --base <sha>` abre a etapa a partir da ordem (ID validado por `^[a-z0-9][a-z0-9-]{0,39}$`, só para etapas novas: B08).
   - `sc.py revisar` ganha o registro do parecer (passa no `lint_parecer`, exige `commit:` igual ao SHA revisado) sem passo manual.
   - `sc.py decidir --etapa <ID> aceitar|corrigir|rejeitar|sem-aceite` exige atestado aprovado e parecer válido do mesmo SHA; grava o usuário real (`--por` obrigatório ou `git config user.name`, nunca nome padrão), a marca de emulação, as métricas (F2) e a linha de `evolucao.md`; publica `aceite` (F2); encerra a etapa sem `sc_rodada`.
   - B06: commit de produto depois do SHA do parecer derruba o parecer; commits só de `sociedade/` não derrubam.
   - Teste de fumaça: uma etapa trivial, num repositório temporário, fecha só com os comandos do README.
   - `SKILL.md`, README e textos dos papéis citam só o ciclo novo.
5. **F5 · B09 sondas e revisão interna** · Galadriel · escreva só: `T/adversarial/` · aceite: pelo menos 5 sondas, uma por DG-01 a DG-05, com o número do DG no nome do teste e, no docstring, o achado que reproduz; verdes as que esta etapa fecha (DG-01, DG-04, DG-05 e a parte do DG-02 coberta pela B01), `expectedFailure` nas demais até a etapa delas (DG-03 → B11/B14; resto do DG-02 → B15). Revisão interna de F1, F2 (B05) e F4 registrada no retorno.

## Portão
- O perfil traz `npm test`, mas o app ainda não existe. Nesta etapa o portão é o do pacote:
  `sc.py entregar --etapa m0-destravar --base <base da fatia> --fatia <N> --pasta-projeto sociedade-do-codigo --comando-teste "python3 -B -m unittest discover -s tests" --pasta-sociedade /home/user/aposte-em-voce/sociedade`
  e, no fim, o mesmo sem `--fatia`, com `--base 3bff553`. O `--comando-teste` é exceção registrada (a B11 vem na A1). O validador `python3 -B scripts/validar_pacote.py` (em `sociedade-do-codigo/`) também precisa passar.
- O atestado final vai para `sociedade/pareceres/atestado-m0-destravar.json` da cópia canônica.

## Paradas
- Mudança de escopo, de contrato ou instalação: volta ao Círdan e a Odival.
- Teto de cerca de 1.500 linhas de produto (sem contar testes). Se a estimativa passar, pare e devolva com a proposta de divisão.
- Publicar status `portao` e `aceite` de verdade: só no SHA final (caso A) ou pelos jobs do caso B.
- Não alterar `.claude/agents/` (fica para a sessão final).
- Até 3 hipóteses diferentes por bloqueio; depois, pare e devolva (Q12).
- Push só do ramo `etapa/m0-destravar` (autorizado por Odival); nunca `claude/*` nem `main`. PR com `gh pr create`, em rascunho, pelo modelo `.github/pull_request_template.md`.

## Entregas verificáveis
Os tipos `delegacoes claude` e `conversa_nova claude` são criados pela F2; a conferência roda com o `sc.py` do candidato (bootstrap).

```entregas
E1 | commit_existe | etapa/m0-destravar
E2 | arquivos_em | 3bff553..etapa/m0-destravar | sociedade-do-codigo/ | .github/
E3 | atestado_aprovado | sociedade/pareceres/atestado-m0-destravar.json | etapa/m0-destravar
E4 | arquivo_existe | sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_ciclo.py
E5 | arquivo_existe | sociedade-do-codigo/tests/adversarial
E6 | delegacoes | claude | c87266ad-1a68-5d63-a2d1-02ee2db138d5 | 5
E7 | conversa_nova | claude | aaaf9dd7d0fa5f821
E8 | push_feito | etapa/m0-destravar
E9 | parecer_valido | sociedade/pareceres/parecer-m0-destravar.md
```

## Itens do backlog e simulações
B01 a B10. Sem simulação nesta etapa (as simulações começam na A1, com a B12).

## Ajustes da aprovação (Odival, 03/10/2026)
1. Push autorizado de `etapa/*` e `jules/*`; base da etapa `3bff553` (ordem e atritos ficam fora do intervalo do candidato e entram no PR como governança).
2. A proteção da `main` já está ativa (PR obrigatório; status `ci`, `portao` e `aceite`; vale para administradores; sem force push nem exclusão). O 403 é falta de permissão da integração. Sai o verificador de proteção.
3. Teste de publicação de status no início da F2; se 403, `portao` e `aceite` como jobs do Actions (caso B). Sem os dois verdes, ninguém faz o merge.
4. Portão do pacote com `--comando-teste`, como exceção registrada.
5. `.claude/agents/` fora desta etapa.
6. Economia: leia só o listado, não repita verificações, até 3 subagentes em paralelo, sem relatórios intermediários.

## Retorno
Até 8 KB, numa devolução só: entregas preenchidas, commits por fatia, atestados, SHA final, link do PR, linhas de produto, resultado da revisão interna da Galadriel, pendências, atritos com o método e o identificador da conversa do Gandalf e de cada subagente.
