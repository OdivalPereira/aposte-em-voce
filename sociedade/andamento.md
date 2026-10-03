# Andamento — Aposte em Você (sessões em nuvem da Sociedade)

Atualizado em 03/10/2026 pelo Círdan, no fim da sessão 2. Limite: 5 KB (Q99).

## Onde estamos

**Sessão 2 (`a1-parser`) aceita por Odival** em 03/10/2026, com `sc.py decidir` ("aceite em emulação", revisor não calibrado, revisão reduzida), **com ressalva de design**: o visual das telas foi reprovado e escapou ao aceite (`evolucao.md`).
- PR: OdivalPereira/aposte-em-voce#2, ramo `etapa/a1-parser`. Candidato `6f2c4fd` (base `d86e90c`); depois dele, só a cauda de `sociedade/`.
- Entregue: portão amarrado ao perfil por área (B11, B11a–B11d); projeto Vite/Preact, leitura no worker, T08, T09 e T99, e2e de rede, CSP. B12: acerto. B13: o portão do Jules reprovou 3 vezes com motivo; a F3 não entrou (vira B17a).
- Decisões novas: Q165 a Q169 (P1 a P5).
- Ramo `jules/a1-parser-pdfs` (`228d049`) enviado só como consulta para a a2, sem PR.

**Próxima ação:** Odival faz o merge do PR #2, testa os próprios extratos na pré-visualização pela T99 e relata por banco (leu, parcial ou falhou, C45). Esse relato abre a **sessão 3, `a2-conferencia-entrevista`**.

## Para a próxima abertura

- **Não leia a proteção da `main`** (ativa; `ci`, `portao` e `aceite`). Abra por `sc.py abrir`, **depois** de criar o worktree; durante a etapa a `sociedade/` canônica é a do worktree (Q166).
- **Delegação em revezamento (Q161)**; especialistas em paralelo não comitam (Q165).
- **Portão:** `sc.py entregar` sem `--comando-teste` (recusado); áreas `app` e `pacote` no perfil. Só o atestado final 1.3.0 com cobertura completa vale no `decidir`.
- **`sc.py revisar`:** passe `--head <candidato>`; copie a ordem para a cópia do revisor (B17b).
- **PR** pelo conector do GitHub. **Testes dirigidos do pacote:** `discover -s tests -p 'test_x.py'`.
- **Telas (Q169):** a a2 tem T03–T07 e T10; precisa de referência visual aprovada por Odival **antes** da ordem, fatias de tela do Legolas e capturas em 360 px no PR.
- **Itens da a2 vindos da a1:** B17a (PDFs sintéticos, Q167), B17b (resto do E3), B17c (menores) e as correções do teste de Odival.
- **Vercel:** pré-visualização por PR protegida por login; não mexa em ramos nem em implantação.

## Sequência

| Sessão | Etapa | Estado |
|---|---|---|
| 1 | m0-destravar (B01–B10) | aceita; integrada |
| 2 | a1-parser (B11–B13, B11a–B11d) | aceita; aguarda merge e o teste de Odival |
| 3 | a2-conferencia-entrevista (B14–B17) | a fazer |
| 4 | a3-documentos-privacidade (B18–B20) | a fazer |
| 5 | a4-publicacao (B21–B23) | a fazer |
| 6 | final (F1–F5), com reserva de US$ 10; inclui `.claude/agents/` | a fazer |

## Pendências fora da nuvem

- Devolução da cópia do pacote ao repositório `sociedade-do-codigo` (C40).
- Instalação da 4.0.0 nas ferramentas (C53).
