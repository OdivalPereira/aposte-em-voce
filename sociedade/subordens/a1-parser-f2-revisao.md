# Subordem a1-parser · revisão interna da F2 (pipeline `src/leitura/`)

Para: Galadriel (Claude Code em nuvem, subagente `galadriel`) · revisão interna de alto impacto (C17, Q10)
De: Gandalf · Etapa a1-parser · Fatia revisada: F2, pipeline de leitura (`src/leitura/`) · Base: `d86e90c` · Cabeça: `5ff94f7` (F2 em `7ea0695`, mais a correção do esperado do caso colunas-trocadas)
Worktree: `/root/.sociedade/trabalho/aposte-em-voce/a1-parser`. Só dados sintéticos. Nunca estime nem relate consumo.

## Objetivo
Revisar sem editar: o pipeline segue `docs/onda-1.md` (seções 5.1 a 5.5 e princípios 1, 2, 4, 6 e 7 da seção 2) e os testes provam o que dizem.

## Aceite da revisão
Parecer com achados (bloqueante, importante, menor), cada um com arquivo, linha e reprodução. Veredito: "pode ir ao portão" ou "volta ao Elrond". Procure especialmente:
- conferência de saldo em centavos inteiros, sem tolerância, sem ponto flutuante; nenhum lançamento, saldo ou horário alterado ou inventado para fechar a conta;
- direção pela coluna ou pelo sinal, saldo só como conferência; "D" e "C" tratados nos dois lados do valor;
- datas `dd/mm/aaaa`, `dd/mm`, `12 SET` com ano inferido do período (virada de ano!) e valores `1.234,56`, `-1.234,56`, `1.234,56 D`, `R$`; arredondamento e centavos de um dígito;
- duplicidade: mesma chave dentro do mesmo arquivo continua dupla; entre arquivos sobrepostos conta uma vez e marca "aparece em dois extratos"; mesmo hash não duplica; descrição normalizada (acento, caixa, espaços);
- status da 5.5 (95% das linhas candidatas e saldo) e casos da 5.4 (imagem, corrompido, fatura de cartão, 30 MB e 200 páginas) com as mensagens do texto; a jornada segue sem o arquivo;
- T99 e logs sem valores, nomes nem descrições; `console.log` e mensagens de erro não vazam conteúdo do extrato; senha só na memória;
- nada em `localStorage`, IndexedDB, cookies, `fetch`/XHR/`sendBeacon`/WebSocket para fora; `pdfjs-dist` e worker servidos do próprio site e carregados só ao escolher o PDF; CSP de `vercel.json` igual à da seção 12;
- o caso `colunas-trocadas` e os demais casos de unidade existem e testam o que dizem (nada de teste vazio, `skip`, `only`, tolerância escondida);
- se o retorno da F2 traz um caso contraditório devolvido, dizer se a contradição é real pela especificação (sem corrigir o esperado: isso é do Gandalf).

## Leia só (até 5 caminhos)
1. `git diff d86e90c..5ff94f7 --stat` e depois `src/leitura/` inteiro.
2. `tests/unit/`.
3. `docs/onda-1.md`, seções 5.1 a 5.5 e 2.
4. `vercel.json` e `tests/e2e/` (teste de rede).
5. `src/telas/` (T08, T09, T99) só para conferir o que é exibido.

## Escreva só
Nada no repositório. O parecer vai no retorno. Rascunhos só no diretório de rascunho da sessão.

## Teste dirigido
Reproduza cada achado com um teste ou comando curto (em cópia temporária fora do worktree): `npx vitest run tests/unit` e a sua sonda.

## Portão da fatia
Não se aplica (o portão da F2 é do Gandalf, depois das correções). O que você achar é corrigido dentro da própria fatia, por quem a fez (Elrond); não nasce fatia nova (ajuste 3).

## Retorno (até 2 KB)
Veredito; achados (classe, arquivo:linha, reprodução, correção sugerida em uma frase); o que fica para o Barbárvore ou o backlog; atritos com o método.
