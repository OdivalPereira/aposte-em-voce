import { describe, expect, it } from 'vitest';
import { centavosComSinal, descricaoNormalizada, inferirAno, lerData, lerHora, lerValor } from '../../src/leitura/normalizar';

describe('lerValor', () => {
  it.each([
    ['1.234,56', 123456, null, null],
    ['-1.234,56', 123456, '-', null],
    ['−1.234,56', 123456, '-', null],
    ['1.234,56 D', 123456, null, 'D'],
    ['1.234,56D', 123456, null, 'D'],
    ['1.234,56 C', 123456, null, 'C'],
    ['R$ 1.234,56', 123456, null, null],
    ['R$1.234,56', 123456, null, null],
    ['-R$ 1.234,56', 123456, '-', null],
    ['R$ -1.234,56', 123456, '-', null],
    ['+R$ 10,00', 1000, '+', null],
    ['50,00-', 5000, '-', null],
    ['(50,00)', 5000, '-', null],
    ['0,05', 5, null, null],
    ['12.345.678,90', 1234567890, null, null],
    ['100,00', 10000, null, null],
  ])('lê %s', (texto, centavos, sinal, dc) => {
    expect(lerValor(texto)).toEqual({ centavos, sinal, dc });
  });

  it.each(['', '-', 'PIX', '1.234', '12,5', '1,234,56', '--5,00', 'R$', '10,00 20,00'])('recusa %j', (texto) => {
    expect(lerValor(texto)).toBeNull();
  });

  it('não usa ponto flutuante: 0,10 + 0,20 está em centavos exatos', () => {
    expect((lerValor('0,10')?.centavos ?? 0) + (lerValor('0,20')?.centavos ?? 0)).toBe(30);
  });

  it('saldo negativo por sinal ou por D', () => {
    expect(centavosComSinal(lerValor('1.000,00 D') as never)).toBe(-100000);
    expect(centavosComSinal(lerValor('-1.000,00') as never)).toBe(-100000);
    expect(centavosComSinal(lerValor('1.000,00') as never)).toBe(100000);
  });
});

describe('lerData', () => {
  it.each([
    ['02/09/2026', 2, 9, 2026],
    ['02/09/26', 2, 9, 2026],
    ['2/9/2026', 2, 9, 2026],
    ['02-09-2026', 2, 9, 2026],
    ['02.09.2026', 2, 9, 2026],
    ['02/09', 2, 9, null],
    ['12 SET', 12, 9, null],
    ['12 set 2026', 12, 9, 2026],
    ['12/SET', 12, 9, null],
    ['12 de setembro de 2026', 12, 9, 2026],
    ['3 MAR', 3, 3, null],
    ['5 março 2026', 5, 3, 2026],
    ['29/02/2028', 29, 2, 2028],
  ])('lê %s', (texto, dia, mes, ano) => {
    expect(lerData(texto)).toMatchObject({ dia, mes, ano });
  });

  it.each(['31/04/2026', '29/02/2026', '32/01/2026', '10/13/2026', 'PIX 02/09', '1.234,56', '10,50', ''])('recusa %j', (texto) => {
    expect(lerData(texto)).toBeNull();
  });

  it('deixa o resto (horário) para quem chamou', () => {
    expect(lerData('02/09/2026 14:35')?.resto).toBe('14:35');
    expect(lerHora('14:35')).toBe('14:35');
    expect(lerHora('9:05:10')).toBe('09:05');
    expect(lerHora('25:00')).toBeNull();
  });
});

describe('inferirAno', () => {
  const ref = (a: string, b: string) => ({
    inicio: { ano: Number(a.slice(0, 4)), mes: Number(a.slice(5, 7)), dia: Number(a.slice(8)) },
    fim: { ano: Number(b.slice(0, 4)), mes: Number(b.slice(5, 7)), dia: Number(b.slice(8)) },
  });
  it('usa o ano em que a data cai dentro do período', () => {
    expect(inferirAno(10, 9, ref('2026-09-01', '2026-09-30'))).toBe(2026);
    expect(inferirAno(28, 12, ref('2025-12-01', '2026-01-31'))).toBe(2025);
    expect(inferirAno(5, 1, ref('2025-12-01', '2026-01-31'))).toBe(2026);
  });
  it('fora do período ou sem período, não inventa', () => {
    expect(inferirAno(10, 5, ref('2026-09-01', '2026-09-30'))).toBeNull();
    expect(inferirAno(10, 9, null)).toBeNull();
  });
});

describe('descricaoNormalizada', () => {
  it('maiúsculas, sem acento nem pontuação', () => {
    expect(descricaoNormalizada('  Pix  enviado — José/Padaria Ltda. ')).toBe('PIX ENVIADO JOSE PADARIA LTDA');
  });
});
