# Retorno da Subordem d1b-robustez · C1 (Correção AI-01 em test_instalar.py)

- Especialista: Elrond (dados, backend e acesso)
- Etapa: d1b-robustez
- Correção: C1 (Achado bloqueador AI-01 da Revisão Interna)
- Worktree: `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- Data: 05/10/2026

---

## 1. O que fiz

1. **Resolução do achado bloqueador AI-01 em `sociedade-do-codigo/tests/test_instalar.py`:**
   - No método `test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge`, substituí a checagem das strings genéricas antigas (`Bash(gh pr merge*-s*)` e `Bash(gh pr merge*-r*)`) que capturavam indevidamente opções como `--repo` e `--subject` (A06).
   - O teste agora exige estritamente a presença dos novos padrões delimitados por espaço introduzidos em F5:
     - `Bash(gh pr merge* -s *)`
     - `Bash(gh pr merge* -s)`
     - `Bash(gh pr merge* -r *)`
     - `Bash(gh pr merge* -r)`
     - Tanto em `adapters/claude/settings.json.modelo` quanto em `.claude/settings.json`.
   - Foram adicionadas asserções negativas (`self.assertNotIn`) para garantir que os padrões genéricos sem delimitação não retornem aos arquivos de configuração.

---

## 2. Arquivos alterados

Estritamente dentro do `Escreva só`:
- `sociedade-do-codigo/tests/test_instalar.py` (modificado)

Nenhum outro arquivo foi alterado. Não foi feito commit nem push.

---

## 3. Saída dos testes dirigidos

### Teste 1: Teste unitário de instalação (`test_instalar.py`)
Comando:
```bash
python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_instalar.py"
```
Saída:
```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.806s

OK
```

### Teste 2: Suíte completa do pacote `sociedade-do-codigo/tests`
Comando:
```bash
python3 -B -m unittest discover -s sociedade-do-codigo/tests
```
Saída:
```text
Ran 818 tests in 78.938s

OK (skipped=1, expected failures=5)
```

---

## 4. O que não verifiquei

1. Não foram realizados commits Git ou push remoto, conforme determinação explícita da subordem e do papel de Elrond.
2. Não foram modificados arquivos fora do `Escreva só`.
3. Os artefatos e documentação da etapa subsequente F6 não foram alterados.
