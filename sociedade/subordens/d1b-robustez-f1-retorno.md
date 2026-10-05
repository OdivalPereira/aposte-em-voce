# Retorno da Subordem d1b-robustez · F1 (Cadeia do registro estrita · A02)

- **Especialista:** Elrond (dados, backend e persistência)
- **Data:** 05/10/2026
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Etapa:** `d1b-robustez`
- **Fatia:** F1 (Cadeia do registro estrita · Achado A02)

---

## 1. O que foi feito
1. **Validação estrita de integridade e corte explícito em `sc_registro.py`:**
   - Adicionada verificação de campo `corte_cadeia` na raiz do registro.
   - Daí em diante (`seq >= corte_cadeia`), todo evento exige obrigatoriamente `hash` não vazio e `prev_hash` válido. Qualquer omissão (inclusive no último evento ou cauda) lança `ErroRegistroCorrompido`.
   - Eventos antes do corte (`seq < corte_cadeia`) são estritamente legados e não podem conter `hash` nem `prev_hash`.
   - Para registros antigos sem `corte_cadeia`, a cadeia inicia a partir do primeiro evento com hash, impedindo omissão posterior.
   - Em `aplicar_mutacao` (real e simulada) e em `importar_resumo_projeto`, o `corte_cadeia` é automaticamente gravado na raiz e preservado nas mutações seguintes.
   - Exposta propriedade `reg.corte_cadeia` e suporte ao parâmetro em `Registro.inicializar`.

2. **Criação da suíte unitária `test_registro_cadeia_estrita.py`:**
   - Implementados 15 testes cobrindo:
     - Corte explícito gravado na primeira mutação e sua preservação.
     - Aceite de eventos legados estritamente antes do corte.
     - Recusa de eventos contendo hash antes do corte.
     - Recusa de remoção de hash na cauda (sem legado e com legado pós-corte).
     - Recusa de remoção de prev_hash na cauda e adulteração de prev_hash.
     - Recusa de evento intermediário sem hash.
     - Recusa de corte inválido (não inteiro, booleano, negativo ou salto futuro).
     - Comportamento em mutações simuladas (`aplicar=False`).

## 2. Arquivos alterados
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_registro.py`
- `sociedade-do-codigo/tests/test_registro_cadeia_estrita.py` (novo)

## 3. Saída dos testes dirigidos
1. **Sondas A02 (`sondas.py`):**
   ```
   {"sonda": "R02-adulteracao", "codigo": 0, "integro_aceito": true, "adulterado_recusado": true, "legado": false, "remoção_hash": false}
   {"sonda": "R02-omissao", "codigo": 0, "integro_aceito": true, "adulterado_recusado": true, "erro": "ErroRegistroCorrompido: Evento EVT-000001 (seq 1) a partir do corte da cadeia (1) sem hash obrigatório.", "legado": false, "remoção_hash": true}
   {"sonda": "R02-legado", "codigo": 0, "integro_aceito": true, "adulterado_recusado": true, "legado": true, "remoção_hash": false}
   {"testes": 3, "falhas": 0, "erros": 0, "pulados": 0}
   ```

2. **Novo teste unitário `test_registro_cadeia_estrita.py`:**
   ```
   Ran 15 tests in 0.047s
   OK
   ```

3. **Suíte completa do pacote (`unittest discover -s sociedade-do-codigo/tests`):**
   ```
   Ran 780 tests in 81.845s
   OK (skipped=1, expected failures=5)
   ```

## 4. O que não foi verificado
- Não foram executadas sondas de outras fatias (A01, A03, A06), que pertencem às fatias F2–F5.
- Não foram feitas alterações nem commits Git no worktree (função do Gandalf).
