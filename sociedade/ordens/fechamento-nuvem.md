# Ordem fechamento-nuvem — menos releitura, extratos mensais como histórico, aceite mais firme

Para: Gandalf (Claude Code em nuvem, subagente `gandalf`, esforço high) · CONVERSA NOVA
Etapa: fechamento-nuvem · Base: `dc35a59` (cabeça do `etapa/a1-parser`; o PR #2 ainda não foi integrado) · Worktree: `~/.sociedade/trabalho/aposte-em-voce/fechamento-nuvem` · Ramo: `etapa/fechamento-nuvem`
Aprovada por Odival em 03/10/2026, com os ajustes da seção "Ajustes da aprovação".
Especialistas: Galadriel (F1), Elrond (F2), Elrond em instância nova (F3) · Revisão interna (Galadriel): F2 (pipeline) e F3 (B15), numa revisão só · Jules: nenhum
Revisão independente: **reduzida** (`barbarvore-reduzida`), marcada "aceite em emulação" e "revisor não calibrado"

## Objetivo
Pedido de Odival: "Quero que a Sociedade gaste menos releitura de contexto, que o app trate vários extratos mensais como um histórico só e que tudo o que foi feito na nuvem fique registrado para continuar fora dela."

Como Odival percebe:
- o `sc.py sessao claude` mostra, por agente e modelo, entrada, cache escrito, cache lido e saída, e o `decidir` grava isso na etapa;
- vários PDFs mensais da mesma conta aparecem como um histórico só, com os meses faltando e o encadeamento de saldos;
- o layout sintético no estilo Nubank sai como "leitura suficiente".

## Leia só
1. Esta ordem.
2. `sociedade/regras.md`, seções 3 e 4.
3. `sociedade/nuvem/backlog.md`: só as linhas B15 e B17b.
4. `docs/onda-1.md`: seções 5.2, 5.3 e 5.5 e a linha T99 da seção 4.
5. `sociedade/perfil.md`, seção "Portão por área".

Cada especialista lê só o seu escreva-só e o que a subordem citar, **por trecho** (regra nova da F1, já valendo nesta etapa).

## Regras de economia já valendo nesta etapa (F1 as formaliza)
- Devolução ao Círdan e ao Gandalf de até **2 KB** no chat; o detalhe vai para `sociedade/subordens/fechamento-nuvem-<fatia>-retorno.md`, que o próximo lê só se precisar.
- Testes e portão com saída curta: só o resumo e as falhas (`| tail`, `--reporter=dot`, `-q`).
- Conversa curta: se a tarefa crescer demais, o agente grava o estado em `sociedade/subordens/fechamento-nuvem-<fatia>-estado.md` e devolve; um agente novo continua lendo só esse arquivo.
- O Gandalf não fica numa conversa longa. Cada rodada sua termina gravando o estado em `sociedade/subordens/fechamento-nuvem-gandalf-estado.md`. A rodada seguinte pode ser um Gandalf novo, que lê só esse arquivo e o retorno recebido.

## Onde se mexe
O candidato não altera `sociedade/`, `docs/` nem `.claude/`. `S = sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`; `T = sociedade-do-codigo/tests`. Especialistas não comitam; o Gandalf comita por fatia e roda o portão num checkout limpo; a base da fatia é o commit anterior (Q165).

## Fatias (escreva-só disjuntos; prioridade F1 > F2 > F3)
Ordem: F1 e F2 em paralelo; F3 depois da F1 (mexe em scripts vizinhos), só se couber.

1. **F1 · Economia de contexto (pacote)** · Galadriel · escreva só: `S/sc_sessao.py`, `S/sc_metricas.py`, `S/sc_ciclo.py` (só a gravação das métricas no `decidir`), `T/test_sessao_consumo.py` (novo), `T/test_metricas.py`, `SKILL.md` e `references/` do núcleo, `skills/sc-execucao/`, `skills/sc-papeis/`, `skills/sc-revisao/SKILL.md` (só o trecho de economia), `sociedade-do-codigo/CHANGELOG.md` · aceite:
   - `sc.py sessao claude` soma, a partir dos logs (principal e `subagents/`), por agente e por modelo: entrada, cache escrito, cache lido e saída. Deduplica por id da mensagem. O nome do agente sai do tipo do subagente ou do início do primeiro pedido. Tem `--desde <ISO 8601>` para medir só o trecho de uma sessão que compartilha o log.
   - O `decidir` grava esse consumo nas métricas da etapa no registro, e a linha de `evolucao.md` ganha a coluna "Consumo (cache lido)". Com o log ausente, fica "n/d", sem quebrar.
   - Teste com transcrições sintéticas: soma, deduplicação, separação por agente e modelo, `--desde` e log ausente.
   - Os textos do pacote (núcleo e skills) passam a ter as regras de economia:
     - conversa curta por agente, com estado em arquivo e continuação por agente novo;
     - saída curta (resumo e falhas) e leitura por trecho;
     - devolução de até 2 KB no chat, com o detalhe em arquivo (revisa a Q99);
     - cada agente lê só o que a ordem ou subordem indicou (reforço da Q21);
     - medir pelo log é permitido e estimar continua proibido (ajusta a regra 8 do núcleo).
   - Suíte do pacote e `validar_pacote.py` verdes.
2. **F2 · Extratos mensais e Nubank (app)** · Elrond · pipeline de **alto impacto** · escreva só: `src/leitura/` (inclui `historico.ts`, novo), `src/app.tsx`, `src/telas/` (**só mudanças funcionais, sem redesenho visual**: exceção à Q169 pedida por Odival), `src/ui/` (só o necessário para os novos dados), `tests/unit/`, `tests/e2e/` · aceite:
   - **Histórico contínuo:** os arquivos da mesma conta são agrupados num histórico em ordem de período. A conta é identificada por banco provável mais um identificador estrutural. Nunca se usa o nome da pessoa nem o número completo da conta; se nada distinguir, entram juntos com um aviso. A tela mostra o período total, os meses cobertos e os meses faltando.
   - **Encadeamento:** o saldo final de um mês tem de ser igual ao saldo inicial do seguinte, em centavos e sem tolerância. Se não for, aparece um aviso nomeando o mês, e nenhum lançamento é alterado (5.2). As regras de duplicidade da 5.3 continuam.
   - **Acrescentar depois:** a pessoa escolhe mais arquivos sem perder os já lidos, com progresso por arquivo. O mesmo arquivo (mesmo hash) não duplica.
   - **T99:** botão "Copiar assinatura do layout". Copia só a estrutura: cabeçalhos da tabela, posição relativa das colunas, formato de data e de valor com os dígitos mascarados (`99/99/9999`, `9.999,99`). Sem valores, nomes nem descrições. Um teste prova que a assinatura de um extrato sintético não contém nenhum dígito real nem nenhuma descrição dele.
   - **Layout sintético "agrupado por dia"**, no estilo Nubank, montado em texto posicionado no teste, sem dado real:
     - valores sem sinal, agrupados por dia sob os títulos "Total de entradas" e "Total de saídas" (cada título com o total do dia);
     - saldo inicial e final do período.

     A direção vem do título do grupo, conferida pelo total do dia e pelo saldo. Esperado: todos os lançamentos lidos, saldo fecha, status "leitura suficiente". Há também uma variante em que o total do dia não bate, que tem de sair "ambígua" ou "parcial" com aviso, nunca "suficiente".
   - **Hipótese do Nubank (Q12):** se a direção pelo título do grupo não se sustentar em até 3 tentativas com hipóteses diferentes, registre as tentativas no retorno e entregue o resto.
   - `npm test`, `npm run lint` e `npm run build` verdes.
3. **F3 · Integridade do aceite (pacote; só se couber)** · Elrond, instância nova · **alto impacto** · escreva só: `S/sc_ciclo.py` (exceto o trecho de métricas da F1; faça a F3 depois da F1), `S/sc_conferir.py`, `S/sc_status.py`, `S/sc_registro.py`, `S/sc_rodada.py`, `S/sc.py` (só `revisar`), `T/test_aceite_nao_forjavel.py` (novo), `T/adversarial/` · aceite: os itens da **B15** e da **B17b** do backlog. As sondas DG-02 que estão em `expectedFailure` por causa da B15 passam a verdes, e a sonda do achado E3 também (`conferir` recusa atestado avulso e atestado de `--area` parcial). Se não couber, para e devolve o que passou no portão.

## Portão
- Por fatia: `sc.py entregar --etapa fechamento-nuvem --base <commit anterior> --fatia <N> --pasta-projeto <worktree> --pasta-sociedade <worktree>/sociedade`, num checkout limpo.
- No fim: o mesmo, sem `--fatia`, com `--base dc35a59`, cobrindo as áreas tocadas.

## Paradas
- Mudança de escopo, de contrato ou instalação fora do projeto: volta ao Círdan e a Odival.
- Teto de 1.500 linhas de produto, contadas por script (Q168). Se a etapa passar, a fatia de menor prioridade para onde estiver: vale só o que passou no portão, e o resto fica pendente.
- Nada em `.claude/agents/`, `sociedade/` nem `docs/`. Dado só sintético.
- Até 3 hipóteses por bloqueio (Q12). Push só de `etapa/fechamento-nuvem`. O PR é aberto pelo Círdan.

## Entregas verificáveis
```entregas
E1 | commit_existe | etapa/fechamento-nuvem
E2 | arquivos_em | dc35a59..etapa/fechamento-nuvem | sociedade-do-codigo/ | src/ | tests/
E3 | atestado_aprovado | sociedade/pareceres/atestado-fechamento-nuvem.json | etapa/fechamento-nuvem
E4 | arquivo_existe | sociedade-do-codigo/tests/test_sessao_consumo.py
E5 | arquivo_existe | src/leitura/historico.ts
E6 | delegacoes | claude | 8c54e58c-9f4a-56c4-a2da-c8f92be280dc | 4
E7 | conversa_nova | claude | a211ac53808a26971
E8 | push_feito | etapa/fechamento-nuvem
E9 | parecer_valido | sociedade/pareceres/parecer-fechamento-nuvem.md
```

## Ajustes da aprovação (Odival, 03/10/2026)
1. A F3 fica com o Elrond, numa instância nova, e não com o Aragorn: B15 e B17b são scripts do método, e o Aragorn é especialista em fontes externas. Cada fatia vai para o especialista do tipo dela.
2. O consumo por sessão é separado por `--desde` (a sessão 3 começou às 19:55 UTC); o da sessão 1 fica "n/d".
3. Dois commits de governança: um antes da parada 2 e um depois da decisão.
4. O PR é aberto com base na `main`; Odival integra o PR #2 antes da parada 2.

## Retorno
Até 2 KB no chat; o detalhe vai para `sociedade/subordens/fechamento-nuvem-gandalf-estado.md`.
