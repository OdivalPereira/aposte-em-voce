# Leitura de extratos (`src/leitura/`)

Núcleo genérico da seção 5 de `docs/onda-1.md`. Não há parser por banco. Tudo roda no aparelho.

## Função pública (para a F3 e para as telas)

```ts
import { lerExtrato, consolidar, diagnosticar, analisarPaginas, agruparHistoricos, assinaturaDoLayout } from '../src/leitura';

lerExtrato(bytes: Uint8Array, senha?: string, opcoes?: { onProgresso?(feito, total): void }): Promise<ResultadoArquivo>
consolidar(arquivos: { nome: string; resultado: ResultadoArquivo }[]): Consolidado   // seção 5.3
diagnosticar(resultados: ResultadoArquivo[]): DiagnosticoArquivo[]                    // T99, só contagens
analisarPaginas(paginas: PaginaTexto[], hash: string): ResultadoArquivo               // pipeline puro, sem PDF (usado nos testes de unidade)
agruparHistoricos(arquivos: ArquivoLido[]): Historicos                                // histórico contínuo por conta (ver abaixo)
assinaturaDoLayout(estrutura: EstruturaLayout | null): string                         // T99: texto copiável, só estrutura
```

- `lerExtrato` roda em Node (Vitest) e no navegador (dentro do worker `worker.ts`). Nunca lança por causa do conteúdo: arquivo com senha, corrompido, imagem, fatura, grande ou longo demais voltam como `status: 'nao-suportado'` com `motivo`.
- O PDF.js (`pdfjs-dist/legacy`) só é carregado por `extrair.ts`, isto é, depois que a pessoa escolhe um PDF. O código do worker do PDF.js vai embutido no nosso worker; nada de CDN.
- Senha: `lerExtrato(bytes)` sobre um PDF cifrado devolve `motivo: 'senha-necessaria'`; com senha errada, `'senha-incorreta'`; com a certa, lê normalmente.

## Formato do resultado por arquivo (JSON puro, `versao: 1`)

```jsonc
{
  "versao": 1,
  "hash": "<sha-256 hex dos bytes do arquivo>",
  "status": "suficiente" | "parcial" | "ambigua" | "nao-suportado",
  "motivo": null | "imagem" | "corrompido" | "fatura-cartao" | "muito-grande" | "muitas-paginas"
          | "senha-necessaria" | "senha-incorreta" | "sem-lancamentos"
          | "direcao-incerta" | "colunas-incertas" | "saldo-nao-fecha" | "linhas-nao-lidas"
          | "total-do-dia-diverge",
  "mensagem": "texto para a pessoa",
  "bancoProvavel": null | "Nubank" | "Mercado Pago" | ...,   // etiqueta por palavra do texto; sem a palavra, null
  "contaFinal": null | "final 4821",   // identificador estrutural: no máximo os 4 últimos dígitos de um número de conta do documento; nunca nome nem número completo
  "estrutura": null | {              // só estrutura do layout (T99); null quando a leitura nem chegou à tabela
    "colunas": [{ "rotulo": "Data", "de": 0, "ate": 1 }],   // da esquerda para a direita; posições em décimos da largura (0 a 10); rótulo só do vocabulário fixo, senão o nome do papel
    "formatosData": ["99/99/9999"],        // dígito vira 9 e letra vira A ("99 AAA 9999")
    "formatosValor": ["-9,99", "9.999,99"], // o primeiro grupo de dígitos vira um só 9
    "grupos": ["Total de entradas", "Total de saídas"]
  },
  "periodo": null | { "inicio": "2026-09-02", "fim": "2026-09-15" },  // menor e maior data dos lançamentos lidos
  "paginas": 1,
  "linhasCandidatas": 4,
  "lancamentos": [
    { "data": "2026-09-02", "hora": null | "14:35", "valorCentavos": 5000, "direcao": "entrada" | "saida",
      "descricao": "PIX ENVIADO PARA LOJA FICTICIA LTDA", "pagina": 1, "saldoCentavos": 95000 | null }
  ],
  "conferencia": {
    "situacao": "fecha" | "nao-fecha" | "indisponivel",
    "saldoInicialCentavos": 100000 | null, "saldoFinalCentavos": 103990 | null,
    "entradasCentavos": 20000, "saidasCentavos": 16010,
    "diferencaCentavos": 0 | null,      // saldoFinal − (saldoInicial + entradas − saídas); null se não há os dois saldos explícitos
    "progressao": null | { "verificadas": 3, "divergentes": 0, "ordem": "documento" | "inversa" }
  }
}
```

Convenções: valores em centavos inteiros e positivos (a direção está em `direcao`); `saldoCentavos` pode ser negativo; datas ISO; `lancamentos` na ordem do documento; `pagina` começa em 1.

### O que o JSON esperado da F3 deve comparar

**Estáveis (comparar):** `contaFinal`, `estrutura`, `status`, `motivo`, `periodo`, `paginas`, `linhasCandidatas`, cada lançamento (`data`, `hora`, `valorCentavos`, `direcao`, `descricao`, `pagina`, `saldoCentavos`), `conferencia` inteira e `bancoProvavel`.

**Não comparar:**
- `mensagem` (texto para a pessoa, pode mudar de redação);
- `hash`, a menos que os bytes do PDF sejam fixos. A pdf-lib grava data de criação e identificador: para um PDF reprodutível, use `PDFDocument.create({ updateMetadata: false })` e fixe `setCreationDate`/`setModificationDate`/`setProducer`/`setCreator`. O hash só importa para o teste de "mesmo arquivo enviado duas vezes".

Não há campo de tempo no resultado.

## Como o pipeline lê (para quem gera PDFs de teste)

1. Itens de texto com posição são agrupados em linhas (tolerância de 3 pt em y) e itens próximos viram células (espaço menor que 2 larguras de caractere).
2. Cabeçalho = linha com pelo menos duas colunas reconhecidas, uma delas monetária (`Valor`, `Crédito`/`Entradas`, `Débito`/`Saídas`) e outra de `Data`, `Descrição`/`Histórico`/`Lançamento` ou `Saldo`. Também reconhece `D/C` como coluna de sinal. Cabeçalhos repetidos por página são descartados; as colunas valem até o próximo cabeçalho. Sem nenhum cabeçalho, lê pelo conteúdo da linha (data, valor, saldo).
3. Cada célula vai para a coluna mais próxima (borda esquerda, direita ou centro; serve a texto à esquerda ou à direita).
4. Linha candidata = linha com data ou com valor. Linha só com texto, logo abaixo (até 1,5 vez o passo normal de linha), continua a descrição anterior. Linha só com data é título de grupo e vale para as linhas seguintes sem data. `SALDO ANTERIOR/INICIAL` e `SALDO FINAL/ATUAL` fornecem os saldos explícitos; `SALDO DO DIA`, `Total ...` e rodapés (`Página x de y`, `Emitido em ...`) são descartados.
5. Direção: coluna de crédito/débito, depois coluna `D/C`, depois sinal do valor (`-`, parênteses, sufixo `D`; `+`, sufixo `C`). Valor sem marca só vale se o documento marca um dos lados (todo valor sem marca é `entrada` quando as saídas levam `-` ou `D`). Sem nenhuma pista, a linha não vira lançamento e o status é `ambigua` (`direcao-incerta`). O saldo nunca decide a direção.
6. Ano de `dd/mm` e de `12 SET`: o período do documento (texto fora da tabela: `dd/mm/aaaa a dd/mm/aaaa`, ou as datas com ano que aparecem fora da tabela). Fora do período ou sem período, a linha não é lida (nunca se inventa ano).
7. Colunas extras só entram na descrição se tiverem letras.
8. **Título de grupo** (layout "agrupado por dia", genérico, sem regra por banco): uma linha cuja descrição é exatamente `Total de entradas` ou `Total de saídas` (também `créditos`/`débitos`) define a direção das linhas abaixo, sem sinal, até o próximo título, a próxima data de dia, saldo ou cabeçalho. O valor dessa linha é o **total do dia**: se há linhas no grupo e a soma lida (em centavos) não é igual ao total declarado, o arquivo sai `ambigua` com `motivo: "total-do-dia-diverge"` e nenhum lançamento é alterado. A direção do título vem depois da coluna, da coluna D/C e do sinal do valor, e antes da inferência do documento; o saldo do período (5.2) segue conferindo o conjunto. Grupo sem linhas (resumo no fim do extrato) não é conferido.

## Histórico contínuo (`historico.ts`)

`agruparHistoricos(arquivos)` devolve `{ historicos, repetidos, semHistorico }`. Função pura; nenhum lançamento é alterado.

- **Quais arquivos entram:** os que não são `nao-suportado` e têm `periodo`. O mesmo hash vai para `repetidos` (o primeiro fica); os demais para `semHistorico`.
- **Conta:** banco provável + `contaFinal`. Bancos diferentes nunca se juntam; dentro do banco, `contaFinal` diferente separa. Arquivos sem `contaFinal` entram juntos num histórico só, com o aviso `sem-identificador` (se há uma única conta identificada no banco, entram nela, com o mesmo aviso). Nome da pessoa e número completo da conta nunca são lidos nem guardados.
- **Cada `Historico`:** `arquivos` em ordem de período (início, fim, nome); `periodo` total (menor início, maior fim); `mesesCobertos` e `mesesFaltando` (`aaaa-mm`; faltando = mês civil entre o primeiro e o último coberto sem arquivo); `avisos`; `consolidado` (a mesma `consolidar` da 5.3, com a duplicidade entre arquivos sobrepostos e a regra do mesmo hash).
- **Encadeamento:** entre arquivos de meses consecutivos, `saldoFinalCentavos` do mês N tem de ser igual a `saldoInicialCentavos` do seguinte, em centavos e sem tolerância; senão, aviso `encadeamento` com o mês (`mm/aaaa`) e mais nada. Se um dos saldos é indisponível, aviso `encadeamento-nao-conferido` (nunca se inventa saldo). Arquivos sobrepostos ou com mês faltando entre eles não se encadeiam.

## Assinatura do layout (T99, `layout.ts`)

`assinaturaDoLayout(resultado.estrutura)` devolve texto com cabeçalhos (só do vocabulário fixo: `Data`, `Histórico`, `Valor`, `Crédito`, `Saldo`...; qualquer outro rótulo vira o nome do papel), posição das colunas em décimos da largura (do conteúdo; sem cabeçalho, inferida das células), formato de data e de valor com todo dígito trocado por `9` e título de grupo só por rótulo. Nunca valor, nome, descrição, banco, conta nem nome de arquivo. A tela copia com `navigator.clipboard.writeText`; falha vira mensagem simples.

Status (5.5): `suficiente` = 95% ou mais das candidatas viraram lançamentos e o saldo fecha ou está indisponível; `parcial` = lacunas ou saldo que não fecha; `ambigua` = direção ou colunas incertas; `nao-suportado` = casos da 5.4 (imagem, corrompido, fatura, tamanho, senha pendente) ou nenhum lançamento reconhecido.

## Ajuda para testes

- `tests/unit/auxiliar/montar.ts`: monta texto posicionado (tabelas) para a unidade.
- `tests/unit/auxiliar/pdf-sintetico.ts`: PDF com texto nas posições dadas (pdf-lib).
- `tests/unit/auxiliar/pdf-com-senha.ts`: PDF com senha (AES-256, revisão 5), que a pdf-lib não sabe gerar. Serve ao gerador da F3 para o caso "PDF com senha".
