import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { lerExtrato } from '../../src/leitura/index.js';
import type { ResultadoArquivo } from '../../src/leitura/tipos.js';

const FIXTURES_PDFS = join(__dirname, '../fixtures/pdfs');
const FIXTURES_ESPERADO = join(__dirname, '../fixtures/esperado');

// Casos especiais que precisam de tratamento diferente
const CASOS_SENHAS: Record<string, string> = {
  'dificil-protegido-aes.pdf': 'senha-teste-123',
};

describe('Leitura de PDFs sintéticos', () => {
  // Listar todos os PDFs gerados
  const pdfFiles = readdirSync(FIXTURES_PDFS)
    .filter(f => f.endsWith('.pdf'))
    .sort();

  for (const pdfFile of pdfFiles) {
    const nomeBase = pdfFile.replace('.pdf', '');
    const expectedFile = join(FIXTURES_ESPERADO, `${nomeBase}.json`);

    it(`lê ${nomeBase}`, async () => {
      // Ler o PDF
      const pdfPath = join(FIXTURES_PDFS, pdfFile);
      const pdfBytes = new Uint8Array(readFileSync(pdfPath));

      // Ler o esperado
      const expectedData = JSON.parse(
        readFileSync(expectedFile, 'utf-8')
      ) as ResultadoArquivo;

      // Ler o PDF com a função
      const senha = CASOS_SENHAS[pdfFile];
      const resultado = await lerExtrato(pdfBytes, senha);

      // Comparar hash (importante para "mesmo arquivo duas vezes")
      if (nomeBase === 'dificil-mesmo-arquivo-duas-vezes') {
        expect(resultado.hash).toBe(expectedData.hash);
      }

      // Comparar campos obrigatórios
      expect(resultado.status).toBe(expectedData.status);
      expect(resultado.motivo).toBe(expectedData.motivo);
      expect(resultado.bancoProvavel).toBe(expectedData.bancoProvavel);
      expect(resultado.periodo).toEqual(expectedData.periodo);
      expect(resultado.paginas).toBe(expectedData.paginas);
      expect(resultado.linhasCandidatas).toBe(expectedData.linhasCandidatas);

      // Comparar lançamentos
      expect(resultado.lancamentos).toEqual(expectedData.lancamentos);

      // Comparar conferência
      expect(resultado.conferencia).toEqual(expectedData.conferencia);
    });
  }

  // Teste específico para "mesmo arquivo duas vezes" - verifica que os hashes são iguais
  it('mesmo arquivo enviado duas vezes tem hash idêntico', async () => {
    const pdfPath = join(FIXTURES_PDFS, 'dificil-mesmo-arquivo-duas-vezes.pdf');
    const pdfBytes1 = new Uint8Array(readFileSync(pdfPath));
    const pdfBytes2 = new Uint8Array(readFileSync(pdfPath));

    const resultado1 = await lerExtrato(pdfBytes1);
    const resultado2 = await lerExtrato(pdfBytes2);

    expect(resultado1.hash).toBe(resultado2.hash);
  });
});
