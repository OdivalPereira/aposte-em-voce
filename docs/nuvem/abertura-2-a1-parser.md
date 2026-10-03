# Sessão 2 — etapa `a1-parser`

**Siga `docs/nuvem/protocolo-sessao.md`.**

| Campo | Conteúdo |
|---|---|
| Pedido | Linha `a1-parser` de `sociedade/nuvem/pedidos.md` |
| Especificação | `docs/onda-1.md`, seções 2, 3, 5, 14 e linha `a1-parser` da 15 |
| Backlog | **B11** (portão amarrado), **B12** (simulação de 3 tentativas), **B13** (Jules emulado gera os PDFs sintéticos) |
| Alto impacto (Galadriel) | Pipeline de leitura (`src/leitura/`) e B11 |
| Revisão | **Completa** |

**O que esta etapa tem de especial:**

1. **Projeto do zero.** Vite, TypeScript, Preact, PDF.js num worker, Vitest, Playwright e ESLint. Os comandos `npm test`, `npm run lint` e `npm run build` do perfil passam a existir.
2. **Simulação B12 (Q12).** Antes de despachar, o Círdan planta, numa subordem de fatia, um problema que exige hipóteses diferentes (por exemplo, um layout sintético com colunas trocadas). Registre se o executor parou e devolveu depois da 3ª tentativa.
3. **Fim da etapa.** Depois da decisão, entregue a Odival:
   - o **link da pré-visualização da Vercel** do PR;
   - um roteiro curto para ele testar os próprios extratos no celular, pela tela T99 (diagnóstico, sem valores).

   Ele relata por banco: leu, parcial ou falhou (C45). Esse relato abre a sessão 3.
