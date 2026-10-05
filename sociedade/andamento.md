# Andamento — Aposte em Você na formação real

Atualizado em 05/10/2026 pelo Círdan. Limite: 5 KB (Q170).

## Formação (desde 03/10, na d1-design)
| Papel | Ferramenta | Modelo |
|---|---|---|
| Círdan | Claude Code | Opus 5.5, high |
| Gandalf e especialistas | Antigravity | Gemini 3.8 Flash, high |
| Barbárvore | Codex | GPT-6 Sol, xhigh, "revisor não calibrado" (Q160) |

Emulação desligada. Jules e executores locais em espera.

## Etapas
| Etapa | Ramo | Resultado |
|---|---|---|
| m0, a1, fechamento-nuvem | integradas (PR #1–#3) | aceite em emulação |
| d1-design | `etapa/d1-design` (`4fdd7b5`), sem PR | **rejeitada** (Q85 esgotado): A01, A02 e A03 nos scripts do método e regressão A06 nas permissões. O design (referência, T08, T09, T99 e capturas em 360 px) ficou sem achado aberto |
| d1b-robustez | `etapa/d1b-robustez`, base `4fdd7b5` | **aberta**: resíduos da d1 e processo honesto; leva o design da d1 para a `main` |

A avaliação da d1, com consumo e retrabalho medidos, está em `sociedade/avaliacao-d1-design.md`. Ela originou as decisões Q176–Q182.

## Pendente, em ordem
1. **d1b-robustez:** a ordem está em `sociedade/ordens/d1b-robustez.md`.
2. Depois do merge: devolver a 3.3.0 ao `sociedade_do_codigo` (C40) e reinstalar no Antigravity e no Codex (C53).
3. **a2a:** conferência e catálogo, com B17a e B17c. **O Jules estreia aqui** (catálogo com fontes e conferência de links). Antes, o Círdan o ativa no perfil e Odival confirma o acesso dele ao repositório (decisão de 05/10).
4. **a2b:** entrevista, com B14 e B15r.
5. a3, a4 e a sessão final.

A fila completa está em `sociedade/nuvem/backlog.md`, seção "Fila fora da nuvem".

## Como o ciclo roda agora
1. **Círdan:**
   - cria o worktree;
   - escreve a ordem (`sc.py ordem`) com os usos conferidos (Q172);
   - espera o "aprovo" de Odival.
2. **Círdan:**
   - roda `sc.py abrir`;
   - faz o **commit de governança no início**, quando muda perfil ou regras (Q178), e o push;
   - roda `sc.py passar --para gandalf`;
   - dá a Odival a pasta e a linha (Q175).
3. **Gandalf** (Antigravity): uma conversa por rodada (Q180). Para no `entregar` final e devolve (Q177). Não edita lógica (Q181).
4. **Círdan:**
   - abre o PR;
   - roda `sc.py conferir --registrar`, `sc.py revisar` e `sc.py passar --para barbarvore`;
   - dá a Odival a pasta e a linha do Codex.
5. **Barbárvore** (Codex): sessão nova. A reconferência também vai em sessão nova e com parecer próprio (Q179, Q180).
6. **Círdan:** `sc.py revisar --parecer`.
7. **Odival:** `sc.py decidir`; corrigir e rejeitar levam motivo.
8. **Círdan:** commit de governança da cauda.
9. **Merge** com o "sim" de Odival: `gh pr merge <n> --merge` (Q174).

## Para a próxima abertura
- A pré-visualização da Vercel é protegida por login. Produção sai só do ramo `producao`, com o "vai" de Odival.
- Dados só sintéticos. O extrato real fica só no celular de Odival.
- O consumo do Antigravity não aparece no log local (n/d). Os indicadores são passos e releituras (`sc.py sessao antigravity`).
