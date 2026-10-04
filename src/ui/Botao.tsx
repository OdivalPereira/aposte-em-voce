import type { ComponentChildren } from 'preact';

export interface BotaoProps {
  children: ComponentChildren;
  variante?: 'primario' | 'secundario' | 'discreto';
  tipo?: 'button' | 'submit' | 'reset';
  aoClicar?: (evento: MouseEvent) => void;
  desabilitado?: boolean;
  rotuloAcessivel?: string;
  classeExtra?: string;
}

export function Botao({
  children,
  variante = 'primario',
  tipo = 'button',
  aoClicar,
  desabilitado = false,
  rotuloAcessivel,
  classeExtra = '',
}: BotaoProps) {
  const classeVariante =
    variante === 'secundario'
      ? 'botao-secundario secundario'
      : variante === 'discreto'
        ? 'botao-discreto link'
        : 'botao-primario';

  const classes = `botao ${classeVariante} ${classeExtra}`.trim();

  return (
    <button
      type={tipo}
      class={classes}
      onClick={aoClicar}
      disabled={desabilitado}
      aria-disabled={desabilitado ? 'true' : undefined}
      aria-label={rotuloAcessivel}
    >
      {children}
    </button>
  );
}
