// T99: diagnóstico por arquivo, para o teste de Odival. Sem valores, nomes nem descrições.
import { useState } from 'preact/hooks';
import { diagnosticar } from '../leitura/diagnostico';
import { assinaturaDoLayout } from '../leitura/layout';
import type { ResultadoArquivo } from '../leitura/tipos';
import type { ItemArquivo } from '../app';
import { Botao, EstadoVazio } from '../ui';

const SALDO = { fecha: 'confere', 'nao-fecha': 'não fecha', indisponivel: 'indisponível' } as const;

export function Diagnostico({ itens, aoVoltar }: { itens: ItemArquivo[]; aoVoltar: () => void }) {
  const resultados = itens.filter((i) => i.resultado).map((i) => i.resultado as ResultadoArquivo);
  const linhas = diagnosticar(resultados);
  const [copia, setCopia] = useState<{ rotulo: string; ok: boolean } | null>(null);

  // T99: copia só a estrutura do layout (nunca valores, nomes nem descrições). Falha ao copiar vira mensagem simples.
  async function copiar(rotulo: string, r: ResultadoArquivo) {
    try {
      await navigator.clipboard.writeText(assinaturaDoLayout(r.estrutura));
      setCopia({ rotulo, ok: true });
    } catch {
      setCopia({ rotulo, ok: false });
    }
  }

  return (
    <section aria-labelledby="titulo-diagnostico">
      <h1 id="titulo-diagnostico">Diagnóstico da leitura</h1>
      <p class="suave">Só contagens. Nenhum valor, nome ou descrição aparece aqui.</p>

      {linhas.length === 0 ? (
        <EstadoVazio
          icone="📊"
          titulo="Nenhum arquivo lido"
          descricao="Nenhum arquivo lido nesta visita. Volte aos extratos para carregar um arquivo PDF."
          textoAcao="Voltar aos extratos"
          aoExecutarAcao={aoVoltar}
        />
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
                <th scope="col">Assinatura do layout</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l, i) => (
                <tr key={l.rotulo}>
                  <th scope="row">{l.rotulo}</th>
                  <td>{l.paginas}</td>
                  <td>{l.linhasCandidatas}</td>
                  <td>{l.lancamentosReconstruidos}</td>
                  <td>
                    {SALDO[l.conferenciaDeSaldo]}
                    {l.progressao ? ` (${l.progressao.verificadas} linhas conferidas, ${l.progressao.divergentes} divergentes)` : ''}
                  </td>
                  <td>
                    {l.statusRotulo}
                    {l.motivo ? ` (${l.motivo})` : ''}
                  </td>
                  <td>
                    {resultados[i]?.estrutura ? (
                      <Botao
                        type="button"
                        variante="secundario"
                        rotuloAcessivel={`Copiar assinatura do layout (${l.rotulo})`}
                        aoClicar={() => void copiar(l.rotulo, resultados[i] as ResultadoArquivo)}
                      >
                        Copiar assinatura do layout
                      </Botao>
                    ) : (
                      'sem assinatura'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {copia && (
        <p
          role="status"
          class={`aviso ${copia.ok ? 'aviso-info' : 'aviso-erro'}`}
          style={{ marginTop: 'var(--esp-3)' }}
        >
          {copia.ok
            ? `Assinatura do layout de ${copia.rotulo} copiada. Ela traz só a estrutura, sem valores, nomes nem descrições.`
            : 'Não foi possível copiar. Tente de novo ou use outro navegador.'}
        </p>
      )}

      <div style={{ marginTop: 'var(--esp-4)' }}>
        <Botao type="button" variante="secundario" aoClicar={aoVoltar}>
          Voltar
        </Botao>
      </div>
    </section>
  );
}
