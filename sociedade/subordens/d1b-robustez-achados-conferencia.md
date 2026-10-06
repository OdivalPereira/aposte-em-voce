# Achados da conferência · d1b-robustez · rodada 2 do Gandalf

Do Círdan, na estação 4 (05/10/2026), antes da revisão independente. Candidato: `5e95a71`. As 11 sondas do revisor da d1 (`R`) passaram; estes achados vêm do uso real.

## K1 · bloqueador · `S/sc_registro.py` (F1, A02)
- **Condição:** o `registro.json` real da etapa tem os eventos 1–41 sem hash, 42–51 com hash e nenhum `corte_cadeia`. Rodei `sc.py conferir --ordem sociedade/ordens/d1b-robustez.md --registrar`.
- **Efeito:** a gravação definiu `corte_cadeia = 52`, o próprio evento novo. Na leitura seguinte: "Evento legado EVT-000042 (seq 42) anterior ao corte da cadeia (52) não pode conter hash". E6 e E7 viraram erro, e o registro do projeto ficou ilegível para o candidato. O Círdan restaurou o arquivo comitado.
- **Aceite:**
  - Na migração, o corte é o primeiro evento a partir do qual todos têm hash (aqui, 42), nunca o evento que está sendo gravado.
  - Um registro com essa forma (legado sem hash, depois cadeia, sem corte) continua legível antes e depois de uma gravação.
  - Teste com fixture sintética dessa forma, passando por `conferir --registrar`.
  - As sondas A02 de `R` continuam verdes.
  - Antes de devolver: copie `sociedade/registro.json` para uma pasta temporária, grave nela com `--pasta-sociedade` e confirme que a leitura funciona. Nunca grave no registro real.

## K2 · relevante · `S/sc_conferir.py` (cauda de governança, Q149 e Q178)
- **Condição:** depois do último commit de produto (`5e95a71`) vem um commit só de `sociedade/` (`c0c316f`).
- **Efeito:** E3 dá "atestado do commit 5e95a71, esperado c0c316f".
- **Aceite:** `commit_existe` e `atestado_aprovado` avaliam o último commit de produto quando os commits posteriores tocam só `sociedade/`, como o portão já faz desde a C2. Qualquer arquivo fora de `sociedade/` depois do atestado continua reprovando. Teste.

## K3 · verificar · `S/sc_conferir.py` (commit `5e95a71`, feito pelo Gandalf, contra a Q181)
- **Condição:** o Gandalf alterou `resolver_conversa_etapa` para aceitar o "repositório raiz associado ao worktree".
- **Risco:** uma conversa aberta na pasta principal do projeto, e não no worktree da etapa, passar a contar como delegação da etapa. Isso reabre a A01.
- **Aceite:**
  - Descubra, no log real do Antigravity, que campo estruturado identifica a pasta de uma conversa aberta num worktree.
  - A identidade usa só campos estruturados.
  - Uma conversa na pasta principal não conta, a menos que um campo estruturado a ligue ao worktree ou ao ramo da etapa.
  - Se não houver como distinguir, o resultado é "não verificado", com motivo.
  - Teste com as duas variantes: a conversa legítima no worktree e a conversa na pasta principal depois da passagem.

## K4 · relevante · `S/sc_conferir.py` (várias rodadas do Gandalf, Q180)
- **Condição:** com uma conversa por rodada, a etapa passa a ter mais de uma conversa do Gandalf, cada uma depois de uma `passagem`.
- **Efeito:** o `@etapa` procura uma conversa só. Na rodada 2, E6 e E7 dariam "ambiguidade" ou contariam só as delegações da rodada nova.
- **Aceite:**
  - Cada `passagem` para o Gandalf liga no máximo uma conversa: a primeira aberta depois dela no worktree, por campo estruturado.
  - `delegacoes` soma as delegações de todas as rodadas da etapa.
  - `conversa_nova` vale para cada rodada (uma ordem por conversa).
  - Ambiguidade só conta dentro de uma mesma rodada.
  - Teste com duas rodadas.

## Como executar (Q177, Q180, Q181)
- **Conversa nova do Gandalf.** Ele lê só esta página, a seção "Onde o Gandalf para" da ordem e o próprio estado.
- **K1:** um `elrond` novo, escreva só `S/sc_registro.py` e um teste novo em `T/`.
- **K2, K3 e K4:** outro `elrond` novo, escreva só `S/sc_conferir.py` e um teste novo em `T/`.
- **O Gandalf não edita lógica.** Ele roda o portão por fatia e o final (`--base 4fdd7b5`), atualiza o próprio estado e **para**. Push só do ramo, sem amend nem reset.
