# Retorno da Subordem d1b-robustez · F2 (Trava da troca · A03)

- **Especialista:** Elrond (dados, backend e persistência)
- **Data:** 05/10/2026
- **Worktree:** `/home/odival/.sociedade/trabalho/aposte-em-voce/d1b-robustez`
- **Etapa:** `d1b-robustez`
- **Fatia:** F2 (Trava da troca · Achado A03)

---

## 1. O que foi feito
1. **Implementação da trava comum de perfil e registro em `sc_rodada.py`:**
   - Adicionada a constante `NOME_ARQUIVO_TRAVA_PERFIL = '.trava_perfil.tmp'` e a exceção `ErroTravaPerfil`.
   - Criado o context manager `trava_perfil_registro(pasta=None, bloqueante=False)` com lock exclusivo não-bloqueante (`fcntl.flock(LOCK_EX | LOCK_NB)`), garantindo serialização estrita e falha imediata com mensagem explícita caso outra operação concorra no perfil/registro.
   - Atualizado `cmd_papel_emulacao`:
     - Sob `--aplicar`, adquire `trava_perfil_registro(p_soc)`.
     - Sob a proteção da trava: relê o perfil e registro frescos do disco, executa a revalidação estrita das regras invariantes (R1–R3), grava `perfil.md` (`atualizar_emulacao`) e aplica o evento em `registro.json` (`reg_fresco.aplicar_mutacao`).
     - Em caso de falha de persistência no evento, restaura o conteúdo anterior de `perfil.md` antes de liberar a trava (fechamento de A05).
   - Atualizado `cmd_papel_trocar`:
     - Sob `--aplicar`, adquire `trava_perfil_registro(p_soc)`.
     - Sob a proteção da trava: relê o perfil e registro frescos, revalida as regras da troca (`validar_regras_troca`), grava `perfil.md` de forma atômica e registra o evento em `registro.json` (`reg_fresco.registrar_troca_papel`).
     - Em caso de falha no evento, restaura o conteúdo anterior de `perfil.md` antes de liberar a trava (fechamento de A05).
   - Resultado: qualquer operação intercalada durante a janela crítica de `papel trocar` ou `papel emulacao` é recusada pela trava ativa ou tem suas violações detectadas na revalidação, garantindo que o perfil final permaneça sempre válido (nunca emulação desligada com violações de R1–R3).

2. **Criação da suíte unitária `sociedade-do-codigo/tests/test_rodada_trava.py`:**
   - 10 testes cobrindo:
     - `test_trava_exclusiva_bloqueia_concorrencia_direta`: colisão direta de duas aquisições não-bloqueantes.
     - `test_trava_liberada_permite_nova_aquisicao`: liberação normal e reaquisição.
     - `test_trava_liberada_apos_excecao`: liberação garantida no bloco `finally` em caso de erro.
     - `test_janela_entre_validacoes_a_partir_de_estado_valido`: exercita a janela antes da revalidação a partir de estado válido, confirmando detecção da violação e recusa do desligamento da emulação.
     - `test_janela_apos_ultima_validacao_recusa_troca_concorrente`: exercita a janela durante a escrita do perfil, confirmando recusa da troca pela trava ativa e conclusão válida do desligamento sem violações.
     - `test_trocar_segura_trava_e_recusa_emulacao_concorrente`: protege o caminho inverso (trocar segurando trava e recusando desligamento concorrente).
     - `test_rollback_emulacao_sob_trava_preserva_fontes`: restauração de `perfil.md` em falha simulada de I/O em desligar.
     - `test_rollback_troca_sob_trava_preserva_fontes`: restauração de `perfil.md` em falha simulada de I/O em trocar.
     - `test_simulacao_nao_cria_arquivo_de_trava`: N5 cumprido (simulação não cria arquivo de trava nem escreve em disco).
     - `test_concorrencia_real_entre_processos`: concorrência real entre subprocessos do SO via trava de arquivo.

## 2. Arquivos alterados
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_rodada.py`
- `sociedade-do-codigo/tests/test_rodada_trava.py` (novo)

## 3. Saída dos testes dirigidos
1. **Sondas A03 e A05 (`sondas.py`):**
   ```
   {"sonda": "R03-apos-revalidacao", "codigo_desligar": 0, "codigo_trocar": ["erro: Operação concorrente em andamento no perfil/registro (trava ativa)."], "emulacao_final": false, "violacoes": [], "janela": "apos-ultima-validacao"}
   {"sonda": "R03-antes-revalidacao", "codigo_desligar": "erro: desligamento de emulação recusado por violação de regra invariante (R1-R3).", "codigo_trocar": [0], "emulacao_final": true, "violacoes": ["Violação de R3: Execução (Coordenador: Gandalf) fora do Google ('Anthropic') requer decisão registrada no registro.json.", "Violação de R3: Execução (Dados e persistência: Elrond) fora do Google ('Anthropic') requer decisão registrada no registro.json."], "janela": "entre-validacoes"}
   {"sonda": "R05-emulacao", "codigo": "OSError: falha sintética de gravação", "fontes_preservadas": true, "troca": false}
   {"sonda": "R05-troca", "codigo": "OSError: falha sintética de gravação", "fontes_preservadas": true, "troca": true}
   {"testes": 4, "falhas": 0, "erros": 0, "pulados": 0}
   ```

2. **Novo teste `test_rodada_trava.py`:**
   ```
   Ran 10 tests in 0.365s
   OK
   ```

3. **Suíte relacionada do pacote (`test_rodada_trava.py`, `test_emulacao.py`, `test_troca_papel.py` e `test_rodada*.py`):**
   ```
   Ran 114 tests in 10.9s
   OK
   ```

## 4. O que não foi verificado
- Não foram executadas as sondas de A01, A02 e A06 (escopo das outras fatias F1, F3, F5).
- Falhas observadas no teste integral do pacote decorrem de trabalho concorrente na fatia F4 em `sc_ciclo.py` (`NameError: name 'commit' is not defined`), fora do escopo da fatia F2.
- Não foram feitos commits nem push (tarefa do Gandalf).
