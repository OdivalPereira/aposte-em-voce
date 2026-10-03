# Subordem fechamento-nuvem · revisão interna da F2 (pipeline) e da F3 (B15), numa revisão só

**Estado: pronta para despacho** (bases e cabeças preenchidas pela rodada 3 do Gandalf). F2 e F3 comitadas; atestados das fatias 1, 2 e 3 aprovados.

Para: Galadriel (subagente `galadriel`) · revisão interna de alto impacto (C17, Q10) · **sem editar**
De: Gandalf · Etapa fechamento-nuvem · Worktree: `/root/.sociedade/trabalho/aposte-em-voce/fechamento-nuvem`
Fatias revisadas: F2 (`793012a..e4dbadd`, `src/leitura/`, telas, testes) e F3 (`e4dbadd..758952a`, pacote). Só dados sintéticos. Nunca estime nem relate consumo.

## Objetivo
Revisar sem editar: (1) o histórico, o encadeamento, a assinatura e o layout "agrupado por dia" seguem `docs/onda-1.md` (5.1 a 5.5 e princípios 1, 2, 4, 6 e 7 da seção 2) e os testes provam o que dizem; (2) a F3 fecha a B15 e a B17b sem abrir brecha nova.

## Aceite da revisão
Parecer com achados (bloqueante, importante, menor), cada um com arquivo, linha e reprodução. Veredito por fatia: "pode ir ao portão" ou "volta ao Elrond". Procure especialmente:
- **F2.** Encadeamento em centavos inteiros e sem tolerância; nenhum lançamento, saldo ou horário alterado ou inventado para fechar a conta ou o encadeamento; saldo indisponível não vira "ok". A conta nunca é identificada por nome da pessoa nem por número completo (cheque o histórico, a tela, o diagnóstico, mensagens e `console`). Meses faltando corretos na virada de ano e em meses de 28 a 31 dias. Mesmo hash não duplica; duplicidade da 5.3 intacta entre arquivos do histórico (mesma chave no mesmo arquivo continua dupla). A assinatura do layout (T99) sem nenhum dígito real, sem valor, nome ou descrição: tente vazar por rótulo de coluna, título de grupo, mensagem de erro e formatos com texto ao redor. Layout "agrupado por dia": direção só pelo título do grupo, total do dia **de fato conferido**; a variante divergente nunca sai "suficiente"; nenhuma regra por nome de banco. Nada em `localStorage`/IndexedDB/cookies e nenhuma requisição nova para fora (o teste de rede segue só GET do mesmo domínio). Telas só com mudança funcional (sem redesenho). Testes sem `skip`, `only`, tolerância escondida nem esperado vindo do código sob teste.
- **F3** (suíte 733 OK, 1 pulado, 5 `expectedFailure`, todas do dg03; as sondas DG-02 e a do E3 devem estar sem `expectedFailure`; ampliações já aprovadas pelo Círdan: 4 testes legados e 3 fixtures; `.github/` intocado, confira). `decidir` e `conferir` recusam atestado avulso, de `--area` parcial, escrito à mão ou alterado na cauda; o fornecedor do perfil não é sobreposto por `--implementador`; `encerrar` exige o evento `decisao`; decisor nunca é nome de papel nem de modelo do perfil; nenhum argumento legado declarativo sobra por outro caminho (`grep`); as sondas DG-02 e a do E3 estão verdes **sem** `expectedFailure` e sem asserção enfraquecida (compare com o diff); os quatro testes antigos ajustados continuam provando o mesmo.
- Divergências de texto entre o que a F1 escreveu (economia, 2 KB) e o comportamento: só aponte.

## Leia só (até 5 caminhos; por trecho)
1. `git diff 793012a..e4dbadd --stat` e depois, da F2: `src/leitura/historico.ts` e as funções novas ou alteradas em `src/leitura/` (`git diff -U0`).
2. `tests/unit/` (só os casos novos) e `tests/e2e/` (só os novos).
3. `docs/onda-1.md`: seções 5.2, 5.3, 5.5 e 2 (por trecho).
4. Da F3: `git diff e4dbadd..758952a -- sociedade-do-codigo/plugins` e `T/test_aceite_nao_forjavel.py`; backlog só nas linhas B15 e B17b.
5. `src/telas/` só para conferir o que é exibido (T09 e T99).

## Escreva só
Nada no repositório. O parecer vai no arquivo de retorno. Rascunhos e sondas só no diretório de rascunho da sessão (scratchpad), em cópia fora do worktree.

## Teste dirigido (saída curta)
Reproduza cada achado com um teste ou comando curto em cópia temporária: `npx vitest run tests/unit --reporter=dot 2>&1 | tail -10` e, para a F3, `python3 -B -m unittest discover -s tests 2>&1 | tail -8` (de `sociedade-do-codigo`) mais a sonda do achado.

## Portão da fatia
Não se aplica (os portões são do Gandalf). O que você achar volta a quem fez a fatia, dentro da própria fatia; não nasce fatia nova.

## Economia e retorno
Leia só o listado, por trecho; saídas curtas; conversa curta (estado em `sociedade/subordens/fechamento-nuvem-revisao-estado.md` se crescer); não comite.
**Retorno até 2 KB no chat**: veredito por fatia, achados (classe, arquivo:linha, reprodução, correção em uma frase), o que fica para o Barbárvore reduzido ou para o backlog, atritos. O parecer completo vai para `sociedade/subordens/fechamento-nuvem-revisao-retorno.md`.
