// Estado só na memória da página: nada em localStorage, IndexedDB ou cookies (princípio 2).
import { useState } from 'preact/hooks';
import { lerNoWorker } from './leitura/cliente';
import type { ResultadoArquivo } from './leitura/tipos';
import { Diagnostico } from './telas/Diagnostico';
import { Extratos } from './telas/Extratos';
import { ResultadoLeitura } from './telas/ResultadoLeitura';

export interface ItemArquivo {
  id: number;
  nome: string;
  /** só guardado enquanto se espera a senha; depois da leitura é solto */
  bytes: Uint8Array | null;
  estado: 'lendo' | 'senha' | 'pronto';
  progresso: { feito: number; total: number } | null;
  resultado: ResultadoArquivo | null;
}

export type Tela = 'extratos' | 'resultado' | 'diagnostico';

let proximoId = 1;

export function App() {
  const [tela, setTela] = useState<Tela>('extratos');
  const [itens, setItens] = useState<ItemArquivo[]>([]);

  const atualizar = (id: number, mudanca: Partial<ItemArquivo>) => setItens((atual) => atual.map((i) => (i.id === id ? { ...i, ...mudanca } : i)));

  async function ler(id: number, bytes: Uint8Array, senha?: string) {
    atualizar(id, { estado: 'lendo', progresso: null });
    const resultado = await lerNoWorker(bytes, senha, (feito, total) => atualizar(id, { progresso: { feito, total } }));
    const pedeSenha = resultado.motivo === 'senha-necessaria' || resultado.motivo === 'senha-incorreta';
    atualizar(id, { estado: pedeSenha ? 'senha' : 'pronto', resultado, bytes: pedeSenha ? bytes : null, progresso: null });
  }

  async function escolher(arquivos: File[]) {
    const novos = arquivos.map((f) => ({ id: proximoId++, nome: f.name, arquivo: f }));
    setItens((atual) => [...atual, ...novos.map((n): ItemArquivo => ({ id: n.id, nome: n.nome, bytes: null, estado: 'lendo', progresso: null, resultado: null }))]);
    for (const n of novos) {
      const bytes = new Uint8Array(await n.arquivo.arrayBuffer());
      await ler(n.id, bytes);
    }
  }

  const pular = (id: number) => setItens((atual) => atual.filter((i) => i.id !== id));

  return (
    <div class="pagina">
      <main>
        {tela === 'extratos' && <Extratos itens={itens} aoEscolher={escolher} aoEnviarSenha={(id, senha) => { const i = itens.find((x) => x.id === id); if (i?.bytes) void ler(id, i.bytes, senha); }} aoPular={pular} aoContinuar={() => setTela('resultado')} />}
        {tela === 'resultado' && <ResultadoLeitura itens={itens} aoVoltar={() => setTela('extratos')} />}
        {tela === 'diagnostico' && <Diagnostico itens={itens} aoVoltar={() => setTela('extratos')} />}
      </main>
      <footer>
        <p class="suave">Versão de teste: conteúdo ainda sem revisão profissional. Nada do que você escolhe sai do seu celular; ao fechar a página, tudo some.</p>
        {tela !== 'diagnostico' && (
          <button type="button" class="link" onClick={() => setTela('diagnostico')}>
            Diagnóstico
          </button>
        )}
      </footer>
    </div>
  );
}
