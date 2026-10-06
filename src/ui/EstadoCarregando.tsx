import { Botao } from './Botao';
import { Progresso } from './Progresso';

export interface EstadoCarregandoProps {
  titulo?: string;
  mensagem: string;
  textoAcao?: string;
  aoExecutarAcao?: () => void;
  progresso?: { feito: number; total: number };
}

export function EstadoCarregando({
  titulo = 'Processando no seu aparelho',
  mensagem,
  textoAcao,
  aoExecutarAcao,
  progresso,
}: EstadoCarregandoProps) {
  return (
    <section
      class="estado estado-carregando"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div class="spinner" aria-hidden="true" />
      <h3 class="estado-titulo">{titulo}</h3>
      <p class="estado-texto">{mensagem}</p>
      {progresso && (
        <Progresso
          valor={progresso.feito}
          maximo={progresso.total}
          rotulo="Páginas processadas"
        />
      )}
      {textoAcao && aoExecutarAcao && (
        <div class="estado-acoes">
          <Botao variante="secundario" aoClicar={aoExecutarAcao}>
            {textoAcao}
          </Botao>
        </div>
      )}
    </section>
  );
}
