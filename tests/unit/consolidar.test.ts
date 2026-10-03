import { describe, expect, it } from 'vitest';
import { consolidar } from '../../src/leitura/consolidar';
import { diagnosticar } from '../../src/leitura/diagnostico';
import type { ArquivoLido, Lancamento, ResultadoArquivo } from '../../src/leitura/tipos';

function lanc(data: string, valor: number, direcao: 'entrada' | 'saida', descricao: string, pagina = 1): Lancamento {
  return { data, hora: null, valorCentavos: valor, direcao, descricao, pagina, saldoCentavos: null };
}

function arquivo(nome: string, hash: string, lancamentos: Lancamento[], status: ResultadoArquivo['status'] = 'suficiente'): ArquivoLido {
  const datas = lancamentos.map((l) => l.data).sort();
  return {
    nome,
    resultado: {
      versao: 1,
      hash,
      status,
      motivo: null,
      mensagem: '',
      bancoProvavel: null,
      periodo: datas.length ? { inicio: datas[0] as string, fim: datas[datas.length - 1] as string } : null,
      paginas: 1,
      linhasCandidatas: lancamentos.length,
      lancamentos,
      conferencia: { situacao: 'indisponivel', saldoInicialCentavos: null, saldoFinalCentavos: null, entradasCentavos: 0, saidasCentavos: 0, diferencaCentavos: null, progressao: null },
    },
  };
}

describe('consolidar (5.3)', () => {
  const pix = lanc('2026-09-10', 5000, 'saida', 'PIX ENVIADO LOJA FICTICIA');

  it('períodos sobrepostos: a mesma chave conta uma vez, marcada "aparece em dois extratos", com as duas origens', () => {
    const a = arquivo('a.pdf', 'h1', [lanc('2026-09-01', 1000, 'entrada', 'DEPOSITO'), pix]);
    const b = arquivo('b.pdf', 'h2', [lanc('2026-09-10', 5000, 'saida', 'Pix enviado — loja ficticia', 3), lanc('2026-09-20', 700, 'saida', 'COMPRA')]);
    const c = consolidar([a, b]);
    expect(c.lancamentos).toHaveLength(3);
    const dup = c.lancamentos.find((l) => l.valorCentavos === 5000);
    expect(dup?.apareceEmDoisExtratos).toBe(true);
    expect(dup?.origens).toEqual([
      { arquivo: 'a.pdf', pagina: 1 },
      { arquivo: 'b.pdf', pagina: 3 },
    ]);
    expect(c.lancamentos.filter((l) => l.apareceEmDoisExtratos)).toHaveLength(1);
    expect(c.saidasCentavos).toBe(5700);
    expect(c.entradasCentavos).toBe(1000);
  });

  it('dentro do mesmo arquivo, chaves iguais são operações distintas e as duas ficam', () => {
    const a = arquivo('a.pdf', 'h1', [pix, { ...pix, pagina: 2 }]);
    const c = consolidar([a]);
    expect(c.lancamentos).toHaveLength(2);
    expect(c.lancamentos.every((l) => !l.apareceEmDoisExtratos)).toBe(true);
    expect(c.saidasCentavos).toBe(10000);
  });

  it('duas iguais em cada um de dois arquivos sobrepostos: continuam duas, não quatro', () => {
    const a = arquivo('a.pdf', 'h1', [pix, pix]);
    const b = arquivo('b.pdf', 'h2', [pix, pix]);
    const c = consolidar([a, b]);
    expect(c.lancamentos).toHaveLength(2);
    expect(c.lancamentos.every((l) => l.apareceEmDoisExtratos)).toBe(true);
  });

  it('o arquivo que tem uma a mais mantém a diferença', () => {
    const c = consolidar([arquivo('a.pdf', 'h1', [pix]), arquivo('b.pdf', 'h2', [pix, pix])]);
    expect(c.lancamentos).toHaveLength(2);
  });

  it('reenviar o mesmo arquivo (mesmo hash) não duplica nada, mesmo com outro nome', () => {
    const c = consolidar([arquivo('a.pdf', 'h1', [pix]), arquivo('copia de a.pdf', 'h1', [pix])]);
    expect(c.lancamentos).toHaveLength(1);
    expect(c.lancamentos[0]?.apareceEmDoisExtratos).toBe(false);
    expect(c.repetidos).toEqual(['copia de a.pdf']);
  });

  it('mesma descrição e valor em meses sem sobreposição: a data faz parte da chave, então são operações distintas', () => {
    // Dois arquivos só podem compartilhar uma chave se compartilham a data, logo seus períodos já se sobrepõem:
    // a regra de sobreposição da 5.3 é consequência da chave. O que protege é a data na chave.
    const a = arquivo('a.pdf', 'h1', [lanc('2026-08-10', 5000, 'saida', 'PIX ENVIADO LOJA FICTICIA')]);
    const b = arquivo('b.pdf', 'h2', [lanc('2026-09-10', 5000, 'saida', 'PIX ENVIADO LOJA FICTICIA')]);
    const c = consolidar([a, b]);
    expect(c.lancamentos).toHaveLength(2);
    expect(c.lancamentos.every((l) => !l.apareceEmDoisExtratos)).toBe(true);
    expect(c.saidasCentavos).toBe(10000);
  });

  it('chaves diferentes (data, valor, direção) nunca se fundem', () => {
    const a = arquivo('a.pdf', 'h1', [pix, lanc('2026-09-10', 5001, 'saida', pix.descricao), lanc('2026-09-10', 5000, 'entrada', pix.descricao), lanc('2026-09-11', 5000, 'saida', pix.descricao)]);
    const b = arquivo('b.pdf', 'h2', [pix]);
    expect(consolidar([a, b]).lancamentos).toHaveLength(4);
  });

  it('arquivo não suportado não contribui, e a jornada continua com os outros', () => {
    const c = consolidar([arquivo('img.pdf', 'h0', [], 'nao-suportado'), arquivo('a.pdf', 'h1', [pix])]);
    expect(c.lancamentos).toHaveLength(1);
    expect(c.semLancamentos).toEqual(['img.pdf']);
  });
});

describe('diagnóstico (T99)', () => {
  it('só contagens e rótulos: nenhum valor, nome ou descrição', () => {
    const a = arquivo('extrato de Maria Silva.pdf', 'h1', [lanc('2026-09-10', 123456, 'saida', 'PIX ENVIADO JOAO FICTICIO')]);
    const d = diagnosticar([a.resultado]);
    const json = JSON.stringify(d);
    expect(json).not.toMatch(/123456|1\.234|JOAO|PIX|Maria|2026/);
    expect(d[0]).toMatchObject({ rotulo: 'Arquivo 1', paginas: 1, linhasCandidatas: 1, lancamentosReconstruidos: 1, conferenciaDeSaldo: 'indisponivel', status: 'suficiente', statusRotulo: 'Leitura suficiente' });
  });
});
