// Princípio 8: nenhuma falha de leitura pode deixar a jornada travada. Toda falha termina o item como "não suportado".
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createHash } from 'node:crypto';
import { lerExtrato, sha256Hex } from '../../src/leitura';
import { lerNoWorker } from '../../src/leitura/cliente';
import { processarPedido, type RespostaLeitura } from '../../src/leitura/worker';
import { COLUNAS_PADRAO, pagina } from './auxiliar/montar';
import { gerarPdf } from './auxiliar/pdf-sintetico';

afterEach(() => vi.unstubAllGlobals());

const esperado = (b: Uint8Array) => createHash('sha256').update(b).digest('hex');

async function pdfSimples() {
  return gerarPdf([pagina({ antes: ['01/09/2026 a 30/09/2026'], colunas: COLUNAS_PADRAO, linhas: [['02/09/2026', 'PIX FICTICIO', '-5,00', '']] })]);
}

describe('sem crypto.subtle (por exemplo, http na rede local)', () => {
  it('o hash continua correto, inclusive nas bordas do bloco de 64 bytes', async () => {
    vi.stubGlobal('crypto', {});
    for (const n of [0, 1, 3, 55, 56, 57, 63, 64, 65, 119, 120, 1000]) {
      const b = Uint8Array.from({ length: n }, (_, i) => (i * 7 + 3) % 256);
      expect(await sha256Hex(b)).toBe(esperado(b));
    }
  });

  it('subtle que rejeita também cai no hash local', async () => {
    vi.stubGlobal('crypto', { subtle: { digest: () => Promise.reject(new Error('indisponível')) } });
    const b = new TextEncoder().encode('abc');
    expect(await sha256Hex(b)).toBe(esperado(b));
  });

  it('lerExtrato lê normalmente, sem pendurar nem rejeitar', async () => {
    vi.stubGlobal('crypto', {});
    const bytes = await pdfSimples();
    const r = await lerExtrato(bytes);
    expect(r.status).toBe('suficiente');
    expect(r.hash).toBe(esperado(bytes));
  });
});

describe('worker: processarPedido', () => {
  it('se a leitura lançar, responde "não suportado" sem vazar a mensagem do erro', async () => {
    const enviadas: RespostaLeitura[] = [];
    await processarPedido({ id: 7, bytes: new Uint8Array(1) }, (m) => enviadas.push(m), () => Promise.reject(new Error('conteúdo secreto 123,45 JOAO')));
    expect(enviadas).toHaveLength(1);
    const m = enviadas[0] as Extract<RespostaLeitura, { tipo: 'resultado' }>;
    expect(m).toMatchObject({ id: 7, tipo: 'resultado' });
    expect(m.resultado).toMatchObject({ status: 'nao-suportado', motivo: 'corrompido', lancamentos: [] });
    expect(JSON.stringify(m)).not.toMatch(/secreto|123,45|JOAO/);
  });
});

describe('cliente: lerNoWorker', () => {
  class Falso extends EventTarget {
    encerrado = false;
    constructor(private readonly comportamento: 'erro' | 'erro-de-mensagem' | 'postMessage-lanca') {
      super();
    }
    postMessage() {
      if (this.comportamento === 'postMessage-lanca') throw new Error('DataCloneError com conteúdo');
      queueMicrotask(() => this.dispatchEvent(new Event(this.comportamento === 'erro' ? 'error' : 'messageerror')));
    }
    terminate() {
      this.encerrado = true;
    }
  }

  for (const comportamento of ['erro', 'erro-de-mensagem', 'postMessage-lanca'] as const) {
    it(`worker com ${comportamento}: o item termina como "não suportado" e o worker é descartado`, async () => {
      const falso = new Falso(comportamento);
      const r = await lerNoWorker(new Uint8Array(4), undefined, () => {}, () => falso as unknown as Worker);
      expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'corrompido' });
      expect(falso.encerrado).toBe(true);
    });
  }

  it('worker que nem consegue ser criado: "não suportado", sem rejeitar', async () => {
    const r = await lerNoWorker(new Uint8Array(4), undefined, () => {}, () => {
      throw new Error('Worker indisponível');
    });
    expect(r).toMatchObject({ status: 'nao-suportado', motivo: 'corrompido' });
  });
});
