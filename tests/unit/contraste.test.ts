import { describe, expect, it } from 'vitest';
import {
  atendeWCAGAA,
  formataRazao,
  luminanciaRelativa,
  normalizarHex,
  razaoContraste,
} from '../../src/ui/contraste';
import { CORES, PARES_CONTRASTE } from '../../src/ui/tokens';

describe('Cálculo de luminância e contraste WCAG 2.2', () => {
  it('normaliza cores hexadecimais de 3 e 6 dígitos', () => {
    expect(normalizarHex('#fff')).toEqual([255, 255, 255]);
    expect(normalizarHex('#000000')).toEqual([0, 0, 0]);
    expect(normalizarHex(' #0b4f9c ')).toEqual([11, 79, 156]);
  });

  it('rejeita cores hexadecimais inválidas', () => {
    expect(() => normalizarHex('#12')).toThrow('Código hex inválido');
    expect(() => normalizarHex('#gggggg')).toThrow('Componente de cor inválido');
  });

  it('calcula a luminância relativa dos extremos conhecidos', () => {
    expect(luminanciaRelativa('#000000')).toBe(0);
    expect(luminanciaRelativa('#ffffff')).toBe(1);
  });

  it('calcula o contraste dos extremos conhecidos', () => {
    expect(razaoContraste('#ffffff', '#000000')).toBeCloseTo(21, 1);
    expect(razaoContraste('#ffffff', '#ffffff')).toBeCloseTo(1, 2);
  });

  it('valida o critério de sucesso WCAG AA', () => {
    expect(atendeWCAGAA(4.5, 'texto-normal')).toBe(true);
    expect(atendeWCAGAA(4.49, 'texto-normal')).toBe(false);
    expect(atendeWCAGAA(3.0, 'componente-ui')).toBe(true);
    expect(atendeWCAGAA(2.99, 'componente-ui')).toBe(false);
    expect(atendeWCAGAA(3.0, 'texto-grande')).toBe(true);
  });
});

describe('Contraste de cada par declarado nos tokens (WCAG 2.2 AA)', () => {
  for (const par of PARES_CONTRASTE) {
    it(`par "${par.id}": ${par.descricao} (${par.frente} em ${par.fundo}) atende mínimo de ${par.minimoEsperado}:1`, () => {
      const razao = razaoContraste(par.frente, par.fundo);
      const atende = atendeWCAGAA(razao, par.tipo);

      expect(
        atende,
        `Contraste insuficiente para "${par.id}": obtido ${formataRazao(razao)}, esperado >= ${par.minimoEsperado}:1`
      ).toBe(true);

      expect(razao).toBeGreaterThanOrEqual(par.minimoEsperado);
    });
  }
});

describe('Verificação das cores semânticas fundamentais', () => {
  it('garante que o texto principal tem contraste superior a 7:1 (AAA) em superfícies brancas', () => {
    const razao = razaoContraste(CORES.texto, CORES.superficie);
    expect(razao).toBeGreaterThanOrEqual(7.0);
  });

  it('garante que o texto secundário cumpre pelo menos 4.5:1 em todas as superfícies aplicáveis', () => {
    expect(razaoContraste(CORES.textoSecundario, CORES.fundo)).toBeGreaterThanOrEqual(4.5);
    expect(razaoContraste(CORES.textoSecundario, CORES.superficie)).toBeGreaterThanOrEqual(4.5);
  });

  it('garante que o foco visual e controles cumprem pelo menos 3:1 (SC 1.4.11 / 2.4.11)', () => {
    expect(razaoContraste(CORES.foco, CORES.superficie)).toBeGreaterThanOrEqual(3.0);
    expect(razaoContraste(CORES.borda, CORES.superficie)).toBeGreaterThanOrEqual(3.0);
  });
});
