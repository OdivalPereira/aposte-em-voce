# Andamento — Aposte em Você (sessões em nuvem da Sociedade)

Atualizado em 03/10/2026 pelo Círdan, no fim da sessão 1. Limite: 5 KB (Q99).

## Onde estamos

**Sessão 1 (`m0-destravar`) aceita por Odival** em 03/10/2026, com `sc.py decidir` ("aceite em emulação", revisor não calibrado).
- PR: OdivalPereira/aposte-em-voce#1, ramo `etapa/m0-destravar`. Candidato `fb3ae42` (base `3bff553`); depois dele, só a cauda de `sociedade/`.
- Ciclo novo no pacote: `sc.py abrir`, `entregar`, `revisar --parecer`, `decidir`. Status `portao` e `aceite` são jobs do Actions (`status.yml`), porque a sessão não publica status pelo `gh` (403).
- Decisões novas: Q161 (revezamento), Q162 (portão por área), Q163 (`sociedade/` no worktree), Q164 (teto de 30 linhas do ajuste do coordenador).

**Próxima ação:** Odival faz o merge do PR #1 e abre a **sessão 2, etapa `a1-parser`**.

## Para a próxima abertura

- **Não leia a proteção da `main`.** Ela está ativa (PR obrigatório; `ci`, `portao` e `aceite`; vale para administradores; sem force push nem exclusão). O 403 da integração é conhecido.
- **Abra a etapa por `sc.py abrir`**, não pelo `sc_rodada`.
- **Delegação em revezamento (Q161):** o Gandalf não aciona subagentes; ele escreve as subordens e o Círdan as despacha sem edição.
- **PR:** o `gh pr create` dá 403 (GraphQL); abra pelo conector do GitHub.
- **Testes dirigidos:** use `discover -s tests -p 'test_x.py'` (a forma `tests.test_x` falha).
- **Itens antecipados na a1 (C39):** B11a (`sociedade/` canônica no worktree e `--pasta-sociedade` no `conferir`), B11b (texto do `sc-revisao`), B11c (portão por área, com a B11), B11d (linha de conferência de `.github/` e `sociedade/pareceres/` no modelo de PR). Ressalvas da m0 já anotadas na B14 e na B15.
- **Merge:** o repositório só aceita merge commit, então o SHA do candidato chega intacto à `main`.
- **Vercel:** ligada por Odival, fora da nuvem. Produção só pelo ramo `producao`; build pulado enquanto não houver `package.json`; pré-visualização por PR protegida por login. A a1 pode criar `vercel.json` com cabeçalhos (CSP) e configuração de build; **não mexa em ramos nem em implantação**.

## Sequência

| Sessão | Etapa | Estado |
|---|---|---|
| 1 | m0-destravar (B01–B10) | aceita; aguarda merge |
| 2 | a1-parser (B11–B13, B11a–B11d); Odival testa os próprios extratos depois | a fazer |
| 3 | a2-conferencia-entrevista (B14–B17) | a fazer |
| 4 | a3-documentos-privacidade (B18–B20) | a fazer |
| 5 | a4-publicacao (B21–B23) | a fazer |
| 6 | final (F1–F5), com reserva de US$ 10; inclui `.claude/agents/` | a fazer |

## Pendências fora da nuvem

- Devolução da cópia do pacote ao repositório `sociedade-do-codigo` (C40).
- Instalação da 4.0.0 nas ferramentas (C53).
