# Sessão 1 — etapa `m0-destravar`

**Siga `docs/nuvem/protocolo-sessao.md`.** Esta etapa é a primeira do método refinado na nuvem (C33).

| Campo | Conteúdo |
|---|---|
| Pedido | Linha `m0-destravar` de `sociedade/nuvem/pedidos.md` |
| Backlog | **B01 a B10** (`sociedade/nuvem/backlog.md`, seção "Etapa 0") |
| Alto impacto (Galadriel) | B01 (ciclo e `decidir`), B02 (modo emulação), B05 (status), B06 (cauda de governança) |
| Revisão | **Completa** (`barbarvore`) |
| Onde se mexe | Só em `sociedade-do-codigo/` (a cópia do pacote) e em `.github/` |

**O que esta etapa tem de especial:**

1. **Bootstrap.** Os mecanismos que ela cria ainda não existem no começo.
   - Para **abrir** a etapa no registro, use o roteiro legado, copiado da revisão de 27/09 (`06-plano.md` §2.1):
     1. `sc_rodada --aplicar abrir --id <etapa> --meta … --base <sha> --aceite C1 …`
     2. `sc.py entregar --etapa <etapa> --base <sha>`
     3. `sc.py conferir --ordem sociedade/ordens/<etapa>.md --registrar`
     4. `sc.py revisar --etapa <etapa> --base <sha>`, com o parecer passando no `lint_parecer.py`
     5. `sc_rodada --aplicar fatia N --fechar --prova sociedade/pareceres/atestado-<etapa>.json`
     6. `sc_rodada --aplicar evidencia …` (evidência **declarada**: DG-02)
     7. `sc_rodada --aplicar parecer … --implementador Gandalf --sincronizar-git`
     8. ~~`sc_rodada --aplicar encerrar`~~ — **não use**: o encerramento é pelo comando novo.
   - Os scripts ficam em `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/`.
   - Para **fechar**, use o **comando novo** que a própria etapa criou (`sc.py decidir`). Esse é o aceite da C33.
   - Todo passo manual ou legado conta como atrito.
2. **Status.** Enquanto a B05 não estiver pronta, os status `portao` e `aceite` não são publicados. Isso é esperado e vira atrito. No fim da etapa, o portão novo publica `portao` no SHA final, e o `decidir` publica `aceite`.
3. **Ambiente.** Confira e relate também:
   - se os links simbólicos de `.claude/skills/` carregaram as skills;
   - se `sc.py sessao claude` encontra as transcrições dos subagentes desta sessão.

   As duas respostas são evidência para a B03.
4. **Sondas (B09).** Cada sonda cita o achado DG que reproduz e vai em `sociedade-do-codigo/tests/` (pasta `adversarial/`).
5. **Métricas (B10).** A primeira linha de `sociedade/evolucao.md` é a desta etapa.
