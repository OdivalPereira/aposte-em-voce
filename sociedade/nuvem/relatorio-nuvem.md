# Relatório das sessões em nuvem — Sociedade do Código (emulação), 03/10/2026

Três sessões no Claude Code em nuvem, com um único fornecedor ocupando todos os papéis (Q147): m0-destravar, a1-parser e fechamento-nuvem. Todas fecharam pelo ciclo documentado, com prova dupla (portão e CI no mesmo SHA), parecer ligado ao commit e decisão de Odival registrada por script.

## O que foi testado
- **Ciclo do método:** `ordem`, `abrir`, `entregar` (portão por área, amarrado ao perfil), `conferir`, `sessao`, `revisar --parecer` e `decidir`. Status `portao` e `aceite` no Actions.
- **Delegação conferida pelo log:** 8 delegações na a1 e 17 na fechamento-nuvem. Revezamento Círdan–Gandalf (Q161).
- **Simulações:**
  - B12, "3 tentativas": o executor parou e devolveu.
  - B13, Jules emulado: o portão do Jules reprovou 3 vezes, com motivo.
  - Hipótese do Nubank: sustentou na 1ª tentativa, no layout sintético.
- **Revisão interna da Galadriel** nas fatias de alto impacto, e **revisão independente** (Barbárvore) completa na m0 e reduzida na a1 e na fechamento-nuvem.

## O que funcionou
- A revisão interna pegou o que o portão não pegaria. Na a1, o `decidir` aceitava atestado avulso; em todas as sessões, houve falhas que travavam a jornada.
- A Q12 funcionou duas vezes: no B12 e na parada da F3 do Jules.
- A `sociedade/` canônica no worktree (Q166) acabou com a cópia manual de registro entre checkouts.
- Medir pelo log mostrou onde está o custo: na releitura. O Gandalf aberto do zero a cada rodada, lendo só o arquivo de estado, custou uma fração do especialista retomado por mensagem.

## O que falhou
- **Visual das telas reprovado.** Nenhuma estação olhava a tela, e as telas foram para o especialista errado (Q169).
- **Jules (Haiku) não conseguiu gerar PDFs com estrutura imitada.** Na 1ª tarefa, o esperado foi tirado do código sob teste (circular). Na 2ª, gerou só parte dos PDFs. Na 3ª, os PDFs vieram mal desenhados (Q167).
- **Listas de escrita das ordens** incompletas em todas as etapas, sempre ampliadas na execução (Q172).
- **Aceite ainda forjável por quem reescreve o atestado e o hash (B15r).** A B15 detecta adulteração, mas não a impede.
- **Metas de comandos (12 por etapa) estouradas em todas as etapas:** 62, 27 e 53. O revezamento multiplica os comandos do Círdan.

## O que mudou no método (Q161–Q173)
- Revezamento no Claude Code (Q161).
- Portão por área, amarrado ao perfil, sem `--comando-teste` (Q162, B11).
- `sociedade/` do worktree como canônica (Q163, Q166).
- Teto do ajuste do coordenador (Q164).
- Fatias em paralelo sem commit do especialista (Q165).
- Dados de teste a partir de layout de referência (Q167).
- Linhas por script (Q168).
- Referência visual, Legolas e capturas em 360 px (Q169).
- Economia de contexto e medição pelo log (Q170).
- Correção por agente novo (Q171).
- `grep` dos usos antes da aprovação (Q172).
- Especialista pelo tipo da fatia (Q173).

**Próximo passo:** continuar na máquina local com a formação real (`sociedade/andamento.md`).
