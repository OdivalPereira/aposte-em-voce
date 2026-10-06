# Retorno da Subordem d1b-robustez · C2

**De:** Elrond (dados, backend e acesso)  
**Para:** Gandalf (coordenador)  
**Data:** 2026-10-05  
**Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`  

---

## 1. O que foi feito
Harmonização determinística do portão de pré-devolução (`sc_pre_devolucao.py`) e da conferência de entregas (`sc_conferir.py`) com as regras Q178 (governança no início) e Q149 (cauda de governança):
1. **Em `sc_pre_devolucao.py` (`obter_arquivos_candidato`):**
   - Ao inspecionar os commits de `base..HEAD`, classifica cada commit por sua composição de caminhos tocados (`git diff-tree`).
   - Se um commit for estritamente de governança (100% de seus arquivos em `sociedade/`) ocorrido antes do primeiro commit de produto (governança no início, Q178) ou em cauda legítima (Q149), suas alterações não são atribuídas ao candidato de produto e não configuram violação de governança.
   - Preservadas e reforçadas as detecções de violação de governança:
     - Commits mistos de produto tocando `sociedade/`.
     - Alterações em `sociedade/perfil.md` ou `sociedade/regras.md` fora do início da etapa (tentativas de enfraquecer o portão pelo candidato, como vigiado na sonda DG-09).
     - Etapa sem nenhum commit de produto onde foram alterados arquivos em `sociedade/` (como vigiado em `test_commit_do_candidato_em_sociedade_reprova`).
2. **Em `sc_conferir.py` (`arquivos_do_intervalo`):**
   - Na checagem de `arquivos_em <base>..<head>`, arquivos alterados exclusivamente em commits puros de governança no intervalo são desconsiderados dos arquivos imputados aos prefixos de produto do candidato.
3. **Novo teste unitário `tests/test_portao_governanca_q178.py`:**
   - 4 testes cobrindo:
     - Aprovação de etapa com commit de governança pura no início (Q178) e conferência `arquivos_em`.
     - Reprovação estrita quando há commit misto adulterando governança.
     - Aprovação com cauda de governança pura (Q149).
     - Testes unitários diretos de `obter_arquivos_candidato` e `arquivos_do_intervalo`.

---

## 2. Arquivos alterados
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_pre_devolucao.py`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py`
- `sociedade-do-codigo/tests/test_portao_governanca_q178.py` (novo)
- `sociedade/subordens/d1b-robustez-c2-retorno.md` (novo)

Nenhum commit ou push foi realizado.

---

## 3. Saída dos testes dirigidos
1. **Teste novo dirigido:**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_portao_governanca_q178.py"
   ```
   **Resultado:**
   ```
   ....
   ----------------------------------------------------------------------
   Ran 4 tests in 0.774s

   OK
   ```

2. **Suíte completa do pacote (`sociedade-do-codigo`):**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests
   ```
   **Resultado:**
   ```
   Ran 822 tests in 81.662s

   OK (skipped=1, expected failures=5)
   ```

3. **Verificação de aceites na etapa real (`d1b-robustez`):**
   - `conferir_item` para `arquivos_em 4fdd7b5..HEAD | sociedade-do-codigo/ | .claude/settings.json | CLAUDE.md`:
     `('feito', '26 arquivos, todos nos prefixos')`
   - `obter_arquivos_candidato(top, '4fdd7b5', top / 'sociedade')`:
     `Governanca: []`, `Caminhos: 28` (sem falsos positivos em `sociedade/`).
   - `sc.py entregar`:
     `higiene_pastas: [OK]`, `testes: [OK] (1013 testes: app 191, pacote 822)`. Atestado reprova unicamente por `arvore_limpa` devido aos arquivos modificados/criados desta subordem que aguardam commit pelo coordenador.

---

## 4. O que não verifiquei
- Não comitei nem fiz push (papel do coordenador).
- Não alterei arquivos de governança canônica ou ordens da etapa.
- Não executei merge na branch principal (`main`).
