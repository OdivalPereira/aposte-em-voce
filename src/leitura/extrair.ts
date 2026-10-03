// Passos 1 e 2 (seção 5.1): abrir o PDF (com senha local) e extrair o texto com posições, via pdfjs-dist.
// Este arquivo é a única camada que toca o PDF.js; o restante do pipeline recebe texto posicionado.
// O PDF.js só é carregado quando esta função roda, isto é, depois que a pessoa escolhe um PDF.
import { ErroLeitura, LIMITE_PAGINAS, type ItemTexto, type Motivo, type PaginaTexto } from './tipos';

export interface PdfTexto {
  totalPaginas: number;
  paginas: PaginaTexto[];
}

/** Traduz a exceção do PDF.js em motivo. Senha pedida e senha errada são casos à parte, para a tela pedir a senha. */
export function motivoDoErro(e: unknown): Motivo {
  const o = e as { name?: string; code?: number } | null;
  if (o?.name === 'PasswordException') return o.code === 2 ? 'senha-incorreta' : 'senha-necessaria';
  return 'corrompido';
}

async function carregarPdfjs() {
  const [pdfjs, worker] = await Promise.all([import('pdfjs-dist/legacy/build/pdf.mjs'), import('pdfjs-dist/legacy/build/pdf.worker.mjs')]);
  // O código do worker do PDF.js vai junto do nosso worker (nada de CDN, nada de segundo arquivo a buscar).
  (globalThis as { pdfjsWorker?: unknown }).pdfjsWorker = worker;
  return pdfjs;
}

export async function extrairTexto(bytes: Uint8Array, senha?: string, onProgresso?: (feito: number, total: number) => void): Promise<PdfTexto> {
  const pdfjs = await carregarPdfjs();
  const tarefa = pdfjs.getDocument({
    data: bytes.slice(), // o PDF.js toma posse do buffer; os bytes originais continuam com quem chamou
    password: senha,
    verbosity: 0,
    useSystemFonts: false,
    disableFontFace: true,
  });
  let doc;
  try {
    doc = await tarefa.promise;
  } catch (e) {
    await tarefa.destroy();
    throw new ErroLeitura(motivoDoErro(e));
  }
  try {
    const total = doc.numPages;
    if (total > LIMITE_PAGINAS) throw new ErroLeitura('muitas-paginas');
    const paginas: PaginaTexto[] = [];
    for (let n = 1; n <= total; n++) {
      const pagina = await doc.getPage(n);
      const conteudo = await pagina.getTextContent();
      const itens: ItemTexto[] = [];
      for (const it of conteudo.items) {
        if (!('str' in it) || it.str.trim() === '') continue;
        itens.push({ texto: it.str, x: it.transform[4] as number, y: it.transform[5] as number, largura: it.width, pagina: n });
      }
      paginas.push({ numero: n, itens });
      pagina.cleanup();
      onProgresso?.(n, total);
    }
    return { totalPaginas: total, paginas };
  } catch (e) {
    if (e instanceof ErroLeitura) throw e;
    throw new ErroLeitura('corrompido');
  } finally {
    await tarefa.destroy();
  }
}
