import { expect, test } from '@playwright/test';
import { gerarPdfComSenha } from '../unit/auxiliar/pdf-com-senha';
import { gerarPdfSemTexto } from '../unit/auxiliar/pdf-sintetico';
import { COLUNAS_PADRAO, pagina } from '../unit/auxiliar/montar';
import { arquivoPdf, extratoSintetico, nadaGuardadoNoAparelho, registrarRede, verificarSoGetDoMesmoDominio, vigiarCsp } from './auxiliar';

test.describe('jornada de leitura (T08, T09, T99) em perfil de celular', () => {
  test('sem PDF: segue sem extrato e o PDF.js nem é baixado', async ({ page, context }) => {
    const rede = registrarRede(context);
    const csp = vigiarCsp(page);
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Extratos (opcional)' })).toBeVisible();
    await page.getByRole('button', { name: 'Continuar sem extrato' }).click();
    await expect(page.getByRole('heading', { name: 'Resultado da leitura' })).toBeVisible();
    await expect(page.getByText('Nenhum extrato lido')).toBeVisible();
    verificarSoGetDoMesmoDominio(rede);
    expect(rede.filter((r) => /pdf|worker/i.test(r.url))).toEqual([]);
    expect(csp).toEqual([]);
    await nadaGuardadoNoAparelho(page, context);
  });

  test('um PDF: leitura no aparelho, T09 com o resultado, T99 sem valores, e a rede só tem GET do mesmo domínio', async ({ page, context }) => {
    const rede = registrarRede(context);
    const csp = vigiarCsp(page);
    const resposta = await page.goto('/');
    // O teste roda sob a CSP e os cabeçalhos de vercel.json (repetidos pelo servidor de pré-visualização).
    const cabecalhos = resposta?.headers() ?? {};
    expect(cabecalhos['content-security-policy']).toContain("script-src 'self'; worker-src 'self' blob:");
    expect(cabecalhos['content-security-policy']).not.toContain('wasm-unsafe-eval');
    expect(cabecalhos['referrer-policy']).toBe('no-referrer');
    expect(cabecalhos['x-content-type-options']).toBe('nosniff');
    expect(rede.filter((r) => /pdf|worker/i.test(r.url))).toEqual([]); // o PDF.js só vem ao escolher um PDF

    await page.setInputFiles('#escolher-pdf', arquivoPdf('extrato-ficticio.pdf', await extratoSintetico()));
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();

    await expect(page.getByRole('heading', { name: 'Resultado da leitura' })).toBeVisible();
    const cartao = page.locator('article');
    await expect(cartao).toContainText('extrato-ficticio.pdf');
    await expect(cartao.locator('dd').nth(1)).toHaveText('02/09/2026 a 15/09/2026'); // período
    await expect(cartao.locator('dd').nth(2)).toHaveText('4'); // lançamentos lidos
    await expect(cartao).toContainText('o saldo confere');
    await expect(cartao).toContainText('Leitura suficiente');
    await expect(page.getByText('Ao todo: 4 lançamentos.')).toBeVisible();

    await page.getByRole('button', { name: 'Diagnóstico' }).click();
    await expect(page.getByRole('heading', { name: 'Diagnóstico da leitura' })).toBeVisible();
    const linha = page.locator('tbody tr');
    await expect(linha).toContainText('Arquivo 1');
    await expect(linha.locator('td').nth(0)).toHaveText('1'); // páginas
    await expect(linha.locator('td').nth(2)).toHaveText('4'); // lançamentos reconstruídos
    const texto = await page.locator('main').innerText();
    for (const proibido of ['PIX', 'FICTICI', 'extrato-ficticio', '50,00', '200,00', '30,10', '1.119', 'R$']) expect(texto).not.toContain(proibido);

    // Rede: só GET do mesmo domínio; o PDF.js e o worker vieram do próprio site, depois da escolha do PDF.
    verificarSoGetDoMesmoDominio(rede);
    expect(rede.some((r) => /pdf/i.test(r.url))).toBe(true);
    expect(csp).toEqual([]); // sob a CSP de vercel.json, sem 'wasm-unsafe-eval'
    await nadaGuardadoNoAparelho(page, context);
  });

  test('dois PDFs de períodos sobrepostos e o mesmo arquivo reenviado: nada duplica', async ({ page, context }) => {
    const rede = registrarRede(context);
    await page.goto('/');
    const bytesA = await extratoSintetico({ corte: 'inicio' }); // os mesmos bytes (mesmo hash) no reenvio
    await page.setInputFiles('#escolher-pdf', [arquivoPdf('a.pdf', bytesA), arquivoPdf('b.pdf', await extratoSintetico({ corte: 'fim' }))]);
    await expect(page.locator('li')).toHaveCount(2);
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.setInputFiles('#escolher-pdf', arquivoPdf('a-de-novo.pdf', bytesA));
    await expect(page.locator('li')).toHaveCount(3);
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    // a: 3 lançamentos (02, 05, 09/09); b: 2 (09 e 15/09); a repetido ignorado. O de 09/09 aparece nos dois extratos.
    await expect(page.getByText(/Ao todo: 4 lançamentos, 1 aparecem em dois extratos e contam uma vez só; 1 arquivo\(s\) repetido\(s\) foram ignorados\./)).toBeVisible();
    verificarSoGetDoMesmoDominio(rede);
  });

  test('PDF só de imagem: mensagem clara e a jornada continua sem o arquivo', async ({ page }) => {
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('escaneado.pdf', Buffer.from(await gerarPdfSemTexto())));
    await expect(page.getByText('Este arquivo é uma imagem; nesta versão lemos só PDFs baixados do banco.')).toBeVisible();
    await page.getByRole('button', { name: 'Seguir sem este arquivo' }).click();
    await expect(page.locator('li')).toHaveCount(0);
    await page.getByRole('button', { name: 'Continuar sem extrato' }).click();
    await expect(page.getByText('Nenhum extrato lido')).toBeVisible();
  });

  test('arquivo corrompido: mensagem clara', async ({ page }) => {
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('quebrado.pdf', Buffer.from('isto não é um pdf, apenas texto qualquer')));
    await expect(page.getByText(/Não conseguimos abrir este arquivo/)).toBeVisible();
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    await expect(page.locator('article')).toContainText('Não suportado');
  });

  test('PDF com senha: pede a senha, recusa a errada, lê com a certa; a senha não sai do aparelho', async ({ page, context }) => {
    const rede = registrarRede(context);
    const doc = gerarPdfComSenha(
      [pagina({ antes: ['Período: 01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX ENVIADO FICTICIO', '-50,00', '']] })],
      'segredo-ficticio',
    );
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('protegido.pdf', Buffer.from(doc)));
    await expect(page.getByText(/Este PDF tem senha/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeDisabled();

    await page.getByLabel(/Senha do PDF/).fill('errada');
    await page.getByRole('button', { name: 'Ler com a senha' }).click();
    await expect(page.getByText(/A senha não abriu o arquivo/)).toBeVisible();

    await page.getByLabel(/Senha do PDF/).fill('segredo-ficticio');
    await page.getByRole('button', { name: 'Ler com a senha' }).click();
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    await expect(page.locator('article')).toContainText('Leitura suficiente');
    verificarSoGetDoMesmoDominio(rede);
    expect(rede.some((r) => r.url.includes('segredo'))).toBe(false);
  });

  test('falhas na leitura nunca travam a jornada (princípio 8)', async ({ page }) => {
    await test.step('worker que não carrega: o item termina como não suportado e pode ser pulado', async () => {
      await page.route('**/assets/worker-*.js', (rota) => rota.abort());
      await page.goto('/');
      await page.setInputFiles('#escolher-pdf', arquivoPdf('qualquer.pdf', await extratoSintetico()));
      await expect(page.getByText(/Não conseguimos abrir este arquivo/)).toBeVisible();
      await expect(page.getByText('Abrindo o arquivo…')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeEnabled();
      await page.getByRole('button', { name: 'Seguir sem este arquivo' }).click();
      await expect(page.locator('li')).toHaveCount(0);
      await page.getByRole('button', { name: 'Continuar sem extrato' }).click();
      await expect(page.getByText('Nenhum extrato lido')).toBeVisible();
    });

    await test.step('worker que nunca responde: o item "lendo" também pode ser pulado', async () => {
      await page.unroute('**/assets/worker-*.js');
      await page.route('**/assets/worker-*.js', () => {}); // a requisição fica pendurada de propósito
      await page.goto('/');
      await page.setInputFiles('#escolher-pdf', arquivoPdf('pendurado.pdf', await extratoSintetico()));
      await expect(page.getByText('Abrindo o arquivo…')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Ver o resultado da leitura' })).toBeDisabled();
      await page.getByRole('button', { name: 'Seguir sem este arquivo' }).click();
      await expect(page.locator('li')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Continuar sem extrato' })).toBeEnabled();
    });
  });

  test('arquivo que o navegador não consegue ler: não suportado, sem vazar o erro, e pode ser pulado', async ({ page }) => {
    await page.addInitScript(() => {
      const original = Blob.prototype.arrayBuffer;
      Blob.prototype.arrayBuffer = function (this: Blob) {
        if ((this as File).name === 'ilegivel.pdf') return Promise.reject(new Error('erro interno com conteúdo'));
        return original.call(this);
      };
    });
    await page.goto('/');
    await page.setInputFiles('#escolher-pdf', arquivoPdf('ilegivel.pdf', await extratoSintetico()));
    await expect(page.getByText(/Não conseguimos abrir este arquivo/)).toBeVisible();
    await expect(page.getByText('erro interno')).toHaveCount(0);
    await page.getByRole('button', { name: 'Ver o resultado da leitura' }).click();
    await expect(page.locator('article')).toContainText('Não suportado');
    await page.getByRole('button', { name: 'Voltar aos extratos' }).click();
    await page.getByRole('button', { name: 'Seguir sem este arquivo' }).click();
    await expect(page.locator('li')).toHaveCount(0);
  });

  test('alvos de toque de 44 px ou mais nos botões', async ({ page }) => {
    await page.goto('/');
    for (const botao of await page.locator('button, label.botao').all()) {
      const caixa = await botao.boundingBox();
      expect(caixa?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  });

  test('foco visível por teclado (WCAG 2.4.7) no botão de escolher PDF em vazio e com arquivos', async ({ page }) => {
    await page.goto('/');

    const labelVazio = page.locator('label[for="escolher-pdf"]');
    const inputArquivo = page.locator('#escolher-pdf');

    // Antes do foco, o label não exibe anel de foco
    const outlineInicial = await labelVazio.evaluate((el) => {
      const s = window.getComputedStyle(el);
      return { width: s.outlineWidth, style: s.outlineStyle };
    });
    expect(outlineInicial.style === 'none' || outlineInicial.width === '0px').toBe(true);

    // Navega via teclado com Tab até o campo de arquivo
    await page.keyboard.press('Tab');
    await expect(inputArquivo).toBeFocused();

    // Com o input focado por teclado, o label visível deve exibir outline de 3px solid var(--cor-foco)
    const estiloFocoVazio = await labelVazio.evaluate((el) => {
      const s = window.getComputedStyle(el);
      return {
        width: s.outlineWidth,
        style: s.outlineStyle,
        color: s.outlineColor,
        offset: s.outlineOffset,
      };
    });
    expect(estiloFocoVazio.width).toBe('3px');
    expect(estiloFocoVazio.style).toBe('solid');
    expect(estiloFocoVazio.color).toBe('rgb(11, 79, 156)');
    expect(estiloFocoVazio.offset).toBe('2px');

    // Adiciona um arquivo PDF para testar T08 no estado com arquivos
    await page.setInputFiles('#escolher-pdf', arquivoPdf('extrato-ficticio.pdf', await extratoSintetico()));
    const labelComArquivos = page.locator('label[for="escolher-pdf"]');
    await expect(labelComArquivos).toHaveText('Acrescentar mais PDFs');

    // Pressiona Tab para navegar na interface com arquivos
    // Primeiro elemento focável na página é o input de acrescentar arquivos
    await page.locator('#titulo-extratos').click(); // desfoca para reiniciar a navegação a partir do topo
    await page.keyboard.press('Tab');
    await expect(inputArquivo).toBeFocused();

    const estiloFocoComArquivos = await labelComArquivos.evaluate((el) => {
      const s = window.getComputedStyle(el);
      return {
        width: s.outlineWidth,
        style: s.outlineStyle,
        color: s.outlineColor,
        offset: s.outlineOffset,
      };
    });
    expect(estiloFocoComArquivos.width).toBe('3px');
    expect(estiloFocoComArquivos.style).toBe('solid');
    expect(estiloFocoComArquivos.color).toBe('rgb(11, 79, 156)');
    expect(estiloFocoComArquivos.offset).toBe('2px');

    // Testa também em viewport de 320 px (critérios C07 foco, C08 toque e C09 reflow)
    await page.setViewportSize({ width: 320, height: 640 });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(320);

    const caixa320 = await labelComArquivos.boundingBox();
    expect(caixa320?.height ?? 0).toBeGreaterThanOrEqual(44);

    // Ao navegar com Tab para o próximo botão ("Seguir sem este arquivo"), o outline sai do label
    await page.keyboard.press('Tab');
    const outlineAposDesfocar = await labelComArquivos.evaluate((el) => {
      const s = window.getComputedStyle(el);
      return { width: s.outlineWidth, style: s.outlineStyle };
    });
    expect(outlineAposDesfocar.style === 'none' || outlineAposDesfocar.width === '0px').toBe(true);
  });
});

