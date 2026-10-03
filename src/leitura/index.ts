// Função pública da leitura (ver LEIAME.md): bytes do PDF (e senha opcional) → resultado por arquivo.
import { conferirSaldo, decidirStatus, MENSAGEM } from './conferir';
import { extrairTexto, motivoDoErro } from './extrair';
import { semAcento } from './normalizar';
import { reconstruir } from './reconstruir';
import { ErroLeitura, LIMITE_BYTES, type ConferenciaSaldo, type Motivo, type PaginaTexto, type ResultadoArquivo } from './tipos';

export type { ArquivoLido, Consolidado, Lancamento, ResultadoArquivo } from './tipos';
export { consolidar } from './consolidar';
export { diagnosticar } from './diagnostico';

const SEM_CONFERENCIA: ConferenciaSaldo = {
  situacao: 'indisponivel',
  saldoInicialCentavos: null,
  saldoFinalCentavos: null,
  entradasCentavos: 0,
  saidasCentavos: 0,
  diferencaCentavos: null,
  progressao: null,
};

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const h = await globalThis.crypto.subtle.digest('SHA-256', bytes.slice());
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function naoSuportado(hash: string, motivo: Motivo, paginas: number): ResultadoArquivo {
  return {
    versao: 1,
    hash,
    status: 'nao-suportado',
    motivo,
    mensagem: MENSAGEM[motivo],
    bancoProvavel: null,
    periodo: null,
    paginas,
    linhasCandidatas: 0,
    lancamentos: [],
    conferencia: SEM_CONFERENCIA,
  };
}

const BANCOS: [string, RegExp][] = [
  ['Caixa Tem', /\bcaixa tem\b/],
  ['Mercado Pago', /\bmercado pago\b/],
  ['PicPay', /\bpicpay\b/],
  ['Nubank', /\bnubank\b|\bnu pagamentos\b/],
  ['Inter', /\bbanco inter\b|\binter\b/],
  ['C6 Bank', /\bc6 bank\b/],
  ['Itaú', /\bitau\b/],
  ['Bradesco', /\bbradesco\b/],
  ['Santander', /\bsantander\b/],
  ['Banco do Brasil', /\bbanco do brasil\b/],
  ['Caixa', /\bcaixa\b/],
];

/** Só uma etiqueta informativa a partir de palavras do texto; não há parser por banco. */
export function bancoProvavel(textoFora: string): string | null {
  const t = semAcento(textoFora).toLowerCase();
  return BANCOS.find(([, re]) => re.test(t))?.[0] ?? null;
}

const MARCAS_FATURA = [/total da fatura/, /pagamento minimo/, /limite (de credito|total|disponivel)/, /fatura (fechada|atual|do cartao|de cartao)/, /vencimento da fatura/, /melhor dia (de|para) compra/];

/** Fatura de cartão: ao menos duas marcas típicas e nenhuma linha de saldo de conta. */
export function pareceFaturaDeCartao(texto: string): boolean {
  const t = semAcento(texto).toLowerCase();
  if (/\bsaldo (anterior|inicial|final)\b/.test(t)) return false;
  return MARCAS_FATURA.filter((re) => re.test(t)).length >= 2;
}

const MINIMO_DE_TEXTO = 40;

/** Pipeline puro sobre texto posicionado (passos 3 a 8). É o que a unidade testa sem PDF. */
export function analisarPaginas(paginas: PaginaTexto[], hash: string, totalPaginas = paginas.length): ResultadoArquivo {
  const texto = paginas.flatMap((p) => p.itens.map((i) => i.texto)).join(' ');
  if (texto.replace(/\s+/g, '').length < MINIMO_DE_TEXTO) return naoSuportado(hash, 'imagem', totalPaginas);
  if (pareceFaturaDeCartao(texto)) return naoSuportado(hash, 'fatura-cartao', totalPaginas);

  const r = reconstruir(paginas);
  const conferencia = conferirSaldo(r.lancamentos, r.saldoInicialCentavos, r.saldoFinalCentavos);
  const { status, motivo } = decidirStatus({
    linhasCandidatas: r.linhasCandidatas,
    lancamentos: r.lancamentos.length,
    semDirecao: r.semDirecao,
    colunasIncertas: r.colunasIncertas,
    conferencia,
  });
  const datas = r.lancamentos.map((l) => l.data).sort();
  const mensagem = motivo ? MENSAGEM[motivo] : conferencia.situacao === 'indisponivel' ? 'Lemos este extrato. O arquivo não traz saldo, então não foi possível conferi-lo.' : MENSAGEM.ok;
  return {
    versao: 1,
    hash,
    status,
    motivo,
    mensagem,
    bancoProvavel: bancoProvavel(r.textoFora),
    periodo: datas.length > 0 ? { inicio: datas[0] as string, fim: datas[datas.length - 1] as string } : null,
    paginas: totalPaginas,
    linhasCandidatas: r.linhasCandidatas,
    lancamentos: r.lancamentos,
    conferencia,
  };
}

export interface OpcoesLeitura {
  /** chamado a cada página lida */
  onProgresso?: (feito: number, total: number) => void;
}

/**
 * Lê um extrato em PDF no próprio aparelho. Nunca lança por causa do conteúdo do arquivo: arquivo
 * ilegível, com senha, imagem, fatura ou grande demais voltam como `status: 'nao-suportado'` com `motivo`.
 */
export async function lerExtrato(bytes: Uint8Array, senha?: string, opcoes: OpcoesLeitura = {}): Promise<ResultadoArquivo> {
  const hash = await sha256Hex(bytes);
  if (bytes.length > LIMITE_BYTES) return naoSuportado(hash, 'muito-grande', 0);
  try {
    const pdf = await extrairTexto(bytes, senha, opcoes.onProgresso);
    return analisarPaginas(pdf.paginas, hash, pdf.totalPaginas);
  } catch (e) {
    return naoSuportado(hash, e instanceof ErroLeitura ? e.motivo : motivoDoErro(e), 0);
  }
}
