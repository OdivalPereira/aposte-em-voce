# Retorno F2 (Elrond) · fechamento-nuvem · base dc35a59

Veredito: **pronto**. Nada comitado (sem add, commit, stash nem checkout). Só dados sintéticos.

## Comandos e contagens (raiz do worktree)
- `npx vitest run tests/unit`: 141 passaram (antes 110; +31), 8 arquivos.
- `npm run lint` (tsc + eslint): limpo.
- `npm run build`: ok.
- `npx playwright test`: 13 passaram (antes 9; +4), perfil Pixel 7.
- `npm test`: 141 unidade + 13 e2e, verde.
- Linhas de produto em `src/`: `git diff --numstat -- src/` = 183 acrescentadas e 15 removidas (inclui 27 de LEIAME) + 303 em arquivos novos (`historico.ts` 157, `layout.ts` 146) = cerca de 485. Abaixo do alvo de 700.

## Arquivos
Novos: `src/leitura/historico.ts`, `src/leitura/layout.ts`, `tests/unit/historico.test.ts` (16), `tests/unit/assinatura.test.ts` (10), `tests/unit/agrupado-por-dia.test.ts` (5), `tests/unit/auxiliar/extrato-mes.ts`, `tests/e2e/historico.spec.ts` (4).
Alterados: `src/leitura/{tipos,reconstruir,conferir,index}.ts`, `src/leitura/LEIAME.md`, `src/telas/{Extratos,ResultadoLeitura,Diagnostico}.tsx`, `src/ui/formatar.ts`, `tests/unit/auxiliar/montar.ts` (+`paginaAgrupada`), `tests/unit/consolidar.test.ts` (campos novos no literal), `tests/e2e/auxiliar.ts` (+`extratoDoMes`).
`src/app.tsx` **não mudou**: o estado já acumula itens (`ItemArquivo[]`, cada um com `resultado`, progresso por arquivo e lista que só cresce); o histórico é calculado na tela de resultado a partir dele. `package.json`, `main.tsx`, worker e configs não foram tocados.

## Contrato novo de `ResultadoArquivo` (versao segue 1; ver LEIAME)
- `contaFinal: string | null`: "final 4821" (no máximo 4 últimos dígitos de um número de conta que o documento traz; sem máscara e com até 4 dígitos não vale). Nunca nome nem número completo.
- `estrutura: EstruturaLayout | null`: `{ colunas: [{rotulo, de, ate}] (décimos da largura), formatosData, formatosValor, grupos }`. `null` só nos casos 5.4 (imagem, fatura, corrompido...).
- `Motivo` novo: `total-do-dia-diverge` (status `ambigua`).
- **Para a F3:** os campos novos entram na lista de "estáveis" do JSON esperado (`contaFinal`, `estrutura`); o `hash` e a `mensagem` seguem fora da comparação.

## Histórico (`agruparHistoricos`)
`{ historicos, repetidos, semHistorico }`. Por histórico: banco provável, `contaFinal`, `arquivos` em ordem de período, `periodo` total, `mesesCobertos`, `mesesFaltando` (aaaa-mm), `avisos` (`encadeamento`, `encadeamento-nao-conferido`, `sem-identificador`; cada um com o mês `mm/aaaa` e mais nada) e `consolidado` (a `consolidar` da 5.3, intacta). Bancos diferentes não se juntam; sem identificador, junta com aviso. Encadeamento só entre meses consecutivos, em centavos e sem tolerância; arquivos sobrepostos ou com mês faltando no meio não se encadeiam. Tela: seção "Histórico: banco, conta final NNNN" com período total, nº de arquivos, meses cobertos, meses faltando e avisos (elemento `section`, os cartões `article` por arquivo seguem iguais). "Ao todo" soma os consolidados por histórico (contas diferentes não se fundem).

## Assinatura (T99)
Botão "Copiar assinatura do layout" por arquivo no Diagnóstico; falha de cópia mostra "Não foi possível copiar..." (sem exceção solta, sem vazar o erro). Texto: colunas (só vocabulário fixo; rótulo fora dele vira o nome do papel), posições em décimos da largura, formato de data e de valor com dígito vira 9 e letra vira A, títulos de grupo. Testes: nenhum dígito fora de `9` (exceto a linha de posições), nenhuma descrição, valor, data, nome, conta, banco nem "R$"; deslocar o layout dá a mesma assinatura.

## Layout "agrupado por dia" (genérico, sem `if (banco)`)
Regra em `reconstruir.ts`: linha cuja descrição é exatamente "Total de entradas/saídas" (ou créditos/débitos) abre um grupo (direção do título, total declarado); fecha em novo título, data de dia, saldo ou cabeçalho. Direção do título vale depois de coluna, D/C e sinal, e antes da inferência do documento. Total declarado diferente da soma lida (centavos, grupo com linhas) → `ambigua` / `total-do-dia-diverge`, nada alterado.
- Base sintética (6 lançamentos em 3 dias, saldo 1.000,00 a 1.165,40): todos lidos, saldo fecha, **suficiente**.
- Variante total de entradas do dia 09 = 130,50 (lidos 125,50): **ambígua** com aviso; também com total de saídas errado. Título trocado num dia (total bate, direção errada): **parcial** (saldo não fecha), sem "consertar" nada.
- **Q12 (hipótese do Nubank):** não esgotou: a 1ª tentativa sustentou-se (direção pelo título em vigor, na ordem de leitura, que é o título mais próximo acima da linha). Hipóteses 2 (blocos por data/total como separador) e 3 (sinal do saldo progressivo) não foram necessárias nem implementadas.

## Pendências e riscos
- Só layout sintético; o formato real do Nubank (sinal "+"/"-" em célula separada do total, "Saldo do dia", valores com "R$") não foi visto. Se o total vier em duas células, o total declarado fica `null` (o grupo ainda dá direção, só não é conferido pelo total).
- Resumo "Total de entradas/saídas" no meio de um extrato em tabela sem cabeçalho e com valores sem sinal agora dá direção às linhas seguintes (antes: direção incerta). A conferência por total do dia e por saldo cobre; sem teste com PDF real.
- `contaFinal` só reconhece "Conta/C/C/CTA" seguido de número; outros rótulos (ex.: "Ag/Conta") caem em "sem identificador" (junta com aviso). Sem agência na identificação, por escolha.
- Os testes e2e de dois PDFs rodam em ~1 s cada; o `ResultadoLeitura` recalcula o histórico a cada render (barato, 60 linhas amostradas por arquivo para a estrutura).

## Atritos com o método (para `sociedade/nuvem/atritos.md`)
1. A subordem diz "já há `node_modules`", mas o worktree não tinha; `npx vitest` falhou com `ERR_MODULE_NOT_FOUND`. Correção: `npm ci --silent` (a subordem já previa o fallback; vale marcar "se faltar" como passo 0).
2. Com `FORCE_COLOR` no ambiente, `NO_COLOR=1` é ignorado e o erro de startup do vitest despejou ~3 KB de ANSI no terminal. Sugestão: `FORCE_COLOR=0 NO_COLOR=1` nos comandos dirigidos, ou `| tail -15` já antes do primeiro teste.
3. A regra "escreve só `src/telas/` sem redesenho" convive bem com o aceite, mas "app.tsx passa a acumular ArquivoLido[]" na subordem não se aplicava (o estado já acumulava); a subordem poderia checar isso antes de pedir.
