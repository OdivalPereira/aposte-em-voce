import type { ComponentChildren } from 'preact';

export interface BotaoProps {
  children: ComponentChildren;
  variante?: 'primario' | 'secundario' | 'discreto';
  tipo?: 'button' | 'submit' | 'reset';
  type?: 'button' | 'submit' | 'reset';
  aoClicar?: (evento: MouseEvent) => void;
  desabilitado?: boolean;
  rotuloAcessivel?: string;
  classeExtra?: string;
}

export function Botao({
  children,
  variante = 'primario',
  tipo,
  type,
  aoClicar,
  desabilitado = false,
  rotuloAcessivel,
  classeExtra = '',
}: BotaoProps) {
  const tipoFinal = tipo ?? type ?? 'button';
  const classeVariante =
    variante === 'secundario'
      ? 'botao-secundario secundario'
      : variante === 'discreto'
        ? 'botao-discreto link'
        : 'botao-primario';

  const classes = `botao ${classeVariante} ${classeExtra}`.trim();

  return (
    <button
      type={tipoFinal}
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
