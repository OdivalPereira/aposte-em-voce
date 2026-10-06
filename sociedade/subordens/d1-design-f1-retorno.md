# Retorno F1 (d1-design) · Legolas

Veredito: **pronto**. Sem commit, sem push. Base da fatia: `8032f0394ebf` (ramo `etapa/d1-design`).

## Objetivo cumprido
Criação da referência visual sóbria, acolhedora e moderna para o app "Aposte em Você", com design tokens completos, componentes fundamentais, estados (cada um com texto e ação) e a página `/referencia.html`, atendendo com rigor a especificação WCAG 2.2 nível AA e a CSP do `vercel.json`.

## Arquivos escritos
1. `src/ui/tokens.ts`: tokens de cor, tipografia, escala única de espaçamento (4 px), raios de borda e pares semânticos de contraste para validação automatizada.
2. `src/ui/tokens.css`: variáveis CSS globais com compatibilidade retroativa para as classes pré-existentes.
3. `src/ui/componentes.css`: estilização dos componentes (botões, cartões, campos, avisos, progresso, listas e estados), com regras para reflow em 320 px, foco visível de alto contraste e `prefers-reduced-motion`.
4. `src/ui/contraste.ts`: motor determinístico W3C para cálculo de luminância relativa e razão de contraste WCAG 2.2.
5. `src/ui/Botao.tsx`: componente Botão acessível com variantes primária, secundária e discreta, com tamanho de alvo mínimo ≥ 44×44 px.
6. `src/ui/Cartao.tsx`: componente Cartão para agrupamento sóbrio de dados e ações.
7. `src/ui/Campo.tsx`: campo de formulário acessível com rotulagem semântica, texto de ajuda e mensagem de erro via `aria-describedby` e `aria-invalid`.
8. `src/ui/Aviso.tsx`: componente de avisos semânticos para informação, atenção e erro com papéis ARIA adequados.
9. `src/ui/Progresso.tsx`: barra de progresso acessível para acompanhamento da leitura e conciliação.
10. `src/ui/Lista.tsx`: componentes `Lista` e `ItemLista` para exibição de movimentações financeiras com formatação em reais e ações individuais de validação.
11. `src/ui/EstadoVazio.tsx`: estado vazio acolhedor com texto explicativo e ações primária/secundária.
12. `src/ui/EstadoCarregando.tsx`: estado de leitura com indicador acessível, texto explicativo e ação de cancelamento/pulo.
13. `src/ui/EstadoErro.tsx`: estado de erro respeitoso, sem jargão e sem tom de julgamento, com ação de recuperação.
14. `src/ui/index.ts`: exportação unificada de componentes, tokens e utilitários.
15. `src/ui/estilos.css`: atualizado exclusivamente para importar `tokens.css` e `componentes.css`, mantendo as telas existentes plenamente funcionais.
16. `src/referencia/referencia.css`: estilos específicos da página de referência visual, sem uso de estilos inline (estritamente aderente à CSP de `style-src 'self'`).
17. `src/referencia/PaginaReferencia.tsx`: interface de demonstração visual completa, exibindo todos os tokens, componentes, estados, auditoria WCAG 2.2 AA e simulação em celular (360 px) e desktop.
18. `src/referencia/main.tsx`: ponto de entrada Preact da referência visual.
19. `referencia.html`: nova página HTML estática de entrada na raiz, sem links a partir do fluxo principal da aplicação.
20. `vite.config.ts`: configurado `build.rollupOptions.input` para incluir tanto `index.html` quanto `referencia.html`.
21. `tests/unit/contraste.test.ts`: bateria de testes de unidade automatizados validando o cálculo de luminância e cada par de contraste declarado nos tokens contra os limiares mínimos WCAG 2.2 AA (≥ 4,5:1 em texto normal e ≥ 3:0:1 em controles de interface).

## Testes dirigidos da subordem
1. `npm test`:
   - `vitest run`: 9 arquivos, 170 testes unitários aprovados (incluindo os 29 testes de contraste).
   - `playwright test`: 13 testes ponta a ponta aprovados com 6 workers em perfil de celular.
2. `npm run lint`:
   - `tsc --noEmit && eslint .`: código de saída 0, zero erros e zero advertências.
3. `npm run build`:
   - `tsc --noEmit && vite build`: build concluído com sucesso, gerando `dist/index.html` e `dist/referencia.html`.

## Diretrizes e Princípios Atendidos
- **Público e Tom:** Interface acolhedora, serena e sóbria voltada a adultos afetados por apostas financeiras (sem cores néon, sem ouro reluzente, sem tons punitivos).
- **Tokens:** Cores, tipografia nativa do sistema e espaçamento único regular (múltiplos de 4 px).
- **Componentes:** Botão (primário, secundário e discreto), cartão, campo, aviso (info, atenção e erro), progresso e lista.
- **Estados:** Vazio, carregando e erro, cada um fornecendo texto claro e ação de continuidade.
- **WCAG 2.2 AA:**
  - Contraste de texto ≥ 4,5:1 (texto principal 17,5:1, secundário 7,6:1, primária 8,0:1, sucesso 11,2:1, erro 7,9:1);
  - Contraste não-textual e foco ≥ 3:1 (borda de campos 4,7:1, foco 8,0:1, barra de progresso 6,5:1);
  - Foco visível com 3 px e offset 2 px, não encoberto (2.4.7, 2.4.11);
  - Alvos de toque de 44×44 px (supera 24×24 px do SC 2.5.8);
  - Reflow sem perda de informação e sem barra horizontal em 320 px (1.4.10);
  - Respeito à ampliação de espaçamento de texto (1.4.12);
  - Suporte a `prefers-reduced-motion` desativando rotações contínuas de spinners.
- **Segurança e CSP:** Nenhuma fonte externa ou CDN, nenhum estilo inline (`style="..."`) e nenhum script inline, respeitando a CSP rigorosa do `vercel.json`.
- **Integridade do Repositório:** Nenhuma alteração em `src/leitura/`, `src/telas/`, `src/app.tsx`, `package.json` ou `vercel.json`.
