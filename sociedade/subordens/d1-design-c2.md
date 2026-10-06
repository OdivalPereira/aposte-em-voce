# Subordem d1-design-c2 · Correções A01, A02, A03, A05 e A06 (Método, Registro, Concorrência e Permissões)

Para: Elrond (Dados e Persistência)
De: Gandalf (Coordenador)
Contexto: Etapa d1-design · Rodada de Correção após Parecer do Barbárvore (Q84/Q85)

## 1. Objetivo da Subordem
Corrigir os achados relatados pelo revisor independente Barbárvore no pacote `sociedade-do-codigo` e nas configurações:
1. **[bloqueador] A01 — sc_conferir.py:** `@etapa` aprova conversa de outra pasta e sem prova temporal válida.
2. **[bloqueador] A02 — sc_rodada.py / sc_registro.py:** comando de emulação não grava nem valida a cadeia de hash exigida pelo critério C25 e F5/L1.
3. **[bloqueador] A03 — sc_rodada.py:** desligar emulação valida estado antigo e permite R3 violada no estado final em cenário concorrente.
4. **[relevante] A05 — sc_rodada.py:** falha no evento deixa o perfil alterado sem registro correspondente (falta de rollback / transação).
5. **[relevante] A06 — .claude/settings.json e adapters/claude/settings.json.modelo:** opções curtas `-s` (squash) e `-r` (rebase) escapam das proibições de `gh pr merge`.

## 2. Arquivos Permitidos
Trabalhe exclusivamente em `/home/odival/.sociedade/trabalho/aposte-em-voce/d1-design`:
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_registro.py`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_rodada.py`
- `.claude/settings.json`
- `sociedade-do-codigo/adapters/claude/settings.json.modelo`
- `sociedade-do-codigo/tests/` (atualização e novos testes)

**PROIBIDO:** Não altere arquivos em `src/`, nem faça commit ou push.

## 3. Requisitos de Cada Correção

### A01 — sc_conferir.py
- **Identidade da pasta:** Normalizar caminhos (`Path(p).resolve().as_posix()`). Comparar a pasta do worktree de forma exata contra as URIs da conversa (evitar correspondência por substring ou prefixo).
- **Pasta obrigatória no transcript:** Não aceitar transcript se a pasta de trabalho dele for diferente da pasta do worktree (`pasta_wt`), mesmo que cite o nome do arquivo de ordem.
- **Prova temporal:** A conversa deve possuir `created_at` com timestamp válido posterior ou igual ao momento da passagem para Gandalf (`ts_passagem`). Recusar se não houver timestamp ou se for anterior à passagem.
- **Ambiguidade:** Se nenhuma conversa atender a todos os critérios ou houver ambiguidade irresolvível, retornar `(NAO_FEITO, motivo)`.
- **Testes:** Adicionar testes negativos em `sociedade-do-codigo/tests/test_conferir_l8.py` cobrindo: pasta errada, prefixo de pasta, ausência de timestamp e timestamp anterior à passagem.

### A02 — sc_registro.py / sc_rodada.py
- **Cadeia de hash nos eventos:**
  - Em `sc_registro.py`, cada novo evento adicionado via `aplicar_mutacao` deve calcular:
    - `prev_hash`: hash do evento anterior com hash (ou vazio se for o primeiro elo).
    - `hash`: SHA-256 do payload canônico do evento sem a chave `hash` (`json.dumps({k: v for k, v in ev.items() if k != 'hash'}, sort_keys=True, ensure_ascii=False)`).
  - Em `carregar_dados_registro`, verificar para cada evento que tenha o campo `hash`:
    - Que `prev_hash` coincide com o hash do evento anterior;
    - Que `hash` coincide com o SHA-256 recalculado dos dados do evento.
    - Se houver divergência (ex.: motivo ou autor adulterado manualmente no arquivo), lançar `ErroRegistroCorrompido`.
  - Tratar eventos legados (sem campo `hash`) de forma compatível, sem quebrar históricos antigos.
- **Testes:** Adicionar teste no qual um evento com hash é gravado, um campo (ex.: motivo) é adulterado manualmente no arquivo, e o recarregamento via `Registro` falha com `ErroRegistroCorrompido`.

### A03 e A05 — sc_rodada.py
- **Rollback em falha de evento (A05):**
  - Em `cmd_papel_emulacao` e `cmd_papel_trocar`, salvar o conteúdo anterior de `perfil.md` antes de qualquer alteração no disco.
  - Se a chamada a `reg.aplicar_mutacao` lançar qualquer exceção (ex.: erro de I/O, erro de concorrência ou registro corrompido), restaurar imediatamente o arquivo `perfil.md` ao seu conteúdo original e relançar o erro.
- **Revalidação R1-R3 contra concorrência (A03):**
  - Em `cmd_papel_emulacao`, revalidar as regras estritas R1-R3 sobre o perfil imediatamente antes de gravar o perfil e o evento, garantindo que operações concorrentes/intercaladas não deixem a emulação desligada com violações de regras invariantes.
- **Testes:** Testar que se a gravação de evento falhar, o `perfil.md` permanece intacto (ou é restaurado), e testar a integridade das regras estritas.

### A06 — Configurações do Claude (.claude/settings.json e modelo)
- Nos arrays de `deny` de `.claude/settings.json` e `sociedade-do-codigo/adapters/claude/settings.json.modelo`, incluir as opções curtas de squash (`-s`) e rebase (`-r`) do comando `gh pr merge`:
  - `"Bash(gh pr merge*-s*)"`
  - `"Bash(gh pr merge*-r*)"`
  - Mantendo todos os deny e ask já existentes.

## 4. Testes Dirigidos
Execute e valide:
- `python3 -B -m unittest discover -s sociedade-do-codigo/tests`
- `python3 -B sociedade-do-codigo/scripts/validar_pacote.py`

## 5. Retorno
Grave o arquivo de detalhe em:
`/home/odival/.sociedade/trabalho/aposte-em-voce/d1-design/sociedade/subordens/d1-design-c2-retorno.md`
E devolva no chat um resumo conciso de até 2 KB com o veredito e o resultado dos testes.
