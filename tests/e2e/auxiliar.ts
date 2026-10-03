import { expect, type BrowserContext, type Page } from '@playwright/test';
import { COLUNAS_PADRAO, pagina } from '../unit/auxiliar/montar';
import { gerarPdf } from '../unit/auxiliar/pdf-sintetico';

export const ORIGEM = 'http://127.0.0.1:4173';

export interface Requisicao {
  metodo: string;
  url: string;
}

/** Registra todas as requisições de rede da página e de seus workers (teste de rede, princípio 1). */
export function registrarRede(context: BrowserContext): Requisicao[] {
  const lista: Requisicao[] = [];
  context.on('request', (r) => {
    if (/^https?:/.test(r.url())) lista.push({ metodo: r.method(), url: r.url() });
  });
  return lista;
}

/** Só GET do mesmo domínio, para arquivos estáticos; nenhum POST, PUT ou PATCH; nenhum terceiro. */
export function verificarSoGetDoMesmoDominio(lista: Requisicao[]) {
  expect(lista.length).toBeGreaterThan(0);
  for (const r of lista) {
    expect(r.metodo, `método de ${r.url}`).toBe('GET');
    expect(r.url.startsWith(`${ORIGEM}/`), `origem de ${r.url}`).toBe(true);
  }
}

export function vigiarCsp(page: Page): string[] {
  const problemas: string[] = [];
  page.on('console', (m) => {
    if (/content security policy|refused to/i.test(m.text())) problemas.push(m.text());
  });
  page.on('pageerror', (e) => problemas.push(`erro na página: ${e.message}`));
  return problemas;
}

export async function nadaGuardadoNoAparelho(page: Page, context: BrowserContext) {
  const estado = await page.evaluate(async () => ({
    local: window.localStorage.length,
    sessao: window.sessionStorage.length,
    cookie: document.cookie,
    bancos: (await indexedDB.databases()).length,
  }));
  expect(estado).toEqual({ local: 0, sessao: 0, cookie: '', bancos: 0 });
  expect(await context.cookies()).toEqual([]);
}

/** Extrato fictício de setembro de 2026 (dados sintéticos). */
export async function extratoSintetico(opcoes: { corte?: 'inicio' | 'fim' | 'tudo' } = {}): Promise<Buffer> {
  const todas = [
    ['02/09/2026', 'PIX ENVIADO PARA\nLOJA FICTICIA LTDA', '-50,00', '950,00'],
    ['05/09/2026', 'PIX RECEBIDO PESSOA FICTICIA', '200,00', '1.150,00'],
    ['09/09/2026', 'PAGAMENTO BOLETO FICTICIO', '-30,10', '1.119,90'],
    ['15/09/2026', 'COMPRA CARTAO MERCADO FICTICIO', '-80,00', '1.039,90'],
  ];
  const corte = opcoes.corte ?? 'tudo';
  const linhas = corte === 'inicio' ? todas.slice(0, 3) : corte === 'fim' ? todas.slice(2) : todas;
  const abre = corte === 'fim' ? '1.150,00' : '1.000,00';
  const fecha = corte === 'inicio' ? '1.119,90' : '1.039,90';
  const pdf = await gerarPdf([
    pagina({
      antes: ['Banco Ficticio - Extrato de conta', 'Período: 01/09/2026 a 30/09/2026'],
      colunas: COLUNAS_PADRAO,
      linhas: [['', 'SALDO ANTERIOR', '', abre], ...linhas, ['', 'SALDO FINAL', '', fecha]],
      depois: ['Página 1 de 1'],
    }),
  ]);
  return Buffer.from(pdf);
}

export function arquivoPdf(nome: string, buffer: Buffer) {
  return { name: nome, mimeType: 'application/pdf', buffer };
}
