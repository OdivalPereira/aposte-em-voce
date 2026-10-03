import { describe, expect, it } from 'vitest';
import { analisarPaginas, assinaturaDoLayout } from '../../src/leitura';
import { contaDoTexto, formatoDeData, formatoDeValor, rotuloDeCabecalho } from '../../src/leitura/layout';
import { paginasDoMes, brl } from './auxiliar/extrato-mes';
import { pagina, paginaAgrupada, type ColunaMontagem } from './auxiliar/montar';

const H = 'c'.repeat(64);

const MOVIMENTOS: [number, string, number][] = [
  [2, 'PIX ENVIADO LOJA FICTICIA', -5000],
  [5, 'PIX RECEBIDO PESSOA FICTICIA', 123456],
  [9, 'PAGAMENTO BOLETO FICTICIO', -3010],
];

/** Dígitos que a assinatura pode ter: só os da linha de posições (décimos da largura, estrutura) e o 9 das máscaras. */
function digitosForaDasPosicoes(assinatura: string): string {
  return assinatura
    .split('\n')
    .filter((l) => !l.startsWith('Posição das colunas'))
    .join('\n')
    .replace(/\D/g, '');
}

describe('T99: assinatura do layout', () => {
  const paginas = paginasDoMes({ ano: 2026, mes: 9, inicial: 100000, movimentos: MOVIMENTOS, conta: 'Conta: 12345678-9', extras: ['Titular: MARIA APARECIDA FICTICIA DA SILVA'] });
  const r = analisarPaginas(paginas, H);
  const assinatura = assinaturaDoLayout(r.estrutura);

  it('traz cabeçalhos, posição relativa das colunas e formatos de data e de valor com os dígitos mascarados', () => {
    expect(assinatura).toContain('Colunas, da esquerda para a direita: Data | Descrição | Valor | Saldo');
    expect(assinatura).toMatch(/Posição das colunas, em décimos da largura: Data \d+-\d+; Descrição \d+-\d+; Valor \d+-\d+; Saldo \d+-\d+/);
    expect(assinatura).toContain('Formato de data: 99/99/9999');
    expect(assinatura).toContain('Formato de valor: -9,99; 9,99; 9.999,99');
    expect(assinatura).toContain('Títulos de grupo: nenhum');
  });

  it('não contém nenhum dígito real nem nenhuma descrição do extrato sintético', () => {
    expect(digitosForaDasPosicoes(assinatura)).toMatch(/^9+$/);
    for (const l of r.lancamentos) {
      expect(assinatura).not.toContain(l.descricao);
      for (const palavra of l.descricao.split(' ')) expect(assinatura, palavra).not.toContain(palavra);
      expect(assinatura).not.toContain(brl(l.valorCentavos));
      expect(assinatura).not.toContain(l.data);
    }
    for (const proibido of ['1.000,00', '1.234,56', '30,10', '50,00', '02/09', '2026', 'MARIA', 'SILVA', 'Titular', '12345678', '6789', 'R$', 'Banco Ficticio', 'PIX']) expect(assinatura, proibido).not.toContain(proibido);
  });

  it('as posições são relativas à largura: o mesmo layout deslocado dá a mesma assinatura', () => {
    const deslocada = paginas.map((p) => ({ ...p, itens: p.itens.map((i) => ({ ...i, x: i.x * 2, largura: i.largura * 2 })) }));
    expect(assinaturaDoLayout(analisarPaginas(deslocada, H).estrutura)).toBe(assinatura);
  });

  it('o layout agrupado por dia traz só os rótulos dos títulos de grupo e nenhum dígito real', () => {
    const p = paginaAgrupada({
      antes: ['Nubank - Extrato', 'Período: 01/09/2026 a 30/09/2026'],
      saldoInicial: '1.000,00',
      dias: [{ data: '02 SET 2026', entradas: { total: '200,00', linhas: [['Transferência recebida PESSOA FICTICIA', '200,00']] }, saidas: { total: '50,00', linhas: [['Pix enviado LOJA FICTICIA', '50,00']] } }],
      saldoFinal: '1.150,00',
    });
    const a = assinaturaDoLayout(analisarPaginas([p], H).estrutura);
    expect(a).toContain('Títulos de grupo: Total de entradas; Total de saídas');
    expect(a).toMatch(/Colunas, da esquerda para a direita: Descrição \| Valor/); // sem cabeçalho: colunas inferidas do conteúdo
    expect(digitosForaDasPosicoes(a)).toMatch(/^9+$/);
    for (const proibido of ['PESSOA', 'FICTICIA', 'LOJA', '200,00', '1.150,00', 'SET']) expect(a, proibido).not.toContain(proibido);
  });

  it('rótulo de cabeçalho que não é do vocabulário (pode ter nome ou descrição) vira o nome do papel', () => {
    const colunas: ColunaMontagem[] = [
      { titulo: 'Data', x: 40 },
      { titulo: 'Histórico de Maria Silva', x: 130 },
      { titulo: 'Valor (R$)', x: 430, dir: true },
      { titulo: 'Saldo (R$)', x: 540, dir: true },
    ];
    const rr = analisarPaginas([pagina({ colunas, linhas: [['', 'SALDO ANTERIOR', '', '1.000,00'], ['02/09/2026', 'PIX ENVIADO LOJA FICTICIA', '-50,00', '950,00'], ['', 'SALDO FINAL', '', '950,00']] })], H);
    const a = assinaturaDoLayout(rr.estrutura);
    expect(a).toContain('Data | Descrição | Valor | Saldo');
    expect(a).not.toContain('Maria');
    expect(rotuloDeCabecalho('Histórico', 'descricao')).toBe('Histórico');
    expect(rotuloDeCabecalho('Valor (R$)', 'valor')).toBe('Valor');
  });

  it('formatos: data e valor mascarados; o texto que acompanha a data (descrição) não entra', () => {
    expect(formatoDeData('02/09/2026')).toBe('99/99/9999');
    expect(formatoDeData('02/09 PIX ENVIADO FULANO')).toBe('99/99');
    expect(formatoDeData('02 SET 2026')).toBe('99 AAA 9999');
    expect(formatoDeData('PIX ENVIADO')).toBeNull();
    expect(formatoDeValor('1.234,56')).toBe('9.999,99');
    expect(formatoDeValor('12.345,67')).toBe('9.999,99');
    expect(formatoDeValor('50,00')).toBe('9,99');
    expect(formatoDeValor('-50,00')).toBe('-9,99');
    expect(formatoDeValor('R$ 1.234,56')).toBe('R$ 9.999,99');
    expect(formatoDeValor('1.234,56 D')).toBe('9.999,99 D');
    expect(formatoDeValor('PIX 50,00')).toBeNull();
  });

  it('sem estrutura (arquivo que nem chegou à tabela), a assinatura é só um aviso fixo, sem vazar nada', () => {
    expect(assinaturaDoLayout(null)).toMatch(/indisponível/);
  });

  it('conta: no máximo os 4 últimos dígitos; sem máscara e curto, não vale', () => {
    expect(contaDoTexto('Agência 0001\nConta: 12345678-9')).toBe('final 6789');
    expect(contaDoTexto('Conta corrente 0001234-5')).toBe('final 2345');
    expect(contaDoTexto('Conta ***4821')).toBe('final 4821');
    expect(contaDoTexto('Conta: 4821')).toBeNull();
    expect(contaDoTexto('Conta: 12345')).toBeNull(); // sem máscara, menos de 6 dígitos
    expect(contaDoTexto('Conta: 123456')).toBe('final 3456');
    expect(contaDoTexto('Conta 2026-09-30')).toBeNull(); // data
    expect(contaDoTexto('Conta 30/09/2026')).toBeNull(); // data
    expect(contaDoTexto('Conta: 123.456.789-00')).toBeNull(); // CPF
    expect(contaDoTexto('Conta: 12345678900')).toBeNull(); // CPF sem pontuação
    expect(contaDoTexto('Conta: ***.456.789-**')).toBeNull(); // CPF mascarado
    expect(contaDoTexto('Conta: xxx.456.789-xx')).toBeNull(); // CPF mascarado
    expect(contaDoTexto('Conta: ***4821')).toBe('final 4821'); // conta mascarada sem forma de CPF segue valendo
    expect(contaDoTexto('Titular: MARIA FICTICIA DA SILVA')).toBeNull();
    expect(contaDoTexto('Prestação de contas 2026')).toBeNull();
  });

  it('o resultado serializado não guarda número completo da conta nem nome', () => {
    const json = JSON.stringify(r);
    for (const proibido of ['12345678', 'MARIA', 'Titular']) expect(json, proibido).not.toContain(proibido);
    expect(r.contaFinal).toBe('final 6789');
  });
});
