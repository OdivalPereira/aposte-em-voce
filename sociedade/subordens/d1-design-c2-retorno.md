# Retorno Correção d1-design-c2 · Elrond

Veredito: **pronto**. Sem commit, sem push. Worktree: `~/.sociedade/trabalho/aposte-em-voce/d1-design` (ramo `etapa/d1-design`).

## 1. Objetivos Cumpridos

Implementação integral das correções para os achados A01, A02, A03, A05 e A06 apontados na revisão independente:

### A01 — sc_conferir.py (Resolução de @etapa e Prova Temporal)
- **Identidade da pasta:** Normalização via `Path(p).resolve().as_posix()` tanto para a pasta do worktree quanto para as URIs registradas na conversa (`conversation_summaries.db` e transcrições). Comparação exata de membros contra o conjunto de URIs resolvidas, impedindo qualquer falso positivo por substring ou prefixo (ex.: `worktree-e8-outro`).
- **Pasta obrigatória no transcript:** Transcrições em `brain` são validadas de forma estrita contra a pasta do worktree; não são mais aceitas apenas por citarem `ordens/{etapa}.md` se a pasta de trabalho for diferente ou divergente.
- **Prova temporal estrita:** A conversa exige `created_at` com timestamp válido posterior ou igual ao momento da passagem para Gandalf (`ts_passagem`). Removida a tolerância indevida de `min(ts_passagem, ts_aberta)`. Conversas sem timestamp ou com timestamp anterior à passagem são recusadas.
- **Ambiguidade irresolvível:** Se nenhuma conversa atender aos critérios ou houver ambiguidade irresolvível (mais de uma após filtro de menção a Gandalf), retorna `(NAO_FEITO, motivo)`.
- **Testes:** 5 novos testes negativos adicionados a `sociedade-do-codigo/tests/test_conferir_l8.py` cobrindo pasta errada, prefixo de pasta, ausência de timestamp, timestamp anterior à passagem e transcript com pasta diferente citando a ordem.

### A02 — sc_registro.py / sc_rodada.py (Cadeia de Hash nos Eventos)
- **Cadeia de hash SHA-256:**
  - Em `sc_registro.py` (`aplicar_mutacao`), cada novo evento passa a ter `prev_hash` (hash do evento anterior com hash, ou vazio se primeiro elo) e `hash` (SHA-256 do payload canônico do evento sem a chave `hash` via `json.dumps({k: v for k, v in ev.items() if k != 'hash'}, sort_keys=True, ensure_ascii=False)`).
  - Em `carregar_dados_registro`, valida-se para cada evento com `hash`: (1) que `prev_hash` coincide com o hash do evento anterior; (2) que `hash` coincide com o SHA-256 recalculado dos dados. Qualquer divergência (adulteração manual de autor, motivo, etc.) dispara `ErroRegistroCorrompido`.
  - Eventos legados (sem chave `hash`) continuam tratados de forma compatível.
- **Testes:** 2 novos testes adicionados em `sociedade-do-codigo/tests/test_registro.py` comprovando que adulteração de qualquer campo (ex.: nota/motivo) ou de `prev_hash` no arquivo em disco é detectada e dispara `ErroRegistroCorrompido`.

### A03 & A05 — sc_rodada.py (Rollback e Revalidação R1-R3 contra Concorrência)
- **Rollback em falha de evento (A05):**
  - Em `cmd_papel_emulacao` e `cmd_papel_trocar`, o conteúdo anterior de `perfil.md` é salvo antes de qualquer escrita no disco. Se `reg.aplicar_mutacao` ou `reg.registrar_troca_papel` lançar qualquer exceção (ex.: erro de I/O, erro de concorrência ou corrupção), `perfil.md` é restaurado imediatamente ao estado original e a exceção é relançada.
- **Revalidação R1-R3 contra concorrência (A03):**
  - Em `cmd_papel_emulacao`, antes de alterar o disco ao desligar o modo emulação, o perfil e o registro frescos são recarregados e revalidados contra as regras estritas R1-R3, evitando que modificações concorrentes deixem a emulação desligada com violações invariantes.
- **Testes:** 3 novos testes adicionados em `sociedade-do-codigo/tests/test_emulacao.py` cobrindo rollback em emulação, rollback em troca de papel e recusa de desligamento diante de violação concorrente de R3.

### A06 — Configurações do Claude (.claude/settings.json e modelo)
- Incluídas as opções curtas `-s` (squash) e `-r` (rebase) de `gh pr merge` nos arrays de `deny`:
  - `"Bash(gh pr merge*-s*)"`
  - `"Bash(gh pr merge*-r*)"`
- Atualizados `.claude/settings.json` e `sociedade-do-codigo/adapters/claude/settings.json.modelo`.
- **Testes:** Adicionado teste `test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge` em `sociedade-do-codigo/tests/test_instalar.py`.

## 2. Arquivos Alterados
1. `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py`
2. `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_registro.py`
3. `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_rodada.py`
4. `.claude/settings.json`
5. `sociedade-do-codigo/adapters/claude/settings.json.modelo`
6. `sociedade-do-codigo/tests/test_conferir_l8.py`
7. `sociedade-do-codigo/tests/test_registro.py`
8. `sociedade-do-codigo/tests/test_emulacao.py`
9. `sociedade-do-codigo/tests/test_instalar.py`

## 3. Proibições Respeitadas
- Arquivos em `src/`: estritamente preservados (nenhum toque).
- Sem commit e sem push.
- Trabalho exclusivo dentro de `/home/odival/.sociedade/trabalho/aposte-em-voce/d1-design`.

## 4. Testes Dirigidos Executados
1. `python3 -B -m unittest discover -s sociedade-do-codigo/tests`:
   - Execução completa da suíte de testes com todas as novas coberturas aprovadas.
2. `python3 -B sociedade-do-codigo/scripts/validar_pacote.py`:
   - `pacote válido` (código de saída 0).
