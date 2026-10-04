# Comandos do ciclo da etapa

Todos via `scripts/sc.py`. O ciclo fecha uma etapa sem passo manual: `abrir`, `entregar`, `revisar` e `decidir`.

Durante a etapa, `abrir`, `entregar`, `conferir --registrar`, `revisar --parecer`, `decidir` e `estado` leem e gravam a `sociedade/` do worktree da etapa (`~/.sociedade/trabalho/<projeto>/<etapa>/sociedade`) se existir; senão, a canônica. `--pasta-sociedade` tem precedência. `estado` sem `--etapa` usa o worktree atual. Se a etapa mudar o perfil (ocupante ou emulação), crie o worktree antes da ordem (`sc.py ordem`), gravando na `sociedade/` do worktree.

| Comando | Faz | Recusa quando |
|---|---|---|
| `abrir --etapa <ID> --ordem <arquivo> --base <commit>` | Abre a etapa no registro a partir da ordem aprovada | ID inválido; ordem inexistente; base inválida; etapa já aberta |
| `entregar --etapa <ID> --base <commit> [--area <nome>]` | Roda portão por área em base..HEAD e grava `sociedade/pareceres/atestado-<ID>.json` | `--comando-teste` (recusado); portão reprova |
| `passar --etapa <ID> --para gandalf\|barbarvore` | Exibe ferramenta, pasta e linha exata a colar na outra ferramenta; grava evento (Q175) | Pasta ausente; papel inválido |
| `revisar --etapa <ID> --base <commit>` | Prepara a cópia descartável para o revisor | Cópia que já existe |
| `revisar --etapa <ID> --parecer <arquivo> --head <commit>` | Registra parecer e salva em `sociedade/pareceres/parecer-<ID>.md` | Falha no lint; commit diferente; registro recusa |
| `decidir --etapa <ID> aceitar\|corrigir\|rejeitar\|sem-aceite --por <nome>` | Grava decisão com nome e commit revisado | Sem `--por` e sem `git config user.name`; etapa não aberta |

Trocas de ocupante: `sc_rodada.py papel trocar` (com `--papel execucao` altera todos os especialistas ativos, Jules e locais). Emulação: `sc_rodada.py papel emulacao ligar|desligar --motivo <m> --autor <a> [--aplicar]`; ao desligar, confere R1–R3 em modo estrito.

## entregar: portão por área

- Comando e timeout vêm só do perfil canônico. `--comando-teste` é recusado.
- Roda áreas tocadas por base..HEAD. Reprovam: árvore suja fora de `sociedade/`, mudança durante portão, saída != 0, timeout, 0 testes e todos pulados.
- Atestado grava perfil, `perfil_sha256`, commit, comandos, timeouts, contagem de testes e saídas.

## decidir

- **aceitar** exige atestado aprovado e parecer válido do **mesmo SHA**, veredito != "não aceitar" e cauda só de `sociedade/`. Registra evidência, grava `aceite_em_emulacao` se ligada, encerra etapa e atualiza `sociedade/evolucao.md`. Com log, grava `consumo`. Integrar é merge do PR, sempre como merge commit (`gh pr merge <n> --merge`), só com o "sim" do usuário na conversa; nega squash, rebase, auto e admin (Q174).
- **corrigir** registra decisão e mantém etapa aberta para nova entrega e revisão.
- **rejeitar** e **sem-aceite** encerram etapa sem aceite (sem exigir atestado ou parecer).

## Cauda de governança (Q149)

Após o SHA revisado só valem commits que tocam apenas `sociedade/`. Commit de produto invalida o parecer.

## Status no GitHub

Jobs `portao` e `aceite` no PR (`sc_status.py`). Falta: commit só de `sociedade/` e push de `etapa/<ID>`.
