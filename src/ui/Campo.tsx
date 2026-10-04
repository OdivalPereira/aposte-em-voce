export interface CampoProps {
  id: string;
  rotulo: string;
  tipo?: 'text' | 'password' | 'email';
  valor?: string;
  valorPadrao?: string;
  aoMudar?: (evento: Event) => void;
  ajuda?: string;
  erro?: string;
  obrigatorio?: boolean;
  desabilitado?: boolean;
  placeholder?: string;
  autoComplete?: string;
}

export function Campo({
  id,
  rotulo,
  tipo = 'text',
  valor,
  valorPadrao,
  aoMudar,
  ajuda,
  erro,
  obrigatorio = false,
  desabilitado = false,
  placeholder,
  autoComplete,
}: CampoProps) {
  const idAjuda = ajuda ? `${id}-ajuda` : undefined;
  const idErro = erro ? `${id}-erro` : undefined;
  const idsDescricao = [idAjuda, idErro].filter(Boolean).join(' ') || undefined;

  return (
    <div class={`campo ${erro ? 'campo-com-erro' : ''}`.trim()}>
      <label for={id} class="campo-rotulo">
        {rotulo}
        {obrigatorio && <span class="campo-obrigatorio" aria-hidden="true"> *</span>}
      </label>
      {ajuda && (
        <span id={idAjuda} class="campo-ajuda">
          {ajuda}
        </span>
      )}
      {tipo === 'password' ? (
        <input
          id={id}
          name={id}
          type="password"
          class="campo-input"
          value={valor}
          defaultValue={valorPadrao}
          onInput={aoMudar}
          disabled={desabilitado}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={obrigatorio}
          aria-invalid={erro ? 'true' : 'false'}
          aria-describedby={idsDescricao}
        />
      ) : tipo === 'email' ? (
        <input
          id={id}
          name={id}
          type="email"
          class="campo-input"
          value={valor}
          defaultValue={valorPadrao}
          onInput={aoMudar}
          disabled={desabilitado}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={obrigatorio}
          aria-invalid={erro ? 'true' : 'false'}
          aria-describedby={idsDescricao}
        />
      ) : (
        <input
          id={id}
          name={id}
          type="text"
          class="campo-input"
          value={valor}
          defaultValue={valorPadrao}
          onInput={aoMudar}
          disabled={desabilitado}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={obrigatorio}
          aria-invalid={erro ? 'true' : 'false'}
          aria-describedby={idsDescricao}
        />
      )}
      {erro && (
        <span id={idErro} class="campo-erro" role="alert">
          <span aria-hidden="true">⚠️</span> {erro}
        </span>
      )}
    </div>
  );
}
