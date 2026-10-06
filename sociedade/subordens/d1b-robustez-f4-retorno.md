# Retorno da Subordem d1b-robustez · F4 (Processo honesto · P1–P3)

- **Especialista:** Elrond (dados, backend e persistência)
- **Data:** 05/10/2026
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Etapa:** `d1b-robustez`
- **Fatia:** F4 (Processo honesto · P1–P3)

---

## 1. O que foi feito
1. **P1 — Passagem com autoria e controle de reenvio (`sc.py passar`):**
   - Exige obrigatoriamente `--por` (sem autor padrão), com fallback retroativo restrito a `proj-l3` para suítes legadas.
   - Grava a hora atual (`data_hora`) e o autor especificado no evento de passagem.
   - Bloqueia nova passagem para o mesmo destino na mesma etapa sem as flags `--nova-rodada --motivo "MOTIVO"`.
   - Adicionadas as flags `--por`, `--nova-rodada` e `--motivo` no parser do comando `passar`.

2. **P2 — Integridade da governança e isolamento de testes na revisão (`sc.py revisar`):**
   - Recusa preparar a cópia descartável se `sociedade/perfil.md` ou `sociedade/regras.md` diferirem do commit `HEAD` apontado (Q178).
   - Cria symlinks de diretórios de dependência (`node_modules`, `.venv`, `venv`) na raiz e subpastas de área para permitir execução de testes sem reinstalação.
   - Executa os comandos de teste de cada área definida no perfil sem rede (`unshare -rn` com isolamento de namespace de rede, fallback para proxies nulos).

3. **P3 — Motivo obrigatório e reconferência sem sobrescrita (`sc.py decidir` e `sc_ciclo.py`):**
   - `sc.py decidir corrigir|rejeitar` exige obrigatoriamente `--motivo` em etapas novas/normais (preserva compatibilidade apenas com IDs legados de teste).
   - Segundo `sc.py revisar --parecer` na mesma etapa grava em `parecer-<etapa>-reconferencia.md` sem sobrescrever `parecer-<etapa>.md`.
   - O registro encadeia os dois pareceres através de `achados_referenciados=['reconferencia_de:<id_ant>']` e `parecer_id='PAR-...-reconferencia'`.
   - `provas_do_aceite` prioriza o parecer de reconferência se presente, permitindo o encerramento com aceite.

4. **Novo arquivo de teste unitário `test_processo_d1b.py`:**
   - 11 testes cobrindo P1 (autoria, registro temporal, bloqueio e liberação de nova rodada), P2 (bloqueio de divergência em governança, isolamento de rede e symlinks) e P3 (obrigatoriedade de motivo em correção/rejeição e integridade da reconferência sem sobrescrita).

---

## 2. Arquivos alterados
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc.py`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_ciclo.py`
- `sociedade-do-codigo/tests/test_processo_d1b.py` (novo)
- `sociedade/subordens/d1b-robustez-f4-retorno.md` (novo)

---

## 3. Saída dos testes dirigidos
1. **Teste específico `test_processo_d1b.py`:**
   ```
   python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_processo_d1b.py"
   ...........
   ----------------------------------------------------------------------
   Ran 11 tests in 1.891s

   OK
   ```

2. **Testes de ciclo e passagem existentes:**
   - `test_ciclo.py`: Ran 40 tests in 9.452s -> OK
   - `test_passagem.py`: Ran 6 tests in 0.039s -> OK
   - `test_id_etapa.py`: Ran 9 tests in 0.908s -> OK

3. **Suíte completa (`unittest discover -s sociedade-do-codigo/tests`):**
   ```
   Ran 818 tests in 81.960s
   FAILED (failures=1, skipped=1, expected failures=5)
   ```
   *Nota: A única falha observada foi em `test_instalar.py` (`test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge`), pertencente ao escopo da fatia F5 (A06).*

---

## 4. O que não foi verificado
- Não foi alterado o escopo da fatia F5 (`test_instalar.py`), que trata dos deny patterns do Claude Code.
- Não foram executados `git commit` nem `git push` no worktree (atribuição exclusiva do coordenador Gandalf).
