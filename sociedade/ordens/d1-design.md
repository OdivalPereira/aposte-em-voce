# Ordem d1-design — referência visual sóbria e acolhedora em T08, T09 e T99, e a Sociedade pronta para a formação real

Para: Gandalf (Antigravity, Gemini 3.8 Flash, esforço high) · CONVERSA NOVA
Etapa: d1-design · Base: `c927e5d` (main, PR #3 integrado) · Worktree: `~/.sociedade/trabalho/aposte-em-voce/d1-design` · Ramo: `etapa/d1-design`
Especialistas: Elrond (F4), Legolas (F1), Galadriel (F3), Elrond em instância nova (F5), Legolas em instância nova (F2) · Revisão interna: nenhuma (a única revisão é a do Barbárvore) · Jules: nenhum
Revisão independente: **reduzida**, Barbárvore (Codex, GPT-6 Sol, xhigh), "revisor não calibrado" (Q160). Primeira etapa na formação real: sem a marca de emulação.

## Objetivo
Pedido de Odival: "Quero que o app tenha uma cara moderna, sóbria e acolhedora, com uma referência visual que eu aprovo e que vale para todas as telas, começando por extratos, resultado e diagnóstico."

E, por decisão de Odival na abertura: a Sociedade do Código é corrigida nesta mesma etapa. Ela sai daqui pronta para a formação real (lacunas L1–L8, abaixo).

Como Odival percebe:
- uma página de referência na pré-visualização, com tokens, componentes e estados, que ele aprova antes de qualquer tela mudar;
- T08, T09 (incluindo o histórico mensal) e T99 com a cara da referência, em capturas de 360 px no PR, sem mudança de comportamento;
- o `CLAUDE.md` e o `.claude/` falam da formação real, e o merge pede o "sim" dele;
- o pacote na 3.2.0: a troca de perfil, a emulação, a passagem entre ferramentas e a conferência no Antigravity e no Codex saem por comando, sem edição à mão.

## Leia só
1. Esta ordem.
2. `sociedade/regras.md`, seções 3 e 4.
3. `docs/onda-1.md`: seção 2 (os 10 princípios) e as linhas T08, T09 e T99 da seção 4.
4. `sociedade/perfil.md`, seção "Portão por área".
5. `sociedade/subordens/d1-design-gandalf-estado.md`, quando existir.

Cada especialista lê só o seu escreva-só e o que a subordem citar, **por trecho**.

## Economia (Q170–Q173)
- Devolução de qualquer agente: até **2 KB** no chat. O detalhe vai para `sociedade/subordens/d1-design-<fatia>-retorno.md`, que o próximo lê só se precisar.
- O Gandalf não fica numa conversa longa. Cada rodada termina gravando o estado em `sociedade/subordens/d1-design-gandalf-estado.md`.
- Correção, ajuste ou continuação vai para um **agente novo** do mesmo papel, que lê o retorno e o achado. Nunca para a instância antiga retomada por mensagem.
- Testes e portão com saída curta: só o resumo e as falhas.

## Onde se mexe
O candidato não altera `sociedade/` nem `docs/` (exceto `docs/capturas/d1-design/`). Só o Gandalf grava os arquivos de estado e retorno em `sociedade/subordens/`. Especialistas não comitam. O Gandalf comita por fatia e roda o portão num checkout limpo, e a base da fatia é o commit anterior (Q165).

Abreviações:
- `P = sociedade-do-codigo`
- `S = P/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`
- `T = P/tests`
- `C = /home/odival/Documentos/Projetos/sociedade_do_codigo/sociedade-do-codigo` (a 3.1.0 canônica, só leitura)

## Lacunas do método (achadas na abertura, corrigidas aqui)
| # | Lacuna | Fatia |
|---|---|---|
| L1 | Não há comando para ligar ou desligar a emulação; a linha do perfil foi editada à mão. Com a emulação ligada, a troca prefixa o motivo com "emulação:", mesmo quando é a troca que sai dela | F5 |
| L2 | `papel trocar --papel execucao` disse "atualizado com sucesso" e gravou o evento, mas não mudou Aragorn, Elrond, Galadriel nem Legolas. A conferência de R3 passou com a execução fora do Google. Não há como alcançar Jules nem executores locais | F5 |
| L3 | A passagem entre ferramentas (pasta e linha exatas) depende da memória do Círdan | F5 |
| L4 | `sc.py sessao` só soma tokens do Claude | F5 |
| L5 | O adaptador Claude do pacote é o da emulação: o modelo nega `gh pr merge` e não há modelo de Círdan só arquiteto | F3 |
| L6 | Os textos do pacote não têm a integração com o "sim" de Odival por merge commit (Q174) nem a passagem (Q175). O ciclo não diz para criar o worktree antes da ordem quando a etapa muda o perfil | F3 |
| L7 | `sc.py ordem --etapa d1-design`, rodado dentro do worktree da etapa, gravou a ordem na `sociedade/` da main, e não na do worktree (Q166) | F5 |
| L8 | As entregas `delegacoes` e `conversa_nova` do Antigravity pedem o id da conversa, que só existe depois da aprovação da ordem | F5 |

## Sequência
1. F4.
2. F1, F3 e F5 em paralelo (escreva-só disjuntos; F3 e F5 partem do commit da F4).
3. **Parada visual.**
4. F2.
5. Integração da versão.
6. Portão final.

## Fatias
1. **F4 · Pacote 3.1.0** · Elrond · escreva só: os arquivos de `P/` que diferem de `C/` (VERSION, `pacote.json`, `CHANGELOG.md`, `README.md`, os quatro manifestos, os quatro `SKILL.md`, `references/contrato-nucleo-projeto.md`, `T/test_ci_pipefail.py`, `T/test_metricas.py`) e `AGENTS.md` (só o bloco, por `sc_sync_agents_md.py --aplicar`) · aceite:
   - `diff -rq P C -x __pycache__` vazio;
   - o bloco do `AGENTS.md` com `nucleo=3.1.0`;
   - suíte do pacote e `validar_pacote.py` verdes.
2. **F1 · Referência visual** · Legolas · escreva só: `src/ui/` (arquivos novos; `estilos.css` só para importar os tokens), `src/referencia/` (novo), `referencia.html` (nova entrada, sem link a partir do app), `vite.config.ts` (só `build.rollupOptions.input`) e `tests/unit/contraste.test.ts` (novo) · aceite:
   - **Direção:** moderna, sóbria e acolhedora. O público é de adultos afetados por apostas: nada de cor de alerta como base, nada de estética de cassino, nada de tom de julgamento.
   - **Tokens:** cor (fundo, superfície, texto, texto secundário, primária, foco, sucesso, atenção, erro, borda), tipografia (família, escala e alturas de linha) e espaçamento (escala única).
   - **Componentes:** botão (primário, secundário e discreto), cartão, campo, aviso (informação, atenção e erro), progresso e lista.
   - **Estados:** vazio, carregando e erro, cada um com texto e ação.
   - **WCAG 2.2 AA:**
     - contraste de 4,5:1 no texto e de 3:1 no texto grande, nos componentes e no foco;
     - foco visível e não encoberto (2.4.7, 2.4.11);
     - alvo de 24×24 px ou mais (2.5.8);
     - reflow em 320 px (1.4.10);
     - espaçamento de texto (1.4.12);
     - `prefers-reduced-motion`.
   - O `contraste.test.ts` calcula o contraste de cada par declarado nos tokens e falha abaixo do mínimo.
   - Nenhuma fonte externa nem CDN (CSP e princípio de privacidade): fonte do sistema ou empacotada no build, com licença livre. Respeite a CSP do `vercel.json` (sem estilo nem script inline) e não mexa nela.
   - A página `/referencia.html` mostra tudo isso em 360 px e em largura de desktop, só com conteúdo fictício.
   - Se o plugin `modern-web-guidance` estiver disponível no Antigravity, o Legolas pode usá-lo.
   - `npm test`, `npm run lint` e `npm run build` verdes.
3. **PARADA VISUAL (Odival).** O Gandalf:
   - comita a F1 e roda o portão da fatia;
   - faz push do `etapa/d1-design`;
   - devolve a Odival o link da pré-visualização da Vercel daquele commit (`gh`, status do commit) com `/referencia.html`;
   - **para**, gravando o estado.

   Odival responde na mesma conversa do Antigravity: "aprovo a referência" ou os ajustes. Cada ajuste vai para um Legolas novo, e o Gandalf para de novo. Nenhuma tela muda antes do "aprovo".
4. **F2 · Aplicação** · Legolas, instância nova, só depois do "aprovo" · escreva só: `src/telas/`, `src/ui/`, `src/app.tsx` (só a estrutura visual), `tests/e2e/` (seletores, se mudarem, e `capturas.spec.ts`, novo), `package.json` (só o script `capturas`) e `docs/capturas/d1-design/` · proibido: `src/leitura/`, `src/ui/formatar.ts` e dependência nova · aceite:
   - T08, T09 e T99 usam só os tokens e componentes da F1, nos estados vazio, carregando e erro.
   - A T09 inclui o histórico mensal: período total, meses cobertos, meses faltando e aviso de encadeamento.
   - Nenhuma mudança de comportamento: os testes de unidade passam sem mudar nenhum esperado. No e2e, só seletores podem mudar, nunca o esperado.
   - `npm run capturas` (`CAPTURAS=1`; fora do `npm test`, porque a spec se pula sem a variável) grava em `docs/capturas/d1-design/`, em 360 px:
     - `referencia`;
     - `t08-vazio`, `t08-carregando` e `t08-erro`;
     - `t09-resultado` e `t09-historico`;
     - `t99-diagnostico`.
   - Todas as capturas só com dados sintéticos.
   - `npm test`, `npm run lint` e `npm run build` verdes.
5. **F3 · Formação real no projeto e no pacote** · Galadriel · escreva só: `.claude/agents/` (apagar), `CLAUDE.md`, `.claude/settings.json`, `P/adapters/claude/`, `P/adapters/antigravity/LEIA-ME.md`, `P/adapters/codex/LEIA-ME.md` e os `.md` de `S/../SKILL.md`, `S/../references/`, `P/plugins/sociedade-do-codigo/skills/sc-papeis/` e `.../sc-execucao/` (nenhum script) · aceite:
   - `.claude/agents/` não existe mais.
   - O `CLAUDE.md` mantém o `@AGENTS.md` e diz:
     - você é o Círdan (arquiteto) e não executa, não revisa nem lê código;
     - a formação: Gandalf e especialistas no Antigravity, Barbárvore no Codex;
     - não despache subagentes do Claude para outros papéis;
     - a cada passo em outra ferramenta, diga a Odival a pasta e a linha exatas (`sc.py passar`, Q175) e espere;
     - integrar é o merge do PR, só com o "sim" de Odival na conversa, sempre como merge commit (`gh pr merge <n> --merge`, Q174);
     - push só de `etapa/*`;
     - dados só sintéticos;
     - economia (Q170–Q173);
     - medir pelo log é permitido e estimar é proibido.

     Sai tudo o que for de sessão em nuvem.
   - `.claude/settings.json`:
     - `Bash(gh pr merge*)` sai de `deny` e vai para `ask`;
     - entram em `deny` `Bash(gh pr merge*--squash*)`, `Bash(gh pr merge*--rebase*)`, `Bash(gh pr merge*--auto*)` e `Bash(gh pr merge*--admin*)`;
     - o resto fica igual, e o `_comentario` cita a Q174.
   - Pacote (L5 e L6):
     - `adapters/claude/CLAUDE.md.modelo` passa a ser o do Círdan na formação real;
     - `settings.json.modelo` com as mesmas regras de merge;
     - o LEIA-ME do Claude, do Antigravity e do Codex com a passagem e o papel de cada ferramenta;
     - núcleo, `sc-papeis` e `sc-execucao` com a Q174, a Q175, os comandos de emulação e de passagem da F5 e a regra "crie o worktree antes da ordem quando a etapa mudar o perfil".
   - `validar_pacote.py` verde.
6. **F5 · Scripts do método** · Elrond, instância nova · escreva só: `S/sc_rodada.py`, `S/sc_perfil.py`, `S/sc_passagem.py`, `S/sc_sessao.py`, `S/sc_conferir.py` (só a L8), `S/sc.py` (só `ordem`, `passar` e `sessao`), `S/sc_worktree.py` (só se a L7 exigir), `T/test_troca_papel.py`, `T/test_emulacao.py` e testes novos em `T/` · aceite, com pelo menos um teste por lacuna, só com dados sintéticos:
   - **L1:** `sc_rodada.py papel emulacao ligar|desligar --motivo --autor [--aplicar]` troca a linha `- **Emulação:**` e grava o evento no registro, em cadeia de hash.
     - Ao desligar, confere R1–R3 em modo estrito e recusa, sem gravar, se houver violação.
     - `papel status` mostra o estado da emulação.
     - O prefixo "emulação:" deixa de entrar no motivo quando a troca é parte da saída da emulação.
   - **L2:** `papel trocar --papel execucao` altera todos os especialistas ativos, e Jules e executores locais são alcançáveis (incluindo `espera`, sem ocupante).
     - Uma troca que não altera nenhuma linha falha e não grava evento.
     - A conferência de R3 acusa execução fora do Google sem decisão registrada.
     - Teste novo `T/test_formacao_real.py`: reproduz a troca desta abertura (perfil sintético todo Anthropic com emulação, saindo para Claude Code + Antigravity + Codex). No fim, `--emulacao` dá "não", `papel status` não mostra aviso e nenhuma linha fica emulada.
   - **L3:** `sc.py passar --etapa <ID> --para gandalf|barbarvore` imprime três linhas:
     - a ferramenta, o modelo e o esforço (do perfil), com "conversa nova";
     - a pasta absoluta (o worktree da etapa ou a cópia do `revisar`);
     - a linha exata a colar.

     Para o Gandalf: `Para: Gandalf. Execute a ordem sociedade/ordens/<ID>.md.`. Para o Barbárvore: a linha com a seção "Revisão" da ordem e o arquivo do parecer. O comando grava um evento `passagem` com data e hora.
   - **L4:** `sc.py sessao codex` soma entrada, cache lido e saída pelo log de `~/.codex/sessions`. `sc.py sessao antigravity` lê as bases de `~/.gemini/antigravity/conversations/`; se o log não expuser tokens, sai "n/d" com o motivo, sem quebrar (Q12: até 3 hipóteses).
   - **L7:** `sc.py ordem --etapa <ID>` grava na `sociedade/` do worktree da etapa, quando ele existe.
   - **L8:** nas entregas `delegacoes` e `conversa_nova` do Antigravity, o id aceita `@etapa`. Ele é resolvido para a conversa aberta na pasta do worktree depois da `passagem` para o Gandalf. Ambiguidade ou ausência: "não feito", com motivo.
   - Suíte do pacote e `validar_pacote.py` verdes.
7. **Integração (Gandalf, até 30 linhas, Q164):** versão **3.2.0** (VERSION, `pacote.json`, manifestos e `SKILL.md`) e CHANGELOG com L1–L8, a partir dos retornos da F3 e da F5. `validar_pacote.py` verde.

## Portão
- Por fatia: `sc.py entregar --etapa d1-design --base <commit anterior> --fatia <N> --pasta-projeto <worktree> --pasta-sociedade <worktree>/sociedade`, num checkout limpo.
- No fim: o mesmo, sem `--fatia` e com `--base c927e5d`, cobrindo as áreas `app` e `pacote`.

## Paradas
- A parada visual da F1.
- Mudança de escopo, de contrato ou instalação fora do projeto: volta ao Círdan e a Odival.
- Teto de 1.500 linhas de produto por área, contadas por script (Q168). Estimativa: cerca de 1.200 em `app`, contando as 447 linhas apagadas de `.claude/agents/`, e cerca de 800 em `pacote`. Se passar, a F2 para onde estiver: vale o que passou no portão, e o resto fica pendente.
- Até 3 hipóteses por bloqueio (Q12).
- Dado só sintético.
- Push só de `etapa/d1-design`.
- O PR é aberto pelo Círdan, com as capturas.

## Fica de fora
- Tema escuro.
- Telas T01–T07 e T10.
- Retirar `/referencia.html` da produção: ela fica como referência viva para as próximas etapas.
- A devolução da 3.2.0 ao repositório canônico e a reinstalação nas ferramentas, que vêm depois do merge, com decisão de Odival.

## Revisão (Barbárvore, reduzida)
Passo 0 e as lentes pertinentes:
1. **Acessibilidade:** WCAG 2.2 AA nos tokens, nos componentes e nas capturas em 360 px, comparadas com a referência aprovada (Q169).
2. **Regressão funcional:** nada em `src/leitura/` e nenhum esperado de teste alterado.
3. **Permissões:** `.claude/settings.json` e `adapters/claude/settings.json.modelo`. Merge só como merge commit e nunca com `--admin` nem `--auto`.
4. **Integridade do método:**
   - a emulação não desliga com R1–R3 violadas;
   - nenhuma troca grava evento sem alterar o perfil;
   - a cadeia de hash do registro se mantém;
   - `@etapa` não aceita uma conversa de outra pasta.

   O `conferir` desta etapa roda com os scripts do candidato. Confira que isso não afrouxa nenhuma entrega.

## Entregas verificáveis
```entregas
E1 | commit_existe | etapa/d1-design
E2 | arquivos_em | c927e5d..etapa/d1-design | src/ | tests/ | referencia.html | vite.config.ts | package.json | docs/capturas/d1-design/ | CLAUDE.md | .claude/ | AGENTS.md | sociedade-do-codigo/
E3 | atestado_aprovado | sociedade/pareceres/atestado-d1-design.json | etapa/d1-design
E4 | arquivo_existe | referencia.html
E5 | arquivo_existe | docs/capturas/d1-design/t09-historico.png
E6 | arquivo_existe | sociedade-do-codigo/tests/test_formacao_real.py
E7 | delegacoes | antigravity | @etapa | 5
E8 | conversa_nova | antigravity | @etapa
E9 | push_feito | etapa/d1-design
E10 | parecer_valido | sociedade/pareceres/parecer-d1-design.md
```

## Retorno
Até 2 KB no chat:
- veredito;
- commits por fatia;
- atestado;
- link da pré-visualização;
- lista das capturas;
- lacunas L1–L8 resolvidas ou pendentes.

O detalhe vai para `sociedade/subordens/d1-design-gandalf-estado.md`.
