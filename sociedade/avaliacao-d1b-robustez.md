# Avaliação da d1b-robustez

Feita pelo Círdan em 06/10/2026. Etapa **rejeitada** por Odival (EVT-000055), com o motivo "separar app e método". O parecer completo do Barbárvore está em `sociedade/pareceres/parecer-d1b-robustez.md` (sha256 `dfe902cc…`): não aceitar, com D01–D08 bloqueadores, D09–D13 relevantes e D14 opcional.

## O que melhorou em relação à d1
- **Q182 cumprida:** 9 delegações aos agentes instalados (`elrond`, `galadriel`), nenhuma com `self`.
- **Q177 cumprida:** o Gandalf parou no `entregar` final, e PR, conferência, cópia e passagem ficaram com o Círdan.
- **Q178 cumprida:** não houve reescrita de histórico.
- **Rodada 2 dentro da meta:** 158 passos e nenhuma edição de lógica pelo Gandalf.
- **A conferência antes da revisão pegou K1:** a gravação real deixava o registro ilegível. O registro foi preservado.
- **Os cenários originais da d1 foram fechados** (A02, A03, A05, A06 e o caminho legítimo da A01), segundo o próprio revisor.
- **O revisor gastou bem menos:** sessão nova com 8,7 milhões de tokens de entrada (eram 18,9 milhões).

## O que falhou, com a causa
| Falha | Causa | Decisão |
|---|---|---|
| 6 dos 8 bloqueadores nos recursos de processo P1–P3 (D01, D05, D06, D07) e na cópia (D11, D12) | O escopo cresceu: recursos novos dentro de uma etapa de correção, por recomendação do Círdan | Q185 |
| D04: a soma de rodadas contradiz a ordem | O achado K4 do Círdan mudou um requisito aprovado | Q184 |
| D02, D03 e D13: variantes adversariais sem fim | Não havia modelo de ameaça; o formato de permissões não distingue opção de texto citado | Q183 |
| D08 e o app sem rodar: a cópia levou o atestado da rodada 1 e um `node_modules` ligado fora da pasta autorizada | A cópia monta `sociedade/` no commit do candidato e liga as dependências | Q186 |
| Parecer não registrável | O revisor citou o SHA da cópia, e não o original | Q186 |
| E6 e E7 não verificáveis | O Antigravity grava a pasta principal do projeto como workspace, e não o worktree | Abrir o worktree como workspace |
| Rodada 1 com 413 passos e uma edição de lógica do Gandalf (`5e95a71`) | Ele depurou a conferência em vez de devolver | Q181, já valia |

## Para a trilha de método (repositório canônico)
- Partir de `02e58dd` (d1b) e dos achados D01–D14, sob um modelo de ameaça escrito (Q183), em etapas de até 3 mecanismos (Q185).
- Incluir: `revisar` montando `sociedade/` no HEAD, com dependências dentro da cópia e o SHA original no parecer; a identidade das conversas quando o workspace é a pasta principal; e a leitura do registro deste projeto, que mistura eventos sem hash (1–41) e com hash (42 em diante, corte 42).
