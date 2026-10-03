// T08: escolher um ou mais PDFs; pedir a senha se houver (usada só no aparelho); leitura no worker, com progresso.
import { useState } from 'preact/hooks';
import type { ItemArquivo } from '../app';

interface Props {
  itens: ItemArquivo[];
  aoEscolher: (arquivos: File[]) => void;
  aoEnviarSenha: (id: number, senha: string) => void;
  aoPular: (id: number) => void;
  aoContinuar: () => void;
}

function PedidoDeSenha({ item, aoEnviar, aoPular }: { item: ItemArquivo; aoEnviar: (senha: string) => void; aoPular: () => void }) {
  const [senha, setSenha] = useState('');
  const idCampo = `senha-${item.id}`;
  return (
    <form
      class="cartao"
      onSubmit={(e) => {
        e.preventDefault();
        aoEnviar(senha);
        setSenha('');
      }}
    >
      <p role="alert">{item.resultado?.mensagem}</p>
      <label for={idCampo}>Senha do PDF “{item.nome}”</label>
      <input id={idCampo} type="password" autocomplete="off" value={senha} onInput={(e) => setSenha((e.target as HTMLInputElement).value)} />
      <p class="suave">A senha é usada só no seu aparelho e não fica guardada.</p>
      <button type="submit">Ler com a senha</button>
      <button type="button" class="secundario" onClick={aoPular}>
        Pular este arquivo
      </button>
    </form>
  );
}

export function Extratos({ itens, aoEscolher, aoEnviarSenha, aoPular, aoContinuar }: Props) {
  const lendo = itens.some((i) => i.estado === 'lendo');
  const aguardandoSenha = itens.some((i) => i.estado === 'senha');
  return (
    <section aria-labelledby="titulo-extratos">
      <h1 id="titulo-extratos">Extratos (opcional)</h1>
      <p>Escolha um ou mais extratos em PDF baixados do seu banco. A leitura acontece neste aparelho; nada é enviado.</p>
      <p class="suave">Você pode seguir sem extrato.</p>

      <input
        id="escolher-pdf"
        class="entrada-arquivo"
        type="file"
        accept="application/pdf,.pdf"
        multiple
        onChange={(e) => {
          const campo = e.target as HTMLInputElement;
          const arquivos = [...(campo.files ?? [])];
          campo.value = '';
          if (arquivos.length > 0) aoEscolher(arquivos);
        }}
      />
      <label class="botao" for="escolher-pdf">
        Escolher PDF
      </label>

      <ul aria-live="polite">
        {itens.map((item) => (
          <li key={item.id} class="cartao">
            <strong>{item.nome}</strong>
            {item.estado === 'lendo' && (
              <p>
                <progress max={item.progresso?.total ?? 1} value={item.progresso?.feito ?? 0} aria-label={`Lendo ${item.nome}`} />
                <span>{item.progresso ? `Lendo página ${item.progresso.feito} de ${item.progresso.total}` : 'Abrindo o arquivo…'}</span>
              </p>
            )}
            {item.estado === 'pronto' && item.resultado && <p>Lido. {item.resultado.status === 'nao-suportado' ? item.resultado.mensagem : ''}</p>}
            {item.estado === 'senha' && <PedidoDeSenha item={item} aoEnviar={(s) => aoEnviarSenha(item.id, s)} aoPular={() => aoPular(item.id)} />}
            {item.estado === 'pronto' && (
              <button type="button" class="secundario" onClick={() => aoPular(item.id)}>
                Seguir sem este arquivo
              </button>
            )}
          </li>
        ))}
      </ul>

      <button type="button" onClick={aoContinuar} disabled={lendo || aguardandoSenha}>
        {itens.length > 0 ? 'Ver o resultado da leitura' : 'Continuar sem extrato'}
      </button>
    </section>
  );
}
