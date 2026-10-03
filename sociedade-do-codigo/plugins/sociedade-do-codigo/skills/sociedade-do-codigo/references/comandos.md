# Comandos do ciclo da etapa

Todos via `scripts/sc.py`. O ciclo fecha uma etapa sem passo manual: `abrir`, `entregar`, `revisar` e `decidir`.

| Comando | Faz | Recusa quando |
|---|---|---|
| `abrir --etapa <ID> --ordem <arquivo> --base <commit>` | Abre a etapa no registro a partir da ordem aprovada (critério `portao`) | ID fora de `^[a-z0-9][a-z0-9-]{0,39}$`; ordem inexistente; base que não resolve; etapa já aberta ou outra ativa |
| `entregar --etapa <ID> --base <commit> [--comando-teste "<cmd>"]` | Roda o portão sobre base..HEAD e grava `sociedade/pareceres/atestado-<ID>.json` | O portão reprova (o atestado sai REPROVADO) |
| `revisar --etapa <ID> --base <commit>` | Prepara a cópia descartável para o revisor | Cópia que já existe |
| `revisar --etapa <ID> --parecer <arquivo> --head <commit>` | Registra o parecer no registro e guarda a cópia em `sociedade/pareceres/parecer-<ID>.md`. O `commit` fica no evento | Parecer que não passa no `lint_parecer`; `commit:` diferente do SHA revisado; registro que recusa (independência) |
| `decidir --etapa <ID> aceitar\|corrigir\|rejeitar\|sem-aceite --por <nome>` | Grava a decisão com o nome de quem decide e o `commit` revisado | Sem `--por` e sem `git config user.name` (não há nome padrão); etapa não aberta |

## decidir

- **aceitar** exige atestado aprovado e parecer válido do **mesmo SHA** (commit do atestado = commit do parecer, também registrado), com veredito diferente de "não aceitar" e cauda só de `sociedade/` até o head. Registra a evidência do portão, grava `aceite_em_emulacao` (se a chave do perfil estiver ligada) com independência "não", encerra a etapa e acrescenta a linha de `sociedade/evolucao.md`. Opções de medida (todas opcionais, ausente = `n/d`): `--minutos`, `--intervencoes`, `--escaparam`, `--sessao`, `--log`, `--projetos`.
- **corrigir** registra a decisão e deixa a etapa aberta: corrija, rode `entregar` e `revisar --parecer` de novo e decida outra vez.
- **rejeitar** e **sem-aceite** registram a decisão e encerram a etapa sem aceite (`desfecho` no evento; nunca elegível à publicação). Não exigem atestado nem parecer: negar não pode depender deles.
- O head da cauda é o ramo `etapa/<ID>`, ou o `HEAD`; `--head` troca.

## Cauda de governança (Q149)

Depois do SHA revisado só valem commits que tocam apenas `sociedade/` (sem merge). Commit de produto derruba o parecer e o `decidir aceitar` recusa. A regra é `sc_ciclo.parecer_vale`.

## Status no GitHub

O `decidir` não publica status pelo `gh`. `portao` e `aceite` são jobs do Actions (`sc_status.py`) que rodam no PR. O comando imprime o que falta: commit só de `sociedade/` e push de `etapa/<ID>`.
