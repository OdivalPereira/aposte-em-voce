# Ordem d1b-robustez — fechar os resíduos da d1 no pacote e tornar o processo honesto e econômico

Para: Gandalf (Antigravity, Gemini 3.8 Flash, high) · CONVERSA NOVA
Etapa: d1b-robustez · Base: `4fdd7b5` (cabeça da d1, com o design) · Worktree: `~/.sociedade/trabalho/aposte-em-voce/d1b-robustez` · Ramo: `etapa/d1b-robustez`
Especialistas (agentes instalados): `elrond`, um novo por fatia (F1–F5); `galadriel` (revisão interna e F6) · Jules: nenhum
**Alto impacto por definição (Q176):** F1–F5. Revisão interna da Galadriel em F1–F5 e revisão independente **completa**.

## Objetivo
Pedido de Odival: "tratar os ajustes residuais de robustez do pacote (`sc_conferir.py`, `sc_registro.py`, `sc_rodada.py` e `.claude/settings.json`), aproveitando o trabalho de design e acessibilidade já concluído", com as correções de processo da avaliação da d1.

Como Odival percebe:
- as sondas que reprovaram a d1 (A01–A03, A06) passam;
- `passar`, `revisar` e `decidir` deixam rastro honesto;
- o revisor roda o app na cópia;
- o PR leva o design da d1 e as correções à `main`.

## Leia só
1. Esta ordem.
2. `sociedade/regras.md`, seções 3 a 5 (Q176–Q181 são novas).
3. `sociedade/avaliacao-d1-design.md`.
4. `sociedade/pareceres/parecer-d1-design.md`, só a seção "Achados".
5. `sociedade/subordens/d1b-robustez-gandalf-estado.md`, quando existir.

## Onde o Gandalf para e o que não faz (Q177, Q180, Q181)
- **Uma rodada só:** da F1 ao `entregar` final, numa conversa de até ~250 passos. Perto do teto, grava o estado e devolve. Depois do `entregar` final, **para e devolve.** PR, `conferir --registrar`, `revisar`, `passar` e governança são do Círdan.
- **Delega ao agente instalado (Q182):** `invoke_subagent` com `TypeName` igual ao nome do especialista (`elrond`, `galadriel`), nunca `self`.
- Não edita lógica nem depura; escreve só estado, subordens e a integração da versão (Q164). Ajuste vai a um especialista novo.
- Nada de amend, reset ou push forçado depois do push (Q178). Push só do `etapa/d1b-robustez`.
- Economia (Q170): devolução de até 2 KB, detalhe em `sociedade/subordens/d1b-robustez-<fatia>-retorno.md`.

## Abreviações
- `S` = `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`; `T` = `sociedade-do-codigo/tests`.
- `R` = `~/.sociedade/trabalho/d1-design/reconferencia-d1-design/revisao-saida` (só leitura); sondas: `python3 -B R/sondas.py --scripts <worktree>/S --somente <testes>`.

## Fatias (escreva-só disjuntos)
Sequência: F1; depois F2–F5 em paralelo; depois a revisão interna; depois a F6, a integração e o `entregar` final.

1. **F1 · A02, cadeia do registro** · escreva só: `S/sc_registro.py` e `T/test_registro_cadeia_estrita.py` (novo) · aceite:
   - Há um corte explícito e gravado entre o formato antigo e a cadeia. Daí em diante, evento sem `hash` ou `prev_hash` é registro corrompido, inclusive na cauda.
   - O legado só vale antes do corte.
   - Sondas `test_A02_adulteracao`, `test_A02_hash_omitido` e `test_A02_legado` verdes.
   - `sc_registro` tem 40 usos: a suíte inteira do pacote fica verde.
2. **F2 · A03, trava da troca** · escreva só: `S/sc_rodada.py` e `T/test_rodada_trava.py` (novo) · aceite:
   - Leitura, validação e gravação de perfil e registro ficam sob uma trava comum, em `papel trocar` e em `papel emulacao`.
   - Uma troca intercalada é recusada ou deixa estado final válido.
   - O teste exercita a janela, a partir de estado válido.
   - Sondas `test_A03_entre_validacoes`, `test_A03_apos_ultima_validacao`, `test_A05_rollback_emulacao` e `test_A05_rollback_troca` verdes.
3. **F3 · A01, identidade da conversa** · escreva só: `S/sc_conferir.py` e `T/test_conferir_identidade.py` (novo) · aceite:
   - `@etapa` resolve a pasta só por campo estruturado do log do Antigravity, nunca por menção no texto.
   - Declaração divergente é recusada.
   - Sem campo estruturado, o resultado é "não verificado", nunca "feito".
   - Só contam conversas iniciadas depois da última `passagem` para o Gandalf, e só delegações com `TypeName` de especialista do perfil; `self` não conta (Q182).
   - O teste passa pelo `conferir_item` e pela medição.
   - Sondas `test_A01_variantes_originais` e `test_A01_identidade_corpo` verdes.
4. **F4 · Processo honesto** · escreva só: `S/sc_passagem.py`, `S/sc_ciclo.py`, `S/sc.py` (só `passar`, `revisar` e `decidir`) e `T/test_processo_d1b.py` (novo) · aceite:
   - **P1:** `passar` exige `--por` (sem autor padrão) e grava sempre a hora atual (sem sobrescrever). Uma segunda passagem para o mesmo destino na mesma etapa exige `--nova-rodada --motivo`.
   - **P2:** `revisar` recusa preparar a cópia se `sociedade/perfil.md` ou `sociedade/regras.md` do worktree diferirem do HEAD (Q178). A cópia roda, sem rede, o comando de teste de cada área do perfil (dependências levadas ou ligadas só para leitura).
   - **P3:** `decidir corrigir|rejeitar` exige `--motivo`. Um segundo `revisar --parecer` na mesma etapa grava `parecer-<etapa>-reconferencia.md` e nunca sobrescreve o primeiro; o registro liga os dois.
5. **F5 · A06, permissões de merge** · escreva só: `.claude/settings.json`, `sociedade-do-codigo/adapters/claude/settings.json.modelo` e `T/test_permissoes_merge.py` (novo) · aceite:
   - Uma tabela de casos, testada nas duas configurações:
     - pedem confirmação: `gh pr merge 12 --merge`, `--merge --repo O/P`, `--merge --subject "x"` e `--merge --body "x"`;
     - são negados: `--squash`, `-s`, `--rebase`, `-r`, `--auto`, `--admin` e as combinações.
   - Sondas `test_A06_configuracoes` e `test_A06_caminho_legitimo` verdes.
   - `test_instalar.py` verde.
6. **Revisão interna** · Galadriel · grava `sociedade/subordens/d1b-robustez-revisao-interna.md` sobre F1–F5, com as sondas de `R` como base. Cada achado vai para um Elrond novo (Q171).
7. **F6 · Textos** · Galadriel · escreva só: `CLAUDE.md`, `sociedade-do-codigo/adapters/claude/CLAUDE.md.modelo`, os `SKILL.md` do núcleo, `sc-execucao`, `sc-papeis` e `sc-revisao`, e `S/../assets/ordem-modelo.md` · aceite:
   - Q176–Q181 e os comandos da F4 descritos.
   - O modelo da ordem ganha a seção "Onde o Gandalf para" e o teto de 8 KB.
   - `validar_pacote.py` verde.
8. **Integração** (Gandalf) · versão **3.3.0** e CHANGELOG com A01–A03, A06 e P1–P3.

## Portão
- Por fatia: `sc.py entregar --etapa d1b-robustez --base <commit anterior> --fatia <N> --pasta-projeto <worktree> --pasta-sociedade <worktree>/sociedade`, num checkout limpo.
- No fim: o mesmo, sem `--fatia`, com `--base 4fdd7b5` e as duas áreas.

## Paradas e fora do escopo
- Teto de 1.500 linhas por área (Q168); estimativa: ~700 no pacote.
- Q12.
- Dado só sintético.
- Nada em `src/` nem em `tests/` do app. O design da d1 vai como está.
- Fica de fora:
  - telas;
  - Jules;
  - tokens do Antigravity (seguem n/d);
  - devolução ao canônico e reinstalação (depois do merge).

## Revisão (Barbárvore, completa, sessão nova)
- Protocolo completo (passo 0, oito lentes e matriz) sobre `c927e5d..HEAD` na área `pacote` e nas permissões. Os scripts da d1 nunca tiveram protocolo completo.
- No app: `src/` e os testes do app iguais a `87c8114`; `npm test` na cópia fecha a A04 com o app.
- As sondas de `R` são o piso.
- Reconferência: sessão nova, só achados e diff (Q180).

## Entregas verificáveis
```entregas
E1 | commit_existe | etapa/d1b-robustez
E2 | arquivos_em | 4fdd7b5..etapa/d1b-robustez | sociedade-do-codigo/ | .claude/settings.json | CLAUDE.md
E3 | atestado_aprovado | sociedade/pareceres/atestado-d1b-robustez.json | etapa/d1b-robustez
E4 | arquivo_existe | sociedade-do-codigo/tests/test_registro_cadeia_estrita.py
E5 | arquivo_existe | sociedade/subordens/d1b-robustez-revisao-interna.md
E6 | delegacoes | antigravity | @etapa | 7
E7 | conversa_nova | antigravity | @etapa
E8 | push_feito | etapa/d1b-robustez
E9 | parecer_valido | sociedade/pareceres/parecer-d1b-robustez.md
```

## Retorno
Até 2 KB: veredito, commits por fatia, atestado, sondas de `R` e achados internos. Detalhe em `sociedade/subordens/d1b-robustez-gandalf-estado.md`.
