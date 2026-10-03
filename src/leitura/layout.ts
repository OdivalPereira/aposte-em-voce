// Estrutura do layout de um extrato (T99) e identificador estrutural da conta. Funções puras.
// A estrutura nunca carrega valor, nome nem descrição: rótulos de coluna só entram se estiverem num
// vocabulário fixo; formatos de data e de valor saem com todo dígito trocado por 9 e toda letra por A.
import { lerData, lerValor, semAcento } from './normalizar';
import type { Direcao, EstruturaLayout } from './tipos';
import type { Coluna, Linha } from './reconstruir';

const VOCABULARIO = new Set([
  'data', 'dia', 'dt', 'historico', 'descricao', 'lancamento', 'lancamentos', 'detalhe', 'detalhes', 'movimentacao', 'movimentacoes',
  'transacao', 'transacoes', 'estabelecimento', 'descritivo', 'memo', 'valor', 'quantia', 'montante', 'credito', 'creditos', 'entrada',
  'entradas', 'debito', 'debitos', 'saida', 'saidas', 'saldo', 'd/c', 'c/d', 'dc', 'natureza', 'sinal', 'tipo',
]);

const CANONICO: Record<string, string> = {
  data: 'Data', descricao: 'Descrição', valor: 'Valor', credito: 'Crédito', debito: 'Débito', saldo: 'Saldo', sinal: 'Sinal', outro: 'Outra coluna',
};

/** Rótulo do cabeçalho: o do documento só se for uma palavra do vocabulário fixo; senão, o nome do papel. */
export function rotuloDeCabecalho(texto: string, papel: string): string {
  const limpo = texto.replace(/\(?\s*R\$\s*\)?/gi, '').replace(/\s+/g, ' ').trim();
  return VOCABULARIO.has(semAcento(limpo).toLowerCase()) ? limpo : (CANONICO[papel] ?? 'Outra coluna');
}

/** Troca todo dígito por 9 e toda letra por A; limita o tamanho. */
export function mascarar(texto: string): string {
  return texto.replace(/\d/g, '9').replace(/\p{L}/gu, 'A').slice(0, 24);
}

/** Formato de uma data lida: só a parte que é data (o resto da célula pode ser descrição). */
export function formatoDeData(texto: string): string | null {
  const t = texto.trim();
  const d = lerData(t);
  return d ? mascarar(t.slice(0, t.length - d.resto.length).trim()) : null;
}

/** Formato de um valor lido: o primeiro grupo de dígitos vira um só 9 ("9,99", "9.999,99", "-9,99"). */
export function formatoDeValor(texto: string): string | null {
  if (!lerValor(texto)) return null;
  let primeiro = true;
  return texto
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\d+/g, (m) => {
      if (primeiro) {
        primeiro = false;
        return '9';
      }
      return '9'.repeat(m.length);
    });
}

/** Título de grupo que define a direção das linhas abaixo ("Total de entradas", "Total de saídas"). */
export function tituloDeGrupo(descricao: string): { direcao: Direcao; rotulo: string } | null {
  const t = semAcento(descricao).toLowerCase().replace(/[:\s]+$/, '');
  const m = /^total (?:de |das? |dos )?(entradas|creditos|saidas|debitos)$/.exec(t);
  if (!m) return null;
  return m[1] === 'entradas' || m[1] === 'creditos' ? { direcao: 'entrada', rotulo: 'Total de entradas' } : { direcao: 'saida', rotulo: 'Total de saídas' };
}

/**
 * Identificador estrutural da conta: no máximo os 4 últimos dígitos de um número de conta que o próprio
 * documento traz. Nome da pessoa nunca é lido; número sem máscara de até 4 dígitos não vale (pode ser o inteiro).
 */
export function contaDoTexto(textoFora: string): string | null {
  const t = semAcento(textoFora).toLowerCase();
  const m = /\b(?:conta|c\/c|cta)\b(?:\s+(?:corrente|poupanca|pagamento|digital))?\s*(?:final|numero|n[o.]?)?\s*[:.]?\s*([0-9x*•][0-9x*•.-]{2,})/.exec(t);
  if (!m) return null;
  const captura = m[1] as string;
  const digitos = captura.replace(/\D/g, '');
  const mascarado = /[x*•]/.test(captura);
  if (digitos.length < 3 || (digitos.length <= 4 && !mascarado)) return null;
  return `final ${digitos.slice(-4)}`;
}

const decimo = (x: number, largura: number, arredonda: (n: number) => number) => Math.max(0, Math.min(10, arredonda((x / largura) * 10)));

/** Reúne a estrutura enquanto o pipeline lê (sem guardar texto do documento além do que é estrutura). */
export class ColetorLayout {
  private cabecalho: { rotulo: string; x0: number; x1: number }[] | null = null;
  private amostra: Linha[] = [];
  private datas = new Set<string>();
  private valores = new Set<string>();
  private grupos = new Set<string>();

  definirCabecalho(linha: Linha, colunas: Coluna[]) {
    this.cabecalho ??= linha.celulas.map((c, i) => ({ rotulo: rotuloDeCabecalho(c.texto, (colunas[i] as Coluna).papel), x0: c.x0, x1: c.x1 }));
  }

  grupo(rotulo: string) {
    this.grupos.add(rotulo);
  }

  candidata(linha: Linha, dataTexto: string, valoresTexto: string[]) {
    if (this.amostra.length < 60) this.amostra.push(linha);
    const fd = dataTexto ? formatoDeData(dataTexto) : null;
    if (fd) this.datas.add(fd);
    for (const v of valoresTexto) {
      const fv = v ? formatoDeValor(v) : null;
      if (fv) this.valores.add(fv);
    }
  }

  construir(larguraRef: number): EstruturaLayout {
    const largura = larguraRef > 0 ? larguraRef : 1;
    let faixas: { rotulo: string; x0: number; x1: number }[];
    if (this.cabecalho) faixas = this.cabecalho;
    else {
      // Sem cabeçalho: faixas por tipo de célula (data, descrição, 1º e 2º valores).
      const por = new Map<string, { x0: number; x1: number }>();
      const somar = (rotulo: string, x0: number, x1: number) => {
        const f = por.get(rotulo);
        por.set(rotulo, f ? { x0: Math.min(f.x0, x0), x1: Math.max(f.x1, x1) } : { x0, x1 });
      };
      for (const l of this.amostra) {
        let temData = false;
        let monetarias = 0;
        for (const c of l.celulas) {
          if (!temData && lerData(c.texto)) {
            temData = true;
            somar('Data', c.x0, c.x1);
          } else if (lerValor(c.texto)) somar(monetarias++ === 0 ? 'Valor' : 'Saldo', c.x0, c.x1);
          else somar('Descrição', c.x0, c.x1);
        }
      }
      faixas = [...por].map(([rotulo, f]) => ({ rotulo, ...f }));
    }
    const colunas = faixas
      .map((f) => ({ rotulo: f.rotulo, de: decimo(f.x0, largura, Math.floor), ate: decimo(f.x1, largura, Math.ceil) }))
      .sort((a, b) => a.de - b.de || a.ate - b.ate);
    return { colunas, formatosData: [...this.datas].sort(), formatosValor: [...this.valores].sort(), grupos: [...this.grupos].sort() };
  }
}

/** Texto copiável do botão T99: só estrutura, nenhum valor, nome nem descrição. */
export function assinaturaDoLayout(e: EstruturaLayout | null): string {
  if (!e) return 'Assinatura do layout: indisponível para este arquivo (a leitura não chegou a ver a tabela).';
  const lista = (itens: string[]) => (itens.length > 0 ? itens.join('; ') : 'nenhum');
  return [
    'Assinatura do layout (só estrutura; sem valores, nomes nem descrições)',
    `Colunas, da esquerda para a direita: ${e.colunas.length > 0 ? e.colunas.map((c) => c.rotulo).join(' | ') : 'nenhuma'}`,
    `Posição das colunas, em décimos da largura: ${e.colunas.length > 0 ? e.colunas.map((c) => `${c.rotulo} ${c.de}-${c.ate}`).join('; ') : 'nenhuma'}`,
    `Formato de data: ${lista(e.formatosData)}`,
    `Formato de valor: ${lista(e.formatosValor)}`,
    `Títulos de grupo: ${lista(e.grupos)}`,
  ].join('\n');
}
