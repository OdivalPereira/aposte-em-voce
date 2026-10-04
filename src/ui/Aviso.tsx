import type { ComponentChildren } from 'preact';

export interface AvisoProps {
  tipo?: 'info' | 'atencao' | 'erro';
  titulo?: string;
  children: ComponentChildren;
  classeExtra?: string;
  papel?: 'alert' | 'status';
}

export function Aviso({
  tipo = 'atencao',
  titulo,
  children,
  classeExtra = '',
  papel,
}: AvisoProps) {
  const classeTipo =
    tipo === 'info'
      ? 'aviso-info'
      : tipo === 'erro'
        ? 'aviso-erro'
        : 'aviso-atencao';

  const icone =
    tipo === 'info'
      ? 'ℹ️'
      : tipo === 'erro'
        ? '🛑'
        : '⚠️';

  const papelAcessivel = papel ?? (tipo === 'erro' ? 'alert' : 'status');

  return (
    <div
      class={`aviso ${classeTipo} ${classeExtra}`.trim()}
      role={papelAcessivel}
      aria-live={tipo === 'erro' ? 'assertive' : 'polite'}
    >
      {titulo && (
        <div class="aviso-titulo">
          <span aria-hidden="true">{icone} </span>
          {titulo}
        </div>
      )}
      <div class="aviso-conteudo">{children}</div>
    </div>
  );
}
