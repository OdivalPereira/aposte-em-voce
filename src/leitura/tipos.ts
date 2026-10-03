// Tipos do pipeline de leitura. Tudo aqui é serializável em JSON (a F3 grava o resultado como "esperado").
// Valores sempre em centavos inteiros; datas sempre ISO (aaaa-mm-dd). Ver LEIAME.md.

/** Item de texto do PDF, em coordenadas do PDF (y cresce para cima). */
export interface ItemTexto {
  texto: string;
  x: number;
  y: number;
  largura: number;
  pagina: number;
}

export interface PaginaTexto {
  numero: number;
  itens: ItemTexto[];
}

export type Direcao = 'entrada' | 'saida';

export type Status = 'suficiente' | 'parcial' | 'ambigua' | 'nao-suportado';

export const ROTULO_STATUS: Record<Status, string> = {
  suficiente: 'Leitura suficiente',
  parcial: 'Parcial',
  ambigua: 'Ambígua',
  'nao-suportado': 'Não suportado',
};

/** Motivo de um status que não seja "suficiente"; `null` quando não há motivo especial. */
export type Motivo =
  | 'imagem'
  | 'corrompido'
  | 'fatura-cartao'
  | 'muito-grande'
  | 'muitas-paginas'
  | 'senha-necessaria'
  | 'senha-incorreta'
  | 'sem-lancamentos'
  | 'direcao-incerta'
  | 'colunas-incertas'
  | 'saldo-nao-fecha'
  | 'linhas-nao-lidas'
  | 'total-do-dia-diverge';

export interface Lancamento {
  /** aaaa-mm-dd */
  data: string;
  /** hh:mm, só quando o documento traz horário */
  hora: string | null;
  /** valor absoluto, em centavos inteiros */
  valorCentavos: number;
  direcao: Direcao;
  /** descrição como no extrato (descrição quebrada já juntada, espaços colapsados) */
  descricao: string;
  /** página (1 a N) onde a linha começa */
  pagina: number;
  /** saldo informado na própria linha, em centavos (pode ser negativo); `null` se a linha não traz */
  saldoCentavos: number | null;
}

export type SituacaoSaldo = 'fecha' | 'nao-fecha' | 'indisponivel';

export interface ConferenciaSaldo {
  situacao: SituacaoSaldo;
  /** "saldo anterior" explícito do documento */
  saldoInicialCentavos: number | null;
  /** "saldo final" explícito do documento */
  saldoFinalCentavos: number | null;
  entradasCentavos: number;
  saidasCentavos: number;
  /** saldoFinal − (saldoInicial + entradas − saídas); `null` se a equação não pôde ser montada */
  diferencaCentavos: number | null;
  /** progressão linha a linha; `null` se nenhuma linha trouxe saldo */
  progressao: { verificadas: number; divergentes: number; ordem: 'documento' | 'inversa' } | null;
}

export interface Periodo {
  inicio: string;
  fim: string;
}

/** Estrutura do layout (T99): sem valores, nomes nem descrições. Posições em décimos da largura (0 a 10). */
export interface EstruturaLayout {
  /** da esquerda para a direita; rótulo do documento só se for do vocabulário fixo (ver `layout.ts`) */
  colunas: { rotulo: string; de: number; ate: number }[];
  /** formatos com dígito trocado por 9 e letra por A (`99/99/9999`, `99 AAA 9999`) */
  formatosData: string[];
  /** formatos com o primeiro grupo de dígitos num só 9 (`9,99`, `9.999,99`, `-9,99`) */
  formatosValor: string[];
  /** títulos de grupo que definem a direção ("Total de entradas", "Total de saídas") */
  grupos: string[];
}

export interface ResultadoArquivo {
  versao: 1;
  /** SHA-256 (hex) dos bytes do arquivo */
  hash: string;
  status: Status;
  motivo: Motivo | null;
  /** texto simples para a pessoa (explicação do status) */
  mensagem: string;
  /** palavra-chave encontrada no texto do documento; `null` quando não há (não há parser por banco) */
  bancoProvavel: string | null;
  /** identificador estrutural da conta: no máximo os 4 últimos dígitos ("final 4821"); `null` se o documento não traz. Nunca nome nem número completo */
  contaFinal: string | null;
  /** estrutura do layout para a assinatura (T99); `null` quando a leitura nem chegou à tabela */
  estrutura: EstruturaLayout | null;
  /** menor e maior data dos lançamentos lidos; `null` sem lançamentos */
  periodo: Periodo | null;
  paginas: number;
  linhasCandidatas: number;
  lancamentos: Lancamento[];
  conferencia: ConferenciaSaldo;
}

export interface ArquivoLido {
  /** nome mostrado à pessoa; só serve de origem, nunca vai ao diagnóstico */
  nome: string;
  resultado: ResultadoArquivo;
}

export interface Origem {
  arquivo: string;
  pagina: number;
}

export interface LancamentoConsolidado extends Lancamento {
  origens: Origem[];
  /** a mesma operação aparece em dois (ou mais) extratos de períodos sobrepostos */
  apareceEmDoisExtratos: boolean;
}

export interface Consolidado {
  lancamentos: LancamentoConsolidado[];
  entradasCentavos: number;
  saidasCentavos: number;
  /** arquivos ignorados por serem o mesmo arquivo reenviado (mesmo hash) */
  repetidos: string[];
  /** arquivos que não contribuíram (status "nao-suportado") */
  semLancamentos: string[];
}

export class ErroLeitura extends Error {
  constructor(
    public readonly motivo: Motivo,
    mensagem?: string,
  ) {
    super(mensagem ?? motivo);
    this.name = 'ErroLeitura';
  }
}

export const LIMITE_BYTES = 30 * 1024 * 1024;
export const LIMITE_PAGINAS = 200;
