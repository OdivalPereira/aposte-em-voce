// Lado da página: cria o worker só quando a pessoa escolhe um PDF e fala com ele por mensagens.
// Falha do worker (não carrega, erro, mensagem ilegível) nunca deixa a leitura pendurada: vira "não suportado".
import { falhaDeLeitura } from './index';
import type { PedidoLeitura, RespostaLeitura } from './worker';
import type { ResultadoArquivo } from './tipos';

type FabricaWorker = () => Worker;

const fabricaPadrao: FabricaWorker = () => new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });

let worker: Worker | null = null;
let proximoId = 1;

function descartar(w: Worker) {
  try {
    w.terminate();
  } catch {
    // já encerrado
  }
  if (worker === w) worker = null;
}

/** Lê um PDF no worker. Os bytes são copiados: quem chama pode tentar de novo com outra senha. Nunca rejeita. */
export function lerNoWorker(
  bytes: Uint8Array,
  senha: string | undefined,
  onProgresso: (feito: number, total: number) => void,
  criar: FabricaWorker = fabricaPadrao,
): Promise<ResultadoArquivo> {
  return new Promise((resolve) => {
    let w: Worker;
    try {
      worker ??= criar();
      w = worker;
    } catch {
      resolve(falhaDeLeitura());
      return;
    }
    const id = proximoId++;
    const limpar = () => {
      w.removeEventListener('message', aoReceber as EventListener);
      w.removeEventListener('error', aoFalhar);
      w.removeEventListener('messageerror', aoFalhar);
    };
    const aoReceber = (e: MessageEvent<RespostaLeitura>) => {
      if (e.data.id !== id) return;
      if (e.data.tipo === 'progresso') onProgresso(e.data.feito, e.data.total);
      else {
        limpar();
        resolve(e.data.resultado);
      }
    };
    const aoFalhar = () => {
      limpar();
      descartar(w); // o próximo arquivo ganha um worker novo
      resolve(falhaDeLeitura());
    };
    w.addEventListener('message', aoReceber as EventListener);
    w.addEventListener('error', aoFalhar);
    w.addEventListener('messageerror', aoFalhar);
    try {
      const copia = bytes.slice();
      const pedido: PedidoLeitura = { id, bytes: copia, senha };
      w.postMessage(pedido, [copia.buffer]);
    } catch {
      aoFalhar();
    }
  });
}
