// T08: escolher um ou mais PDFs; pedir a senha se houver (usada só no aparelho); leitura no worker, com progresso.
import { useState } from 'preact/hooks';
import type { ItemArquivo } from '../app';
import { Aviso, Botao, Campo, EstadoCarregando, EstadoVazio } from '../ui';

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
      {item.resultado?.mensagem && (
        <Aviso tipo="atencao" papel="alert">
          {item.resultado.mensagem}
        </Aviso>
      )}
      <Campo
        id={idCampo}
        tipo="password"
        rotulo={`Senha do PDF “${item.nome}”`}
        ajuda="A senha é usada só no seu aparelho e não fica guardada."
        autoComplete="off"
        valor={senha}
        aoMudar={(e) => setSenha((e.target as HTMLInputElement).value)}
      />
      <div class="estado-acoes" style={{ justifyContent: 'flex-start', marginTop: 'var(--esp-2)' }}>
        <Botao tipo="submit" variante="primario">
          Ler com a senha
        </Botao>
        <Botao tipo="button" variante="secundario" aoClicar={aoPular}>
          Pular este arquivo
        </Botao>
      </div>
    </form>
  );
}

export function Extratos({ itens, aoEscolher, aoEnviarSenha, aoPular, aoContinuar }: Props) {
  const lendo = itens.some((i) => i.estado === 'lendo');
  const aguardandoSenha = itens.some((i) => i.estado === 'senha');
  // Mesmo arquivo reenviado (mesmo hash): o segundo não conta de novo.
  const hashesVistos = new Set<string>();
  const repetido = new Set<number>();
  for (const i of itens) {
    const h = i.resultado?.hash;
    if (!h || i.resultado?.status === 'nao-suportado') continue;
    if (hashesVistos.has(h)) repetido.add(i.id);
    else hashesVistos.add(h);
  }

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

      {itens.length === 0 ? (
        <EstadoVazio
          icone="📄"
          titulo="Nenhum extrato adicionado"
          descricao="Você pode carregar seus extratos em PDF para conferir as movimentações com privacidade total no aparelho, ou continuar sem extrato."
          textoAcao="Escolher PDF"
          idInput="escolher-pdf"
          acaoSecundaria={{
            texto: 'Continuar sem extrato',
            aoExecutar: aoContinuar,
          }}
        />
      ) : (
        <>
          <div style={{ margin: 'var(--esp-3) 0' }}>
            <label class="botao botao-secundario" for="escolher-pdf">
              Acrescentar mais PDFs
            </label>
            <p class="suave">Os arquivos já lidos continuam aqui; os novos entram no mesmo histórico.</p>
          </div>

          <ul aria-live="polite">
            {itens.map((item) => (
              <li key={item.id} class="cartao" style={{ marginBottom: 'var(--esp-3)' }}>
                <header class="cartao-cabecalho">
                  <h3>{item.nome}</h3>
                </header>

                <div class="cartao-corpo">
                  {item.estado === 'lendo' && (
                    <EstadoCarregando
                      titulo={`Lendo ${item.nome}`}
                      mensagem={item.progresso ? `Lendo página ${item.progresso.feito} de ${item.progresso.total}` : 'Abrindo o arquivo…'}
                      progresso={item.progresso ? { feito: item.progresso.feito, total: item.progresso.total } : undefined}
                      textoAcao="Seguir sem este arquivo"
                      aoExecutarAcao={() => aoPular(item.id)}
                    />
                  )}

                  {item.estado === 'pronto' && item.resultado && (
                    <>
                      {item.resultado.status === 'nao-suportado' ? (
                        <Aviso tipo="erro">
                          Lido. {item.resultado.mensagem}
                        </Aviso>
                      ) : (
                        <p class="suave">Lido. {item.resultado.mensagem}</p>
                      )}
                    </>
                  )}

                  {repetido.has(item.id) && (
                    <Aviso tipo="atencao">
                      Este arquivo é igual a outro já lido e não conta de novo.
                    </Aviso>
                  )}

                  {item.estado === 'senha' && (
                    <PedidoDeSenha item={item} aoEnviar={(s) => aoEnviarSenha(item.id, s)} aoPular={() => aoPular(item.id)} />
                  )}
                </div>

                {item.estado === 'pronto' && (
                  <footer class="cartao-rodape">
                    <Botao tipo="button" variante="secundario" aoClicar={() => aoPular(item.id)}>
                      Seguir sem este arquivo
                    </Botao>
                  </footer>
                )}
              </li>
            ))}
          </ul>

          <div style={{ marginTop: 'var(--esp-4)' }}>
            <Botao
              type="button"
              variante="primario"
              aoClicar={aoContinuar}
              desabilitado={lendo || aguardandoSenha}
            >
              Ver o resultado da leitura
            </Botao>
          </div>
        </>
      )}
    </section>
  );
}
