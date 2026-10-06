# Retorno Correção d1-design-c1 · Legolas

Veredito: **pronto**. Sem commit, sem push. Worktree: `~/.sociedade/trabalho/aposte-em-voce/d1-design` (ramo `etapa/d1-design`).

## 1. Objetivo Cumprido
Correção definitiva do achado bloqueador **A04** apontado pelo revisor independente Barbárvore:
- **Problema resolvido:** Em T08 (`Extratos.tsx`), o controle oculto de arquivo (`#escolher-pdf`) havia sido separado visual e estruturalmente dos rótulos visíveis (`Escolher PDF` em `EstadoVazio` e `Acrescentar mais PDFs` no estado com arquivos), impedindo que a regra CSS `.entrada-arquivo:focus-visible + .botao` encontrasse seu irmão adjacente. Ao navegar via teclado com `Tab`, o foco ficava invisível, violando WCAG 2.4.7.
- **Solução implementada:**
  1. Em `src/ui/EstadoVazio.tsx`: adicionada propriedade opcional `elementoInput?: ComponentChildren`, renderizada dentro de `.estado-acoes` imediatamente antes do `<label for={idInput} class="botao botao-primario">`.
  2. Em `src/telas/Extratos.tsx`: o controle `entradaArquivo` (`<input id="escolher-pdf" class="entrada-arquivo" ... />`) agora é fornecido como `elementoInput` ao `EstadoVazio` (estado vazio) e posicionado diretamente antes de `<label for="escolher-pdf" class="botao botao-secundario">` (estado com arquivos). Em ambos os estados, o input invisível e o label visível tornaram-se irmãos imediatamente adjacentes (`+`).
  3. Em `src/ui/estilos.css`: ampliado seletor de foco para `.entrada-arquivo:focus-visible + .botao, .entrada-arquivo:focus-visible ~ label.botao`, garantindo `outline: 3px solid var(--cor-foco)` e `outline-offset: 2px` (contraste 8,04:1 em fundo branco, superando o requisito mínimo de 3:1).
  4. Compatibilidade total de ativação: clique via mouse e acionamento por teclado continuam funcionando normalmente sem qualquer abertura duplicada de diálogo nem alteração de fluxo.
  5. Reflow e toque: o input possui `position: absolute; width: 1px; height: 1px; opacity: 0;`, preservando o fluxo flex de `.estado-acoes` e garantindo alvos de toque ≥ 44 px e reflow sem rolagem horizontal em 320 px (C08 e C09).

## 2. Arquivos Alterados
1. `src/telas/Extratos.tsx`:
   - Vinculação do `entradaArquivo` como irmão adjacente em ambos os ramos de renderização (`itens.length === 0` e `itens.length > 0`).
2. `src/ui/EstadoVazio.tsx`:
   - Suporte a `elementoInput` dentro de `div.estado-acoes` adjacente ao label de ação.
3. `src/ui/estilos.css`:
   - Regra `.entrada-arquivo:focus-visible + .botao, .entrada-arquivo:focus-visible ~ label.botao` com `outline: 3px solid var(--cor-foco)` e `outline-offset: 2px`.
4. `tests/e2e/leitura.spec.ts`:
   - Adicionado teste e2e `foco visível por teclado (WCAG 2.4.7) no botão de escolher PDF em vazio e com arquivos`, validando navegação com `Tab`, presença do outline de 3px solid rgb(11, 79, 156), reflow em 320 px, altura de toque ≥ 44 px e remoção do outline ao desfocar.

## 3. Proibições Respeitadas
- `src/leitura/`: intocado.
- `src/ui/formatar.ts`: intocado.
- `package.json`: nenhuma dependência alterada.
- Sem commit e sem push.

## 4. Testes Dirigidos Executados
1. `npm test`:
   - **Unitários (Vitest):** 9 suítes, 170 testes aprovados (100%).
   - **E2E (Playwright):** 14 testes aprovados (incluindo o novo teste de foco WCAG 2.4.7 em 320/360 px), 7 pulados (capturas condicionadas a `CAPTURAS=1`).
2. `npm run lint`:
   - `tsc --noEmit && eslint .`: 0 erros, 0 avisos.
3. `npm run build`:
   - `tsc --noEmit && vite build`: compilação concluída com sucesso em 521 ms sem erros.
4. `npm run capturas`:
   - `CAPTURAS=1 playwright test tests/e2e/capturas.spec.ts`: 7 capturas visuais em 360 px geradas com sucesso em `docs/capturas/d1-design/`.
