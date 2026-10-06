export interface ProgressoProps {
  valor: number;
  maximo: number;
  rotulo?: string;
  mostrarTexto?: boolean;
}

export function Progresso({
  valor,
  maximo,
  rotulo = 'Progresso',
  mostrarTexto = true,
}: ProgressoProps) {
  const percentual = maximo > 0 ? Math.round((valor / maximo) * 100) : 0;
  const textoProgresso = `${valor} de ${maximo} (${percentual}%)`;

  return (
    <div class="progresso-container" role="region" aria-label={rotulo}>
      {mostrarTexto && (
        <div class="progresso-cabecalho">
          <span>{rotulo}</span>
          <span aria-hidden="true">{textoProgresso}</span>
        </div>
      )}
      <progress
        value={valor}
        max={maximo}
        aria-label={`${rotulo}: ${textoProgresso}`}
      >
        {textoProgresso}
      </progress>
    </div>
  );
}
