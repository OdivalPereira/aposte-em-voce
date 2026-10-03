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

/** SHA-256 em JS puro, só para quando o `crypto.subtle` não existe (por exemplo, http na rede local). */
function sha256Local(dados: Uint8Array): string {
  const K: number[] = [];
  const H = new Array<number>(8);
  for (let n = 2, achados = 0; achados < 64; n++) {
    let primo = true;
    for (let d = 2; d * d <= n; d++) if (n % d === 0) primo = false;
    if (!primo) continue;
    if (achados < 8) H[achados] = (Math.pow(n, 0.5) * 2 ** 32) | 0;
    K[achados++] = (Math.pow(n, 1 / 3) * 2 ** 32) | 0;
  }
  const comprimento = dados.length;
  const blocos = Math.ceil((comprimento + 9) / 64);
  const m = new Uint8Array(blocos * 64);
  m.set(dados);
  m[comprimento] = 0x80;
  const visao = new DataView(m.buffer);
  visao.setUint32(m.length - 8, Math.floor((comprimento * 8) / 2 ** 32));
  visao.setUint32(m.length - 4, (comprimento * 8) >>> 0);
  const w = new Array<number>(64);
  const rot = (x: number, n: number) => (x >>> n) | (x << (32 - n));
  for (let b = 0; b < blocos; b++) {
    for (let i = 0; i < 16; i++) w[i] = visao.getUint32(b * 64 + i * 4);
    for (let i = 16; i < 64; i++) {
      const w15 = w[i - 15] as number;
      const w2 = w[i - 2] as number;
      const s0 = rot(w15, 7) ^ rot(w15, 18) ^ (w15 >>> 3);
      const s1 = rot(w2, 17) ^ rot(w2, 19) ^ (w2 >>> 10);
      w[i] = ((w[i - 16] as number) + s0 + (w[i - 7] as number) + s1) | 0;
    }
    let [a, bb, c, d, e, f, g, h] = H as [number, number, number, number, number, number, number, number];
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rot(e, 6) ^ rot(e, 11) ^ rot(e, 25)) + ((e & f) ^ (~e & g)) + (K[i] as number) + (w[i] as number)) | 0;
      const t2 = ((rot(a, 2) ^ rot(a, 13) ^ rot(a, 22)) + ((a & bb) ^ (a & c) ^ (bb & c))) | 0;
      h = g;
      g = f;
      f = e;
      e = (d + t1) | 0;
      d = c;
      c = bb;
      bb = a;
      a = (t1 + t2) | 0;
    }
    const novo = [a, bb, c, d, e, f, g, h];
    for (let i = 0; i < 8; i++) H[i] = ((H[i] as number) + (novo[i] as number)) | 0;
  }
  return H.map((x) => (x >>> 0).toString(16).padStart(8, '0')).join('');
}

/** SHA-256 (hex). Usa o `crypto.subtle`; se faltar ou falhar, cai no cálculo local, nunca rejeita. */
export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  try {
    const subtle = globalThis.crypto?.subtle;
    if (subtle) {
      const h = await subtle.digest('SHA-256', bytes.slice());
      return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('');
    }
  } catch {
    // segue para o cálculo local
  }
  return sha256Local(bytes);
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

/** Resultado para qualquer falha inesperada da leitura: sem conteúdo, nome nem valor; o item pode ser pulado. */
export function falhaDeLeitura(): ResultadoArquivo {
  return naoSuportado('', 'corrompido', 0);
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
  let hash = '';
  try {
    hash = await sha256Hex(bytes);
    if (bytes.length > LIMITE_BYTES) return naoSuportado(hash, 'muito-grande', 0);
    const pdf = await extrairTexto(bytes, senha, opcoes.onProgresso);
    return analisarPaginas(pdf.paginas, hash, pdf.totalPaginas);
  } catch (e) {
    return naoSuportado(hash, e instanceof ErroLeitura ? e.motivo : motivoDoErro(e), 0);
  }
}
