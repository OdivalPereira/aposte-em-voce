# Andamento — Aposte em Você: passagem da nuvem para a máquina local

Atualizado em 03/10/2026 pelo Círdan, no fim da sessão 3, a **última em nuvem**. Limite: 5 KB (Q99, Q170).

## O que cada sessão fez

| Sessão | Etapa | PR | Resultado |
|---|---|---|---|
| 1 | m0-destravar (B01–B10) | #1, integrado | Ciclo `abrir`, `entregar`, `revisar --parecer`, `decidir`; status `portao` e `aceite` no Actions; modo emulação |
| 2 | a1-parser (B11–B13, B11a–B11d) | #2, integrado | Portão amarrado ao perfil por área; app Vite/Preact com leitura no worker, T08, T09, T99 e CSP. Visual reprovado (Q169). F3 do Jules não entrou (B17a) |
| 3 | fechamento-nuvem | #3, **aguarda o merge** | Consumo medido pelo log e regras de economia (Q170–Q173); histórico mensal por conta, encadeamento de saldos, assinatura do layout na T99, layout agrupado por dia (estilo Nubank); B15 (adulteração detectada) e B17b |

Todas aceitas por Odival com `sc.py decidir`, "aceite em emulação" e "revisor não calibrado".

## Consumo medido (log, Q170)

| Sessão | Cache lido | Cache escrito | Saída |
|---|---|---|---|
| 1 | n/d (outro contêiner) | n/d | n/d |
| 2 | 65,8 milhões | 2,3 milhões | 79 mil |
| 3 | 43,1 milhões | 1,8 milhão | 45 mil |

Quase tudo é releitura. As maiores parcelas vêm de agentes retomados por mensagem (Elrond: 15 milhões na sessão 3). O Gandalf aberto do zero a cada rodada, lendo só o arquivo de estado, ficou em 2,2 milhões.

## Pendente, em ordem de prioridade

A fila completa está em `sociedade/nuvem/backlog.md`, seção "Fila fora da nuvem":
0. Troca do perfil para a formação real.
1. **d1-design.**
2. **a2a**: conferência e catálogo, com B17a e B17c.
3. **a2b**: entrevista, com B14 e B15r.
4. a3, a4 e a sessão final.

Antes da d1, Odival testa os extratos mensais na pré-visualização do PR #3 e cola a assinatura do layout (T99) quando um banco falhar.

## Como retomar com a formação real

1. **Integre o PR #3** (Odival). Instale o pacote nas ferramentas (C53) e devolva a cópia ao repositório `sociedade-do-codigo` (C40).
2. **Primeira etapa local: comece pela troca do perfil.** Ela não foi feita no PR #3, porque o `aceite` confere o fornecedor do parecer com o perfil e ficaria vermelho.
   - Use `sc_rodada.py papel trocar`, com motivo e autor (R4).
   - Desligue `- **Emulação:** sim`.
   - A formação real:

   | Papel | Ferramenta | Modelo | Esforço |
   |---|---|---|---|
   | Círdan | Claude Code | Opus 5.5 | high |
   | Gandalf e especialistas | Antigravity | Gemini 3.8 Flash | high |
   | Barbárvore | Codex | GPT-6 Sol | xhigh, "revisor não calibrado" (Q160) |

3. **d1-design.** Pedido: "Quero que o app tenha uma cara moderna, sóbria e acolhedora, com uma referência visual que eu aprovo e que vale para todas as telas, começando por extratos, resultado e diagnóstico." A referência visual é aprovada por Odival **antes** da ordem. As fatias de tela são do Legolas, e o PR traz capturas em 360 px (Q169, Q173).
4. **Ciclo:**
   - `sc.py ordem` e, antes da aprovação, o `grep` dos usos reais (Q172);
   - `sc_worktree.py criar` e depois `sc.py abrir`; durante a etapa, a `sociedade/` do worktree é a canônica (Q166);
   - `sc.py entregar` sem `--comando-teste`, por área;
   - `sc.py conferir --registrar`;
   - `sc.py revisar --head <candidato>`, depois o Barbárvore no Codex, depois `sc.py revisar --parecer`;
   - `sc.py decidir --por Odival`.
5. **Delegação.** No Antigravity, o Gandalf delega direto. O revezamento (Q161) era limite do Claude Code. Correção vai a um agente novo (Q171), com devolução de até 2 KB e estado em arquivo (Q170).
6. **Medição.** O `sc.py sessao` soma tokens só para o Claude (F1). Para o Antigravity e o Codex, isso fica para o pacote.

## Para a próxima abertura

- Não leia a proteção da `main`; ela exige `ci`, `portao` e `aceite`. O PR sai pelo `gh`, se a ferramenta permitir; na nuvem saía pelo conector.
- A pré-visualização da Vercel é protegida por login. Produção sai só do ramo `producao`, com o "vai" de Odival.
- Dados só sintéticos. Extrato real fica só no celular de Odival.
