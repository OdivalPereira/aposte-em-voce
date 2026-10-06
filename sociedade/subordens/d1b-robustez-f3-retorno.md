# Retorno da Subordem d1b-robustez · F3 (Identidade da conversa · A01)

- **Especialista:** Elrond (dados, persistência e backend)
- **Data:** 05/10/2026
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Etapa:** `d1b-robustez`
- **Fatia:** F3 (Identidade da conversa · Achado A01)

---

## 1. O que foi feito
1. **Resolução estrita de identidade de workspace em `sc_conferir.py` (`resolver_conversa_etapa`):**
   - `@etapa` resolve a pasta APENAS por campo estruturado do Antigravity: `workspace_uris` em `resumos.db` ou campos estruturados nos metadados/JSON do log (`workspace`, `workspace_uris`, `workspaces`, `cwd`, `app_data_dir`) e declarações formais no prompt inicial (`Pasta: ...`, `Worktree: ...`, ou mapeamentos `<user_information>`).
   - Removida completamente a busca incidental no corpo do transcript (mensagens posteriores do assistente/usuário citando caminhos como referência), fechando em definitivo a vulnerabilidade do Achado A01.
   - Declaração divergente de pasta (seja no SQLite, nas propriedades do JSON ou na declaração do prompt inicial) é imediatamente recusada e marcada como divergente.
   - Sem campo estruturado de workspace que comprove o vínculo da conversa ao worktree, a conversa não é aceita e o resultado em `conferir_item` é `não verificado` (`NAO_VERIFICADO`), nunca `feito`.
   - Conversas com timestamp ausente, inválido ou anterior à última passagem para o Gandalf são descartadas.

2. **Validação estrita de delegações e especialistas ativos (Q182):**
   - Implementadas `_obter_especialistas_ativos(pasta_sociedade)` e `_contar_delegacoes_antigravity(log_path, especialistas_ativos)`.
   - Só contam chamadas a `invoke_subagent` com `TypeName` ou `Role` de especialistas com estado `ativo` no perfil (`perfil.md`) ou role genérico `Especialista` (fixtures sintéticas).
   - `self` é estritamente descartado e não conta como delegação (Q182).
   - Chamadas a papéis de liderança/coordenação (ex.: `gandalf`, `cirdan`, `barbarvore`) ou especialistas com estado `espera` (ex.: `jules`) não contam como delegações válidas.

3. **Criação da suíte unitária `test_conferir_identidade.py`:**
   - 10 testes cobrindo:
     - Resolução via `workspace_uris` no SQLite passando por `conferir_item` e medição.
     - Resolução via campo estruturado `workspace` direto no JSON do transcript.
     - Bloqueio de menção incidental no corpo do transcript (achado A01 reproduzido).
     - Recusa de declaração divergente no prompt inicial ou metadados.
     - Conversa sem campo estruturado retornando `não verificado`, nunca `feito`.
     - Descarte de conversas anteriores à passagem para Gandalf.
     - Descarte de conversas anteriores à ÚLTIMA passagem quando há rodadas múltiplas.
     - Contagem de delegações restritas a especialistas ativos do perfil.
     - Exclusão estrita de `self` na contagem de delegações (Q182).
     - Descarte de delegações para coordenador (`gandalf`) ou especialistas inativos (`jules` em espera).
     - Suporte a `Subagents` passados como lista ou string JSON codificada.

## 2. Arquivos alterados
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py`
- `sociedade-do-codigo/tests/test_conferir_identidade.py` (novo)

## 3. Saída dos testes dirigidos
1. **Sondas A01 (`sondas.py`):**
   ```
   {"sonda": "R01-identidade", "variante": "ordem-e-mencao-no-corpo", "E7": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"], "E8": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"]}
   {"sonda": "R01-legitima", "variante": "legitima", "E7": ["feito", "5 delegações"], "E8": ["feito", "1 ordem na conversa"]}
   {"sonda": "R01-outra-pasta", "variante": "outra-pasta", "E7": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"], "E8": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"]}
   {"sonda": "R01-prefixo", "variante": "prefixo", "E7": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"], "E8": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"]}
   {"sonda": "R01-sem-tempo", "variante": "sem-tempo", "E7": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"], "E8": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"]}
   {"sonda": "R01-anterior-passagem", "variante": "anterior-passagem", "E7": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"], "E8": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"]}
   {"sonda": "R01-ausente", "variante": "ausente", "E7": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"], "E8": ["não feito", "nenhuma conversa do Antigravity encontrada para a etapa \"e8\" após a passagem"]}
   {"sonda": "R01-ambigua", "variante": "ambigua", "E7": ["não feito", "ambiguidade: 2 conversas do Antigravity encontradas para a etapa \"e8\" após a passagem"], "E8": ["não feito", "ambiguidade: 2 conversas do Antigravity encontradas para a etapa \"e8\" após a passagem"]}
   {"testes": 2, "falhas": 0, "erros": 0, "pulados": 0}
   ```

2. **Novo teste unitário `test_conferir_identidade.py`:**
   ```
   Ran 10 tests in 0.092s
   OK
   ```

3. **Teste existente `test_conferir_l8.py`:**
   ```
   Ran 10 tests in 0.089s
   OK
   ```

4. **Suíte do pacote (`unittest discover -s sociedade-do-codigo/tests`):**
   ```
   Ran 797 tests in 78.196s
   FAILED (failures=1, skipped=1, expected failures=5)
   ```
   *(Nota: a única falha é a pré-existente de F5 em `test_instalar.py`, alheia à F3; todos os testes de conferência e identidade passaram 100%).*

## 4. O que não foi verificado
- Não foram executadas as sondas de outras fatias (A02, A03, A06), de responsabilidade das fatias correspondentes.
- Não foram criados commits nem push no Git (função do Gandalf).
