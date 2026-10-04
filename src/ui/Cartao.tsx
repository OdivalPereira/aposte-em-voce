import type { ComponentChildren } from 'preact';

export interface CartaoProps {
  titulo?: string;
  subtitulo?: string;
  children: ComponentChildren;
  rodape?: ComponentChildren;
  classeExtra?: string;
}

export function Cartao({
  titulo,
  subtitulo,
  children,
  rodape,
  classeExtra = '',
}: CartaoProps) {
  return (
    <article class={`cartao ${classeExtra}`.trim()}>
      {(titulo || subtitulo) && (
        <header class="cartao-cabecalho">
          {titulo && <h3>{titulo}</h3>}
          {subtitulo && <p class="suave">{subtitulo}</p>}
        </header>
      )}
      <div class="cartao-corpo">{children}</div>
      {rodape && <footer class="cartao-rodape">{rodape}</footer>}
    </article>
  );
}
