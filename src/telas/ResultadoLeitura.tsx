// T09: por arquivo, banco provável, período, lançamentos lidos, conferência de saldo e status (seção 5.5).
import { agruparHistoricos } from '../leitura/historico';
import { ROTULO_STATUS, type ResultadoArquivo } from '../leitura/tipos';
import type { ItemArquivo } from '../app';
import { dataBr, mesBr, reais } from '../ui/formatar';

function textoDoSaldo(r: ResultadoArquivo): string {
  const c = r.conferencia;
  if (r.status === 'nao-suportado') return 'não se aplica';
  if (c.situacao === 'indisponivel') return 'indisponível: o arquivo não traz saldo';
  if (c.situacao === 'fecha') return 'o saldo confere';
  return c.diferencaCentavos !== null ? `o saldo não fecha (diferença de ${reais(Math.abs(c.diferencaCentavos))})` : 'o saldo não fecha';
}

export function ResultadoLeitura({ itens, aoVoltar }: { itens: ItemArquivo[]; aoVoltar: () => void }) {
  const lidos = itens.filter((i) => i.resultado);
  const { historicos, repetidos } = agruparHistoricos(lidos.map((i) => ({ nome: i.nome, resultado: i.resultado as ResultadoArquivo })));
  const totalLancamentos = historicos.reduce((n, h) => n + h.consolidado.lancamentos.length, 0);
  const emDois = historicos.reduce((n, h) => n + h.consolidado.lancamentos.filter((l) => l.apareceEmDoisExtratos).length, 0);
  return (
    <section aria-labelledby="titulo-resultado">
      <h1 id="titulo-resultado">Resultado da leitura</h1>
      {lidos.length === 0 && <p>Nenhum extrato lido. Você segue sem extrato; a entrevista e a conferência vêm nas próximas etapas desta versão de teste.</p>}
      {historicos.map((h, i) => (
        <section class="cartao" key={i} aria-label={`Histórico ${i + 1}`}>
          <h2>{`Histórico: ${h.bancoProvavel ?? 'banco não identificado'}${h.contaFinal ? `, conta ${h.contaFinal}` : ''}`}</h2>
          <dl>
            <dt>Período total</dt>
            <dd>{`${dataBr(h.periodo.inicio)} a ${dataBr(h.periodo.fim)}`}</dd>
            <dt>Arquivos no histórico</dt>
            <dd>{h.arquivos.length}</dd>
            <dt>Meses cobertos</dt>
            <dd>{h.mesesCobertos.map(mesBr).join(', ')}</dd>
            <dt>Meses faltando</dt>
            <dd>{h.mesesFaltando.length > 0 ? h.mesesFaltando.map(mesBr).join(', ') : 'nenhum'}</dd>
          </dl>
          {h.avisos.map((a, k) => (
            <p class="aviso" key={k}>
              {a.mensagem}
            </p>
          ))}
        </section>
      ))}
      {lidos.map((item) => {
        const r = item.resultado as ResultadoArquivo;
        return (
          <article class="cartao" key={item.id}>
            <h3>{item.nome}</h3>
            <dl>
              <dt>Banco provável</dt>
              <dd>{r.bancoProvavel ?? 'não identificado'}</dd>
              <dt>Período</dt>
              <dd>{r.periodo ? `${dataBr(r.periodo.inicio)} a ${dataBr(r.periodo.fim)}` : 'não identificado'}</dd>
              <dt>Lançamentos lidos</dt>
              <dd>{r.lancamentos.length}</dd>
              <dt>Conferência de saldo</dt>
              <dd>{textoDoSaldo(r)}</dd>
              <dt>Status</dt>
              <dd>
                <span class={`status status-${r.status}`}>{ROTULO_STATUS[r.status]}</span>
              </dd>
            </dl>
            <p>{r.mensagem}</p>
            {(r.status === 'parcial' || r.status === 'ambigua') && <p class="aviso">Este arquivo entra com aviso: confira com atenção cada movimentação.</p>}
          </article>
        );
      })}
      {lidos.length > 0 && (
        <p>
          Ao todo: {totalLancamentos} lançamentos
          {emDois > 0 ? `, ${emDois} aparecem em dois extratos e contam uma vez só` : ''}
          {repetidos.length > 0 ? `; ${repetidos.length} arquivo(s) repetido(s) foram ignorados` : ''}.
        </p>
      )}
      <button type="button" class="secundario" onClick={aoVoltar}>
        Voltar aos extratos
      </button>
    </section>
  );
}
