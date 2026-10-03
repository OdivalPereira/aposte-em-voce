import { describe, expect, it } from 'vitest';
import { analisarPaginas } from '../../src/leitura';
import { COLUNAS_PADRAO, pagina, type ColunaMontagem } from './auxiliar/montar';

const H = 'a'.repeat(64);

describe('colunas-trocadas (caso da ordem)', () => {
  // Esquerda para a direita: Valor (R$), Data, Histórico, Saldo (R$).
  const colunas: ColunaMontagem[] = [
    { titulo: 'Valor (R$)', x: 100, dir: true },
    { titulo: 'Data', x: 130 },
    { titulo: 'Histórico', x: 230 },
    { titulo: 'Saldo (R$)', x: 540, dir: true },
  ];
  const montar = (saldoFinal: string) =>
    analisarPaginas(
      [
        pagina({
          colunas,
          linhas: [
            ['', '', 'SALDO ANTERIOR', '1.000,00'],
            ['-50,00', '02/09/2026', 'PIX ENVIADO LOJA FICTICIA', '950,00'],
            ['200,00', '05/09/2026', 'PIX RECEBIDO PESSOA FICTICIA', '1.150,00'],
            ['-30,10', '09/09/2026', 'PAGAMENTO BOLETO FICTICIO', '1.119,91'],
            ['', '', 'SALDO FINAL', saldoFinal],
          ],
        }),
      ],
      H,
    );

  it('lê 3 lançamentos com a direção e os valores certos', () => {
    const r = montar('1.119,91');
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao, l.descricao])).toEqual([
      ['2026-09-02', 5000, 'saida', 'PIX ENVIADO LOJA FICTICIA'],
      ['2026-09-05', 20000, 'entrada', 'PIX RECEBIDO PESSOA FICTICIA'],
      ['2026-09-09', 3010, 'saida', 'PAGAMENTO BOLETO FICTICIO'],
    ]);
    expect(r.linhasCandidatas).toBe(3);
  });

  // CONTRADIÇÃO DA ORDEM COM A SEÇÃO 5.2: 1.150,00 − 30,10 = 1.119,90, e não 1.119,91. A ordem manda esperar
  // "saldo fecha" e "leitura suficiente", mas a conta em centavos, sem tolerância, não fecha por 1 centavo
  // (a equação também: 1.000,00 + 200,00 − 80,10 = 1.119,90 ≠ 1.119,91). Não se altera lançamento nem saldo
  // para fechar. Correção do esperado pelo Gandalf (ajuste 4, Q164), pela 5.2 e pela 5.5: o saldo não fecha e o status
  // é Parcial. O teste abaixo afirma exatamente isso; a variante seguinte, com 1.119,90, fecha e é Leitura suficiente.
  it('como na ordem (saldo final 1.119,91): pela 5.2 o saldo NÃO fecha, por 1 centavo, e o status é Parcial', () => {
    const r = montar('1.119,91');
    expect(r.conferencia.situacao).toBe('nao-fecha');
    expect(r.conferencia.diferencaCentavos).toBe(1);
    expect(r.conferencia.progressao).toMatchObject({ verificadas: 3, divergentes: 1 });
    expect(r.status).toBe('parcial');
    expect(r.motivo).toBe('saldo-nao-fecha');
  });

  it('variante com os saldos aritmeticamente coerentes (1.119,90): saldo fecha e leitura suficiente', () => {
    const r = analisarPaginas(
      [
        pagina({
          colunas,
          linhas: [
            ['', '', 'SALDO ANTERIOR', '1.000,00'],
            ['-50,00', '02/09/2026', 'PIX ENVIADO LOJA FICTICIA', '950,00'],
            ['200,00', '05/09/2026', 'PIX RECEBIDO PESSOA FICTICIA', '1.150,00'],
            ['-30,10', '09/09/2026', 'PAGAMENTO BOLETO FICTICIO', '1.119,90'],
            ['', '', 'SALDO FINAL', '1.119,90'],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos).toHaveLength(3);
    expect(r.conferencia.situacao).toBe('fecha');
    expect(r.status).toBe('suficiente');
  });
});

describe('formatos de data e valor no pipeline', () => {
  it('data dd/mm sem ano: o ano vem do período do documento', () => {
    const r = analisarPaginas(
      [
        pagina({
          antes: ['Extrato de conta', 'Período: 01/09/2026 a 30/09/2026'],
          colunas: COLUNAS_PADRAO,
          linhas: [
            ['02/09', 'PIX ENVIADO MERCADO FICTICIO', '-50,00', ''],
            ['12/09', 'PIX RECEBIDO AMIGO FICTICIO', '120,00', ''],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => l.data)).toEqual(['2026-09-02', '2026-09-12']);
    expect(r.conferencia.situacao).toBe('indisponivel');
    expect(r.status).toBe('suficiente');
    expect(r.periodo).toEqual({ inicio: '2026-09-02', fim: '2026-09-12' });
  });

  it('data "12 SET" e valores com R$, D e sinal', () => {
    const r = analisarPaginas(
      [
        pagina({
          antes: ['Período de 01/09/2026 até 30/09/2026'],
          colunas: COLUNAS_PADRAO,
          linhas: [
            ['12 SET', 'COMPRA FICTICIA UM', 'R$ 1.234,56 D', ''],
            ['13 SET', 'TRANSFERENCIA FICTICIA', '-R$ 10,00', ''],
            ['14 SET', 'DEPOSITO FICTICIO', '+R$ 2.000,00', ''],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao])).toEqual([
      ['2026-09-12', 123456, 'saida'],
      ['2026-09-13', 1000, 'saida'],
      ['2026-09-14', 200000, 'entrada'],
    ]);
  });

  it('sem ano em lugar nenhum: não inventa, a linha fica não lida e o status é parcial', () => {
    const r = analisarPaginas([pagina({ colunas: COLUNAS_PADRAO, linhas: [['02/09', 'PIX ENVIADO FICTICIO UM', '-50,00', ''], ['03/09', 'PIX ENVIADO FICTICIO DOIS', '-10,00', '']] })], H);
    expect(r.lancamentos).toHaveLength(0);
    expect(r.linhasCandidatas).toBe(2);
    expect(r.status).toBe('nao-suportado');
  });

  it('horário na célula da data vira hora; sem horário, hora é nula', () => {
    const r = analisarPaginas(
      [
        pagina({
          antes: ['01/09/2026 a 30/09/2026'],
          colunas: COLUNAS_PADRAO,
          linhas: [
            ['02/09/2026 14:35', 'PIX ENVIADO FICTICIO', '-50,00', ''],
            ['03/09/2026', 'PIX ENVIADO FICTICIO', '-50,00', ''],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => l.hora)).toEqual(['14:35', null]);
  });
});

describe('direção', () => {
  it('colunas separadas de crédito e débito', () => {
    const cols: ColunaMontagem[] = [
      { titulo: 'Data', x: 40 },
      { titulo: 'Histórico', x: 110 },
      { titulo: 'Crédito', x: 400, dir: true },
      { titulo: 'Débito', x: 470, dir: true },
      { titulo: 'Saldo', x: 545, dir: true },
    ];
    const r = analisarPaginas(
      [
        pagina({
          colunas: cols,
          linhas: [
            ['', 'SALDO ANTERIOR', '', '', '500,00'],
            ['02/09/2026', 'DEPOSITO FICTICIO', '100,00', '', '600,00'],
            ['03/09/2026', 'SAQUE FICTICIO', '', '40,00', '560,00'],
            ['', 'SALDO FINAL', '', '', '560,00'],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => [l.valorCentavos, l.direcao])).toEqual([
      [10000, 'entrada'],
      [4000, 'saida'],
    ]);
    expect(r.conferencia.situacao).toBe('fecha');
    expect(r.status).toBe('suficiente');
  });

  it('coluna C/D com valores sem sinal', () => {
    const cols: ColunaMontagem[] = [
      { titulo: 'Data', x: 40 },
      { titulo: 'Histórico', x: 110 },
      { titulo: 'Valor', x: 420, dir: true },
      { titulo: 'D/C', x: 450 },
    ];
    const r = analisarPaginas(
      [
        pagina({
          antes: ['01/09/2026 a 30/09/2026'],
          colunas: cols,
          linhas: [
            ['02/09/2026', 'DEPOSITO FICTICIO', '100,00', 'C'],
            ['03/09/2026', 'SAQUE FICTICIO', '40,00', 'D'],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => l.direcao)).toEqual(['entrada', 'saida']);
    expect(r.status).toBe('suficiente');
  });

  it('valores sem nenhum sinal nem coluna de direção: ambígua, sem chutar a direção', () => {
    const r = analisarPaginas(
      [pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO UM', '50,00', ''], ['03/09/2026', 'PIX FICTICIO DOIS', '10,00', '']] })],
      H,
    );
    expect(r.lancamentos).toHaveLength(0);
    expect(r.status).toBe('ambigua');
    expect(r.motivo).toBe('direcao-incerta');
  });

  it('valor sem marca vale entrada quando o documento marca as saídas com "-"', () => {
    const r = analisarPaginas(
      [pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO UM', '50,00', ''], ['03/09/2026', 'PIX FICTICIO DOIS', '-10,00', '']] })],
      H,
    );
    expect(r.lancamentos.map((l) => l.direcao)).toEqual(['entrada', 'saida']);
  });
});

describe('reconstrução', () => {
  it('descrição quebrada em duas linhas é juntada; cabeçalho repetido e rodapé são descartados', () => {
    const r = analisarPaginas(
      [
        pagina({
          numero: 1,
          antes: ['Período: 01/09/2026 a 30/09/2026'],
          colunas: COLUNAS_PADRAO,
          linhas: [
            ['02/09/2026', 'PIX ENVIADO PARA\nLOJA FICTICIA LTDA', '-50,00', '950,00'],
            ['03/09/2026', 'COMPRA NO DEBITO', '-20,00', '930,00'],
          ],
          depois: ['Página 1 de 2'],
        }),
        pagina({
          numero: 2,
          colunas: COLUNAS_PADRAO,
          linhas: [['04/09/2026', 'PIX RECEBIDO FICTICIO', '70,00', '1.000,00']],
          depois: ['Página 2 de 2'],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => l.descricao)).toEqual(['PIX ENVIADO PARA LOJA FICTICIA LTDA', 'COMPRA NO DEBITO', 'PIX RECEBIDO FICTICIO']);
    expect(r.lancamentos.map((l) => l.pagina)).toEqual([1, 1, 2]);
    expect(r.linhasCandidatas).toBe(3);
    expect(r.conferencia.progressao).toMatchObject({ verificadas: 2, divergentes: 0 });
    expect(r.status).toBe('suficiente');
  });

  it('cabeçalho só na primeira página: as colunas valem nas seguintes', () => {
    const r = analisarPaginas(
      [
        pagina({ numero: 1, antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO UM', '-50,00', '']] }),
        pagina({ numero: 2, cabecalho: false, colunas: COLUNAS_PADRAO, linhas: [['03/09/2026', 'PIX FICTICIO DOIS', '-10,00', '']] }),
      ],
      H,
    );
    expect(r.lancamentos).toHaveLength(2);
  });

  it('data em título de grupo vale para as linhas seguintes sem data', () => {
    const cols: ColunaMontagem[] = [
      { titulo: 'Descrição', x: 40 },
      { titulo: 'Valor', x: 400, dir: true },
    ];
    const r = analisarPaginas(
      [
        pagina({
          antes: ['Período: 01/09/2026 a 30/09/2026'],
          colunas: cols,
          linhas: [['02 SET 2026', ''], ['PIX ENVIADO FICTICIO', '-50,00'], ['PIX RECEBIDO FICTICIO', '+80,00'], ['03 SET 2026', ''], ['COMPRA FICTICIA', '-5,00']],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao])).toEqual([
      ['2026-09-02', 5000, 'saida'],
      ['2026-09-02', 8000, 'entrada'],
      ['2026-09-03', 500, 'saida'],
    ]);
  });

  it('sem cabeçalho e com um valor por linha: lê pelo conteúdo', () => {
    const itens = pagina({ colunas: [{ titulo: 'x', x: 40 }, { titulo: 'y', x: 130 }, { titulo: 'z', x: 430, dir: true }], cabecalho: false, antes: ['Extrato 01/09/2026 a 30/09/2026'], linhas: [['02/09/2026', 'PIX ENVIADO FICTICIO', '-50,00'], ['03/09/2026', 'PIX RECEBIDO FICTICIO', '+10,00']] });
    const r = analisarPaginas([itens], H);
    expect(r.lancamentos).toHaveLength(2);
    expect(r.status).toBe('suficiente');
  });

  it('saldo por linha em ordem decrescente (mais novo primeiro) também confere', () => {
    const r = analisarPaginas(
      [
        pagina({
          antes: ['01/09/2026 a 30/09/2026'],
          colunas: COLUNAS_PADRAO,
          linhas: [
            ['05/09/2026', 'PIX RECEBIDO FICTICIO', '200,00', '1.150,00'],
            ['02/09/2026', 'PIX ENVIADO FICTICIO', '-50,00', '950,00'],
            ['', 'SALDO FINAL', '', '1.150,00'],
          ],
        }),
      ],
      H,
    );
    expect(r.conferencia.progressao).toMatchObject({ ordem: 'inversa', divergentes: 0 });
    expect(r.conferencia.situacao).toBe('fecha');
  });
});

describe('conferência de saldo (5.2)', () => {
  const base = (valor: string, saldoFinal: string) =>
    analisarPaginas(
      [
        pagina({
          antes: ['01/09/2026 a 30/09/2026'],
          colunas: COLUNAS_PADRAO,
          linhas: [
            ['', 'SALDO ANTERIOR', '', '100,00'],
            ['02/09/2026', 'PIX ENVIADO FICTICIO', valor, ''],
            ['', 'SALDO FINAL', '', saldoFinal],
          ],
        }),
      ],
      H,
    );

  it('saldo inicial + entradas − saídas = saldo final fecha', () => {
    const r = base('-40,00', '60,00');
    expect(r.conferencia).toMatchObject({ situacao: 'fecha', diferencaCentavos: 0, entradasCentavos: 0, saidasCentavos: 4000 });
    expect(r.status).toBe('suficiente');
  });

  it('um centavo de diferença não fecha (sem tolerância) e o lançamento não é alterado', () => {
    const r = base('-40,00', '60,01');
    expect(r.conferencia.situacao).toBe('nao-fecha');
    expect(r.conferencia.diferencaCentavos).toBe(1);
    expect(r.lancamentos[0]?.valorCentavos).toBe(4000);
    expect(r.status).toBe('parcial');
  });

  it('sem saldos: conferência indisponível, e ainda assim leitura suficiente', () => {
    const r = analisarPaginas([pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX ENVIADO FICTICIO', '-40,00', '']] })], H);
    expect(r.conferencia.situacao).toBe('indisponivel');
    expect(r.conferencia.saldoInicialCentavos).toBeNull();
    expect(r.status).toBe('suficiente');
  });

  it('linha ilegível entre as válidas: a razão cai abaixo de 95% e o status é parcial', () => {
    const linhas = Array.from({ length: 9 }, (_, i) => [`0${i + 1}/09/2026`, `COMPRA FICTICIA ${i + 1}`, '-10,00', '']);
    linhas.push(['10/09/2026', 'COMPRA FICTICIA 10', '??', '']);
    const r = analisarPaginas([pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas })], H);
    expect(r.linhasCandidatas).toBe(10);
    expect(r.lancamentos).toHaveLength(9);
    expect(r.status).toBe('parcial');
    expect(r.motivo).toBe('linhas-nao-lidas');
  });
});

describe('casos fora do suporte (5.4)', () => {
  it('PDF sem texto útil: imagem', () => {
    const r = analisarPaginas([{ numero: 1, itens: [] }], H, 1);
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'imagem', lancamentos: [] });
    expect(r.mensagem).toBe('Este arquivo é uma imagem; nesta versão lemos só PDFs baixados do banco.');
  });

  it('fatura de cartão', () => {
    const r = analisarPaginas(
      [pagina({ antes: ['Fatura fechada do cartão', 'Total da fatura R$ 300,00', 'Pagamento mínimo R$ 45,00', 'Data de vencimento 10/10/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'COMPRA FICTICIA', '-50,00', '']] })],
      H,
    );
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'fatura-cartao' });
    expect(r.mensagem).toBe('Parece fatura de cartão; nesta versão lemos extratos de conta.');
  });

  it('texto que não é extrato: sem lançamentos, não suportado', () => {
    const r = analisarPaginas([pagina({ antes: ['Este é um documento qualquer sem tabela de movimentações, apenas texto corrido.'], colunas: COLUNAS_PADRAO, linhas: [] })], H);
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'sem-lancamentos' });
  });
});

describe('banco provável', () => {
  it('é só uma etiqueta pelas palavras do texto; sem palavra, nulo', () => {
    const com = analisarPaginas([pagina({ antes: ['Mercado Pago', '01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO', '-1,00', '']] })], H);
    const sem = analisarPaginas([pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO', '-1,00', '']] })], H);
    expect(com.bancoProvavel).toBe('Mercado Pago');
    expect(sem.bancoProvavel).toBeNull();
  });
});

describe('outros desenhos de tabela (genérico, sem parser por banco)', () => {
  it('coluna de número de documento é ignorada; saldo com C/D e valor com D', () => {
    const cols: ColunaMontagem[] = [
      { titulo: 'Data Mov.', x: 40 },
      { titulo: 'Nr. Doc.', x: 105 },
      { titulo: 'Histórico', x: 170 },
      { titulo: 'Valor', x: 460, dir: true },
      { titulo: 'Saldo', x: 545, dir: true },
    ];
    const r = analisarPaginas(
      [
        pagina({
          antes: ['Período: 01/09/2026 a 30/09/2026'],
          colunas: cols,
          linhas: [
            ['01/09/2026', '000000', 'SALDO ANTERIOR', '', '100,00 C'],
            ['02/09/2026', '000123', 'PIX ENVIADO FICTICIO', '150,00 D', '50,00 D'],
            ['03/09/2026', '000124', 'DEPOSITO FICTICIO', '250,00 C', '200,00 C'],
            ['', '', 'SALDO FINAL', '', '200,00 C'],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => [l.descricao, l.valorCentavos, l.direcao, l.saldoCentavos])).toEqual([
      ['PIX ENVIADO FICTICIO', 15000, 'saida', -5000],
      ['DEPOSITO FICTICIO', 25000, 'entrada', 20000],
    ]);
    expect(r.conferencia.situacao).toBe('fecha');
    expect(r.status).toBe('suficiente');
  });

  it('colunas de entradas e saídas com traço no lado vazio e linhas com saldo do dia ignoradas', () => {
    const cols: ColunaMontagem[] = [
      { titulo: 'Data', x: 40 },
      { titulo: 'Descrição', x: 110 },
      { titulo: 'Entradas', x: 400, dir: true },
      { titulo: 'Saídas', x: 470, dir: true },
      { titulo: 'Saldo', x: 545, dir: true },
    ];
    const r = analisarPaginas(
      [
        pagina({
          antes: ['Período: 01/09/2026 a 30/09/2026'],
          colunas: cols,
          linhas: [
            ['02/09/2026', 'DEPOSITO FICTICIO', '100,00', '-', ''],
            ['02/09/2026', 'COMPRA FICTICIA', '-', '25,50', ''],
            ['', 'SALDO DO DIA', '', '', '74,50'],
            ['', 'Total de entradas 100,00', '', '', ''],
          ],
        }),
      ],
      H,
    );
    expect(r.lancamentos.map((l) => [l.valorCentavos, l.direcao])).toEqual([
      [10000, 'entrada'],
      [2550, 'saida'],
    ]);
    expect(r.linhasCandidatas).toBe(2);
    expect(r.status).toBe('suficiente');
  });

  it('sem cabeçalho e com dois valores por linha (valor e saldo): só a conferência aritmética confirma as colunas', () => {
    const cols = [{ titulo: 'a', x: 40 }, { titulo: 'b', x: 120 }, { titulo: 'c', x: 430, dir: true }, { titulo: 'd', x: 540, dir: true }];
    const bom = analisarPaginas([pagina({ cabecalho: false, antes: ['01/09/2026 a 30/09/2026'], colunas: cols, linhas: [['02/09/2026', 'PIX FICTICIO UM', '-50,00', '950,00'], ['03/09/2026', 'PIX FICTICIO DOIS', '+10,00', '960,00']] })], H);
    expect(bom.conferencia.situacao).toBe('fecha');
    expect(bom.status).toBe('suficiente');
    const ruim = analisarPaginas([pagina({ cabecalho: false, antes: ['01/09/2026 a 30/09/2026'], colunas: cols, linhas: [['02/09/2026', 'PIX FICTICIO UM', '-50,00', '950,00'], ['03/09/2026', 'PIX FICTICIO DOIS', '+10,00', '999,00']] })], H);
    expect(ruim.status).toBe('ambigua');
    expect(ruim.motivo).toBe('colunas-incertas');
  });
});
