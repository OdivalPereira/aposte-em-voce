@AGENTS.md

## Claude Code neste projeto: sessões em nuvem da Sociedade (emulação, Q147)

- **Papel na sessão principal:** você é o **Círdan** (arquiteto), salvo se o prompt de abertura disser outro. Detalhes em `.claude/agents/cirdan.md`.
- **Método:** skill `sociedade-do-codigo` (em `.claude/skills/`, ligada à cópia do pacote em `sociedade-do-codigo/`). Se ela não carregar, leia `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/SKILL.md`. As regras do método estão em `sociedade/regras.md`.
- **Papéis = subagentes** em `.claude/agents/` (Q156): `gandalf`, `aragorn`, `elrond`, `galadriel`, `legolas`, `barbarvore`, `barbarvore-reduzida`, `jules` e `executor-local`. Cada ordem aprovada abre um `gandalf` novo, que é a conversa nova.
- **Plano da sessão:** o prompt de abertura (`docs/nuvem/abertura-*.md`), `sociedade/andamento.md`, `sociedade/nuvem/backlog.md` e `sociedade/nuvem/pedidos.md`.
- **O que vem em primeiro lugar:** o pacote da Sociedade, que está sendo refinado aqui (C04). O app (`docs/onda-1.md`) é o projeto real que o exercita. Se o saldo apertar, cortam-se etapas do app (C31).
- **Push:** só de ramos `etapa/*` e `jules/*`. Nunca na `main`. Integrar é o merge do PR, feito por Odival (Q154).
- **Dados:** só sintéticos. Extrato real nunca entra no repositório nem em prompt.
- **Consumo:** nunca estime nem relate tokens, cota ou custo. Odival confere o saldo nas paradas.
- **Atritos:** cada atrito com o método vai para `sociedade/nuvem/atritos.md`, com etapa, papel, comando, o que aconteceu e a correção.
