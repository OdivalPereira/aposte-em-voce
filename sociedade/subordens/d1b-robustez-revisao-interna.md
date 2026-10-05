# Parecer da Revisão Interna · d1b-robustez (F1 a F5)

- **Revisora Interna:** Galadriel (métodos, qualidade e testes de comportamento)
- **Data:** 05/10/2026
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Etapa:** `d1b-robustez`
- **Base..HEAD:** `4fdd7b5..8566ffd`
- **Veredito:** **REPROVADO / CORRIGIR** (1 achado bloqueador do portão da suíte do pacote em `test_instalar.py`)

---

## 1. Veredito e Síntese Executiva

As correções de lógica e robustez das fatias **F1 a F4** foram implementadas com excelente rigor técnico, fechando comprovadamente os achados A01, A02, A03, A05 e os requisitos de processo honesto P1, P2 e P3. As sondas de Barbárvore (`R/sondas.py`) para A01, A02, A03 e A05 estão 100% verdes.

Na fatia **F5**, a delimitação de argumentos curtos em `.claude/settings.json` e `adapters/claude/settings.json.modelo` resolveu a colisão com `--repo` e `--subject` (A06). Porém, o teste unitário pré-existente `test_instalar.py` (adicionado na d1-design para asserir os padrões defeituosos que geraram A06) **não foi atualizado**, pois estava fora do `Escreva só` da subordem F5. Como resultado:
- O critério explícito de F5 (*"`test_instalar.py` verde"*) **falhou**;
- A suíte completa do pacote quebrou com 1 falha em 818 testes (`FAIL: test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge`).

Conforme as regras do papel de Galadriel ("Não corrige o que revisa internamente; devolve ao especialista", "Não aprova sem executar o teste"), o veredito da revisão interna é **REPROVADO / CORRIGIR**, devendo o Gandalf despachar o ajuste pontual de `test_instalar.py` a um novo Elrond (Q171) antes de prosseguir com F6 e entrega final.

---

## 2. Avaliação Detalhada por Fatia

### F1 · Cadeia do registro estrita e corte explícito (A02)
- **Commit:** `008811e`
- **Arquivos:** `sc_registro.py` e `test_registro_cadeia_estrita.py`
- **Critérios da ordem:**
  1. Corte explícito e gravado entre formato antigo e cadeia (`corte_cadeia`): **Cumprido**. Campo gravado na inicialização e mutações; eventos `seq >= corte_cadeia` exigem `hash` e `prev_hash`.
  2. Legado só vale antes do corte: **Cumprido**. Evento com hash/prev_hash antes de `corte_cadeia` é recusado com `ErroRegistroCorrompido`.
  3. Omissão na cauda ou meio recusada: **Cumprido**. Elimina o escape de A02.
  4. Sondas R02 verdes: **Cumprido** (`test_A02_adulteracao`, `test_A02_hash_omitido` e `test_A02_legado` aprovadas).
- **Qualidade dos testes:** 15 testes em `test_registro_cadeia_estrita.py`. Testam mutação real em disco, recarga, recusa de saltos de corte, tipos inválidos e adulteração de cauda. Testes de comportamento robustos, sem tautologias.
- **Estado:** **APROVADO**.

### F2 · Trava comum da troca e emulação (A03 / A05)
- **Commit:** `1981b03`
- **Arquivos:** `sc_rodada.py` e `test_rodada_trava.py`
- **Critérios da ordem:**
  1. Leitura, validação e gravação sob trava comum: **Cumprido**. Implementado `trava_perfil_registro` usando `fcntl.flock(LOCK_EX | LOCK_NB)` em `.trava_perfil.tmp`.
  2. Revalidação R1–R3 sob trava antes da escrita: **Cumprido**. Bloqueia estado final inválido.
  3. Troca intercalada recusada ou deixa estado válido: **Cumprido**. Retorna erro de concorrência explícito (`ErroTravaPerfil`).
  4. Rollback em falha de persistência: **Cumprido**. Restaura `perfil.md` original em caso de exceção no registro (fecha A05).
  5. Sondas R03 e R05 verdes: **Cumprido** (`test_A03_entre_validacoes`, `test_A03_apos_ultima_validacao`, `test_A05_rollback_emulacao`, `test_A05_rollback_troca` aprovadas).
- **Qualidade dos testes:** 10 testes em `test_rodada_trava.py`. Exercitam colisão direta, liberação, rollback, simulação sem criar arquivo e concorrência real entre subprocessos do SO.
- **Estado:** **APROVADO**.

### F3 · Identidade da conversa @etapa (A01 / Q182)
- **Commit:** `2629497`
- **Arquivos:** `sc_conferir.py` e `test_conferir_identidade.py`
- **Critérios da ordem:**
  1. Resolução apenas por campo estruturado do Antigravity: **Cumprido**. Usa `workspace_uris` do SQLite ou campos estruturados nos metadados/primeira linha (`workspace`, `cwd`, etc.) e declarações formais no cabeçalho do prompt.
  2. Descarte de menções textuais posteriores no corpo: **Cumprido**. Elimina a brecha onde o assistente citava um caminho como referência.
  3. Declaração divergente recusada: **Cumprido**. Conversas divergentes são descartadas da seleção.
  4. Sem campo estruturado retorna "não verificado": **Cumprido**. `conferir_item` retorna `NAO_VERIFICADO`, nunca `FEITO`.
  5. Só conversas posteriores à passagem e delegações para especialistas ativos: **Cumprido**. `self` e coordenadores/inativos são estritamente excluídos (Q182).
  6. Sondas R01 verdes: **Cumprido** (`test_A01_variantes_originais` com 7 variantes e `test_A01_identidade_corpo` aprovadas).
- **Qualidade dos testes:** 10 testes em `test_conferir_identidade.py`. Cobrem ponta a ponta `resolver_conversa_etapa`, `conferir_item` e medição, reproduzindo com fidelidade a estrutura do Antigravity.
- **Estado:** **APROVADO**.

### F4 · Processo honesto (P1–P3)
- **Commit:** `640409b`
- **Arquivos:** `sc.py`, `sc_ciclo.py` e `test_processo_d1b.py`
- **Critérios da ordem:**
  1. P1: `passar` exige `--por`, carimba hora atual e bloqueia reenvio sem `--nova-rodada --motivo`: **Cumprido**.
  2. P2: `revisar` recusa preparar cópia se governança diferir do `HEAD` (Q178): **Cumprido**. Symlinks para `node_modules` e `.venv` configurados; execução de testes de área sem rede (`_executar_sem_rede`).
  3. P3: `decidir` exige `--motivo` para `corrigir` e `rejeitar`: **Cumprido**. Segundo parecer grava em `parecer-<etapa>-reconferencia.md` sem sobrescrever o primeiro e encadeia no registro com `achados_referenciados`.
- **Qualidade dos testes:** 11 testes em `test_processo_d1b.py`. Cobrem rigorosamente o CLI e transições de ciclo.
- **Estado:** **APROVADO**.

### F5 · Permissões de merge (A06) e `test_instalar.py`
- **Commit:** `8566ffd`
- **Arquivos:** `.claude/settings.json`, `adapters/claude/settings.json.modelo` e `test_permissoes_merge.py`
- **Critérios da ordem:**
  1. Tabela de casos pedem confirmação (ask) e negados (deny): **Cumprido**. Testado exaustivamente em `test_permissoes_merge.py` (18 comandos ask e 40 comandos deny).
  2. Sondas A06 verdes: **Cumprido no worktree**. A falha de `test_A06_caminho_legitimo` em `sondas.py` decorre unicamente de `ROOT` fixo apontando para `reconferencia-d1-design`; a mesma verificação executada contra `W` passa 100%.
  3. `test_instalar.py` verde: **FALHOU**.
- **Estado:** **REPROVADO POR REGRESSÃO NO TESTE DE INSTALAÇÃO (Achado AI-01)**.

---

## 3. Lista de Achados da Revisão Interna

### [bloqueador] Achado AI-01: Inconsistência em `test_instalar.py` quebra o portão da suíte completa de testes
- **Local:** `sociedade-do-codigo/tests/test_instalar.py:133–152` (`test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge`)
- **Condição:** O teste unitário `test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge` assere textualmente a presença de:
  ```python
  self.assertIn("Bash(gh pr merge*-s*)", deny_modelo)
  self.assertIn("Bash(gh pr merge*-r*)", deny_modelo)
  ...
  self.assertIn("Bash(gh pr merge*-s*)", deny_settings)
  self.assertIn("Bash(gh pr merge*-r*)", deny_settings)
  ```
- **Efeito:**
  A execução de `unittest discover -s sociedade-do-codigo/tests` falha com:
  ```
  AssertionError: 'Bash(gh pr merge*-s*)' not found in ['Bash(git push *)', ...]
  Ran 818 tests in 78.363s
  FAILED (failures=1)
  ```
- **Causa Raiz:** O teste em `test_instalar.py` foi escrito na d1 com as strings genéricas que colidiam com `--repo` e `--subject`. Na F5, o Elrond substituiu com acerto os padrões nos dois arquivos JSON pelos padrões delimitados (`Bash(gh pr merge* -s *)`, `Bash(gh pr merge* -s)`, `Bash(gh pr merge* -r *)`, `Bash(gh pr merge* -r)`), mas não podia alterar `test_instalar.py` porque este arquivo não constava no `Escreva só` da subordem F5.
- **Prescrição de Correção para novo Elrond (Q171):**
  Despachar subordem a novo Elrond com `Escreva só: sociedade-do-codigo/tests/test_instalar.py`.
  No método `test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge`:
  1. Substituir as asserções de `"Bash(gh pr merge*-s*)"` e `"Bash(gh pr merge*-r*)"` pelas formas delimitadas:
     - `self.assertIn("Bash(gh pr merge* -s *)", deny_modelo)`
     - `self.assertIn("Bash(gh pr merge* -s)", deny_modelo)`
     - `self.assertIn("Bash(gh pr merge* -r *)", deny_modelo)`
     - `self.assertIn("Bash(gh pr merge* -r)", deny_modelo)`
     - e idêntico para `deny_settings`.
  2. Adicionar asserções negativas garantindo que os curingas genéricos não retornem:
     - `self.assertNotIn("Bash(gh pr merge*-s*)", deny_modelo)`
     - `self.assertNotIn("Bash(gh pr merge*-r*)", deny_modelo)`
     - `self.assertNotIn("Bash(gh pr merge*-s*)", deny_settings)`
     - `self.assertNotIn("Bash(gh pr merge*-r*)", deny_settings)`

---

## 4. Evidências de Execução dos Testes

### 1. Sondas de Barbárvore (`sondas.py --scripts W/S`)
Comando:
```bash
python3 -B ~/.sociedade/trabalho/d1-design/reconferencia-d1-design/revisao-saida/sondas.py \
  --scripts /home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez/sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts
```
Resultado:
- R01 (identidade e 7 variantes): **100% verde**
- R02 (adulteração, omissão de hash na cauda, legado): **100% verde**
- R03 (após revalidação e entre validações): **100% verde**
- R05 (rollback emulacao e rollback troca): **100% verde**
- R06 (aliases proibidos): **100% verde**
- *(R06-caminho-legítimo falhou apenas no script externo por ler pasta fixa; teste equivalente em `test_permissoes_merge.py` passou 100%)*

### 2. Suíte de novos testes unitários (F1 a F5)
Comando:
```bash
python3 -B -m unittest \
  sociedade-do-codigo/tests/test_registro_cadeia_estrita.py \
  sociedade-do-codigo/tests/test_rodada_trava.py \
  sociedade-do-codigo/tests/test_conferir_identidade.py \
  sociedade-do-codigo/tests/test_processo_d1b.py \
  sociedade-do-codigo/tests/test_permissoes_merge.py
```
Resultado:
```
Ran 53 tests in 2.305s
OK
```

### 3. Suíte Integral do Pacote
Comando:
```bash
python3 -B -m unittest discover -s sociedade-do-codigo/tests
```
Resultado:
```
Ran 818 tests in 78.363s
FAILED (failures=1, skipped=1, expected failures=5)
```
*(Única falha: `test_instalar.py`, documentada no Achado AI-01)*.

---

## 5. O que não foi verificado

1. Não foram feitas modificações nos arquivos de código ou teste, conforme o papel de Galadriel ("Não corrige o que revisa internamente; devolve ao especialista").
2. Não foram realizados commits Git ou push remoto.
3. Não foi executado o motor real do Claude Code nem o CLI `gh` contra a API do GitHub (a validação foi realizada sobre a especificação formal de permissões do Claude Code e correspondência de padrões).
4. As alterações de texto e documentação da fatia F6 (`CLAUDE.md`, `ordem-modelo.md`, etc.) não foram avaliadas, pois compõem a fatia subsequente.
