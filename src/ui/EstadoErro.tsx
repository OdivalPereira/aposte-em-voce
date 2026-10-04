import type { ComponentChildren } from 'preact';
import { Botao } from './Botao';

export interface EstadoErroProps {
  titulo: string;
  mensagem: ComponentChildren;
  textoAcao: string;
  aoExecutarAcao: () => void;
  textoAcaoSecundaria?: string;
  aoExecutarAcaoSecundaria?: () => void;
}

export function EstadoErro({
  titulo,
  mensagem,
  textoAcao,
  aoExecutarAcao,
  textoAcaoSecundaria,
  aoExecutarAcaoSecundaria,
}: EstadoErroProps) {
  return (
    <section
      class="estado estado-erro"
      role="alert"
      aria-labelledby="estado-erro-titulo"
    >
      <div class="estado-icone" aria-hidden="true">
        ⚠️
      </div>
      <h3 id="estado-erro-titulo" class="estado-titulo">
        {titulo}
      </h3>
      <p class="estado-texto">{mensagem}</p>
      <div class="estado-acoes">
        <Botao variante="primario" aoClicar={aoExecutarAcao}>
          {textoAcao}
        </Botao>
        {textoAcaoSecundaria && aoExecutarAcaoSecundaria && (
          <Botao variante="secundario" aoClicar={aoExecutarAcaoSecundaria}>
            {textoAcaoSecundaria}
          </Botao>
        )}
      </div>
    </section>
  );
}
