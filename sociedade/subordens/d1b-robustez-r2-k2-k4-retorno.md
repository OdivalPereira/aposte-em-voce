# Retorno de Subordem · d1b-robustez-r2-k2-k4

- **Especialista:** Elrond (dados, persistência e backend)
- **Subordem:** `sociedade/subordens/d1b-robustez-r2-k2-k4.md`
- **Data:** 2026-10-05
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Ramo:** `etapa/d1b-robustez`

---

## 1. Resumo da Execução

Todos os objetivos dos achados K2, K3 e K4 foram implementados estritamente conforme as especificações e aceites da subordem, sem comitar nem fazer push.

### K2 (Cauda de governança pós-atestado, Q149/Q178)
- Implementada a função `obter_ultimo_commit_produto(raiz, ref='HEAD')` em `sc_conferir.py`, que retrocede no histórico de commits enquanto os commits tocarem exclusivamente arquivos em `sociedade/` (cauda de governança).
- `commit_existe`: avalia o último commit de produto se `HEAD` estiver em cauda de pura governança. Quando informado commit esperado, valida que não houve alterações fora de `sociedade/` pós-produto.
- `atestado_aprovado`: quando `args[1]` (ex: `HEAD`) descende do commit do atestado por uma cadeia exclusivamente composta por commits em `sociedade/`, aceita o atestado (`FEITO`). Caso qualquer arquivo fora de `sociedade/` tenha sido alterado após o atestado, continua reprovando (`NAO_FEITO`).

### K3 (Identidade estrita de conversa e worktree, Q181/A01)
- Removida a permissão que adicionava a raiz do repositório Git associado (`common_git`) ao conjunto `pastas_validas`.
- Agora `pastas_validas` contém estritamente o worktree da etapa (`pasta_wt_norm`).
- Conversas abertas na pasta principal do repositório ou sem comprovação estruturada não contam; se mencionarem a ordem da etapa, retornam `NAO_VERIFICADO` com mensagem `sem campo estruturado de workspace para a etapa "{etapa}" no Antigravity` (nunca `feito`).
- Conversas declaradamente de outros worktrees são descartadas como divergentes.

### K4 (Múltiplas rodadas do Gandalf, Q180)
- Implementada a função `resolver_conversas_etapa(etapa, ...)` que identifica todas as passagens para Gandalf e resolve individualmente a conversa legítima de cada rodada (primeira conversa aberta após a respectiva passagem no worktree por campo estruturado).
- `resolver_conversa_etapa`: preserva compatibilidade com o retorno unitário para chamadas diretas, retornando instância de `ConversaResolvida(str)` contendo o atributo `.todas_conversas`.
- `delegacoes`: totaliza as delegações de especialistas ativos somando todas as rodadas da etapa.
- `conversa_nova`: valida que em cada rodada há no máximo uma única ordem por conversa.
- Ambiguidade: só é reportada se houver múltiplas conversas conflitantes dentro da mesma rodada; múltiplas conversas distribuídas em rodadas distintas não geram ambiguidade.

---

## 2. Arquivos Alterados

1. `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py`
   - Adicionadas classes e funções: `ConversaResolvida`, `obter_ultimo_commit_produto`, `resolver_conversas_etapa`.
   - Refatorada `resolver_conversa_etapa`.
   - Atualizados `commit_existe`, `atestado_aprovado`, `delegacoes` e `conversa_nova` em `conferir_item`.
2. `sociedade-do-codigo/tests/test_conferir_rodada2.py` (novo)
   - 11 testes cobrindo cenários sintéticos de K2, K3 e K4.
3. `sociedade/subordens/d1b-robustez-r2-k2-k4-retorno.md` (este relatório).

Nenhum outro arquivo foi alterado.

---

## 3. Testes Dirigidos Executados

1. **Testes de identidade existentes (`test_conferir_identidade.py`):**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_conferir_identidade.py"
   ```
   **Resultado:** `Ran 10 tests in 0.142s - OK`

2. **Novos testes de rodada 2 (`test_conferir_rodada2.py`):**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_conferir_rodada2.py"
   ```
   **Resultado:** `Ran 11 tests in 0.318s - OK`

3. **Testes de portão e governança Q178 (`test_portao_governanca_q178.py`):**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_portao_governanca_q178.py"
   ```
   **Resultado:** `Ran 4 tests in 0.723s - OK`

4. **Testes de conferência L8 (`test_conferir_l8.py`):**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests -p "test_conferir_l8.py"
   ```
   **Resultado:** `Ran 10 tests in 0.157s - OK`

5. **Suíte completa do pacote:**
   ```bash
   python3 -B -m unittest discover -s sociedade-do-codigo/tests
   ```
   **Resultado:** `Ran 845 tests in 79.202s - OK (skipped=1, expected failures=5)`
