// Lado da página: cria o worker só quando a pessoa escolhe um PDF e fala com ele por mensagens.
import type { PedidoLeitura, RespostaLeitura } from './worker';
import type { ResultadoArquivo } from './tipos';

let worker: Worker | null = null;
let proximoId = 1;

function obterWorker(): Worker {
  worker ??= new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
  return worker;
}

/** Lê um PDF no worker. Os bytes são copiados: quem chama pode tentar de novo com outra senha. */
export function lerNoWorker(bytes: Uint8Array, senha: string | undefined, onProgresso: (feito: number, total: number) => void): Promise<ResultadoArquivo> {
  const w = obterWorker();
  const id = proximoId++;
  return new Promise((resolve) => {
    const aoReceber = (e: MessageEvent<RespostaLeitura>) => {
      if (e.data.id !== id) return;
      if (e.data.tipo === 'progresso') onProgresso(e.data.feito, e.data.total);
      else {
        w.removeEventListener('message', aoReceber);
        resolve(e.data.resultado);
      }
    };
    w.addEventListener('message', aoReceber);
    const copia = bytes.slice();
    const pedido: PedidoLeitura = { id, bytes: copia, senha };
    w.postMessage(pedido, [copia.buffer]);
  });
}
