/**
 * Cálculo determinístico de luminância e razão de contraste segundo WCAG 2.1 / 2.2.
 * Fórmula W3C:
 * L = 0.2126 * R + 0.7152 * G + 0.0722 * B
 * Razão = (L1 + 0.05) / (L2 + 0.05) onde L1 >= L2
 */

export function normalizarHex(hex: string): [number, number, number] {
  const limpo = hex.replace('#', '').trim();
  let rStr: string;
  let gStr: string;
  let bStr: string;

  if (limpo.length === 3) {
    const c0 = limpo[0];
    const c1 = limpo[1];
    const c2 = limpo[2];
    if (!c0 || !c1 || !c2) {
      throw new Error(`Código hex inválido: "${hex}"`);
    }
    rStr = c0 + c0;
    gStr = c1 + c1;
    bStr = c2 + c2;
  } else if (limpo.length === 6) {
    rStr = limpo.slice(0, 2);
    gStr = limpo.slice(2, 4);
    bStr = limpo.slice(4, 6);
  } else {
    throw new Error(`Código hex inválido: "${hex}"`);
  }

  const r = parseInt(rStr, 16);
  const g = parseInt(gStr, 16);
  const b = parseInt(bStr, 16);

  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) {
    throw new Error(`Componente de cor inválido no hex: "${hex}"`);
  }

  return [r, g, b];
}

export function luminanciaRelativa(hex: string): number {
  const [r255, g255, b255] = normalizarHex(hex);

  const rSrgb = r255 / 255;
  const gSrgb = g255 / 255;
  const bSrgb = b255 / 255;

  const rLin = rSrgb <= 0.04045 ? rSrgb / 12.92 : Math.pow((rSrgb + 0.055) / 1.055, 2.4);
  const gLin = gSrgb <= 0.04045 ? gSrgb / 12.92 : Math.pow((gSrgb + 0.055) / 1.055, 2.4);
  const bLin = bSrgb <= 0.04045 ? bSrgb / 12.92 : Math.pow((bSrgb + 0.055) / 1.055, 2.4);

  return 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin;
}

export function razaoContraste(cor1: string, cor2: string): number {
  const l1 = luminanciaRelativa(cor1);
  const l2 = luminanciaRelativa(cor2);

  const maisClaro = Math.max(l1, l2);
  const maisEscuro = Math.min(l1, l2);

  return (maisClaro + 0.05) / (maisEscuro + 0.05);
}

export function formataRazao(razao: number): string {
  return `${razao.toFixed(2)}:1`;
}

export function atendeWCAGAA(
  razao: number,
  tipo: 'texto-normal' | 'texto-grande' | 'componente-ui'
): boolean {
  if (tipo === 'texto-normal') return razao >= 4.5;
  return razao >= 3.0; // texto-grande ou componente-ui
}
