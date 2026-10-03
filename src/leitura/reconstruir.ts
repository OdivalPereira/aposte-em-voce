// Passos 3, 4, 5 e 7 do pipeline (seção 5.1): linhas por coordenada, cabeçalhos e colunas, lançamentos
// reconstruídos e direção. Núcleo genérico: nenhuma regra por banco. Funções puras sobre texto posicionado.
import { ColetorLayout, tituloDeGrupo } from './layout';
import {
  centavosComSinal,
  descricaoNormalizada,
  diasNoMes,
  inferirAno,
  iso,
  lerData,
  lerHora,
  lerValor,
  semAcento,
  type PeriodoReferencia,
  type ValorLido,
} from './normalizar';
import type { Direcao, EstruturaLayout, Lancamento, PaginaTexto } from './tipos';

// ---------- passo 3: linhas por coordenada ----------

export interface Celula {
  texto: string;
  x0: number;
  x1: number;
}

export interface Linha {
  pagina: number;
  y: number;
  celulas: Celula[];
}

const TOLERANCIA_Y = 3;

function larguraDoCaractere(texto: string, largura: number): number {
  const n = texto.length || 1;
  return largura > 0 ? largura / n : 5;
}

/** Agrupa os itens de uma página em linhas (por y) e junta itens próximos em células (por x). */
export function agruparLinhas(pagina: PaginaTexto): Linha[] {
  const itens = pagina.itens
    .filter((i) => i.texto.trim() !== '')
    .sort((a, b) => b.y - a.y || a.x - b.x);
  const grupos: { y: number; itens: typeof itens }[] = [];
  for (const item of itens) {
    const g = grupos[grupos.length - 1];
    if (g && Math.abs(g.y - item.y) <= TOLERANCIA_Y) g.itens.push(item);
    else grupos.push({ y: item.y, itens: [item] });
  }
  return grupos.map((g) => {
    const ordenados = [...g.itens].sort((a, b) => a.x - b.x);
    const celulas: Celula[] = [];
    let ultimoCw = 5;
    for (const it of ordenados) {
      const cw = larguraDoCaractere(it.texto, it.largura);
      const x1 = it.x + (it.largura > 0 ? it.largura : cw * it.texto.length);
      const c = celulas[celulas.length - 1];
      if (c && it.x - c.x1 <= 2 * Math.max(cw, ultimoCw)) {
        const colar = it.x - c.x1 <= 0.15 * cw || /\s$/.test(c.texto) || /^\s/.test(it.texto);
        c.texto = (c.texto + (colar ? '' : ' ') + it.texto).replace(/\s+/g, ' ').trim();
        c.x1 = Math.max(c.x1, x1);
      } else {
        celulas.push({ texto: it.texto.replace(/\s+/g, ' ').trim(), x0: it.x, x1 });
      }
      ultimoCw = cw;
    }
    return { pagina: pagina.numero, y: g.y, celulas };
  });
}

// ---------- passo 4: cabeçalhos e colunas ----------

export type PapelColuna = 'data' | 'descricao' | 'valor' | 'credito' | 'debito' | 'saldo' | 'sinal' | 'outro';

export interface Coluna {
  papel: PapelColuna;
  x0: number;
  x1: number;
}

function papelDoCabecalho(texto: string): PapelColuna {
  const t = semAcento(texto)
    .toLowerCase()
    .replace(/\(?\s*r\$\s*\)?/g, '')
    .replace(/[:*]+$/g, '')
    .trim();
  if (t.length > 28) return 'outro';
  if (/^(d\s*\/\s*c|c\s*\/\s*d|dc|cd|natureza|sinal|tipo( de)? (lancamento|movimento|operacao))$/.test(t)) return 'sinal';
  if (/^(data|dt\.?|dia)\b/.test(t)) return 'data';
  if (/^(historico|descricao|lancamentos?|detalhes?|movimentacao|movimentacoes|transacao|transacoes|estabelecimento|descritivo|memo)\b/.test(t)) return 'descricao';
  if (/^(valor|quantia|montante)\b/.test(t)) return 'valor';
  if (/^(credito|creditos|entrada|entradas|crd)\b/.test(t)) return 'credito';
  if (/^(debito|debitos|saida|saidas|dbt)\b/.test(t)) return 'debito';
  if (/^saldo\b/.test(t)) return 'saldo';
  return 'outro';
}

/** Uma linha é cabeçalho se tem ao menos duas colunas reconhecidas, uma delas monetária. */
export function detectarCabecalho(linha: Linha): Coluna[] | null {
  const colunas = linha.celulas.map((c) => ({ papel: papelDoCabecalho(c.texto), x0: c.x0, x1: c.x1 }));
  const reconhecidos = new Set(colunas.map((c) => c.papel).filter((p) => p !== 'outro'));
  const monetaria = reconhecidos.has('valor') || reconhecidos.has('credito') || reconhecidos.has('debito');
  const outra = reconhecidos.has('data') || reconhecidos.has('descricao') || reconhecidos.has('saldo');
  return reconhecidos.size >= 2 && monetaria && outra ? colunas : null;
}

function colunaDaCelula(c: Celula, colunas: Coluna[]): Coluna {
  let melhor = colunas[0] as Coluna;
  let menor = Infinity;
  for (const col of colunas) {
    const d = Math.min(Math.abs(c.x0 - col.x0), Math.abs(c.x1 - col.x1), Math.abs((c.x0 + c.x1) / 2 - (col.x0 + col.x1) / 2));
    if (d < menor) {
      menor = d;
      melhor = col;
    }
  }
  return melhor;
}

// ---------- campos de uma linha ----------

interface Campos {
  data: string;
  desc: string;
  valor: string;
  credito: string;
  debito: string;
  saldo: string;
  sinal: string;
  /** células monetárias na linha (usado no modo sem cabeçalho) */
  monetarias: number;
  haColunaCreditoDebito: boolean;
}

function juntar(partes: string[]): string {
  return partes.join(' ').replace(/\s+/g, ' ').trim();
}

/** Célula monetária vazia: traço de preenchimento ("-", "—"). */
function semTraco(t: string): string {
  return /^[-–—]$/.test(t) ? '' : t;
}

function camposPorColunas(linha: Linha, colunas: Coluna[]): Campos {
  const por: Record<PapelColuna, string[]> = { data: [], descricao: [], valor: [], credito: [], debito: [], saldo: [], sinal: [], outro: [] };
  for (const c of linha.celulas) por[colunaDaCelula(c, colunas).papel].push(c.texto);
  return {
    data: juntar(por.data),
    // Colunas extras entram na descrição só se trouxerem letras ("Tipo", "Categoria"); números de documento ficam de fora.
    desc: juntar([...por.descricao, ...por.outro.filter((t) => /\p{L}/u.test(t))]),
    valor: semTraco(juntar(por.valor)),
    credito: semTraco(juntar(por.credito)),
    debito: semTraco(juntar(por.debito)),
    saldo: semTraco(juntar(por.saldo)),
    sinal: juntar(por.sinal),
    monetarias: linha.celulas.filter((c) => lerValor(c.texto)).length,
    haColunaCreditoDebito: colunas.some((c) => c.papel === 'credito' || c.papel === 'debito'),
  };
}

/** Sem cabeçalho: a data é a primeira célula que começa por data; o valor, a primeira monetária; o saldo, a segunda. */
function camposPorConteudo(linha: Linha): Campos {
  let data = '';
  const monetarias: string[] = [];
  const resto: string[] = [];
  for (const c of linha.celulas) {
    if (!data && lerData(c.texto)) data = c.texto;
    else if (lerValor(c.texto)) monetarias.push(c.texto);
    else resto.push(c.texto);
  }
  return {
    data,
    desc: juntar(resto),
    valor: monetarias[0] ?? '',
    credito: '',
    debito: '',
    saldo: monetarias[1] ?? '',
    sinal: '',
    monetarias: monetarias.length,
    haColunaCreditoDebito: false,
  };
}

// ---------- passo 5 e 7: lançamentos ----------

interface Bruta {
  pagina: number;
  dia: number | null;
  mes: number | null;
  ano: number | null;
  hora: string | null;
  descricao: string;
  valor: ValorLido | null;
  /** direção definida pela coluna (crédito/débito ou sinal D/C); `undefined` = decidir pelo sinal do valor */
  direcaoColuna: Direcao | undefined;
  saldo: number | null;
  dataIlegivel: boolean;
  /** grupo "agrupado por dia" (título que define a direção) em vigor na linha */
  grupo: GrupoDia | null;
}

/** Grupo sob um título como "Total de entradas": a direção vem do título; o total declarado confere a soma. */
interface GrupoDia {
  direcao: Direcao;
  /** total declarado no título, em centavos; `null` se o título não traz valor */
  declarado: number | null;
  linhas: number;
  /** soma dos lançamentos lidos do grupo, em centavos */
  soma: number;
}

export interface Reconstrucao {
  linhasCandidatas: number;
  lancamentos: Lancamento[];
  saldoInicialCentavos: number | null;
  saldoFinalCentavos: number | null;
  /** candidatas sem direção determinada */
  semDirecao: number;
  /** candidatas que não viraram lançamento (data, valor ou direção ilegíveis) */
  naoLidas: number;
  cabecalhoEncontrado: boolean;
  /** modo sem cabeçalho com mais de um valor por linha: colunas só se confirmam pela conferência de saldo */
  colunasIncertas: boolean;
  /** texto das linhas fora da tabela (período, banco) */
  textoFora: string;
  /** estrutura do layout para a assinatura (T99) */
  estrutura: EstruturaLayout;
  /** grupos com linhas cujo total declarado não bate com a soma lida (nenhum lançamento é alterado) */
  totaisDivergentes: number;
}

const RUIDO = /^(pagina|pag\.?)\s*\d+(\s*(de|\/)\s*\d+)?$|^(emitido|gerado|extrato gerado)\b|^www\.|^sac\b|^ouvidoria\b|^cnpj\b|^(continua|continuacao)\b/;

function mediana(valores: number[]): number {
  if (valores.length === 0) return Infinity;
  const v = [...valores].sort((a, b) => a - b);
  return v[Math.floor(v.length / 2)] as number;
}

function direcaoDoSinal(texto: string): Direcao | undefined {
  const t = semAcento(texto).toLowerCase().replace(/[^a-z+-]/g, '');
  if (t === 'd' || t === 'debito' || t === '-' || t === 'saida') return 'saida';
  if (t === 'c' || t === 'credito' || t === '+' || t === 'entrada') return 'entrada';
  return undefined;
}

type Marcador = 'inicial' | 'final' | 'outro';

function marcadorDeSaldo(desc: string): Marcador | null {
  const d = semAcento(desc).toLowerCase();
  if (!/^saldo\b/.test(d)) return null;
  if (/\b(anterior|inicial)\b/.test(d)) return 'inicial';
  if (/\b(final|atual)\b/.test(d) && !/\bdo dia\b/.test(d)) return 'final';
  return 'outro';
}

/** Reconstrói os lançamentos de todas as páginas, em ordem de documento. */
export function reconstruir(paginas: PaginaTexto[]): Reconstrucao {
  const porPagina = paginas.map((p) => agruparLinhas(p));
  const haCabecalho = porPagina.some((ls) => ls.some((l) => detectarCabecalho(l)));

  const brutas: Bruta[] = [];
  const fora: string[] = [];
  let colunas: Coluna[] | null = null;
  let anterior: Bruta | null = null;
  let anteriorY = 0;
  let anteriorPagina = 0;
  let ultimaData: { dia: number; mes: number; ano: number | null } | null = null;
  let candidatas = 0;
  let saldoInicial: number | null = null;
  let saldoFinal: number | null = null;
  let colunasIncertas = false;
  let tabelaComecou = !haCabecalho;
  const layout = new ColetorLayout();
  const grupos: GrupoDia[] = [];
  let grupo: GrupoDia | null = null;
  let larguraRef = 0;
  for (const p of paginas) for (const i of p.itens) larguraRef = Math.max(larguraRef, i.x + i.largura);

  for (const linhas of porPagina) {
    const passo = mediana(linhas.slice(1).map((l, i) => (linhas[i] as Linha).y - l.y));
    for (const linha of linhas) {
      const cab = detectarCabecalho(linha);
      if (cab) {
        colunas = cab;
        layout.definirCabecalho(linha, cab);
        tabelaComecou = true;
        anterior = null;
        grupo = null;
        continue;
      }
      const textoLinha = juntar(linha.celulas.map((c) => c.texto));
      if (!tabelaComecou) {
        fora.push(textoLinha);
        continue;
      }
      const campos = colunas ? camposPorColunas(linha, colunas) : camposPorConteudo(linha);
      const temDinheiro = !!(campos.valor || campos.credito || campos.debito);
      if (!temDinheiro && campos.data && !lerData(campos.data)) {
        // Texto na coluna da data que não é data (rodapé, aviso): é texto, não candidata.
        campos.desc = juntar([campos.data, campos.desc]);
        campos.data = '';
      }
      const descNorm = semAcento(campos.desc).toLowerCase();

      // Marcadores de saldo e totais: não são lançamentos.
      const marcador = marcadorDeSaldo(campos.desc);
      if (marcador) {
        const txt = campos.saldo || campos.valor || campos.credito || campos.debito;
        const v = txt ? lerValor(txt) : null;
        if (v && marcador === 'inicial' && saldoInicial === null) saldoInicial = centavosComSinal(v);
        if (v && marcador === 'final') saldoFinal = centavosComSinal(v);
        anterior = null;
        grupo = null;
        fora.push(textoLinha);
        continue;
      }
      // Título de grupo ("Total de entradas" / "Total de saídas"): define a direção das linhas abaixo e traz o total do dia.
      const tituloGrupo = tituloDeGrupo(campos.desc);
      if (tituloGrupo) {
        const txt = campos.valor || campos.credito || campos.debito;
        const v = txt ? lerValor(txt) : null;
        grupo = { direcao: tituloGrupo.direcao, declarado: v ? v.centavos : null, linhas: 0, soma: 0 };
        grupos.push(grupo);
        layout.grupo(tituloGrupo.rotulo);
        anterior = null;
        fora.push(textoLinha);
        continue;
      }
      if (/^totais?\b/.test(descNorm) || RUIDO.test(descNorm)) {
        anterior = null;
        fora.push(textoLinha);
        continue;
      }

      const data = campos.data ? lerData(campos.data) : null;
      // Título de grupo que caiu na coluna da descrição (tabela sem coluna de data): "02 SET 2026".
      const titulo = !temDinheiro && !campos.data && !campos.saldo ? lerData(campos.desc) : null;
      if (titulo && !titulo.resto) {
        ultimaData = { dia: titulo.dia, mes: titulo.mes, ano: titulo.ano };
        anterior = null;
        grupo = null;
        fora.push(textoLinha);
        continue;
      }

      if (!temDinheiro && !campos.data) {
        // Continuação da descrição (mesma página, logo abaixo) ou ruído (rodapé, aviso).
        if (anterior && campos.desc && linha.pagina === anteriorPagina && anteriorY - linha.y <= 1.5 * passo) {
          anterior.descricao = juntar([anterior.descricao, campos.desc]);
          anteriorY = linha.y;
        } else {
          anterior = null;
          fora.push(textoLinha);
        }
        continue;
      }
      if (!temDinheiro && data && !campos.desc && !campos.saldo) {
        // Linha só com data: título de grupo ("02 SET 2026"); vale para as linhas seguintes sem data.
        ultimaData = { dia: data.dia, mes: data.mes, ano: data.ano };
        anterior = null;
        grupo = null;
        fora.push(textoLinha);
        continue;
      }

      candidatas++;
      if (grupo) grupo.linhas++;
      layout.candidata(linha, campos.data, [campos.valor, campos.credito, campos.debito, campos.saldo]);
      let hora: string | null = null;
      let descricao = campos.desc;
      if (data?.resto) {
        const h = lerHora(data.resto);
        if (h) hora = h;
        else descricao = juntar([data.resto, descricao]);
      }
      const candidataData = data ?? (campos.data ? null : ultimaData);
      if (data) ultimaData = { dia: data.dia, mes: data.mes, ano: data.ano };
      // Horário sozinho numa célula da descrição ("14:35"): vira hora, não descrição.
      const mHora = /(^|\s)(\d{1,2}:\d{2})(?::\d{2})?(?=\s|$)/.exec(descricao);
      if (mHora && !hora && lerHora(mHora[2] as string)) {
        hora = lerHora(mHora[2] as string);
        descricao = juntar([descricao.replace(mHora[0], ' ')]);
      }

      // Valor e direção.
      let valor: ValorLido | null = null;
      let direcaoColuna: Direcao | undefined;
      if (campos.haColunaCreditoDebito) {
        // Célula com valor zero conta como vazia (algumas contas preenchem os dois lados).
        const c = campos.credito ? lerValor(campos.credito) : null;
        const d = campos.debito ? lerValor(campos.debito) : null;
        const cOcupada = !!campos.credito && !(c && c.centavos === 0);
        const dOcupada = !!campos.debito && !(d && d.centavos === 0);
        if (cOcupada && !dOcupada) {
          valor = c;
          direcaoColuna = 'entrada';
        } else if (dOcupada && !cOcupada) {
          valor = d;
          direcaoColuna = 'saida';
        } else if (!cOcupada && !dOcupada && campos.valor) {
          valor = lerValor(campos.valor);
        }
      } else {
        valor = campos.valor ? lerValor(campos.valor) : null;
      }
      if (campos.sinal && !direcaoColuna) direcaoColuna = direcaoDoSinal(campos.sinal);
      if (!colunas && campos.monetarias > 1) colunasIncertas = true;
      const saldoLido = campos.saldo ? lerValor(campos.saldo) : null;

      const bruta: Bruta = {
        pagina: linha.pagina,
        dia: candidataData?.dia ?? null,
        mes: candidataData?.mes ?? null,
        ano: candidataData?.ano ?? null,
        hora,
        descricao,
        valor,
        direcaoColuna,
        saldo: saldoLido ? centavosComSinal(saldoLido) : null,
        dataIlegivel: candidataData === null,
        grupo,
      };
      brutas.push(bruta);
      anterior = bruta;
      anteriorY = linha.y;
      anteriorPagina = linha.pagina;
    }
  }

  return finalizar(brutas, {
    candidatas,
    saldoInicial,
    saldoFinal,
    colunasIncertas,
    cabecalhoEncontrado: haCabecalho,
    fora,
    estrutura: layout.construir(larguraRef),
    grupos,
  });
}

// ---------- fechamento: período, ano e direção do documento ----------

const RE_DATA_COMPLETA = /\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b/g;

function datasCompletas(texto: string): string[] {
  const out: string[] = [];
  for (const m of texto.matchAll(RE_DATA_COMPLETA)) {
    const d = lerData(m[0]);
    if (d && d.ano !== null) out.push(iso(d.ano, d.mes, d.dia));
  }
  // "12 set 2026", "12 de setembro de 2026"
  for (const m of semAcento(texto).toLowerCase().matchAll(/\b\d{1,2}\s*(?:de\s+)?[a-z]{3,9}\.?\s*(?:de\s+)?\d{4}\b/g)) {
    const d = lerData(m[0]);
    if (d && d.ano !== null) out.push(iso(d.ano, d.mes, d.dia));
  }
  return out;
}

function paraReferencia(inicio: string, fim: string): PeriodoReferencia {
  const p = (s: string) => ({ ano: Number(s.slice(0, 4)), mes: Number(s.slice(5, 7)), dia: Number(s.slice(8, 10)) });
  return { inicio: p(inicio), fim: p(fim) };
}

/** Período do documento (texto fora da tabela); na falta, as datas com ano que as próprias linhas trazem. */
export function periodoDoDocumento(textoFora: string, datasDasLinhas: string[]): PeriodoReferencia | null {
  const intervalo = /(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s*(?:a|ate|até|à|-|–)\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})/i.exec(textoFora);
  if (intervalo) {
    const a = lerData(intervalo[1] as string);
    const b = lerData(intervalo[2] as string);
    if (a?.ano && b?.ano) {
      const ia = iso(a.ano, a.mes, a.dia);
      const ib = iso(b.ano, b.mes, b.dia);
      return ia <= ib ? paraReferencia(ia, ib) : paraReferencia(ib, ia);
    }
  }
  const todas = [...datasCompletas(textoFora)].sort();
  if (todas.length > 0) return paraReferencia(todas[0] as string, todas[todas.length - 1] as string);
  const mesAno = /\b(\d{1,2})\/(\d{4})\b/.exec(textoFora);
  if (mesAno && Number(mesAno[1]) >= 1 && Number(mesAno[1]) <= 12) {
    const mes = Number(mesAno[1]);
    const ano = Number(mesAno[2]);
    return paraReferencia(iso(ano, mes, 1), iso(ano, mes, diasNoMes(mes, ano)));
  }
  const proprias = [...datasDasLinhas].sort();
  if (proprias.length > 0) return paraReferencia(proprias[0] as string, proprias[proprias.length - 1] as string);
  return null;
}

function finalizar(
  brutas: Bruta[],
  r: {
    candidatas: number;
    saldoInicial: number | null;
    saldoFinal: number | null;
    colunasIncertas: boolean;
    cabecalhoEncontrado: boolean;
    fora: string[];
    estrutura: EstruturaLayout;
    grupos: GrupoDia[];
  },
): Reconstrucao {
  const textoFora = r.fora.join('\n');
  const proprias = brutas.filter((b) => b.ano !== null && b.dia !== null && b.mes !== null).map((b) => iso(b.ano as number, b.mes as number, b.dia as number));
  const periodo = periodoDoDocumento(textoFora, proprias);

  // Direção do documento para valores sem sinal (só quando o documento marca um dos lados).
  let negativos = 0;
  let positivos = 0;
  for (const b of brutas) {
    if (!b.valor || b.direcaoColuna) continue;
    if (b.valor.sinal === '-' || b.valor.dc === 'D') negativos++;
    else if (b.valor.sinal === '+' || b.valor.dc === 'C') positivos++;
  }
  const semMarca: Direcao | undefined = negativos > 0 && positivos === 0 ? 'entrada' : positivos > 0 && negativos === 0 ? 'saida' : undefined;

  const lancamentos: Lancamento[] = [];
  let semDirecao = 0;
  let naoLidas = 0;
  for (const b of brutas) {
    if (!b.valor || b.dataIlegivel || b.dia === null || b.mes === null) {
      naoLidas++;
      continue;
    }
    const ano = b.ano ?? inferirAno(b.dia, b.mes, periodo);
    if (ano === null) {
      naoLidas++;
      continue;
    }
    let direcao: Direcao | undefined = b.direcaoColuna;
    if (!direcao) {
      if (b.valor.sinal === '-' || b.valor.dc === 'D') direcao = 'saida';
      else if (b.valor.sinal === '+' || b.valor.dc === 'C') direcao = 'entrada';
      else direcao = b.grupo?.direcao ?? semMarca;
    }
    if (!direcao) {
      semDirecao++;
      continue;
    }
    lancamentos.push({
      data: iso(ano, b.mes, b.dia),
      hora: b.hora,
      valorCentavos: b.valor.centavos,
      direcao,
      descricao: b.descricao,
      pagina: b.pagina,
      saldoCentavos: b.saldo,
    });
    if (b.grupo && direcao === b.grupo.direcao) b.grupo.soma += b.valor.centavos;
  }
  return {
    linhasCandidatas: r.candidatas,
    lancamentos,
    saldoInicialCentavos: r.saldoInicial,
    saldoFinalCentavos: r.saldoFinal,
    semDirecao,
    naoLidas: naoLidas + semDirecao,
    cabecalhoEncontrado: r.cabecalhoEncontrado,
    colunasIncertas: r.colunasIncertas,
    textoFora,
    estrutura: r.estrutura,
    totaisDivergentes: r.grupos.filter((g) => g.declarado !== null && g.linhas > 0 && g.soma !== g.declarado).length,
  };
}

/** Chave de duplicidade da seção 5.3: data, valor em centavos, direção e descrição normalizada. */
export function chaveDeDuplicidade(l: Pick<Lancamento, 'data' | 'valorCentavos' | 'direcao' | 'descricao'>): string {
  return [l.data, l.valorCentavos, l.direcao, descricaoNormalizada(l.descricao)].join('|');
}
