// Extrato sintético de um mês, no estilo tabela (Data | Descrição | Valor | Saldo), para os testes do histórico.
import { analisarPaginas } from '../../../src/leitura';
import type { ArquivoLido, PaginaTexto } from '../../../src/leitura/tipos';
import { COLUNAS_PADRAO, pagina } from './montar';

/** 123456 -> "1.234,56"; -5000 -> "-50,00" */
export function brl(centavos: number): string {
  const abs = Math.abs(centavos);
  const inteiro = String(Math.floor(abs / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${centavos < 0 ? '-' : ''}${inteiro},${String(abs % 100).padStart(2, '0')}`;
}

export interface PedidoMes {
  ano: number;
  mes: number;
  /** saldo anterior, em centavos */
  inicial: number;
  /** [dia, descrição, valor assinado em centavos] */
  movimentos: [number, string, number][];
  /** saldo final declarado; padrão: o que a conta dá. `null` = sem linha de saldo final */
  final?: number | null;
  /** linha de conta no cabeçalho do documento; padrão "Conta: ***4821"; `null` = o documento não traz conta */
  conta?: string | null;
  banco?: string;
  /** linhas extras do cabeçalho do documento (por exemplo, o nome do titular, que nunca pode vazar) */
  extras?: string[];
  /** sem linhas de saldo anterior e final, nem saldo por lançamento */
  semSaldo?: boolean;
}

const dd = (n: number) => String(n).padStart(2, '0');

export function paginasDoMes(p: PedidoMes): PaginaTexto[] {
  const ultimo = new Date(p.ano, p.mes, 0).getDate();
  let saldo = p.inicial;
  const linhas: string[][] = [];
  if (!p.semSaldo) linhas.push(['', 'SALDO ANTERIOR', '', brl(p.inicial)]);
  for (const [dia, desc, valor] of p.movimentos) {
    saldo += valor;
    linhas.push([`${dd(dia)}/${dd(p.mes)}/${p.ano}`, desc, brl(valor), p.semSaldo ? '' : brl(saldo)]);
  }
  const final = p.final === undefined ? saldo : p.final;
  if (!p.semSaldo && final !== null) linhas.push(['', 'SALDO FINAL', '', brl(final)]);
  return [
    pagina({
      antes: [`${p.banco ?? 'Banco Ficticio'} - Extrato de conta`, ...(p.conta === null ? [] : [p.conta ?? 'Conta: ***4821']), ...(p.extras ?? []), `Período: 01/${dd(p.mes)}/${p.ano} a ${ultimo}/${dd(p.mes)}/${p.ano}`],
      colunas: COLUNAS_PADRAO,
      linhas,
      depois: ['Página 1 de 1'],
    }),
  ];
}

/** Resultado já lido (sem PDF) de um extrato mensal sintético; `hash` distingue arquivos. */
export function arquivoDoMes(nome: string, p: PedidoMes, hash = nome.padEnd(64, 'f').slice(0, 64)): ArquivoLido {
  return { nome, resultado: analisarPaginas(paginasDoMes(p), hash) };
}
