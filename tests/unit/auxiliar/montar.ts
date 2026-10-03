// Monta texto posicionado (como o PDF.js entregaria) para os testes de unidade, e o PDF correspondente.
import type { ItemTexto, PaginaTexto } from '../../../src/leitura/tipos';

export interface ColunaMontagem {
  titulo: string;
  /** borda esquerda; com `dir`, a borda direita */
  x: number;
  dir?: boolean;
}

export const LARGURA_CHAR = 5;
export const PASSO = 18;
export const PASSO_QUEBRA = 11;

function item(texto: string, x: number, y: number, dir: boolean | undefined, pagina: number): ItemTexto {
  const largura = texto.length * LARGURA_CHAR;
  return { texto, x: dir ? x - largura : x, y, largura, pagina };
}

export interface PedidoPagina {
  numero?: number;
  /** linhas soltas antes da tabela (título, período): texto na coluna 0 */
  antes?: string[];
  colunas: ColunaMontagem[];
  /** cabeçalho presente nesta página? (padrão: sim) */
  cabecalho?: boolean;
  /** cada linha: um texto por coluna; "\n" dentro da célula quebra a descrição em outra linha */
  linhas: string[][];
  /** linhas soltas depois da tabela (rodapé) */
  depois?: string[];
}

/** Uma página no estilo de tabela, com y decrescente (coordenadas do PDF). */
export function pagina(p: PedidoPagina): PaginaTexto {
  const numero = p.numero ?? 1;
  const itens: ItemTexto[] = [];
  let y = 780;
  for (const t of p.antes ?? []) {
    itens.push(item(t, 40, y, false, numero));
    y -= PASSO;
  }
  y -= PASSO;
  if (p.cabecalho !== false) {
    for (const c of p.colunas) itens.push(item(c.titulo, c.x, y, c.dir, numero));
    y -= PASSO;
  }
  for (const linha of p.linhas) {
    let extras = 0;
    linha.forEach((celula, i) => {
      const col = p.colunas[i];
      if (!col || celula === '') return;
      celula.split('\n').forEach((parte, k) => {
        itens.push(item(parte, col.x, y - k * PASSO_QUEBRA, col.dir, numero));
        extras = Math.max(extras, k);
      });
    });
    y -= PASSO + extras * PASSO_QUEBRA;
  }
  y -= 60;
  for (const t of p.depois ?? []) {
    itens.push(item(t, 40, y, false, numero));
    y -= PASSO;
  }
  return { numero, itens };
}

/** Colunas usuais: Data | Descrição | Valor (à direita) | Saldo (à direita). */
export const COLUNAS_PADRAO: ColunaMontagem[] = [
  { titulo: 'Data', x: 40 },
  { titulo: 'Descrição', x: 130 },
  { titulo: 'Valor (R$)', x: 430, dir: true },
  { titulo: 'Saldo (R$)', x: 540, dir: true },
];
