import type { ComponentChildren } from 'preact';

export interface CartaoProps {
  como?: 'article' | 'section' | 'div' | 'li';
  titulo?: string;
  subtitulo?: string;
  children: ComponentChildren;
  rodape?: ComponentChildren;
  classeExtra?: string;
  ariaLabel?: string;
}

export function Cartao({
  como: Elemento = 'article',
  titulo,
  subtitulo,
  children,
  rodape,
  classeExtra = '',
  ariaLabel,
}: CartaoProps) {
  return (
    <Elemento class={`cartao ${classeExtra}`.trim()} aria-label={ariaLabel}>
      {(titulo || subtitulo) && (
        <header class="cartao-cabecalho">
          {titulo && <h3>{titulo}</h3>}
          {subtitulo && <p class="suave">{subtitulo}</p>}
        </header>
      )}
      <div class="cartao-corpo">{children}</div>
      {rodape && <footer class="cartao-rodape">{rodape}</footer>}
    </Elemento>
  );
}
