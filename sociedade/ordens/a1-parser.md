# Ordem a1-parser — o celular lê extratos em PDF sem nada sair do aparelho, e o portão fica amarrado ao perfil

Para: Gandalf (Claude Code em nuvem, subagente `gandalf`, esforço high) · CONVERSA NOVA
Etapa: a1-parser · Base: `d86e90c` · Worktree: `~/.sociedade/trabalho/aposte-em-voce/a1-parser` (criado pelo Círdan com `sc_worktree.py criar`) · Ramo: `etapa/a1-parser`
Especialistas: Aragorn (F1), Elrond (F2), Jules (F3) · Revisão interna (Galadriel): F1 (só a B11) e F2 (pipeline `src/leitura/`) · Jules: F3 (B13)
Aprovada por Odival em 03/10/2026, com os ajustes da seção "Ajustes da aprovação".
Revisão independente: **reduzida** (`barbarvore-reduzida`, ajuste de Odival nesta sessão), marcada "aceite em emulação" e "revisor não calibrado"

## Objetivo
Pedido de Odival (`sociedade/nuvem/pedidos.md`, linha `a1-parser`): "Quero abrir no celular extratos em PDF de vários bancos e ver, sem nada sair do aparelho, quantas movimentações o site conseguiu ler e se os saldos fecham, para testar com os meus extratos."

Como Odival percebe: na pré-visualização da Vercel do PR, ele escolhe um ou mais PDFs na T08 (com senha, se houver), vê na T09 o resultado por arquivo e na T99 o diagnóstico sem valores, nomes nem descrições; e o portão da etapa roda só os comandos do perfil, por área, sem `--comando-teste`.

## Leia só
1. Esta ordem.
2. `docs/onda-1.md`: seções 2, 3 e 5; na 4, só T08, T09 e T99; na 14, a tabela e os PDFs sintéticos; na 15, a linha `a1-parser`.
3. `sociedade/nuvem/backlog.md`: linhas B11, B12, B13 e B11a a B11d.
4. `sociedade/regras.md`, seções 3 e 4.
5. `sociedade/perfil.md`, seções "Comandos" e "Portão por área".

Cada especialista lê, além disso, só os arquivos do seu escreva-só e os que a subordem citar.

## Onde se mexe
O candidato **não altera** `sociedade/` (Q60), `docs/` nem `.claude/`. Prefixos: `S = sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`; `T = sociedade-do-codigo/tests`.

## Fatias (escreva-só disjuntos)
Ordem: F1 e F2 em paralelo; F3 depois da F2 (precisa do `package.json`). Delegação em revezamento (Q161): o Gandalf escreve as subordens e devolve; o Círdan as despacha sem edição e entrega os retornos ao Gandalf.

1. **F1 · B11, B11a a B11d (pacote)** · Aragorn · B11 de **alto impacto** · escreva só: `S/sc_ciclo.py`, `S/sc.py`, `S/sc_conferir.py`, `S/sc_status.py` (só se o atestado mudar de formato), `S/sc_perfil.py`, `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sc-revisao/` (só texto), `T/test_portao_amarrado.py` (novo), `T/test_sociedade_worktree.py` (novo), `T/adversarial/`, `.github/pull_request_template.md`, `.github/workflows/status.yml` (só se o atestado mudar de formato), `sociedade-do-codigo/CHANGELOG.md` · aceite:
   - **B11, portão amarrado:** `sc.py entregar` recusa `--comando-teste`; comando e timeout vêm só da seção "Portão por área" do perfil canônico. Reprova: árvore suja (qualquer mudança fora de `sociedade/`, rastreada ou não; arquivos ignorados pelo `.gitignore`, como `node_modules/`, `dist/` e relatórios de teste, não contam), 0 testes, todos pulados, timeout. O atestado grava, por área, comando, timeout, contagem de testes, SHA-256 do perfil e o commit. Contagem lida da saída do `unittest` e do Vitest (e do Playwright, se rodar junto). Caminhos com `git -c core.quotepath=off ... -z` e normalizados em NFC.
   - Teste com `node_modules/` presente (e ignorado pelo `.gitignore`) e o portão aprovando.
   - **Portão por área (B11c):** sem `--area`, roda todas as áreas que `base..HEAD` toca; com `--area <nome>`, só aquela. A área de um caminho é a do prefixo mais longo da tabela; `.github/` conta para as duas.
   - **Sondas verdes** em `T/adversarial/`: DG-03 (árvore suja; tira o `expectedFailure` do que a B11 fecha), DG-09 em 3 casos (`--comando-teste` recusado, 0 testes, todos pulados) e DG-11 (arquivo com acento em NFD e espaço no nome aparece certo na lista do atestado e no `arquivos_em`).
   - **B11a:** durante a etapa, `conferir --registrar`, `revisar --parecer`, `decidir` e `estado` leem e gravam a `sociedade/` do worktree da etapa (`~/.sociedade/trabalho/<projeto>/<etapa>/sociedade`, se existir); `sc.py conferir` aceita `--pasta-sociedade`; nenhum desses grava no checkout principal. Teste: uma etapa num worktree temporário fecha sem cópia manual.
   - **B11b:** nenhuma skill do pacote cita `sc_rodada parecer`; o `sc-revisao` manda registrar o parecer por `sc.py revisar --parecer`.
   - **B11d:** o modelo de PR tem a linha "Conferi o diff de `.github/` e `sociedade/pareceres/`".
   - Suíte do pacote e `python3 -B scripts/validar_pacote.py` verdes.
2. **F2 · projeto e leitura (app)** · Elrond · pipeline de **alto impacto** · escreva só: `package.json`, `package-lock.json`, `index.html`, `vite.config.ts`, `tsconfig*.json`, `eslint.config.js`, `vitest.config.ts`, `playwright.config.ts`, `vercel.json`, `.gitignore`, `public/`, `src/` (só `main.tsx`, `app.tsx`, `telas/`, `ui/`, `leitura/`), `tests/unit/`, `tests/e2e/`, `.github/workflows/ci.yml` · aceite:
   - Stack da seção 3 (Vite, TypeScript, Preact, `pdfjs-dist` num worker servido do próprio site e carregado só quando a pessoa escolhe um PDF, Vitest, Playwright, ESLint e `tsc --noEmit`); `npm test`, `npm run lint` e `npm run build` existem e passam. Licenças compatíveis com a AGPL-3.0. Playwright com o Chromium já instalado no ambiente (`PLAYWRIGHT_BROWSERS_PATH`); não rode `playwright install`.
   - Pipeline da seção 5.1 (passos 1 a 9) em `src/leitura/`, genérico, sem parser por banco; conferência de saldo da 5.2 em centavos, sem tolerância; duplicidades da 5.3; casos da 5.4; status da 5.5. Função pública documentada para a F3: bytes do PDF e senha opcional → resultado por arquivo, no formato que a F3 vai gravar como JSON esperado.
   - Unidade em `tests/unit/` com texto posicionado montado no próprio teste: datas e valores em todos os formatos da 5.1, direção, conferência de saldo, consolidação e duplicidade, e o caso `colunas-trocadas` abaixo.
   - Telas T08, T09 e T99 (T99 sem valores, nomes nem descrições), em Preact simples; nada em `localStorage`, IndexedDB ou cookies.
   - Ponta a ponta em `tests/e2e/` (perfil de celular): jornada de leitura com um PDF gerado no próprio teste; o teste de rede registra todas as requisições e só aceita GET do mesmo domínio.
   - `vercel.json` com CSP e cabeçalhos de segurança e a configuração de build. Não mexa em ramos nem em implantação.
   - `ci.yml` roda lint, build e `npm test` do app (com Playwright) além do que já roda.
   - **Caso `colunas-trocadas`** (unidade): colunas, da esquerda para a direita, `Valor (R$)`, `Data`, `Histórico`, `Saldo (R$)`. Linhas: `SALDO ANTERIOR` com saldo `1.000,00`; `-50,00 | 02/09/2026 | PIX ENVIADO LOJA FICTICIA | 950,00`; `200,00 | 05/09/2026 | PIX RECEBIDO PESSOA FICTICIA | 1.150,00`; `-30,10 | 09/09/2026 | PAGAMENTO BOLETO FICTICIO | 1.119,91`; `SALDO FINAL` `1.119,91`. Esperado: 3 lançamentos, saldo fecha, status "leitura suficiente".
3. **F3 · B13, PDFs sintéticos (Jules)** · Jules, em worktree próprio no ramo `jules/a1-parser-pdfs`, a partir do commit da F2 · escreva só: `scripts/gerar-pdfs-sinteticos.ts`, `tests/fixtures/pdfs/`, `tests/fixtures/esperado/`, `tests/leitura/` · aceite:
   - Gerador com `pdf-lib` (dependência de desenvolvimento declarada pela F2), dados fictícios e estrutura imitada, sem logotipo nem marca: os 6 layouts da seção 14 e os casos difíceis listados lá (pelo menos 8, incluindo senha, só imagem, mesmo arquivo duas vezes e períodos sobrepostos), cada um com o JSON esperado.
   - `tests/leitura/` roda a função pública da F2 em cada PDF e compara com o esperado: 100% dos lançamentos nos 6 layouts limpos e o status certo em cada caso difícil.
   - Portão do Jules (`sc_jules_portao.py`) com os arquivos permitidos acima e `npx vitest run tests/leitura`; o Gandalf integra por merge no `etapa/a1-parser`. No máximo 3 tarefas do Jules abertas, janela de 45 min. Sem push do ramo `jules/*`.
   - Se a leitura falhar num layout, o Jules não mexe em `src/`: o Gandalf devolve à F2 (Elrond) numa subordem de correção.

## Portão
- Por fatia: `sc.py entregar --etapa a1-parser --base <base da fatia> --fatia <N> --pasta-sociedade ~/.sociedade/trabalho/aposte-em-voce/a1-parser/sociedade`, com o `sc.py` do worktree.
- **Transição:** até a F1 entrar, o portão é o atual, com `--comando-teste` do perfil (exceção registrada, como na m0). Depois da F1, só o perfil, por área, sem `--comando-teste`.
- No fim: o mesmo, sem `--fatia`, com `--base d86e90c`, cobrindo as duas áreas. Atestado em `sociedade/pareceres/atestado-a1-parser.json` do worktree.

## Paradas
- Mudança de escopo, de contrato ou instalação fora do projeto: volta ao Círdan e a Odival. Dependências npm do projeto não são instalação fora do projeto.
- Teto de cerca de 1.500 linhas de produto (sem testes, gerador e fixtures). Se a estimativa passar, pare e devolva com a proposta de divisão.
- Não alterar `.claude/agents/`, `sociedade/` nem `docs/`.
- Até 3 hipóteses diferentes por bloqueio, cada uma registrada; depois, pare e devolva (Q12).
- Push só de `etapa/a1-parser`. O PR é aberto pelo Círdan, pelo conector do GitHub, com o modelo de PR.
- Nenhum dado real; nenhum envio de dado para fora do aparelho.

## Entregas verificáveis
A conferência roda com o `sc.py` do candidato, antes do commit de governança, quando `etapa/a1-parser` ainda é o candidato.

```entregas
E1 | commit_existe | etapa/a1-parser
E2 | arquivos_em | d86e90c..etapa/a1-parser | sociedade-do-codigo/ | .github/ | src/ | tests/ | scripts/ | public/ | package.json | package-lock.json | index.html | vite.config.ts | tsconfig | eslint.config.js | vitest.config.ts | playwright.config.ts | vercel.json | .gitignore
E3 | atestado_aprovado | sociedade/pareceres/atestado-a1-parser.json | etapa/a1-parser
E4 | arquivo_existe | sociedade-do-codigo/tests/test_portao_amarrado.py
E5 | arquivo_existe | scripts/gerar-pdfs-sinteticos.ts
E6 | arquivo_existe | src/leitura
E7 | delegacoes | claude | 8c54e58c-9f4a-56c4-a2da-c8f92be280dc | 5
E8 | conversa_nova | claude | a25b082c93b93db79
E9 | push_feito | etapa/a1-parser
E10 | parecer_valido | sociedade/pareceres/parecer-a1-parser.md
```

## Itens do backlog e simulações
B11, B11a a B11d, B12 e B13. B12: simulação "3 tentativas" plantada pelo Círdan; o resultado vai para os atritos.

## Ajustes da aprovação (Odival, 03/10/2026)
1. Árvore suja ignora só `sociedade/` e os arquivos ignorados pelo `.gitignore` (`node_modules/`, `dist/`, relatórios de teste). A F2 cria o `.gitignore`; a F1 testa com `node_modules/` presente e o portão aprovando.
2. Perfil com a seção "Portão por área" (áreas `app` e `pacote`), escrita pelo Círdan na `sociedade/` do worktree antes do `abrir`. A cópia manual da ordem, do perfil e dos atritos para o worktree é atrito registrado (bootstrap da B11a).
3. Revisão interna da Galadriel: o que ela achar é corrigido dentro da própria fatia, por quem a fez. Nenhuma fatia nova; o que não couber vai para o Barbárvore ou para o backlog.
4. Caso de teste da ordem que se mostrar contraditório com a especificação não trava a fatia: o especialista entrega o resto e devolve só esse caso, com as hipóteses tentadas. A correção do esperado é do Gandalf, pela especificação, dentro do teto de 30 linhas (Q164).
5. Teto: a F2 pode passar de ~500 linhas. Se a etapa passar de 1.500 linhas de produto, o que sobrar vira item da a2, sem fatia nova.
6. Push só de `etapa/a1-parser`.

## Retorno
Até 8 KB, numa devolução só por rodada: subordens (na primeira), entregas preenchidas, commits por fatia, atestados, SHA final, linhas de produto, revisão interna da Galadriel, tarefas do Jules com identificador e resultado do portão do Jules, tentativas por bloqueio, pendências e atritos.
