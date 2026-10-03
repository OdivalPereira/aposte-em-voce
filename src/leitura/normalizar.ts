// Passo 6: normalizar datas e valores. Funções puras; valores em centavos inteiros, sem ponto flutuante.

/** Minúsculas, sem acentos, espaços colapsados. */
export function semAcento(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Descrição normalizada (chave de duplicidade): maiúsculas, sem acentos nem pontuação. */
export function descricaoNormalizada(s: string): string {
  return semAcento(s)
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, ' ')
    .trim();
}

const MESES: Record<string, number> = {
  jan: 1, janeiro: 1,
  fev: 2, fevereiro: 2,
  mar: 3, marco: 3,
  abr: 4, abril: 4,
  mai: 5, maio: 5,
  jun: 6, junho: 6,
  jul: 7, julho: 7,
  ago: 8, agosto: 8,
  set: 9, setembro: 9,
  out: 10, outubro: 10,
  nov: 11, novembro: 11,
  dez: 12, dezembro: 12,
};
const NOME_MES = '(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)';

export interface DataLida {
  dia: number;
  mes: number;
  /** `null` quando o documento não traz o ano (dd/mm, "12 SET") */
  ano: number | null;
  /** o que sobrou depois da data (ex.: um horário ou parte da descrição) */
  resto: string;
}

export function bissexto(ano: number): boolean {
  return (ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0;
}

export function diasNoMes(mes: number, ano: number | null): number {
  if (mes === 2) return ano !== null && !bissexto(ano) ? 28 : 29;
  return [4, 6, 9, 11].includes(mes) ? 30 : 31;
}

function anoDeDoisDigitos(a: string): number {
  return a.length === 2 ? 2000 + Number(a) : Number(a);
}

/**
 * Lê uma data no início do texto: `dd/mm/aaaa`, `dd/mm/aa`, `dd-mm-aaaa`, `dd.mm.aaaa`, `dd/mm`,
 * `12 SET`, `12 set 2026`, `12/SET`, `12 de setembro de 2026`.
 * Devolve `null` se o texto não começa por uma data válida.
 */
export function lerData(texto: string): DataLida | null {
  const t = semAcento(texto).toLowerCase();
  let dia: number;
  let mes: number;
  let ano: number | null = null;
  let tamanho: number;

  let m = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})(?![\d/])/.exec(t);
  if (m) {
    dia = Number(m[1]);
    mes = Number(m[2]);
    ano = anoDeDoisDigitos(m[3] as string);
    tamanho = m[0].length;
  } else if ((m = new RegExp(`^(\\d{1,2})\\s*(?:de\\s+|[/.-]\\s*)?${NOME_MES}\\b\\.?(?:\\s*(?:de\\s+|[/.-]\\s*)?(\\d{4})\\b)?`).exec(t))) {
    dia = Number(m[1]);
    mes = MESES[m[2] as string] as number;
    ano = m[3] ? Number(m[3]) : null;
    tamanho = m[0].length;
  } else if ((m = /^(\d{1,2})[/.-](\d{1,2})(?![\d/.-]|,\d)/.exec(t))) {
    dia = Number(m[1]);
    mes = Number(m[2]);
    tamanho = m[0].length;
  } else {
    return null;
  }
  if (mes < 1 || mes > 12 || dia < 1 || dia > diasNoMes(mes, ano)) return null;
  // `texto` e `t` têm o mesmo comprimento fora de acentos combinados; o resto é só informativo.
  return { dia, mes, ano, resto: texto.trim().slice(tamanho).trim() };
}

export function iso(ano: number, mes: number, dia: number): string {
  return `${String(ano).padStart(4, '0')}-${String(mes).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
}

export interface PeriodoReferencia {
  inicio: { ano: number; mes: number; dia: number };
  fim: { ano: number; mes: number; dia: number };
}

/**
 * Infere o ano de uma data sem ano a partir do período do documento. Só escolhe um ano em que a data
 * cai dentro do período; fora disso devolve `null` (não inventa).
 */
export function inferirAno(dia: number, mes: number, periodo: PeriodoReferencia | null): number | null {
  if (!periodo) return null;
  const ini = periodo.inicio;
  const fim = periodo.fim;
  for (let ano = ini.ano; ano <= fim.ano; ano++) {
    if (dia > diasNoMes(mes, ano)) continue;
    const v = iso(ano, mes, dia);
    if (v >= iso(ini.ano, ini.mes, ini.dia) && v <= iso(fim.ano, fim.mes, fim.dia)) return ano;
  }
  return null;
}

export interface ValorLido {
  /** valor absoluto em centavos */
  centavos: number;
  /** sinal explícito: "-" ou parênteses = `-`; "+" = `+`; nenhum = `null` */
  sinal: '-' | '+' | null;
  /** sufixo D (débito) ou C (crédito), se houver */
  dc: 'D' | 'C' | null;
}

const NUM = '(\\d{1,3}(?:\\.\\d{3})+|\\d+),(\\d{2})';
const RE_VALOR = new RegExp(`^([+-])?\\s*(?:R\\$)?\\s*([+-])?\\s*${NUM}\\s*([DC])?\\s*([+-])?$`, 'i');

/** Lê um valor monetário em reais e devolve centavos inteiros. A célula inteira precisa ser o valor. */
export function lerValor(texto: string): ValorLido | null {
  let t = texto.replace(/[−–—]/g, '-').replace(/\s+/g, ' ').trim();
  let parenteses = false;
  const p = /^\((.*)\)$/.exec(t);
  if (p) {
    parenteses = true;
    t = (p[1] as string).trim();
  }
  const m = RE_VALOR.exec(t);
  if (!m) return null;
  const sinais = [m[1], m[2], m[6]].filter((s): s is string => !!s);
  if (sinais.length > 1) return null;
  const reais = (m[3] as string).replace(/\./g, '');
  const centavos = Number(reais) * 100 + Number(m[4]);
  if (!Number.isSafeInteger(centavos)) return null;
  const dc = m[5] ? ((m[5] as string).toUpperCase() as 'D' | 'C') : null;
  const sinal = parenteses ? '-' : ((sinais[0] as '-' | '+' | undefined) ?? null);
  return { centavos, sinal, dc };
}

/** Valor com sinal (saldo): "-" e "D" negativos. */
export function centavosComSinal(v: ValorLido): number {
  return v.sinal === '-' || v.dc === 'D' ? -v.centavos : v.centavos;
}

export function lerHora(texto: string): string | null {
  const m = /^(\d{1,2}):(\d{2})(?::\d{2})?$/.exec(texto.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  if (h > 23 || min > 59) return null;
  return `${String(h).padStart(2, '0')}:${m[2]}`;
}
