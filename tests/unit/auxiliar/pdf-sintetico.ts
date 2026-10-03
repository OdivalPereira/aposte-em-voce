// Gera um PDF com texto nas posições dadas (dados fictícios), para provar a camada do PDF.js.
import { PDFDocument, StandardFonts } from 'pdf-lib';
import type { PaginaTexto } from '../../../src/leitura/tipos';

export async function gerarPdf(paginas: PaginaTexto[], opcoes: { tamanhoFonte?: number } = {}): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const fonte = await doc.embedFont(StandardFonts.Helvetica);
  const tamanho = opcoes.tamanhoFonte ?? 8;
  for (const p of paginas) {
    const pg = doc.addPage([595, 842]);
    for (const it of p.itens) pg.drawText(it.texto, { x: it.x, y: it.y, size: tamanho, font: fonte });
  }
  return doc.save();
}

/** PDF de uma página sem nenhum texto (imagem escaneada, para o efeito de "sem texto útil"). */
export async function gerarPdfSemTexto(): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  doc.addPage([595, 842]);
  return doc.save();
}
