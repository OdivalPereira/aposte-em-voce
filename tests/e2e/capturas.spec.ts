import { test } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import type { PedidoMes } from '../unit/auxiliar/extrato-mes';
import { arquivoPdf, extratoDoMes, extratoSintetico } from './auxiliar';

const PASTA_CAPTURAS = join(process.cwd(), 'docs/capturas/d1-design');

test.describe('Capturas visuais em 360 px (D1-Design)', () => {
  test.skip(!process.env.CAPTURAS, 'Executar somente quando CAPTURAS=1');

  test.beforeAll(() => {
    mkdirSync(PASTA_CAPTURAS, { recursive: true });
  });

  test.use({
    viewport: { width: 360, height: 800 },
    deviceScaleFactor: 1,
  });

  test('referencia.png', async ({ page }) => {
    await page.goto('/referencia.html');
    await page.waitForSelector('.ref-pagina');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 'referencia.png'),
      fullPage: true,
    });
  });

  test('t08-vazio.png', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#titulo-extratos');
    await page.waitForSelector('.estado-vazio');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 't08-vazio.png'),
      fullPage: true,
    });
  });

  test('t08-carregando.png', async ({ page }) => {
    // Retarda a rota do worker para manter o estado lendo ativo
    await page.route('**/assets/worker-*.js', () => {});
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('extrato-mensal.pdf', await extratoSintetico()));
    await page.waitForSelector('.estado-carregando');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 't08-carregando.png'),
      fullPage: true,
    });
  });

  test('t08-erro.png', async ({ page }) => {
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('extrato-danificado.pdf', Buffer.from('conteúdo sintético danificado não pdf')));
    await page.waitForSelector('.aviso-erro');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 't08-erro.png'),
      fullPage: true,
    });
  });

  test('t09-resultado.png', async ({ page }) => {
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('extrato-setembro.pdf', await extratoSintetico()));
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    await page.waitForSelector('#titulo-resultado');
    await page.waitForSelector('article.cartao');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 't09-resultado.png'),
      fullPage: true,
    });
  });

  test('t09-historico.png', async ({ page }) => {
    const AGO: PedidoMes = {
      ano: 2026,
      mes: 8,
      inicial: 100000,
      movimentos: [
        [3, 'PIX RECEBIDO PESSOA FICTICIA', 50000],
        [20, 'COMPRA MERCADO FICTICIO', -12000],
      ],
    };
    // SET com saldo inicial ligeiramente divergente para acionar o aviso de encadeamento
    const SET_DIVERGENTE: PedidoMes = {
      ano: 2026,
      mes: 9,
      inicial: 138001,
      movimentos: [
        [2, 'PIX ENVIADO LOJA FICTICIA', -5000],
        [15, 'PAGAMENTO BOLETO FICTICIO', -3010],
      ],
    };
    // NOV com outubro faltando para registrar mês faltando
    const NOV: PedidoMes = {
      ano: 2026,
      mes: 11,
      inicial: 130000,
      movimentos: [
        [5, 'PIX RECEBIDO PESSOA FICTICIA', 20000],
        [18, 'COMPRA CARTAO FICTICIO', -4000],
      ],
    };

    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', [
      arquivoPdf('extrato-ago-2026.pdf', await extratoDoMes(AGO)),
      arquivoPdf('extrato-set-2026.pdf', await extratoDoMes(SET_DIVERGENTE)),
      arquivoPdf('extrato-nov-2026.pdf', await extratoDoMes(NOV)),
    ]);
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    await page.waitForSelector('#titulo-resultado');
    await page.waitForSelector('section.cartao[aria-label^="Histórico"]');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 't09-historico.png'),
      fullPage: true,
    });
  });

  test('t99-diagnostico.png', async ({ page }) => {
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('extrato-setembro.pdf', await extratoSintetico()));
    await page.getByRole('button', { name: 'Diagnóstico' }).click();
    await page.waitForSelector('#titulo-diagnostico');
    await page.waitForSelector('tbody tr');
    await page.screenshot({
      path: join(PASTA_CAPTURAS, 't99-diagnostico.png'),
      fullPage: true,
    });
  });
});
