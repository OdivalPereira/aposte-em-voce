import { describe, expect, it } from 'vitest';
import { agruparHistoricos } from '../../src/leitura';
import type { ArquivoLido } from '../../src/leitura/tipos';
import { arquivoDoMes, type PedidoMes } from './auxiliar/extrato-mes';

// Três meses encadeados: o saldo final de cada um é o inicial do seguinte.
const AGO: PedidoMes = { ano: 2026, mes: 8, inicial: 100000, movimentos: [[3, 'PIX RECEBIDO PESSOA FICTICIA', 50000], [20, 'COMPRA MERCADO FICTICIO', -12000]] }; // fecha em 138.000
const SET: PedidoMes = { ano: 2026, mes: 9, inicial: 138000, movimentos: [[2, 'PIX ENVIADO LOJA FICTICIA', -5000], [15, 'PAGAMENTO BOLETO FICTICIO', -3010]] }; // fecha em 129.990
const OUT: PedidoMes = { ano: 2026, mes: 10, inicial: 129990, movimentos: [[5, 'PIX RECEBIDO PESSOA FICTICIA', 20000], [18, 'COMPRA CARTAO FICTICIO', -4000]] };

const ago = () => arquivoDoMes('ago.pdf', AGO);
const set = (mudanca: Partial<PedidoMes> = {}) => arquivoDoMes('set.pdf', { ...SET, ...mudanca });
const out = () => arquivoDoMes('out.pdf', OUT);
const nomes = (as: ArquivoLido[]) => as.map((a) => a.nome);

describe('histórico contínuo', () => {
  it('agrupa os arquivos da mesma conta em ordem de período, mesmo enviados fora de ordem', () => {
    const { historicos, repetidos, semHistorico } = agruparHistoricos([out(), ago(), set()]);
    expect(historicos).toHaveLength(1);
    const h = historicos[0]!;
    expect(nomes(h.arquivos)).toEqual(['ago.pdf', 'set.pdf', 'out.pdf']);
    expect(h.periodo).toEqual({ inicio: '2026-08-03', fim: '2026-10-18' });
    expect(h.mesesCobertos).toEqual(['2026-08', '2026-09', '2026-10']);
    expect(h.mesesFaltando).toEqual([]);
    expect(h.avisos).toEqual([]);
    expect(h.consolidado.lancamentos).toHaveLength(6);
    expect(h.consolidado.lancamentos.map((l) => l.data)).toEqual([...h.consolidado.lancamentos.map((l) => l.data)].sort());
    expect(repetidos).toEqual([]);
    expect(semHistorico).toEqual([]);
  });

  it('meses faltando: o mês civil entre o primeiro e o último coberto sem arquivo', () => {
    const { historicos } = agruparHistoricos([out(), ago()]);
    const h = historicos[0]!;
    expect(h.mesesCobertos).toEqual(['2026-08', '2026-10']);
    expect(h.mesesFaltando).toEqual(['2026-09']);
    expect(h.avisos).toEqual([]); // sem arquivo de setembro, não há encadeamento a conferir
  });

  it('meses faltando atravessam a virada do ano', () => {
    const dez = arquivoDoMes('dez.pdf', { ano: 2026, mes: 12, inicial: 0, movimentos: [[3, 'PIX RECEBIDO FICTICIO', 1000], [5, 'TARIFA FICTICIA', -100]] });
    const mar = arquivoDoMes('mar.pdf', { ano: 2027, mes: 3, inicial: 900, movimentos: [[3, 'PIX RECEBIDO FICTICIO', 1000], [5, 'TARIFA FICTICIA', -100]] });
    const h = agruparHistoricos([mar, dez]).historicos[0]!;
    expect(h.mesesFaltando).toEqual(['2027-01', '2027-02']);
  });

  it('encadeamento fecha: saldo final do mês igual ao inicial do seguinte, sem aviso (inclusive na virada do ano)', () => {
    expect(agruparHistoricos([ago(), set(), out()]).historicos[0]!.avisos).toEqual([]);
    const dez = arquivoDoMes('dez.pdf', { ano: 2026, mes: 12, inicial: 0, movimentos: [[3, 'PIX RECEBIDO FICTICIO', 1000], [5, 'TARIFA FICTICIA', -100]] });
    const jan = arquivoDoMes('jan.pdf', { ano: 2027, mes: 1, inicial: 900, movimentos: [[3, 'PIX RECEBIDO FICTICIO', 1000], [5, 'TARIFA FICTICIA', -100]] });
    expect(agruparHistoricos([dez, jan]).historicos[0]!.avisos).toEqual([]);
  });

  it('encadeamento não fecha por 1 centavo: aviso nomeando o mês e nenhum lançamento alterado', () => {
    const antes = agruparHistoricos([ago(), set(), out()]).historicos[0]!.consolidado.lancamentos;
    const h = agruparHistoricos([ago(), set({ inicial: 138001 }), out()]).historicos[0]!;
    const aviso = h.avisos.filter((a) => a.tipo === 'encadeamento');
    expect(aviso[0]).toMatchObject({ mes: '2026-08' });
    expect(aviso[0]!.mensagem).toContain('08/2026');
    expect(aviso[0]!.mensagem).not.toMatch(/\d{2,3}[.,]\d{2}/); // só o mês: nenhum valor no aviso
    // setembro agora termina em 129.991, então o encadeamento de setembro para outubro também avisa
    expect(h.avisos.map((a) => a.mes)).toEqual(['2026-08', '2026-09']);
    // lançamentos idênticos em dados (o saldo de linha é do documento; nada foi mexido para fechar)
    expect(h.consolidado.lancamentos.map((l) => [l.data, l.valorCentavos, l.direcao, l.descricao])).toEqual(antes.map((l) => [l.data, l.valorCentavos, l.direcao, l.descricao]));
  });

  it('saldo indisponível num dos lados: "encadeamento não conferido" nomeando o mês, sem inventar saldo', () => {
    const h = agruparHistoricos([ago(), set({ semSaldo: true })]).historicos[0]!;
    expect(h.avisos).toHaveLength(1);
    expect(h.avisos[0]).toMatchObject({ tipo: 'encadeamento-nao-conferido', mes: '2026-08' });
    expect(h.avisos[0]!.mensagem).toContain('08/2026');
  });

  it('arquivos do mesmo mês que se sobrepõem não geram aviso de encadeamento', () => {
    const a = arquivoDoMes('a.pdf', { ...SET, movimentos: [[2, 'PIX ENVIADO LOJA FICTICIA', -5000], [9, 'PAGAMENTO BOLETO FICTICIO', -3010]] });
    const b = arquivoDoMes('b.pdf', { ...SET, inicial: 133000, movimentos: [[9, 'PAGAMENTO BOLETO FICTICIO', -3010], [15, 'COMPRA CARTAO FICTICIO', -8000]] });
    const h = agruparHistoricos([a, b]).historicos[0]!;
    expect(h.avisos).toEqual([]);
    expect(h.mesesCobertos).toEqual(['2026-09']);
  });
});

describe('identificação da conta', () => {
  it('contas diferentes (identificador estrutural) e bancos diferentes não se juntam', () => {
    const a = arquivoDoMes('a.pdf', { ...AGO, conta: 'Conta: ***4821' });
    const b = arquivoDoMes('b.pdf', { ...SET, conta: 'Conta: ***9937' });
    const c = arquivoDoMes('c.pdf', { ...OUT, conta: 'Conta: ***4821', banco: 'Nubank' });
    const { historicos } = agruparHistoricos([a, b, c]);
    expect(historicos.map((h) => [h.bancoProvavel, h.contaFinal, nomes(h.arquivos)])).toEqual([
      [null, 'final 4821', ['a.pdf']],
      [null, 'final 9937', ['b.pdf']],
      ['Nubank', 'final 4821', ['c.pdf']],
    ]);
    expect(historicos.every((h) => h.avisos.length === 0)).toBe(true);
  });

  it('a mesma conta em meses diferentes forma um histórico só', () => {
    const { historicos } = agruparHistoricos([arquivoDoMes('a.pdf', { ...AGO, conta: 'Conta: ***4821' }), arquivoDoMes('b.pdf', { ...SET, conta: 'Conta: ***4821' })]);
    expect(historicos).toHaveLength(1);
    expect(historicos[0]!.contaFinal).toBe('final 4821');
  });

  it('sem identificador distintivo, os arquivos entram juntos com um aviso', () => {
    const sem = (nome: string, p: PedidoMes) => arquivoDoMes(nome, { ...p, conta: null });
    const h = agruparHistoricos([sem('a.pdf', AGO), sem('b.pdf', SET)]).historicos;
    expect(h).toHaveLength(1);
    expect(h[0]!.contaFinal).toBeNull();
    expect(h[0]!.avisos.map((a) => a.tipo)).toEqual(['sem-identificador']);
  });

  it('um arquivo sem identificador junto de uma única conta identificada entra nela, com aviso', () => {
    const h = agruparHistoricos([arquivoDoMes('a.pdf', AGO), arquivoDoMes('s.pdf', { ...SET, conta: null })]).historicos;
    expect(h).toHaveLength(1);
    expect(h[0]!.contaFinal).toBe('final 4821');
    expect(h[0]!.avisos.map((a) => a.tipo)).toEqual(['sem-identificador']);
  });

  it('nome do titular e número completo da conta nunca aparecem no histórico', () => {
    const a = arquivoDoMes('a.pdf', { ...AGO, conta: 'Conta: 12345678-9', extras: ['Titular: MARIA APARECIDA FICTICIA DA SILVA', 'CPF ***.456.789-**'] });
    const b = arquivoDoMes('b.pdf', { ...SET, conta: 'Conta corrente 12345678-9', extras: ['Cliente: MARIA APARECIDA FICTICIA DA SILVA'] });
    const r = agruparHistoricos([a, b]);
    expect(r.historicos).toHaveLength(1);
    expect(r.historicos[0]!.contaFinal).toBe('final 6789');
    const json = JSON.stringify(r);
    for (const proibido of ['MARIA', 'APARECIDA', 'SILVA', 'Titular', '12345678', '2345678', '456.789']) expect(json, proibido).not.toContain(proibido);
  });

  it('número de conta sem máscara de até 4 dígitos não vale como identificador (poderia ser o inteiro)', () => {
    expect(arquivoDoMes('a.pdf', { ...AGO, conta: 'Conta: 4821' }).resultado.contaFinal).toBeNull();
    expect(arquivoDoMes('a.pdf', { ...AGO, conta: 'Conta: ***4821' }).resultado.contaFinal).toBe('final 4821');
  });
});

describe('duplicidade da 5.3 dentro do histórico', () => {
  it('períodos sobrepostos: a mesma operação conta uma vez ("aparece em dois extratos"); no mesmo arquivo, chaves iguais ficam', () => {
    const a = arquivoDoMes('a.pdf', { ...SET, movimentos: [[2, 'PIX ENVIADO LOJA FICTICIA', -5000], [2, 'PIX ENVIADO LOJA FICTICIA', -5000], [9, 'PAGAMENTO BOLETO FICTICIO', -3010]] });
    const b = arquivoDoMes('b.pdf', { ...SET, inicial: 128000, movimentos: [[9, 'PAGAMENTO BOLETO FICTICIO', -3010], [15, 'COMPRA CARTAO FICTICIO', -8000]] });
    const h = agruparHistoricos([a, b]).historicos[0]!;
    expect(h.consolidado.lancamentos).toHaveLength(4); // 2 iguais de a + boleto uma vez + compra
    expect(h.consolidado.lancamentos.filter((l) => l.apareceEmDoisExtratos)).toHaveLength(1);
  });

  it('o mesmo arquivo reenviado (mesmo hash) não duplica e é apontado como repetido', () => {
    const a = ago();
    const r = agruparHistoricos([a, { nome: 'ago-de-novo.pdf', resultado: a.resultado }, set()]);
    expect(r.repetidos).toEqual(['ago-de-novo.pdf']);
    expect(r.historicos[0]!.consolidado.lancamentos).toHaveLength(4);
    expect(nomes(r.historicos[0]!.arquivos)).toEqual(['ago.pdf', 'set.pdf']);
  });

  it('arquivo não suportado fica fora do histórico, e sem arquivos não há histórico', () => {
    const quebrado: ArquivoLido = { nome: 'q.pdf', resultado: { ...ago().resultado, status: 'nao-suportado', motivo: 'corrompido', periodo: null, lancamentos: [] } };
    const r = agruparHistoricos([quebrado, ago()]);
    expect(r.semHistorico).toEqual(['q.pdf']);
    expect(r.historicos).toHaveLength(1);
    expect(agruparHistoricos([])).toEqual({ historicos: [], repetidos: [], semHistorico: [] });
  });
});
