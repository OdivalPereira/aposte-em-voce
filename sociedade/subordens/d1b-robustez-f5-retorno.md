# Retorno da Subordem d1b-robustez · F5 (Permissões de merge · A06)

- Especialista: Elrond (dados, backend e acesso)
- Etapa: d1b-robustez
- Fatia: F5 (A06 · Permissões de merge)
- Worktree: `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- Base da fatia: `008811ef597e`
- Data: 05/10/2026

---

## 1. O que fiz

1. **Correção do achado A06 em `.claude/settings.json` e `sociedade-do-codigo/adapters/claude/settings.json.modelo`:**
   - Na d1, a introdução de `Bash(gh pr merge*-s*)` e `Bash(gh pr merge*-r*)` causou regressão porque capturou opções legítimas como `--subject` (contém `-s`) e `--repo` (contém `-r`).
   - Substituí os curingas genéricos pelas formas estritamente delimitadas por espaço:
     - `Bash(gh pr merge* -s *)` (com argumentos posteriores)
     - `Bash(gh pr merge* -s)` (ao final do comando)
     - `Bash(gh pr merge* -r *)` (com argumentos posteriores)
     - `Bash(gh pr merge* -r)` (ao final do comando)
   - Mantidos os bloqueios estritos de `--squash`, `--rebase`, `--auto`, `--admin` e suas combinações.

2. **Criação da suíte `sociedade-do-codigo/tests/test_permissoes_merge.py`:**
   - Valida a integridade das seções `permissions.ask` e `permissions.deny` em ambos os arquivos de configuração.
   - Garante a ausência dos curingas genéricos `Bash(gh pr merge*-s*)` e `Bash(gh pr merge*-r*)`.
   - Testa exaustivamente a tabela de aceite:
     - Pedem confirmação (`ask: True`, `deny: False`): `gh pr merge 12 --merge`, `gh pr merge 12 -m`, `gh pr merge 123 --merge`, `gh pr merge 123 -m`, `gh pr merge 123 --merge --repo O/P`, `gh pr merge 123 --merge --repo Organizacao/Projeto`, `gh pr merge 123 --merge --subject "x"`, `gh pr merge 123 --merge --subject "Etapa d1"`, `gh pr merge 123 --merge --body "x"`, `gh pr merge 123 -m --repo O/P`, etc.
     - São negados (`deny: True`): `--squash`, `-s`, `--rebase`, `-r`, `--auto`, `--admin` e combinações (`--merge --squash`, `--merge -s`, `-s --merge`, `--merge -r`, `-s --auto`, `--squash --admin`, etc.).
   - Replica a lógica exata das sondas de Barbárvore (`test_A06_configuracoes` e `test_A06_caminho_legitimo`) avaliando diretamente os arquivos do worktree `W`.

---

## 2. Arquivos alterados

Estritamente dentro do `Escreva só`:
- `.claude/settings.json` (modificado)
- `sociedade-do-codigo/adapters/claude/settings.json.modelo` (modificado)
- `sociedade-do-codigo/tests/test_permissoes_merge.py` (criado)

Nenhum outro arquivo foi alterado. Nenhum commit ou push foi realizado.

---

## 3. Saída dos testes dirigidos

### Teste 1: Sondas de Barbárvore (`sondas.py`)
Comando:
```bash
python3 -B ~/.sociedade/trabalho/d1-design/reconferencia-d1-design/revisao-saida/sondas.py --somente test_A06_configuracoes,test_A06_caminho_legitimo
```
Saída:
```json
{"sonda": "R06-legitimo", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 --merge --repo Organizacao/Projeto", "padroes": ["Bash(gh pr merge*-r*)"]}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 --merge", "ask": true, "deny": false}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 -m", "ask": true, "deny": false}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 -s", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 -r", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 --squash", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 --rebase", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 --auto", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": ".claude/settings.json", "comando": "gh pr merge 123 --admin", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 --merge", "ask": true, "deny": false}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 -m", "ask": true, "deny": false}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 -s", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 -r", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 --squash", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 --rebase", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 --auto", "ask": true, "deny": true}
{"sonda": "R06-aliases", "arquivo": "sociedade-do-codigo/adapters/claude/settings.json.modelo", "comando": "gh pr merge 123 --admin", "ask": true, "deny": true}
{"testes": 2, "falhas": 1, "erros": 0, "pulados": 0}
__main__.Sondas.test_A06_caminho_legitimo Traceback (most recent call last):
  File "/home/odival/.sociedade/trabalho/d1-design/reconferencia-d1-design/revisao-saida/sondas.py", line 181, in test_A06_caminho_legitimo
    self.assertFalse(patterns)
AssertionError: ['Bash(gh pr merge*-r*)'] is not false
```
**Análise da falha:**
Em `sondas.py`, linha 5: `ROOT=Path(__file__).resolve().parents[1]` aponta fixamente para o diretório `/home/odival/.sociedade/trabalho/d1-design/reconferencia-d1-design` (a reconferência anterior da d1-design). As linhas 170 e 177 leem `(ROOT/name).read_text()`. Assim, `sondas.py` não lê o worktree `W` (`d1b-robustez`), mas sim os arquivos não corrigidos da d1-design. Como `R` é estritamente de leitura, o arquivo `sondas.py` não foi modificado. A mesma verificação de Barbárvore executada contra `W` passa 100% verde em `test_permissoes_merge.py`.

---

### Teste 2: Novo teste unitário (`test_permissoes_merge.py`)
Comando:
```bash
python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_permissoes_merge.py"
```
Saída:
```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.005s

OK
```
Todos os 7 testes (incluindo subtestes das tabelas de aceite e réplica das sondas contra `W`) passaram com sucesso.

---

### Teste 3: Suíte existente (`test_instalar.py`)
Comando:
```bash
python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_instalar.py"
```
Saída:
```
......F......
======================================================================
FAIL: test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge (test_instalar.TesteInstalar.test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez/sociedade-do-codigo/tests/test_instalar.py", line 139, in test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge
    self.assertIn("Bash(gh pr merge*-s*)", deny_modelo)
AssertionError: 'Bash(gh pr merge*-s*)' not found in ['Bash(git push *)', 'Bash(git merge *)', 'Bash(gh pr merge*--squash*)', 'Bash(gh pr merge* -s *)', 'Bash(gh pr merge* -s)', 'Bash(gh pr merge*--rebase*)', 'Bash(gh pr merge* -r *)', 'Bash(gh pr merge* -r)', 'Bash(gh pr merge*--auto*)', 'Bash(gh pr merge*--admin*)', 'Bash(gh release *)', 'Read(./.env)', 'Read(./.env.*)']

----------------------------------------------------------------------
Ran 13 tests in 0.862s

FAILED (failures=1)
```
**Análise da falha:**
No commit `240f1b99` da d1-design, o teste `test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge` foi adicionado em `test_instalar.py` exigindo literalmente as strings `"Bash(gh pr merge*-s*)"` e `"Bash(gh pr merge*-r*)"`. Esse teste asseriu exatamente o padrão defeituoso que gerou o achado A06 do Revisor Independente. Para corrigir A06, esses padrões genéricos tiveram de ser removidos e substituídos pelos delimitados. Como `test_instalar.py` não consta no `Escreva só` da F5, respeitei estritamente as regras do papel e não o alterei. Recomenda-se que o coordenador Gandalf atualize ou remova essa asserção de `test_instalar.py` na integração final (F6), direcionando a cobertura para `test_permissoes_merge.py`.

---

## 4. O que não verifiquei

1. Execução do motor de permissões do Claude Code em sessão interativa (a validação foi realizada via correspondência exata de padrões fnmatch/glob conforme a especificação do Claude Code).
2. Não alterei `test_instalar.py` nem `sondas.py` por estarem fora do escopo de escrita (`Escreva só`), documentando a causa raiz das respectivas falhas acima.
