// Web Worker da leitura: recebe os bytes, lê no próprio aparelho e devolve o resultado.
// Nada aqui usa rede. O PDF.js só entra quando este worker é criado, isto é, quando a pessoa escolhe um PDF.
import { falhaDeLeitura, lerExtrato } from './index';
import type { ResultadoArquivo } from './tipos';

export interface PedidoLeitura {
  id: number;
  bytes: Uint8Array;
  senha?: string;
}

export type RespostaLeitura =
  | { id: number; tipo: 'progresso'; feito: number; total: number }
  | { id: number; tipo: 'resultado'; resultado: ResultadoArquivo };

/** Trata um pedido. Qualquer erro vira "não suportado" (sem a mensagem do erro): a jornada nunca fica pendurada. */
export async function processarPedido(
  pedido: PedidoLeitura,
  enviar: (m: RespostaLeitura) => void,
  ler: typeof lerExtrato = lerExtrato,
): Promise<void> {
  const { id, bytes, senha } = pedido;
  let resultado: ResultadoArquivo;
  try {
    resultado = await ler(bytes, senha, { onProgresso: (feito, total) => enviar({ id, tipo: 'progresso', feito, total }) });
  } catch {
    resultado = falhaDeLeitura();
  }
  enviar({ id, tipo: 'resultado', resultado });
}

// Só se registra quando este módulo roda dentro de um Worker (nos testes, é apenas importado).
const escopo = globalThis as unknown as {
  WorkerGlobalScope?: new () => unknown;
  onmessage: ((e: MessageEvent<PedidoLeitura>) => void) | null;
  postMessage: (m: RespostaLeitura) => void;
};
if (typeof escopo.WorkerGlobalScope !== 'undefined' && globalThis instanceof escopo.WorkerGlobalScope) {
  escopo.onmessage = (e) => {
    void processarPedido(e.data, (m) => escopo.postMessage(m));
  };
}
