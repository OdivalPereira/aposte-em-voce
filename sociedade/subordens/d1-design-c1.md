# Subordem d1-design-c1 · Correção A04 (Acessibilidade de Foco no Botão Escolher PDF)

Para: Legolas (Interface e Acessibilidade)
De: Gandalf (Coordenador)
Contexto: Etapa d1-design · Rodada de Correção após Parecer do Barbárvore (Q84/Q85)

## 1. Objetivo da Subordem
Corrigir o achado bloqueador **A04** relatado pelo revisor independente Barbárvore:
- **Achado A04:** A escolha de PDF perde o foco visível após a nova estrutura (`src/telas/Extratos.tsx:85`; `src/ui/EstadoVazio.tsx:35`; `src/ui/estilos.css:82`).
- **Problema:** Na tela T08 (Extratos) vazia e na tela com arquivos, ao navegar via teclado com `Tab`, o input invisível de upload recebe foco (`:focus-visible`), mas o botão/rótulo visível (`Escolher PDF` / `Acrescentar mais PDFs`) não exibe o indicador visual de foco (outline de alto contraste 3:1), violando WCAG 2.4.7 (Foco Visível). A regra `.entrada-arquivo:focus-visible + .botao` não se aplica porque o input e o label não são mais irmãos imediatamente adjacentes no DOM.

## 2. Arquivos Permitidos
Trabalhe exclusivamente em `/home/odival/.sociedade/trabalho/aposte-em-voce/d1-design`:
- `src/telas/Extratos.tsx`
- `src/ui/EstadoVazio.tsx`
- `src/ui/estilos.css`
- `tests/` (apenas adicionar teste de foco de acessibilidade se pertinente, sem alterar esperados existentes de testes)

**PROIBIDO:** Não altere `src/leitura/`, `src/ui/formatar.ts`, nem dependências em `package.json`. Não faça commit nem push.

## 3. Requisitos da Correção
1. Garantir que, ao navegar via teclado (`Tab`), o rótulo/botão visível receba outline visível claro:
   - Outline: `3px solid var(--cor-foco)` e `outline-offset: 2px`.
   - Deve funcionar tanto na T08 vazia (`EstadoVazio`) quanto na T08 com arquivos (`Acrescentar mais PDFs`).
2. Utilizar técnicas robustas e compatíveis com CSP (sem estilos inline dinâmicos proibidos):
   - Ajustar a estrutura ou seletores CSS (ex.: `:focus-within`, `:has(:focus-visible)`, ou posicionamento do input como irmão direto `+` do label no JSX).
3. Garantir que o clique com mouse e a ativação por teclado continuem funcionando normalmente sem abrir diálogos duplicados.
4. Não quebrar nenhum teste existente do app (`npm test`), lint (`npm run lint`), build (`npm run build`) e capturas (`npm run capturas`).

## 4. Testes Dirigidos
Execute e valide:
- `npm test`
- `npm run lint`
- `npm run build`
- `npm run capturas`

## 5. Retorno
Grave o arquivo de detalhe em:
`/home/odival/.sociedade/trabalho/aposte-em-voce/d1-design/sociedade/subordens/d1-design-c1-retorno.md`
E devolva no chat um resumo conciso de até 2 KB com o veredito e o resultado dos testes.
