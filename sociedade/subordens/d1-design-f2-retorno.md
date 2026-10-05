# Retorno F2 (d1-design) · Legolas

Veredito: **pronto**. Sem commit, sem push. Base da fatia: `97010fa58308` (worktree `~/.sociedade/trabalho/aposte-em-voce/d1-design`, ramo `etapa/d1-design`).

## Objetivo cumprido
Aplicação rigorosa da referência visual aprovada (tokens e componentes de UI criados na F1) às telas T08 (`Extratos.tsx`), T09 (`ResultadoLeitura.tsx`), T99 (`Diagnostico.tsx`) e à estrutura visual do `app.tsx`, mantendo 100% do comportamento funcional existente (nenhum esperado de teste unitário ou e2e foi modificado). A T09 foi enriquecida com a exibição do histórico mensal completo (período total, meses cobertos, meses faltando e aviso de encadeamento). Foi configurado o script `npm run capturas` e a spec Playwright `tests/e2e/capturas.spec.ts` (que se pula fora de `CAPTURAS=1`), gerando as 7 capturas em 360 px com dados estritamente sintéticos em `docs/capturas/d1-design/`.

## Arquivos alterados e criados
1. `src/telas/Extratos.tsx` (T08):
   - Aplica os componentes `EstadoVazio` (quando sem extratos), `EstadoCarregando` (leitura em andamento), `Aviso` (erros, alertas de arquivos duplicados) e `Botao` (primário e secundário);
   - `PedidoDeSenha` refatorado com `Campo` acessível e `Botao`;
   - Preservados os seletores e alvos de toque ≥ 44 px.
2. `src/telas/ResultadoLeitura.tsx` (T09):
   - Aplica `EstadoVazio` quando sem extratos lidos;
   - Seção de Histórico consolidado em `Cartao` (`section[aria-label^="Histórico"]`) com período total, arquivos no histórico, meses cobertos, meses faltando e `Aviso` de encadeamento de saldo;
   - Cartões individuais de arquivo em `article.cartao` com lista de definição (`dl`), rotulagem de status e avisos semânticos;
   - `Botao` secundário para retorno seguro aos extratos.
3. `src/telas/Diagnostico.tsx` (T99):
   - Aplica `EstadoVazio` quando nenhum arquivo foi lido;
   - Tabela em `.tabela-rolagem` com tokens de cores e bordas semânticas;
   - `Botao` secundário para copiar assinatura de layout com rotulagem acessível (`rotuloAcessivel`);
   - Feedback de cópia utilizando `Aviso` com `role="status"`.
4. `src/app.tsx`:
   - Cabeçalho visual sóbrio com a marca "Aposte em Você" e tag indicativa de processamento no aparelho;
   - Botão discreto `Botao variante="discreto"` no rodapé para acesso ao Diagnóstico.
5. `src/ui/`:
   - `src/ui/Botao.tsx`: suporte à propriedade `type` como alias transparente de `tipo`;
   - `src/ui/Cartao.tsx`: suporte a `como?: 'article' | 'section' | 'div' | 'li'` e `ariaLabel`;
   - `src/ui/EstadoVazio.tsx`: suporte a `idInput` para vinculação direta com `<label for="...">`;
   - `src/ui/EstadoCarregando.tsx`: suporte a `titulo` customizável;
   - `src/ui/Aviso.tsx`: suporte a propriedade `papel` explícita (`'alert' | 'status'`);
   - `src/ui/estilos.css`: regras de tipografia e espaçamento baseadas em tokens, formatação de listas de definição (`dl`), tabelas e cabeçalhos com reflow estrito em 320/360 px.
6. `package.json`:
   - Adicionado script `"capturas": "CAPTURAS=1 playwright test tests/e2e/capturas.spec.ts"`.
7. `tests/e2e/capturas.spec.ts`:
   - Nova suíte de testes Playwright configurada para pular execução sem `CAPTURAS=1`;
   - Viewport em 360 px com `deviceScaleFactor: 1`;
   - Cria o diretório `docs/capturas/d1-design/` e grava as 7 capturas em formato PNG full-page.
8. `docs/capturas/d1-design/`:
   - `referencia.png` (365 × 11709 px)
   - `t08-vazio.png` (360 × 810 px)
   - `t08-carregando.png` (360 × 973 px)
   - `t08-erro.png` (360 × 901 px)
   - `t09-resultado.png` (360 × 1111 px)
   - `t09-historico.png` (360 × 1955 px)
   - `t99-diagnostico.png` (360 × 800 px)

## Proibições estritamente respeitadas
- `src/leitura/`: intocado.
- `src/ui/formatar.ts`: intocado.
- Nenhuma dependência nova adicionada no `package.json`.
- Nenhum commit realizado; nenhum push realizado.
- Somente dados sintéticos utilizados nas capturas e testes.

## Testes dirigidos da subordem
1. `npm test`:
   - Unitários (vitest): 9 arquivos, 170 testes aprovados.
   - E2E (playwright): 13 testes aprovados, 7 testes pulados (`capturas.spec.ts` skipped sem `CAPTURAS=1`).
2. `npm run lint`:
   - `tsc --noEmit && eslint .`: 0 erros, 0 avisos.
3. `npm run build`:
   - `tsc --noEmit && vite build`: build concluído com sucesso.
4. `npm run capturas`:
   - 7 testes executados com sucesso em 4.0s gerando todas as imagens em `docs/capturas/d1-design/`.
5. `ls -la docs/capturas/d1-design/`:
   - 7 arquivos PNG gerados e verificados.
