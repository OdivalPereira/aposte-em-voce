import type { ComponentChildren } from 'preact';
import { Botao } from './Botao';

export interface EstadoVazioProps {
  titulo: string;
  descricao: ComponentChildren;
  textoAcao: string;
  aoExecutarAcao: () => void;
  icone?: string;
  acaoSecundaria?: {
    texto: string;
    aoExecutar: () => void;
  };
}

export function EstadoVazio({
  titulo,
  descricao,
  textoAcao,
  aoExecutarAcao,
  icone = '📄',
  acaoSecundaria,
}: EstadoVazioProps) {
  return (
    <section class="estado estado-vazio" aria-labelledby="estado-vazio-titulo">
      <div class="estado-icone" aria-hidden="true">
        {icone}
      </div>
      <h3 id="estado-vazio-titulo" class="estado-titulo">
        {titulo}
      </h3>
      <p class="estado-texto">{descricao}</p>
      <div class="estado-acoes">
        <Botao variante="primario" aoClicar={aoExecutarAcao}>
          {textoAcao}
        </Botao>
        {acaoSecundaria && (
          <Botao variante="secundario" aoClicar={acaoSecundaria.aoExecutar}>
            {acaoSecundaria.texto}
          </Botao>
        )}
      </div>
    </section>
  );
}
