// Camada do PDF.js: PDFs gerados aqui, com dados fictícios, passam pela função pública `lerExtrato`.
import { describe, expect, it } from 'vitest';
import { lerExtrato } from '../../src/leitura';
import { motivoDoErro } from '../../src/leitura/extrair';
import { COLUNAS_PADRAO, pagina } from './auxiliar/montar';
import { gerarPdfComSenha } from './auxiliar/pdf-com-senha';
import { gerarPdf, gerarPdfSemTexto } from './auxiliar/pdf-sintetico';

describe('lerExtrato com PDF de verdade', () => {
  it('lê um extrato de duas páginas, com a descrição quebrada e o saldo conferido', async () => {
    const bytes = await gerarPdf([
      pagina({
        numero: 1,
        antes: ['Banco Ficticio - Extrato', 'Período: 01/09/2026 a 30/09/2026'],
        colunas: COLUNAS_PADRAO,
        linhas: [
          ['', 'SALDO ANTERIOR', '', '1.000,00'],
          ['02/09/2026', 'PIX ENVIADO PARA\nLOJA FICTICIA LTDA', '-50,00', '950,00'],
          ['05/09/2026', 'PIX RECEBIDO PESSOA FICTICIA', '200,00', '1.150,00'],
        ],
        depois: ['Página 1 de 2'],
      }),
      pagina({
        numero: 2,
        colunas: COLUNAS_PADRAO,
        linhas: [
          ['09/09/2026', 'PAGAMENTO BOLETO FICTICIO', '-30,10', '1.119,90'],
          ['', 'SALDO FINAL', '', '1.119,90'],
        ],
        depois: ['Página 2 de 2'],
      }),
    ]);
    const progresso: number[] = [];
    const r = await lerExtrato(bytes, undefined, { onProgresso: (feito) => progresso.push(feito) });
    expect(r.status).toBe('suficiente');
    expect(r.paginas).toBe(2);
    expect(r.hash).toMatch(/^[0-9a-f]{64}$/);
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao, l.descricao, l.pagina])).toEqual([
      ['2026-09-02', 5000, 'saida', 'PIX ENVIADO PARA LOJA FICTICIA LTDA', 1],
      ['2026-09-05', 20000, 'entrada', 'PIX RECEBIDO PESSOA FICTICIA', 1],
      ['2026-09-09', 3010, 'saida', 'PAGAMENTO BOLETO FICTICIO', 2],
    ]);
    expect(r.conferencia).toMatchObject({ situacao: 'fecha', saldoInicialCentavos: 100000, saldoFinalCentavos: 111990 });
    expect(progresso).toEqual([1, 2]);
    // O resultado é JSON puro: serializa e volta igual (formato do "esperado" da F3).
    expect(JSON.parse(JSON.stringify(r))).toEqual(r);
  });

  it('o mesmo PDF dá o mesmo hash e o mesmo resultado', async () => {
    const bytes = await gerarPdf([pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO', '-5,00', '']] })]);
    const [a, b] = await Promise.all([lerExtrato(bytes), lerExtrato(bytes)]);
    expect(a).toEqual(b);
  });

  it('PDF sem texto: imagem, não suportado', async () => {
    const r = await lerExtrato(await gerarPdfSemTexto());
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'imagem', lancamentos: [] });
  });

  it('bytes que não são PDF: corrompido, não suportado, sem lançar', async () => {
    const r = await lerExtrato(new TextEncoder().encode('isto não é um pdf, só texto qualquer'));
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'corrompido' });
    expect(r.mensagem).toMatch(/corrompido/);
  });

  it('arquivo acima de 30 MB: recusado antes de abrir, com mensagem', async () => {
    const r = await lerExtrato(new Uint8Array(30 * 1024 * 1024 + 1));
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'muito-grande' });
    expect(r.mensagem).toMatch(/30 MB/);
  });

  it('mais de 200 páginas: não suportado, com mensagem', async () => {
    const vazias = Array.from({ length: 201 }, (_, i) => ({ numero: i + 1, itens: [] }));
    const r = await lerExtrato(await gerarPdf(vazias));
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'muitas-paginas' });
    expect(r.mensagem).toMatch(/200/);
  });
});

describe('PDF com senha (AES-256)', () => {
  const doc = [
    pagina({
      antes: ['Período: 01/09/2026 a 30/09/2026'],
      colunas: COLUNAS_PADRAO,
      linhas: [['02/09/2026', 'PIX ENVIADO FICTICIO', '-50,00', '']],
    }),
  ];

  it('sem senha pede a senha; com a senha errada diz que errou; com a certa lê', async () => {
    const bytes = gerarPdfComSenha(doc, 'segredo-ficticio');
    expect(await lerExtrato(bytes)).toMatchObject({ status: 'nao-suportado', motivo: 'senha-necessaria' });
    expect(await lerExtrato(bytes, 'outra-senha')).toMatchObject({ status: 'nao-suportado', motivo: 'senha-incorreta' });
    const r = await lerExtrato(bytes, 'segredo-ficticio');
    expect(r.status).toBe('suficiente');
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao])).toEqual([['2026-09-02', 5000, 'saida']]);
  });
});

describe('erros do PDF.js', () => {
  it('senha pedida e senha errada são motivos próprios, para a tela pedir a senha', () => {
    expect(motivoDoErro({ name: 'PasswordException', code: 1 })).toBe('senha-necessaria');
    expect(motivoDoErro({ name: 'PasswordException', code: 2 })).toBe('senha-incorreta');
    expect(motivoDoErro({ name: 'InvalidPDFException' })).toBe('corrompido');
    expect(motivoDoErro(new Error('qualquer'))).toBe('corrompido');
  });
});
