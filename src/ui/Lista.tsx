import type { ComponentChildren } from 'preact';

export interface ItemListaProps {
  id?: string;
  titulo: ComponentChildren;
  subtitulo?: ComponentChildren;
  valor?: ComponentChildren;
  tipoValor?: 'saida' | 'entrada' | 'neutro';
  acoes?: ComponentChildren;
}

export function ItemLista({
  titulo,
  subtitulo,
  valor,
  tipoValor = 'neutro',
  acoes,
}: ItemListaProps) {
  const classeValor =
    tipoValor === 'saida'
      ? 'lista-item-saida'
      : tipoValor === 'entrada'
        ? 'lista-item-entrada'
        : '';

  return (
    <li class="lista-item">
      <div class="lista-item-conteudo">
        <div class="lista-item-titulo">{titulo}</div>
        {subtitulo && <div class="lista-item-subtitulo">{subtitulo}</div>}
      </div>
      {valor && (
        <div class={`lista-item-valor ${classeValor}`.trim()}>
          {valor}
        </div>
      )}
      {acoes && <div class="lista-item-acoes">{acoes}</div>}
    </li>
  );
}

export interface ListaProps {
  rotulo?: string;
  children: ComponentChildren;
  classeExtra?: string;
}

export function Lista({ rotulo, children, classeExtra = '' }: ListaProps) {
  return (
    <ul
      class={`lista ${classeExtra}`.trim()}
      role="list"
      aria-label={rotulo}
    >
      {children}
    </ul>
  );
}
