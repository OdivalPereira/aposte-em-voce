// T99: diagnóstico por arquivo, para o teste de Odival. Sem valores, nomes nem descrições.
import { diagnosticar } from '../leitura/diagnostico';
import type { ResultadoArquivo } from '../leitura/tipos';
import type { ItemArquivo } from '../app';

const SALDO = { fecha: 'confere', 'nao-fecha': 'não fecha', indisponivel: 'indisponível' } as const;

export function Diagnostico({ itens, aoVoltar }: { itens: ItemArquivo[]; aoVoltar: () => void }) {
  const linhas = diagnosticar(itens.filter((i) => i.resultado).map((i) => i.resultado as ResultadoArquivo));
  return (
    <section aria-labelledby="titulo-diagnostico">
      <h1 id="titulo-diagnostico">Diagnóstico da leitura</h1>
      <p class="suave">Só contagens. Nenhum valor, nome ou descrição aparece aqui.</p>
      {linhas.length === 0 ? (
        <p>Nenhum arquivo lido nesta visita.</p>
      ) : (
        <div class="tabela-rolagem">
          <table>
            <thead>
              <tr>
                <th scope="col">Arquivo</th>
                <th scope="col">Páginas</th>
                <th scope="col">Linhas candidatas</th>
                <th scope="col">Lançamentos reconstruídos</th>
                <th scope="col">Conferência de saldo</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l) => (
                <tr key={l.rotulo}>
                  <th scope="row">{l.rotulo}</th>
                  <td>{l.paginas}</td>
                  <td>{l.linhasCandidatas}</td>
                  <td>{l.lancamentosReconstruidos}</td>
                  <td>{SALDO[l.conferenciaDeSaldo]}{l.progressao ? ` (${l.progressao.verificadas} linhas conferidas, ${l.progressao.divergentes} divergentes)` : ''}</td>
                  <td>{l.statusRotulo}{l.motivo ? ` (${l.motivo})` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button type="button" class="secundario" onClick={aoVoltar}>
        Voltar
      </button>
    </section>
  );
}
