import { expect, test } from '@playwright/test';
import type { PedidoMes } from '../unit/auxiliar/extrato-mes';
import { arquivoPdf, extratoDoMes, nadaGuardadoNoAparelho, registrarRede, verificarSoGetDoMesmoDominio, vigiarCsp } from './auxiliar';

// Três meses encadeados (dados sintéticos): o saldo final de cada um é o inicial do seguinte.
const AGO: PedidoMes = { ano: 2026, mes: 8, inicial: 100000, movimentos: [[3, 'PIX RECEBIDO PESSOA FICTICIA', 50000], [20, 'COMPRA MERCADO FICTICIO', -12000]] };
const SET: PedidoMes = { ano: 2026, mes: 9, inicial: 138000, movimentos: [[2, 'PIX ENVIADO LOJA FICTICIA', -5000], [15, 'PAGAMENTO BOLETO FICTICIO', -3010]] };
const OUT: PedidoMes = { ano: 2026, mes: 10, inicial: 129990, movimentos: [[5, 'PIX RECEBIDO PESSOA FICTICIA', 20000], [18, 'COMPRA CARTAO FICTICIO', -4000]] };

test.describe('histórico contínuo em perfil de celular', () => {
  test('dois meses com um faltando; acrescentar o terceiro sem perder os anteriores; o mesmo arquivo não duplica', async ({ page, context }) => {
    const rede = registrarRede(context);
    const csp = vigiarCsp(page);
    await page.goto('/');

    // outubro e agosto, fora de ordem; setembro está faltando
    await page.setInputFiles('#escolher-pdf', [arquivoPdf('outubro.pdf', await extratoDoMes(OUT)), arquivoPdf('agosto.pdf', await extratoDoMes(AGO))]);
    await expect(page.locator('li')).toHaveCount(2);
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();

    const historico = page.getByLabel('Histórico 1');
    await expect(historico).toContainText('Período total');
    await expect(historico.locator('dd').nth(0)).toHaveText('03/08/2026 a 18/10/2026');
    await expect(historico.locator('dd').nth(1)).toHaveText('2');
    await expect(historico.locator('dd').nth(2)).toHaveText('08/2026, 10/2026');
    await expect(historico.locator('dd').nth(3)).toHaveText('09/2026');
    await expect(page.getByText('Ao todo: 4 lançamentos.')).toBeVisible();

    // acrescentar setembro (e depois o mesmo setembro de novo) sem perder os já lidos
    await page.getByRole('button', { name: 'Voltar aos extratos' }).click();
    await expect(page.locator('li')).toHaveCount(2);
    await expect(page.getByText('Acrescentar mais PDFs')).toBeVisible();
    const setembro = await extratoDoMes(SET);
    await page.setInputFiles('#escolher-pdf', arquivoPdf('setembro.pdf', setembro));
    await expect(page.locator('li')).toHaveCount(3);
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.setInputFiles('#escolher-pdf', arquivoPdf('setembro-de-novo.pdf', setembro));
    await expect(page.locator('li')).toHaveCount(4);
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await expect(page.getByText('Este arquivo é igual a outro já lido e não conta de novo.')).toBeVisible();
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();

    await expect(historico.locator('dd').nth(1)).toHaveText('3');
    await expect(historico.locator('dd').nth(2)).toHaveText('08/2026, 09/2026, 10/2026');
    await expect(historico.locator('dd').nth(3)).toHaveText('nenhum');
    await expect(historico).not.toContainText('encadeamento');
    await expect(page.getByText(/Ao todo: 6 lançamentos; 1 arquivo\(s\) repetido\(s\) foram ignorados\./)).toBeVisible();
    await expect(page.locator('article')).toHaveCount(4); // um cartão por arquivo enviado, como antes

    verificarSoGetDoMesmoDominio(rede);
    expect(csp).toEqual([]);
    await nadaGuardadoNoAparelho(page, context);
  });

  test('saldo que não encadeia: aviso nomeando o mês, sem valores, e os lançamentos intactos', async ({ page }) => {
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', [arquivoPdf('agosto.pdf', await extratoDoMes(AGO)), arquivoPdf('setembro.pdf', await extratoDoMes({ ...SET, inicial: 138001 }))]);
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    const aviso = page.getByLabel('Histórico 1').locator('.aviso');
    await expect(aviso).toHaveCount(1);
    await expect(aviso).toContainText('08/2026');
    await expect(aviso).not.toContainText('1.380');
    await expect(page.getByText('Ao todo: 4 lançamentos.')).toBeVisible();
  });

  test('T99: copiar a assinatura do layout, só estrutura', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('agosto.pdf', await extratoDoMes({ ...AGO, conta: 'Conta: 12345678-9', extras: ['Titular: MARIA APARECIDA FICTICIA DA SILVA'] })));
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.getByRole('button', { name: 'Diagnóstico' }).click();
    await page.getByRole('button', { name: 'Copiar assinatura do layout' }).click();
    await expect(page.getByRole('status')).toContainText('copiada');
    const copiado = await page.evaluate(() => navigator.clipboard.readText());
    expect(copiado).toContain('Colunas, da esquerda para a direita: Data | Descrição | Valor | Saldo');
    expect(copiado).toContain('Formato de data: 99/99/9999');
    expect(copiado).toContain('Formato de valor: -9,99; 9,99; 9.999,99');
    const semPosicoes = copiado.split('\n').filter((l) => !l.startsWith('Posição das colunas')).join('\n');
    expect(semPosicoes.replace(/\D/g, '')).toMatch(/^9+$/);
    for (const proibido of ['PIX', 'FICTICI', 'MARIA', 'SILVA', '12345678', '6789', '2026', '1.000,00', 'agosto']) expect(copiado, proibido).not.toContain(proibido);
  });

  test('T99: se o navegador não deixa copiar, aparece uma mensagem simples', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('negado com conteúdo')) }, configurable: true });
    });
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('agosto.pdf', await extratoDoMes(AGO)));
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.getByRole('button', { name: 'Diagnóstico' }).click();
    await page.getByRole('button', { name: 'Copiar assinatura do layout' }).click();
    await expect(page.getByRole('status')).toContainText('Não foi possível copiar');
    await expect(page.getByText('negado com conteúdo')).toHaveCount(0);
  });
});
