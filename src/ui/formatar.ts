export function dataBr(isoData: string): string {
  const [a, m, d] = isoData.split('-');
  return `${d}/${m}/${a}`;
}

export function reais(centavos: number): string {
  const neg = centavos < 0;
  const abs = Math.abs(centavos);
  const inteiro = String(Math.floor(abs / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${neg ? '-' : ''}R$ ${inteiro},${String(abs % 100).padStart(2, '0')}`;
}
