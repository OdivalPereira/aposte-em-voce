// Web Worker da leitura: recebe os bytes, lê no próprio aparelho e devolve o resultado.
// Nada aqui usa rede. O PDF.js só entra quando este worker é criado, isto é, quando a pessoa escolhe um PDF.
import { lerExtrato } from './index';
import type { ResultadoArquivo } from './tipos';

export interface PedidoLeitura {
  id: number;
  bytes: Uint8Array;
  senha?: string;
}

export type RespostaLeitura =
  | { id: number; tipo: 'progresso'; feito: number; total: number }
  | { id: number; tipo: 'resultado'; resultado: ResultadoArquivo };

const contexto = self as unknown as {
  onmessage: ((e: MessageEvent<PedidoLeitura>) => void) | null;
  postMessage: (m: RespostaLeitura) => void;
};

contexto.onmessage = async (e) => {
  const { id, bytes, senha } = e.data;
  const resultado = await lerExtrato(bytes, senha, {
    onProgresso: (feito, total) => contexto.postMessage({ id, tipo: 'progresso', feito, total }),
  });
  contexto.postMessage({ id, tipo: 'resultado', resultado });
};
