# Sessão 6 — final (reserva de US$ 10, C60)

**Siga `docs/nuvem/protocolo-sessao.md`, com estas diferenças:**
- não há etapa de app;
- a ordem é de **governança e revisão**.

| Item | O que fazer |
|---|---|
| **F1** | Revisão **completa** (`barbarvore`) do diff acumulado do pacote: `git diff <primeiro commit do repositório>..HEAD -- sociedade-do-codigo/`. Ela pega as costuras entre as etapas (C47). Achados bloqueadores voltam como correção única (Q85) |
| **F2** | `sociedade/regras.md` final e `sociedade/nuvem/decisoes-q146.md` final, com as decisões novas aprovadas nas paradas. Mudança de regra sem aprovação fica como proposta |
| **F3** | Proposta de ajuste das regras de leitura (Q21, Q99, Q128), com os números medidos (C52) |
| **F4** | `sociedade/nuvem/relatorio-final.md` (o que foi testado e como; métricas contra as metas; atritos; o que a emulação não testou; backlog restante), `sociedade/nuvem/manual-odival.md` (uma página), entrada 4.0.0 no `sociedade-do-codigo/CHANGELOG.md` com a origem de cada mudança, e `VERSION` 4.0.0 (C48, C49) |
| **F5** | Aviso de depreciação em `sc_rodada`, `sc_passagem`, na calibração e nos níveis; nenhum documento os cita como caminho normal (C28) |

**Fim.** Peça a Odival o merge do PR final. A devolução ao repositório `sociedade-do-codigo` (C40) e a instalação nas ferramentas (C53) acontecem depois, numa conversa local.
