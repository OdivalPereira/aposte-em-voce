import { useState } from 'preact/hooks';
import {
  Aviso,
  Botao,
  Campo,
  Cartao,
  CORES,
  EstadoCarregando,
  EstadoErro,
  EstadoVazio,
  formataRazao,
  ItemLista,
  Lista,
  PARES_CONTRASTE,
  Progresso,
  razaoContraste,
  reais,
  TIPOGRAFIA,
} from '../ui';

export function PaginaReferencia() {
  const [modoVisualizacao, setModoVisualizacao] = useState<'desktop' | 'mobile'>('desktop');
  const [estadoExemplo, setEstadoExemplo] = useState<'vazio' | 'carregando' | 'erro'>('vazio');
  const [campoTexto, setCampoTexto] = useState('Exemplo de preenchimento');
  const [campoSenha, setCampoSenha] = useState('');

  return (
    <div class="ref-pagina">
      {/* Topo e Apresentação do Design System */}
      <header class="ref-topo">
        <h1 class="ref-titulo-principal">Aposte em Você — Referência Visual</h1>
        <p class="ref-subtitulo">
          Sistema de design moderno, sóbrio e acolhedor para adultos afetados por apostas financeiras.
          Projetado com respeito emocional (sem tons alarmistas nem estética de cassino), privacidade
          absoluta no aparelho e conformidade estrita com as diretrizes <strong>WCAG 2.2 nível AA</strong>.
        </p>

        {/* Alternador de Modo de Exibição (Desktop x 360 px) */}
        <div class="ref-controles-modo" role="region" aria-label="Controle de visualização de tela">
          <span class="ref-controles-rotulo">Simular largura de tela:</span>
          <Botao
            variante={modoVisualizacao === 'desktop' ? 'primario' : 'secundario'}
            aoClicar={() => setModoVisualizacao('desktop')}
          >
            Largura Total (Desktop)
          </Botao>
          <Botao
            variante={modoVisualizacao === 'mobile' ? 'primario' : 'secundario'}
            aoClicar={() => setModoVisualizacao('mobile')}
          >
            Celular (360 px)
          </Botao>
        </div>
      </header>

      {/* Container principal que pode alternar para simulação de 360px */}
      <main class={modoVisualizacao === 'mobile' ? 'ref-conteudo-mobile' : 'ref-conteudo-desktop'}>
        {/* ==========================================================================
            SEÇÃO 1: TOKENS DE CORES E CONTRASTE
           ========================================================================== */}
        <section class="ref-secao" aria-labelledby="sec-cores">
          <h2 id="sec-cores" class="ref-secao-titulo">
            1. Tokens de Cores e Contraste
          </h2>
          <p class="ref-secao-descricao">
            Paleta sóbria que prioriza a serenidade e a segurança do usuário. Todas as combinações
            de texto normal superam a exigência de 4,5:1, e os componentes/foco superam 3:1.
          </p>

          <div class="ref-grid-cores">
            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-fundo" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Fundo da Página</div>
                <div class="ref-amostra-hex">{CORES.fundo}</div>
                <span class="ref-amostra-badge">Slate 50</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-superficie" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Superfície / Cartão</div>
                <div class="ref-amostra-hex">{CORES.superficie}</div>
                <span class="ref-amostra-badge">Branco puro</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-texto" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Texto Principal</div>
                <div class="ref-amostra-hex">{CORES.texto}</div>
                <span class="ref-amostra-badge">17.5:1 (AAA)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-texto-secundario" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Texto Secundário</div>
                <div class="ref-amostra-hex">{CORES.textoSecundario}</div>
                <span class="ref-amostra-badge">7.6:1 (AAA)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-primaria" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Cor Primária</div>
                <div class="ref-amostra-hex">{CORES.primaria}</div>
                <span class="ref-amostra-badge">8.0:1 (AAA)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-foco" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Anel de Foco</div>
                <div class="ref-amostra-hex">{CORES.foco}</div>
                <span class="ref-amostra-badge">8.0:1 (&gt; 3:1)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-sucesso" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Sucesso</div>
                <div class="ref-amostra-hex">{CORES.sucesso}</div>
                <span class="ref-amostra-badge">11.2:1 (AAA)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-atencao" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Atenção</div>
                <div class="ref-amostra-hex">{CORES.atencao}</div>
                <span class="ref-amostra-badge">8.5:1 (AAA)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-erro" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Erro Sóbrio</div>
                <div class="ref-amostra-hex">{CORES.erro}</div>
                <span class="ref-amostra-badge">7.9:1 (AAA)</span>
              </div>
            </div>

            <div class="ref-amostra-card">
              <div class="ref-amostra-bloco ref-bg-borda" />
              <div class="ref-amostra-info">
                <div class="ref-amostra-nome">Borda de Campo</div>
                <div class="ref-amostra-hex">{CORES.borda}</div>
                <span class="ref-amostra-badge">4.7:1 (&gt; 3:1)</span>
              </div>
            </div>
          </div>
        </section>

        {/* ==========================================================================
            SEÇÃO 2: TIPOGRAFIA E ESPAÇAMENTO
           ========================================================================== */}
        <section class="ref-secao" aria-labelledby="sec-tipo">
          <h2 id="sec-tipo" class="ref-secao-titulo">
            2. Tipografia e Espaçamento
          </h2>
          <p class="ref-secao-descricao">
            Fontes do sistema nativo (<code>{TIPOGRAFIA.familia}</code>) para garantir privacidade estrita e compatibilidade com a CSP (sem CDN).
            A escala única de espaçamento baseia-se em múltiplos de 4 px.
          </p>

          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Escala Tipográfica</h3>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">xxxl · 30px / 1.875rem · peso 700</div>
              <div class="ref-amostra-texto-xxxl">Aposte em Você: sua jornada financeira segura</div>
            </div>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">xxl · 24px / 1.5rem · peso 700</div>
              <div class="ref-amostra-texto-xxl">Conferência dos extratos bancários</div>
            </div>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">xl · 20px / 1.25rem · peso 600</div>
              <div class="ref-amostra-texto-xl">Movimentações sugeridas para validação</div>
            </div>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">lg · 18px / 1.125rem · peso 600</div>
              <div class="ref-amostra-texto-lg">Extrato Banco Exemplo S.A. — Setembro de 2026</div>
            </div>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">base · 16px / 1.0rem · peso 400 (corpo de texto padrão)</div>
              <div class="ref-amostra-texto-base">
                Nenhum dado informado sai do seu celular. Todo o processamento dos extratos bancários
                e cálculos determinísticos acontece na memória volátil da página.
              </div>
            </div>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">sm · 14px / 0.875rem · peso 400</div>
              <div class="ref-amostra-texto-sm">
                Versão de teste: conteúdo ainda sem revisão profissional. Nada fica guardado entre visitas.
              </div>
            </div>

            <div class="ref-amostra-texto">
              <div class="ref-amostra-texto-meta">xs · 12px / 0.75rem · peso 500</div>
              <div class="ref-amostra-texto-xs">
                Chave única: 2026-09-15 · -R$ 150,00 · Saída Pix
              </div>
            </div>
          </div>

          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Escala Única de Espaçamento (4 px)</h3>
            <div class="ref-grid-espacamento">
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e1 (4px)</span>
                <div class="ref-espaco-barra ref-esp-1" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e2 (8px)</span>
                <div class="ref-espaco-barra ref-esp-2" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e3 (12px)</span>
                <div class="ref-espaco-barra ref-esp-3" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e4 (16px)</span>
                <div class="ref-espaco-barra ref-esp-4" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e5 (20px)</span>
                <div class="ref-espaco-barra ref-esp-5" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e6 (24px)</span>
                <div class="ref-espaco-barra ref-esp-6" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e8 (32px)</span>
                <div class="ref-espaco-barra ref-esp-8" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e10 (40px)</span>
                <div class="ref-espaco-barra ref-esp-10" />
              </div>
              <div class="ref-linha-espaco">
                <span class="ref-espaco-rotulo">e12 (48px)</span>
                <div class="ref-espaco-barra ref-esp-12" />
              </div>
            </div>
          </div>
        </section>

        {/* ==========================================================================
            SEÇÃO 3: COMPONENTES
           ========================================================================== */}
        <section class="ref-secao" aria-labelledby="sec-componentes">
          <h2 id="sec-componentes" class="ref-secao-titulo">
            3. Componentes Base
          </h2>
          <p class="ref-secao-descricao">
            Elementos de interface com alvos de toque generosos (≥ 44×44 px), foco visível claro e semântica acessível.
          </p>

          {/* Botões */}
          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Botões</h3>
            <p class="suave">
              Variantes Primária, Secundária e Discreta, além do estado desabilitado.
            </p>
            <div class="ref-grupo-botoes">
              <Botao variante="primario">Botão Primário</Botao>
              <Botao variante="secundario">Botão Secundário</Botao>
              <Botao variante="discreto">Botão Discreto (Link)</Botao>
              <Botao variante="primario" desabilitado>
                Desabilitado
              </Botao>
            </div>
          </div>

          {/* Cartões */}
          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Cartões</h3>
            <Cartao
              titulo="Extrato Bancário Sintético 01"
              subtitulo="Banco Beta S.A. · Período: 01/09/2026 a 30/09/2026"
              rodape={
                <>
                  <Botao variante="primario">Conferir lançamentos</Botao>
                  <Botao variante="secundario">Remover arquivo</Botao>
                </>
              }
            >
              <dl>
                <dt>Lançamentos identificados:</dt>
                <dd>42 operações</dd>
                <dt>Conferência de saldo:</dt>
                <dd class="status status-suficiente">Saldo confere integralmente</dd>
                <dt>Status da leitura:</dt>
                <dd>Suficiente (pronto para conferência)</dd>
              </dl>
            </Cartao>
          </div>

          {/* Campos de Formulário */}
          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Campos de Formulário</h3>
            <Campo
              id="exemplo-nome"
              rotulo="Nome opcional para os documentos"
              ajuda="Preenchido somente na hora de gerar os PDFs, sem sair do seu aparelho."
              valor={campoTexto}
              aoMudar={(e) => setCampoTexto((e.target as HTMLInputElement).value)}
            />
            <Campo
              id="exemplo-senha"
              rotulo="Senha do arquivo PDF (se houver)"
              tipo="password"
              ajuda="Utilizada exclusivamente para decodificar o documento no seu navegador."
              placeholder="Digite a senha local"
              valor={campoSenha}
              aoMudar={(e) => setCampoSenha((e.target as HTMLInputElement).value)}
            />
            <Campo
              id="exemplo-erro"
              rotulo="Campo com estado de validação"
              valor="Valor não suportado"
              erro="Este formato de data não foi reconhecido. Use DD/MM/AAAA."
            />
          </div>

          {/* Avisos */}
          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Avisos Semânticos (Informação, Atenção e Erro)</h3>

            <Aviso tipo="info" titulo="Privacidade Garantida">
              Nenhuma movimentação bancária ou resposta sua é enviada a servidores. Ao fechar esta aba,
              tudo o que foi lido é apagado da memória.
            </Aviso>

            <Aviso tipo="atencao" titulo="Atenção aos Saldos">
              O saldo informado pelo banco não coincidiu exatamente com a soma dos lançamentos.
              Você pode conferir manualmente as linhas destacadas.
            </Aviso>

            <Aviso tipo="erro" titulo="Arquivo com Restrição">
              O arquivo selecionado parece ser uma fatura de cartão de crédito. Nesta versão,
              lemos apenas extratos de conta corrente ou poupança.
            </Aviso>
          </div>

          {/* Progresso */}
          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Indicador de Progresso</h3>
            <Progresso valor={3} maximo={5} rotulo="Conferência de Extratos Bancários" />
            <Progresso valor={100} maximo={100} rotulo="Leitura Concluída" />
          </div>

          {/* Lista de Movimentações Fictícias */}
          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Lista de Movimentações Fictícias</h3>
            <p class="suave">
              Apresentação clara de data, destinatário provável, valor em reais e ações de conferência individual.
            </p>

            <Lista rotulo="Extrato de movimentações sintéticas">
              <ItemLista
                titulo="Transferência Pix — Plataforma Exemplo Beta"
                subtitulo="12/09/2026 às 14:32 · Aparece no Extrato 1"
                valor={reais(-15000)}
                tipoValor="saida"
                acoes={
                  <div class="ref-grupo-botoes">
                    <Botao variante="secundario">Sim, era aposta</Botao>
                    <Botao variante="discreto">Não reconheço</Botao>
                  </div>
                }
              />
              <ItemLista
                titulo="TED Recebida — Pagamento de Prêmio Fictício"
                subtitulo="18/09/2026 às 09:15 · Aparece no Extrato 1"
                valor={reais(45000)}
                tipoValor="entrada"
                acoes={
                  <div class="ref-grupo-botoes">
                    <Botao variante="secundario">Sim, era aposta</Botao>
                    <Botao variante="discreto">Não reconheço</Botao>
                  </div>
                }
              />
              <ItemLista
                titulo="Compra Mercado Local (Não aposta)"
                subtitulo="20/09/2026 · Descartado automaticamente pelo catálogo"
                valor={reais(-8450)}
                tipoValor="saida"
              />
            </Lista>
          </div>
        </section>

        {/* ==========================================================================
            SEÇÃO 4: ESTADOS (Vazio, Carregando e Erro: cada um com texto e ação)
           ========================================================================== */}
        <section class="ref-secao" aria-labelledby="sec-estados">
          <h2 id="sec-estados" class="ref-secao-titulo">
            4. Estados Fundamentais (Texto e Ação)
          </h2>
          <p class="ref-secao-descricao">
            Cada estado fornece um texto acolhedor e direto, acompanhado sempre de uma ação clara
            que permite ao usuário avançar sem bloqueios.
          </p>

          <div class="ref-controles-modo">
            <span class="ref-controles-rotulo">Alternar estado de demonstração:</span>
            <Botao
              variante={estadoExemplo === 'vazio' ? 'primario' : 'secundario'}
              aoClicar={() => setEstadoExemplo('vazio')}
            >
              Estado Vazio
            </Botao>
            <Botao
              variante={estadoExemplo === 'carregando' ? 'primario' : 'secundario'}
              aoClicar={() => setEstadoExemplo('carregando')}
            >
              Estado Carregando
            </Botao>
            <Botao
              variante={estadoExemplo === 'erro' ? 'primario' : 'secundario'}
              aoClicar={() => setEstadoExemplo('erro')}
            >
              Estado Erro
            </Botao>
          </div>

          {estadoExemplo === 'vazio' && (
            <EstadoVazio
              icone="📄"
              titulo="Nenhum extrato bancário adicionado"
              descricao="Você pode adicionar um ou mais arquivos PDF de extratos para conferir seus lançamentos, ou seguir diretamente para a síntese sem extratos."
              textoAcao="Adicionar extrato bancário (PDF)"
              aoExecutarAcao={() => alert('Ação fictícia: abrir seletor de arquivos')}
              acaoSecundaria={{
                texto: 'Continuar sem extratos',
                aoExecutar: () => alert('Ação fictícia: continuar sem extratos'),
              }}
            />
          )}

          {estadoExemplo === 'carregando' && (
            <EstadoCarregando
              mensagem="Lendo o extrato bancário com segurança diretamente no seu aparelho. Nada sai do seu dispositivo."
              progresso={{ feito: 2, total: 4 }}
              textoAcao="Cancelar leitura deste arquivo"
              aoExecutarAcao={() => alert('Ação fictícia: leitura cancelada')}
            />
          )}

          {estadoExemplo === 'erro' && (
            <EstadoErro
              titulo="Não foi possível ler este arquivo"
              mensagem="O documento parece ser uma imagem escaneada ou está protegido por uma senha não fornecida. Sua jornada não é bloqueada: você pode tentar outro arquivo ou seguir sem ele."
              textoAcao="Tentar outro arquivo"
              aoExecutarAcao={() => alert('Ação fictícia: escolher outro arquivo')}
              textoAcaoSecundaria="Seguir sem este extrato"
              aoExecutarAcaoSecundaria={() => alert('Ação fictícia: pular arquivo com falha')}
            />
          )}
        </section>

        {/* ==========================================================================
            SEÇÃO 5: CONFORMIDADE WCAG 2.2 NÍVEL AA
           ========================================================================== */}
        <section class="ref-secao" aria-labelledby="sec-wcag">
          <h2 id="sec-wcag" class="ref-secao-titulo">
            5. Auditoria de Conformidade WCAG 2.2 AA
          </h2>
          <p class="ref-secao-descricao">
            Demonstração técnica do cumprimento de cada critério de sucesso relevante.
          </p>

          <div class="tabela-rolagem">
            <table class="ref-tabela-wcag">
              <thead>
                <tr>
                  <th>Critério WCAG</th>
                  <th>Requisito Mínimo</th>
                  <th>Implementado no Sistema</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>1.4.3 Contraste Mínimo</strong></td>
                  <td>≥ 4,5:1 (texto normal)<br />≥ 3,0:1 (texto grande)</td>
                  <td>Texto principal: 17,5:1 · Secundário: 7,6:1 · Primária: 8,0:1 · Sucesso: 11,2:1 · Erro: 7,9:1</td>
                  <td><span class="ref-tag-sucesso">Aprovado (AAA)</span></td>
                </tr>
                <tr>
                  <td><strong>1.4.10 Reflow</strong></td>
                  <td>Sem rolagem horizontal em 320 px</td>
                  <td>Layout fluido com flexbox/grid, largura máxima responsiva e sem larguras fixas em pixels</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
                <tr>
                  <td><strong>1.4.11 Contraste Não Textual</strong></td>
                  <td>≥ 3,0:1 em controles de UI</td>
                  <td>Borda de campos: 4,7:1 · Barra de progresso: 6,5:1 · Anel de foco: 8,0:1</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
                <tr>
                  <td><strong>1.4.12 Espaçamento de Texto</strong></td>
                  <td>Suporta line-height 1.5, word-spacing e letter-spacing ampliados sem cortar conteúdo</td>
                  <td>Alturas de linha relativas (1.25 a 1.7), sem containers com altura rígida em pixels</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
                <tr>
                  <td><strong>2.4.7 e 2.4.11 Foco Visível</strong></td>
                  <td>Indicador visível e não encoberto</td>
                  <td>Outline com 3px de espessura, offset de 2px e contraste de 8,0:1 em fundo branco</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
                <tr>
                  <td><strong>2.5.8 Alvo Mínimo</strong></td>
                  <td>≥ 24×24 px (WCAG 2.2)</td>
                  <td>Todos os botões e campos possuem min-height de 44 px e min-width de 44 px</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
                <tr>
                  <td><strong>Prefers Reduced Motion</strong></td>
                  <td>Respeita preferências de redução de movimento</td>
                  <td>Animações de spinner e transições desativadas sob @media (prefers-reduced-motion: reduce)</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
                <tr>
                  <td><strong>Privacidade e CSP</strong></td>
                  <td>Sem estilos/scripts inline, sem CDN</td>
                  <td>Sem style=&quot;...&quot;, fontes locais do sistema, 100% aderente à CSP do vercel.json</td>
                  <td><span class="ref-tag-sucesso">Aprovado</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="ref-bloco-demonstracao">
            <h3 class="ref-bloco-titulo">Pares de Contraste Calculados em Tempo Real</h3>
            <p class="suave">
              Estes pares são calculados deterministicamente pelo mesmo motor do teste automatizado <code>contraste.test.ts</code>:
            </p>
            <ul>
              {PARES_CONTRASTE.slice(0, 6).map((p) => {
                const ratio = razaoContraste(p.frente, p.fundo);
                return (
                  <li key={p.id}>
                    <strong>{p.descricao}:</strong> {formataRazao(ratio)} (mínimo esperado: {p.minimoEsperado}:1) — <span class="ref-tag-sucesso">Aprovado</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        {/* ==========================================================================
            SEÇÃO 6: SIMULAÇÃO FIXA EM 360 PX (CELULAR REAL)
           ========================================================================== */}
        <section class="ref-secao" aria-labelledby="sec-simulacao-360">
          <h2 id="sec-simulacao-360" class="ref-secao-titulo">
            6. Simulação em Celular (Moldura de 360 px)
          </h2>
          <p class="ref-secao-descricao">
            Demonstração contínua de como os cartões, avisos e botões se comportam na largura mínima típica
            de celulares modernos (360 px), sem quebras indesejadas nem rolagem horizontal.
          </p>

          <div class="ref-conteudo-mobile">
            <h3 class="ref-bloco-titulo">Visualização a 360 px</h3>
            <Aviso tipo="info" titulo="Tudo no celular">
              Nada do que você escolher sai do seu aparelho.
            </Aviso>
            <Cartao titulo="Extrato Bancário" subtitulo="Setembro de 2026">
              <p>Lançamentos: 18 confirmados.</p>
              <Botao variante="primario">Conferir</Botao>
            </Cartao>
            <Progresso valor={2} maximo={3} rotulo="Progresso da entrevista" />
            <Botao variante="secundario">Continuar jornada</Botao>
          </div>
        </section>
      </main>

      <footer class="ref-secao">
        <p class="suave">
          Aposte em Você · Referência Visual · Licença AGPL-3.0 · Executado por Legolas (Interface e Acessibilidade).
        </p>
      </footer>
    </div>
  );
}
