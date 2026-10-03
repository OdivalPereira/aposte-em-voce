# Subordem a1-parser · F2c (correção da F2, achados da revisão interna)

Para: Elrond (Claude Code em nuvem, subagente `elrond`) · correção dentro da própria fatia (ajuste 3 da aprovação)
De: Gandalf · Etapa a1-parser · Base da correção: `fce98d9` (ramo `etapa/a1-parser`; F2 em `7ea0695` e `5ff94f7`) · Worktree: `/root/.sociedade/trabalho/aposte-em-voce/a1-parser`
Só dados sintéticos. Nunca estime nem relate consumo. A F3 (Jules) trabalha em worktree próprio e não toca `src/`.

## Objetivo e aceite
Corrigir só os 4 achados da Galadriel. Cada correção com teste que falha antes e passa depois.
1. **IMPORTANTE, a jornada não pode travar se a leitura falhar (princípio 8).** `src/leitura/index.ts:116` (`sha256Hex` fora do try: sem `crypto.subtle`, por exemplo `npm run dev` por http na rede local, `lerExtrato` rejeita), `src/leitura/worker.ts:240` (sem try), `src/leitura/cliente.ts:205` (sem `onerror`/reject), `src/app.tsx:36-43` (falha de `arrayBuffer()` não tratada); o item fica em "lendo" para sempre e `src/telas/Extratos.tsx` não oferece "Seguir sem este arquivo" nesse estado ("Ver o resultado" fica desabilitado). Aceite: toda falha no worker, no cliente ou na leitura do arquivo termina o item como `nao-suportado` (motivo `corrompido` ou outro já existente, sem vazar conteúdo, nome nem valor); o item sempre pode ser pulado ("Seguir sem este arquivo") e a jornada continua sem ele; sem o `crypto.subtle`, a leitura ainda funciona ou falha com `nao-suportado`, nunca pendura. Teste de unidade (hash indisponível, worker/cliente com erro) e, se couber, e2e que prove que o item sai de "lendo" e pode ser pulado.
2. **IMPORTANTE, `src/leitura/reconstruir.ts:440`:** período "mm/aaaa" termina sempre no dia 30 (`28 + (mes === 2 ? 0 : 2)`); "referente a 01/2026" deixa `31/01` não lida e fev/2028 perde `29/02`. Aceite: função `diasNoMes(mes, ano)` (bissexto correto, inclusive 2100) usada no fim do período; teste com jan/2026 (dia 31), fev/2028 (dia 29), fev/2026 (dia 28) e abr (dia 30).
3. **MENOR, `src/leitura/consolidar.ts:10`:** `sobrepoe` é código morto (a chave já contém a data); mutação com `true` fixo passa nos 9 testes e `tests/unit/consolidar.test.ts:77` não discrimina. Aceite: remover o código morto (ou documentar por que existe e renomear), sem mudar o comportamento da 5.3, e o teste do :77 passa a discriminar (falha se a regra de sobreposição for trocada por `true`).
4. **MENOR, `tests/unit/pipeline.test.ts:121`:** o título diz "status é parcial", mas o `expect` é `nao-suportado`. Ajustar só o título.

## Fora desta subordem (não corrigir; vão ao backlog/Barbárvore da a2)
Prefixo colado "D 40,00"/"C 100,00"/"CR"/"DB"; valor sem marca como entrada quando só as saídas são marcadas; "50,00 D" em coluna Crédito; razão de 95% em float; erro interno aparecendo como "corrompido"; falta de teste de 30 MB e 200 páginas; `consolidar` ordenando só por data. Se um deles atrapalhar uma das correções acima, pare e devolva.

## Leia só (até 5 caminhos)
1. `src/leitura/index.ts`, `src/leitura/worker.ts` e `src/leitura/cliente.ts`.
2. `src/app.tsx` e `src/telas/Extratos.tsx`.
3. `src/leitura/reconstruir.ts` (em torno da linha 440) e `src/leitura/consolidar.ts`.
4. `tests/unit/consolidar.test.ts` e `tests/unit/pipeline.test.ts`.
5. `tests/e2e/leitura.spec.ts` e `src/leitura/LEIAME.md` (só se a correção mudar o contrato; se mudar, atualize o LEIAME).

## Escreva só
`src/leitura/index.ts`, `src/leitura/worker.ts`, `src/leitura/cliente.ts`, `src/leitura/reconstruir.ts`, `src/leitura/consolidar.ts`, `src/leitura/LEIAME.md` (só se o contrato mudar), `src/app.tsx`, `src/telas/Extratos.tsx`, e os testes `tests/unit/` e `tests/e2e/` que cobrem esses arquivos (novos ou existentes). Nada mais: não toque em `package.json`, `vercel.json`, `sociedade/`, `docs/`, `.claude/`, `sociedade-do-codigo/`, `scripts/` nem `tests/fixtures/` e `tests/leitura/` (F3). A função pública e o formato do JSON não mudam (a F3 depende deles); se precisar mudar, pare e devolva.

## Teste dirigido
`npx vitest run tests/unit`, `npm run lint`, `npm run build`, `npx playwright test` e `npm test`. Registre o comando e a contagem de cada um (nenhum teste apagado, pulado ou enfraquecido).

## Regras de trabalho
Sem `git commit`, `add`, `stash` nem `checkout` (o Gandalf comita). Até 3 hipóteses diferentes por bloqueio, cada uma registrada; depois pare e devolva (Q12). Mudança de escopo ou de contrato: pare e devolva.

## Portão da fatia (rodado pelo Gandalf)
`python3 sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc.py entregar --etapa a1-parser --base fce98d9 --fatia 2c --area app --pasta-projeto /root/.sociedade/trabalho/aposte-em-voce/a1-parser --pasta-sociedade /root/.sociedade/trabalho/aposte-em-voce/a1-parser/sociedade` (sem `--comando-teste`).

## Retorno (até 2 KB)
Arquivos alterados, o que mudou em cada achado (uma frase), comandos de teste e contagens, linhas de produto novas, hipóteses tentadas, pendências e atritos com o método.
