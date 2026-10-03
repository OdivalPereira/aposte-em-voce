# Aposte em Você — especificação da onda 1 (rascunho do lote 2, 03/10/2026)

**Fontes**
- `planejamento-consolidado-claude-cloud-aposte-em-voce-2026-10-02.md` (seções 7 a 19).
- Decisões N3, N4, N8–N14 e N20–N22 do plano v1.
- Entrevista C45, C46, C56, C65 e C66 (`sociedade/entrevista-nuvem-2026-10-03.md`).

**Destino:** `docs/onda-1.md` no repositório `aposte-em-voce`. O Círdan escreve as ordens a partir daqui.

## 1. O que é a onda 1

Um site **estático**, aberto por link no celular, gratuito, para **adultos** no Brasil. A pessoa:
- responde a uma entrevista;
- se quiser, carrega extratos bancários em PDF;
- confere uma a uma as movimentações sugeridas como apostas;
- recebe um resultado e baixa quatro documentos.

**Tudo acontece no aparelho. Nada do que a pessoa informa sai do celular.**

Onda 2, fora daqui: conta por e-mail e senha, guarda de 6 meses, e-mails e redação por IA (N3).

## 2. Princípios que nenhuma etapa pode quebrar

| # | Princípio | Origem |
|---|---|---|
| 1 | Nada sai do aparelho: sem servidor de dados, sem analytics, sem script de terceiros, sem fonte ou CDN externos. A CSP bloqueia, e um teste de ponta a ponta prova que não houve envio | N8, N20, seção 16 |
| 2 | Nada fica guardado entre visitas: dados só na memória da página; nada em `localStorage`, IndexedDB ou cookies. Guardar = baixar os PDFs | C66 |
| 3 | Desenvolvimento só com dados sintéticos. O teste com extratos reais é feito por Odival, no celular dele, e nada é enviado | N10, Q24/Q57 |
| 4 | Cálculo, triagem e textos são separados: somas, sinais, saldos, duplicidades e pontuação são código determinístico com teste. Os textos são modelos fixos, sem IA | seção 19.3, N3 |
| 5 | Sem diagnóstico, laudo, percentual de "chance de ludopatia" nem promessa jurídica ou de devolução | seções 10.3, 14.3–14.5 |
| 6 | **Valor enviado não é perda.** Rótulos: "valor enviado", "valor recebido" e "diferença observada" | seção 13.3 |
| 7 | **Cada movimentação é confirmada individualmente**, sem confirmação em grupo; itens incertos ficam fora dos totais confirmados | seção 12.4 |
| 8 | Funciona sem extrato e sem cadastro, e a jornada nunca trava por falta de PDF | seção 7.2 |
| 9 | Versão de teste, com aviso visível de "conteúdo ainda sem revisão profissional"; textos só com fontes oficiais datadas | N14 |
| 10 | Ajuda de urgência sempre à mão; nenhuma pergunta de triagem de risco à vida | C65 |

## 3. Stack e estrutura

**Stack** (licenças compatíveis com a AGPL-3.0, N22)

| Função | Escolha |
|---|---|
| Linguagem e build | TypeScript e Vite |
| Interface | Preact (pequeno, bom para celular simples) |
| Leitura de PDF | `pdfjs-dist` num Web Worker, carregado só quando a pessoa escolhe um PDF. O worker é servido do próprio site |
| Geração de PDF | `pdf-lib` com `@pdf-lib/fontkit` e a fonte Noto Sans (OFL), embutida, para os acentos |
| Testes | Vitest (unidade e leitura), Playwright (ponta a ponta, perfil de celular, rede) e axe-core (acessibilidade) |
| Qualidade | ESLint e `tsc --noEmit` |
| Hospedagem | Vercel, estático, com cabeçalhos em `vercel.json` (N11) |

**Estrutura do repositório**

```
aposte-em-voce/
  package.json  vite.config.ts  vercel.json  tsconfig.json
  src/
    app.tsx  telas/  ui/
    leitura/      worker.ts extrair.ts reconstruir.ts normalizar.ts conferir.ts consolidar.ts diagnostico.ts
    catalogo/     catalogo.json sugerir.ts
    entrevista/   pgsi.ts roteiro.ts financeiro.ts
    resultado/    calculos.ts
    documentos/   gerar.ts modelos/ fontes/
    conteudo/     orientacoes.ts urgencia.ts privacidade.ts
  scripts/gerar-pdfs-sinteticos.ts
  tests/unit/  tests/leitura/  tests/fixtures/{pdfs,esperado}/  tests/e2e/
  docs/  sociedade/  sociedade-do-codigo/ (cópia do pacote, C20)  .claude/  .github/
```

**Comandos do perfil:**
- teste: `npm test` (Vitest, mais Playwright em modo CI);
- lint: `npm run lint`;
- build: `npm run build`.

## 4. Jornada e telas

| Tela | Conteúdo | Notas |
|---|---|---|
| T01 Acolhimento | Para que serve, gratuito, para adultos, versão de teste, "nada sai do seu celular; ao fechar, tudo some" | Botão "Precisa de ajuda agora?" fixo em todas as telas (C65) |
| T02 Idade | "Você tem 18 anos ou mais?" | "Não" leva à T02b: orientação geral (CVV 188, conversar com um adulto de confiança, escola ou CRAS), fora do fluxo adulto |
| T03 Caminho | Começar pela entrevista; extratos são opcionais e podem ser acrescentados depois | Nunca bloqueia sem PDF |
| T04 Triagem | As 9 perguntas do PGSI (seção 8.1), com "prefiro não responder" | Uma pergunta por tela, com barra de progresso |
| T05 Perguntas complementares | O roteiro da seção 8.2, todas opcionais | — |
| T06 Bloco financeiro | Renda aproximada, despesas essenciais e dívidas, todos opcionais e aproximados | Seção 8.3 |
| T07 Relato | Texto livre opcional | Aviso: evitar CPF, nomes de terceiros e números de conta |
| T08 Extratos | Escolher um ou mais PDFs; pedir a senha do PDF se houver, usada só no aparelho | Leitura no worker, com progresso |
| T09 Resultado da leitura | Por arquivo: banco provável, período, lançamentos lidos, conferência de saldo e status | Seção 5.5 |
| T10 Conferência | Cada movimentação sugerida em um cartão: data, hora (só se houver), valor, direção, destinatário compreensível e motivo. Botões "Sim, era aposta", "Não" e "Não lembro" | Corrigir resposta; "Adicionar uma que faltou"; nada em grupo |
| T11 Resultado | Resumo financeiro (seção 9), triagem (seção 8.1) e relato organizado, com as três origens separadas e visíveis | Cartão de urgência e próximos passos |
| T12 Documentos | Quatro PDFs (seção 10); campo opcional de nome, preenchido só no aparelho na hora de baixar | Sem CPF |
| T13 Orientações | Serviços nacionais e como achar o do seu município (seção 11) | Links oficiais com "consultado em" |
| T14 Privacidade e quem faz | O que fica no aparelho (tudo), o que o servidor vê (só o pedido das páginas), sem cookies e sem medição. Responsável: Odival; contato `contato@<domínio>` | N21 |
| T99 Diagnóstico | Para o teste de Odival (N10, C45): por arquivo, páginas, linhas candidatas, lançamentos reconstruídos, conferência de saldo e status, **sem valores, nomes nem descrições** | Link discreto no rodapé |

## 5. Leitura dos extratos

### 5.1 Pipeline no worker

1. Abrir o PDF (com senha local, se houver).
2. Extrair o texto com posições.
3. Agrupar em linhas por coordenada.
4. Detectar cabeçalhos e colunas: data, descrição, valor, sinal, crédito/débito e saldo.
5. Reconstruir lançamentos: juntar descrições quebradas e descartar cabeçalhos e rodapés repetidos.
6. Normalizar datas (dd/mm/aaaa, dd/mm, "12 SET", ano inferido do período do documento) e valores ("1.234,56", "-1.234,56", "1.234,56 D", "R$"), em centavos inteiros.
7. Definir a direção pela coluna ou pelo sinal; usar o saldo só como conferência.
8. Conferir a coerência.
9. Consolidar os arquivos.
10. Sugerir candidatos.

É um núcleo genérico; não há parser por banco (seção 11.1). Layouts específicos servem só como casos de teste.

### 5.2 Conferência de saldo

- `saldo inicial + entradas − saídas = saldo final`, em centavos e sem tolerância. Quando há saldo por linha, confere a progressão linha a linha.
- Sem saldos: "conferência indisponível".
- **Nunca** alterar lançamento para fechar a conta, nunca inventar saldo e nunca inventar horário.

### 5.3 Vários arquivos e duplicidades

- Cada lançamento guarda a origem (arquivo e página).
- Chave de duplicidade: data, valor em centavos, direção e descrição normalizada.
- **Entre arquivos com períodos sobrepostos**, a mesma chave conta uma vez só, marcada como "aparece em dois extratos".
- **Dentro de um mesmo arquivo**, chaves iguais são operações distintas e as duas ficam.
- Reenviar o mesmo arquivo (mesmo hash) não duplica nada.

### 5.4 Fora do suporte na onda 1

| Caso | Tratamento |
|---|---|
| PDF só de imagem ou sem texto útil | "Este arquivo é uma imagem; nesta versão lemos só PDFs baixados do banco." Sem OCR |
| PDF corrompido | Mensagem clara |
| Fatura de cartão | "Parece fatura de cartão; nesta versão lemos extratos de conta" |
| Arquivo muito grande | Limite de 30 MB e 200 páginas, com mensagem |

Em todos os casos a jornada continua sem o arquivo.

### 5.5 Status por arquivo

| Status | Quando |
|---|---|
| **Leitura suficiente** | 95% ou mais das linhas candidatas viraram lançamentos, e o saldo fecha (ou está indisponível sem incoerência) |
| **Parcial** | Lançamentos lidos, mas com lacunas ou saldo que não fecha |
| **Ambígua** | Direção ou colunas incertas |
| **Não suportado** | Casos da seção 5.4 |

Só a leitura suficiente entra direto na conferência. Parcial e ambígua entram com aviso e uma explicação simples.

## 6. Catálogo e sugestões

**Catálogo (`catalogo.json`).** Montado a partir das listas do Ministério da Fazenda (empresas autorizadas e lista histórica até a MP 1.394/2026), com estes campos:
- `razao_social`, `cnpj`, `marcas`, `dominios`;
- `nomes_no_extrato` (variações prováveis);
- `intermediario` (sim ou não);
- `fonte`, `consultado_em` e `periodo_vinculo`.

Ausência na lista não descarta nada. Intermediário não prova aposta.

**Sugestões.** Cada candidato leva um **motivo** curto e uma **força** (forte, média ou fraca, nunca percentual):
- nome ou marca do catálogo: forte;
- intermediário conhecido: média;
- vários pagamentos ao mesmo destino em pouco tempo: média;
- termos como "bet", "aposta" ou "sports" na descrição: fraca.

Frequência e horário só ordenam e explicam. Não entram na triagem nem provam nada (seção 12.3).

## 7. Conferência individual

- Um cartão por movimentação. A resposta pode ser corrigida, e é possível adicionar uma movimentação que o sistema deixou passar (data, valor, direção e destino digitado).
- Nada é marcado em grupo nem por semelhança (seção 12.4).
- Os totais confirmados usam só "Sim". "Não lembro" aparece em lista separada.
- Cada item guarda a classificação e a origem: "confirmado pela pessoa", "acrescentado pela pessoa".

## 8. Entrevista

### 8.1 Triagem PGSI (N13)

- **Texto:** as 9 perguntas, com a escala e as faixas do *Guia de Cuidado para Pessoas com Problemas Relacionados a Jogos de Apostas* do Ministério da Saúde (2026), sobre os últimos 12 meses.
- **Pontuação:** de 0 a 3 por item, total de 0 a 27. As faixas e os rótulos são os do guia, sem percentual.
- **Respostas incompletas:** com item sem resposta, o total sai como "incompleto" e a faixa não é mostrada.
- **Fonte e condições de uso:** aparecem no resultado e nos documentos.
- **Antes de publicar (A3)**, a sessão confere as condições de uso do instrumento e da tradução. **Se não estiverem claras**, o site troca a triagem por um link ao autoteste oficial do Ministério e um campo opcional para a pessoa anotar o resultado (N13).
- **Este documento não reproduz as perguntas.** A sessão as transcreve do guia oficial, com a citação.

### 8.2 Perguntas complementares

Roteiro próprio, todas as perguntas com "prefiro não responder":
- há quanto tempo aposta;
- em que tipo de jogo (esportivas, cassino online, outros);
- com que frequência, recentemente;
- se já tentou parar ou reduzir;
- se conhece ou usou a autoexclusão;
- impacto em família, trabalho, sono ou estudos;
- se fez dívidas por causa das apostas;
- se usou dinheiro reservado a contas ou a benefícios (pergunta opcional, nunca inferida pelo banco);
- quem sabe da situação;
- o que deseja agora: parar, reduzir, entender ou organizar dívidas.

Nada disso entra na pontuação do PGSI (seção 10.3).

### 8.3 Bloco financeiro

Tudo opcional e aproximado (Q9), sem pedir comprovante:
- renda mensal aproximada;
- despesas essenciais aproximadas;
- dívidas: tipo de credor, valor aproximado, em atraso (sim ou não).

Aparece sempre como "informado pela pessoa".

## 9. Resultado e cálculos

**Três blocos, sempre separados e rotulados pela origem:**

| Bloco | Conteúdo |
|---|---|
| **Triagem** | Pontuação e faixa, com os limites |
| **Observações dos extratos** | Período coberto e arquivos usados; valor enviado e valor recebido confirmados; diferença observada; número de movimentações; distribuição por mês; valores por destinatário reconhecido; o que ficou de fora (não lembro, partes não lidas) |
| **Informado pela pessoa** | Relato, bloco financeiro e respostas complementares |

**Frases obrigatórias:**
- "não encontramos" é diferente de "não houve";
- "a diferença observada não é necessariamente perda";
- uma pontuação baixa não garante ausência de problema.

## 10. Documentos (pdf-lib, gerados no aparelho)

**Todos trazem:**
- **Cabeçalho:** "Documento informativo preparado pela própria pessoa no site Aposte em Você (versão de teste). Não é laudo, parecer nem diagnóstico."
- **Dados de emissão:** data, período e fontes.
- **Identificação:** nome opcional digitado na hora; sem CPF.

| Documento | Conteúdo | Cuidados |
|---|---|---|
| **Relatório completo** | Tudo da seção 9, mais próximos passos, orientações e limitações | — |
| **Para o psicólogo** | Motivo da busca, relato, triagem com limites, padrões observados (frequência, sem diagnóstico), contexto financeiro resumido e dúvidas para o atendimento | "Relatório informativo", nunca "laudo" (CFP 06/2019) |
| **Para o advogado** | Cronologia relatada, períodos e fontes, valores confirmados, dívidas informadas, questões a avaliar, o que **não** está comprovado e documentos que a pessoa pode reunir | Sem parecer nem promessa de resultado |
| **Para o banco** | Modelo de carta: pedido de análise e renegociação, descrição factual, valores que a pessoa confirmar e campos em branco (agência, conta, contrato) para preencher à mão | **Sem** triagem, saúde mental nem relato íntimo |

Os documentos precisam funcionar impressos e no celular, com acentos corretos e quebra de página limpa.

## 11. Orientações e urgência

**Urgência (C65).** Botão fixo e cartão no resultado com:
- CVV 188 (24 h, gratuito, também por chat em cvv.org.br);
- SAMU 192;
- UPA ou pronto-socorro;
- CAPS.

O site não faz pergunta de triagem de risco à vida.

**Orientações nacionais**, cada uma com o tipo de ajuda e o link oficial "consultado em <data>":

| Tema | Onde |
|---|---|
| Saúde | UBS e CAPS (SUS), com o material do Ministério da Saúde sobre apostas |
| Assistência social | CRAS |
| Orientação jurídica gratuita | Defensoria Pública |
| Dívidas | Registrato (Banco Central), para ver as próprias dívidas, e consumidor.gov.br e Procon, para renegociação |
| Restrição de acesso às apostas | Plataforma centralizada de autoexclusão (gov.br), explicando o alcance real dela |
| Seu município | Como achar o serviço local: busca oficial de unidades e prefeitura |

Não há diretório próprio de endereços (seção 18.2). Os textos regulatórios citam a fonte e a data, e a situação da MP 1.394/2026 é reconferida antes de publicar.

## 12. Privacidade e segurança (N8)

**Cabeçalhos em `vercel.json`:**
- `Content-Security-Policy: default-src 'self'; script-src 'self'; worker-src 'self' blob:; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`. Acrescentar `'wasm-unsafe-eval'` em `script-src` só se o PDF.js exigir, com o motivo registrado.
- `Referrer-Policy: no-referrer`.
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- `X-Content-Type-Options: nosniff`.

**Regras:**
- Sem rotas de API, funções de servidor, cookies ou script de medição (N20).
- Os textos do site não dizem "anônimo". Dizem com exatidão o que fica e o que sai (seção 16.2).

## 13. Acessibilidade e desempenho

**Acessibilidade:** referência WCAG 2.2 AA nas telas principais.
- Contraste, rótulos e foco visível.
- Alvos de toque de 44 px ou mais.
- Leitor de tela no fluxo T01–T12.
- axe-core sem violações sérias nem críticas.

**Desempenho:**
- JavaScript inicial de até 150 KB gzip, sem o PDF.js.
- PDF.js só ao escolher um PDF.
- Extrato sintético de 10 páginas lido em até 5 s com a CPU a 4x mais lenta (Playwright).

## 14. Testes

| Tipo | O que cobre |
|---|---|
| **Unidade** | Normalização de datas e valores, direção, conferência de saldo, consolidação e duplicidade, sugestões, PGSI (total, faixa e incompleto) e cálculos |
| **Leitura** | `scripts/gerar-pdfs-sinteticos.ts` gera os PDFs e o JSON esperado de cada um, com dados fictícios e estrutura **imitada**, sem logotipo nem marca |
| **Ponta a ponta** (perfil de celular) | Jornada sem PDF; jornada com 2 PDFs sobrepostos; conferência com correção; os 4 documentos baixados; menor de idade; botão de ajuda |
| **Rede** | Durante toda a jornada, registra todas as requisições. Só pode haver GET do mesmo domínio para arquivos estáticos; nenhum POST, PUT ou PATCH; nenhum domínio de terceiros |

**PDFs sintéticos de leitura:**
- **6 layouts:** Nubank, Mercado Pago, PicPay, Inter, Caixa Tem e Caixa (C56).
- **8 casos difíceis ou mais:**
  - descrição em 2 linhas;
  - cabeçalho repetido por página;
  - sinal negativo;
  - coluna C/D;
  - saldo por linha;
  - sem saldo;
  - data sem ano;
  - PDF com senha;
  - PDF só de imagem, que precisa dar "não suportado";
  - mesmo arquivo enviado duas vezes;
  - períodos sobrepostos.

**Meta de leitura:** 100% dos lançamentos nos 6 layouts limpos e o status certo em cada caso difícil. Não há meta de "acerto universal" (seção 22.2).

## 15. Etapas e critérios de aceite (C46; uma etapa = uma sessão = um PR)

| Etapa | Entrega | Aceite verificável |
|---|---|---|
| **a1-parser** | Projeto configurado (seção 3); leitura (seção 5) com senha local; gerador de PDFs sintéticos e o JSON esperado; telas T08, T09 e T99; pré-visualização na Vercel. Alto impacto: pipeline de leitura (Galadriel) | CI e portão verdes; testes de leitura com a meta da seção 14; ponta a ponta de rede verde na jornada de leitura; **Odival testa os próprios extratos na pré-visualização e relata por banco: leu, parcial ou falhou (C45)** |
| **a2-conferencia-entrevista** | Catálogo com fonte (seção 6); sugestões; T10 conferência individual; T03–T07 entrevista; correções do teste de Odival. Alto impacto: totais e duplicidades | Testes de unidade das seções 6–8; ponta a ponta da conferência com correção e com "acrescentar"; nenhuma confirmação em grupo possível |
| **a3-documentos-privacidade** | T11, T12, T13, T14, T01, T02/T02b e o botão de ajuda; os 4 documentos; CSP e cabeçalhos; conferência da licença do PGSI e de todos os links. Alto impacto: privacidade e documentos | Os 4 PDFs gerados e com acentos; ponta a ponta de rede verde na jornada inteira; cabeçalhos presentes na pré-visualização; relatório de links com data |
| **a4-publicacao** | Acessibilidade, desempenho, revisão de todos os textos contra os princípios da seção 2, ajustes finais e publicação em produção com o "vai" de Odival (C55) | axe sem violações sérias; metas da seção 13; lista de conferência dos princípios assinada pelo Barbárvore; condições da N8 cumpridas; domínio próprio, ou o `.vercel.app` enquanto o DNS não estiver pronto |

## 16. Fora da onda 1

- Conta, e-mail, guarda e IA (onda 2).
- OCR, fotos e áudio.
- Aplicativo nativo.
- Open Finance ou acesso direto à conta.
- Diretório próprio de serviços.
- Público menor de idade, além da tela de orientação.
- Projeto comercial separado.
- Qualquer medição de uso no site.

## 17. A conferir na nuvem antes de publicar

- Condições de uso do PGSI e da tradução (seção 8.1).
- Links oficiais e datas (seção 11).
- Situação da MP 1.394/2026 e da lista da Fazenda.
- Alcance atual da plataforma de autoexclusão.
- Se o PDF.js exige `'wasm-unsafe-eval'` (seção 12).
- Licenças das dependências (compatíveis com a AGPL-3.0).
