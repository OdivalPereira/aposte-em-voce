# Retorno da Subordem d1b-robustez · Rodada 2 · K1 (Corte da cadeia de registro em migração com legado)

- **Especialista:** Elrond (dados, persistência e backend)
- **Data:** 05/10/2026
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Etapa:** `d1b-robustez` (Rodada 2)
- **Achado:** K1 (bloqueador)

---

## 1. O que foi feito
1. **Resolução de `corte_cadeia` em migração com legado (`sc_registro.py`):**
   - Implementada a função auxiliar `resolver_corte_cadeia(eventos_disco, eventos_novos=None, corte_existente=None)`.
   - Se `corte_cadeia` já existir gravado na raiz, ele é rigorosamente preservado.
   - Se `corte_cadeia` for `None` (como ocorre no registro legado em migração com eventos 1..41 sem hash e 42..51 com hash):
     - O corte é definido como o `seq` do primeiro evento que já possui hash no disco (neste caso, `42`).
     - Nunca é definido como o `seq` do evento novo sendo gravado quando já existia cadeia anterior no disco.
     - Se nenhum evento anterior possuía hash (legado 100% puro), o corte assume o `seq` do primeiro evento formatado novo.
   - Integrado em `aplicar_mutacao` (execução real com lock exclusivo e simulação) e em `importar_resumo_projeto`.
   - `sociedade/registro.json` real NÃO foi tocado nem modificado.

2. **Criação da suíte unitária de testes sintéticos (`test_registro_migracao_legado.py`):**
   - 12 testes cobrindo:
     1. Carregamento válido de registro com eventos 1..41 sem hash e 42..51 com hash, sem `corte_cadeia`.
     2. Gravação de mutação via `aplicar_mutacao`: `corte_cadeia` atribuído como 42 (não 52); arquivo íntegro e re-carregável sem erro.
     3. Mutação simulada (`aplicar=False`): `corte_cadeia` atribuído como 42 em memória, sem tocar no disco.
     4. Gravação de conferência via `conferir --registrar`: `corte_cadeia` atribuído como 42 e arquivo íntegro.
     5. Importação de resumo externo (`importar_resumo_projeto`): `corte_cadeia` atribuído como 42.
     6. Detecção e recusa de adulteração antes do corte (inserção indevida de `hash` ou `prev_hash` em evento legado).
     7. Detecção e recusa de adulteração depois do corte (alteração de dados, adulteração de `prev_hash`, remoção de hash na cauda).
     8. Detecção e recusa de adulterações antes da migração (com `corte_cadeia` ainda `None`).

3. **Confirmação isolada em diretório temporário (`/tmp`):**
   - Cópia do arquivo real `sociedade/registro.json` para pasta temporária `/tmp/teste_isolado_k1_.../sociedade/registro.json`.
   - Validação da leitura inicial com 52 eventos e `corte_cadeia: None`.
   - Execução de `aplicar_mutacao` gravando evento 53: `corte_cadeia` foi definido como 42 e o arquivo foi recarregado com sucesso por nova instância de `Registro`.
   - Execução de `conferir --registrar` gravando evento 54: `corte_cadeia` preservado como 42 e recarregado com sucesso.

## 2. Arquivos alterados / criados
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_registro.py` (alterado)
- `sociedade-do-codigo/tests/test_registro_migracao_legado.py` (novo)
- `sociedade/subordens/d1b-robustez-r2-k1-retorno.md` (relatório de retorno)

## 3. Saída dos testes dirigidos
1. **Sondas A02 (`sondas.py`):**
   ```
   {"sonda": "R02-adulteracao", "codigo": 0, "integro_aceito": true, "adulterado_recusado": true, "legado": false, "remoção_hash": false}
   {"sonda": "R02-omissao", "codigo": 0, "integro_aceito": true, "adulterado_recusado": true, "erro": "ErroRegistroCorrompido: Evento EVT-000001 (seq 1) a partir do corte da cadeia (1) sem hash obrigatório.", "legado": false, "remoção_hash": true}
   {"sonda": "R02-legado", "codigo": 0, "integro_aceito": true, "adulterado_recusado": true, "legado": true, "remoção_hash": false}
   {"testes": 3, "falhas": 0, "erros": 0, "pulados": 0}
   ```

2. **Nova suíte unitária (`test_registro_migracao_legado.py`):**
   ```
   Ran 12 tests in 0.036s
   OK
   ```

3. **Suíte completa do pacote (`unittest discover -s sociedade-do-codigo/tests`):**
   ```
   Ran 834 tests in 83.437s
   OK (skipped=1, expected failures=5)
   ```

4. **Teste isolado com cópia de `sociedade/registro.json`:**
   ```
   [OK] Leitura inicial do registro real copiado: Total eventos: 52, corte_cadeia no disco: None
   [OK] Leitura após mutação no registro copiado: Total eventos: 53, corte_cadeia no disco: 42
   [OK] Leitura após conferir --registrar no registro copiado: Total eventos: 54, corte_cadeia: 42
   TODAS AS VALIDAÇÕES ISOLADAS PASSARAM COM SUCESSO!
   ```

## 4. O que não foi verificado
- Não foi feita nenhuma alteração em `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py` (objeto das fatias K2, K3 e K4).
- Não foi feito commit nem push (atribuição do Gandalf).
