import { describe, expect, it } from 'vitest';
import { analisarPaginas } from '../../src/leitura';
import { paginaAgrupada, type DiaAgrupado } from './auxiliar/montar';

const H = 'b'.repeat(64);

// Layout "agrupado por dia": valores sem sinal sob "Total de entradas" e "Total de saídas", cada título com o total do dia.
// Saldo: 1.000,00 + 200,00 − 50,00 − 30,10 + 125,50 − 80,00 = 1.165,40.
function dias(totalEntradasDia9 = '125,50'): DiaAgrupado[] {
  return [
    {
      data: '02 SET 2026',
      entradas: { total: '200,00', linhas: [['Transferência recebida PESSOA FICTICIA', '200,00']] },
      saidas: { total: '50,00', linhas: [['Pix enviado LOJA FICTICIA', '50,00']] },
    },
    { data: '05 SET 2026', saidas: { total: '30,10', linhas: [['Pagamento de boleto FICTICIO', '30,10']] } },
    {
      data: '09 SET 2026',
      entradas: { total: totalEntradasDia9, linhas: [['Depósito FICTICIO', '100,00'], ['Estorno COMPRA FICTICIA', '25,50']] },
      saidas: { total: '80,00', linhas: [['Compra MERCADO FICTICIO', '80,00']] },
    },
  ];
}

const montar = (d: DiaAgrupado[], saldoFinal = '1.165,40') =>
  analisarPaginas(
    [paginaAgrupada({ antes: ['Nubank - Extrato da conta', 'Período: 01/09/2026 a 30/09/2026'], saldoInicial: '1.000,00', dias: d, saldoFinal, depois: ['Página 1 de 1'] })],
    H,
  );

const ESPERADOS = [
  ['2026-09-02', 20000, 'entrada', 'Transferência recebida PESSOA FICTICIA'],
  ['2026-09-02', 5000, 'saida', 'Pix enviado LOJA FICTICIA'],
  ['2026-09-05', 3010, 'saida', 'Pagamento de boleto FICTICIO'],
  ['2026-09-09', 10000, 'entrada', 'Depósito FICTICIO'],
  ['2026-09-09', 2550, 'entrada', 'Estorno COMPRA FICTICIA'],
  ['2026-09-09', 8000, 'saida', 'Compra MERCADO FICTICIO'],
];

describe('layout agrupado por dia (direção pelo título do grupo)', () => {
  it('lê todos os lançamentos, o saldo fecha e a leitura é suficiente', () => {
    const r = montar(dias());
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao, l.descricao])).toEqual(ESPERADOS);
    expect(r.linhasCandidatas).toBe(6);
    expect(r.conferencia).toMatchObject({ situacao: 'fecha', saldoInicialCentavos: 100000, saldoFinalCentavos: 116540, entradasCentavos: 32550, saidasCentavos: 16010, diferencaCentavos: 0 });
    expect(r.status).toBe('suficiente');
    expect(r.motivo).toBeNull();
    expect(r.bancoProvavel).toBe('Nubank');
  });

  it('a estrutura registra os títulos de grupo e o formato de data "99 AAA 9999"', () => {
    const r = montar(dias());
    expect(r.estrutura?.grupos).toEqual(['Total de entradas', 'Total de saídas']);
    expect(r.estrutura?.formatosData).toEqual([]); // a data é título do dia, não célula de lançamento
    expect(r.estrutura?.formatosValor).toEqual(['9,99']);
  });

  it('variante: total do dia que não bate sai "ambígua" com aviso, nunca "suficiente", e nenhum lançamento muda', () => {
    const r = montar(dias('130,50'));
    expect(r.status).toBe('ambigua');
    expect(r.motivo).toBe('total-do-dia-diverge');
    expect(r.mensagem).toMatch(/total de algum dia não bate/);
    expect(r.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao, l.descricao])).toEqual(ESPERADOS);
    expect(r.conferencia.situacao).toBe('fecha'); // o saldo continua o que o documento diz; nada é alterado para fechar
  });

  it('variante: total de saídas do dia que não bate também não é "suficiente"', () => {
    const d = dias();
    (d[2] as DiaAgrupado).saidas = { total: '90,00', linhas: [['Compra MERCADO FICTICIO', '80,00']] };
    const r = montar(d);
    expect(r.status).not.toBe('suficiente');
    expect(r.motivo).toBe('total-do-dia-diverge');
  });

  it('saldo final que não fecha: parcial, com as direções ainda vindas do título', () => {
    const r = montar(dias(), '1.165,41');
    expect(r.status).toBe('parcial');
    expect(r.motivo).toBe('saldo-nao-fecha');
    expect(r.conferencia.diferencaCentavos).toBe(1);
    expect(r.lancamentos).toHaveLength(6);
  });

  it('título trocado num dia (o total do dia bate, mas a direção está errada): o saldo derruba para "parcial"', () => {
    const d = dias();
    (d[1] as DiaAgrupado).entradas = (d[1] as DiaAgrupado).saidas;
    delete (d[1] as DiaAgrupado).saidas;
    const r = montar(d);
    expect(r.status).toBe('parcial');
    expect(r.motivo).toBe('saldo-nao-fecha');
    expect(r.lancamentos.find((l) => l.valorCentavos === 3010)?.direcao).toBe('entrada'); // a direção vem do título; nada é "corrigido" pelo saldo
  });
});
