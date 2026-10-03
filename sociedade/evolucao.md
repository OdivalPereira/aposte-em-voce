# Evolução — uma linha por etapa (Q51, Q98, Q153)

**Origem dos números:** registro e medição de sessão (`sc.py sessao claude`). O `decidir` grava a linha (backlog B10).

**Metas da Q153 (C35):**
- até 12 comandos do método por etapa;
- 0 edições manuais em arquivos de controle;
- até 5 intervenções de Odival e até 30 min dele.

| Etapa | Versão do método | Revisões até o aceite | Bloqueadores achados | Escaparam ao aceite | Trocas de papel | Eventos de cota | Comandos | Erros | Edições manuais | Intervenções | Minutos de Odival | Consumo (cache lido) | Dentro da meta? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| m0-destravar | 3.0.0 | 1 | 0 | n/d | 0 | 0 | 62 | 0 | 1 | 3 | n/d | n/d | não |
| a1-parser | 3.0.0 | 1 | 0 | 1 | 0 | 0 | 27 | 0 | 0 | 3 | n/d | n/d | não |
| fechamento-nuvem | 3.0.0 | 1 | 0 | n/d | 0 | 0 | 53 | 0 | 0 | 3 | n/d | 42367486 | não |

## Escaparam ao aceite
- **a1-parser (03/10/2026, Odival):** visual das telas T08, T09 e T99 reprovado ("parece site antigo"). Nenhuma estação olhou a tela. Causas: a especificação não tem direção visual; a ordem deu as telas ao Elrond, não ao Legolas; nenhuma estação olha a tela. As telas não serão mexidas agora; a regra nova é a Q169 (P5).

## Consumo por sessão (medido pelo log, Q170)
| Sessão | Etapa | Entrada | Cache escrito | Cache lido | Saída |
|---|---|---|---|---|---|
| 1 | m0-destravar | n/d | n/d | n/d | n/d |
| 2 | a1-parser | 3.445 | 2.268.543 | 65.815.150 | 79.155 |
| 3 | fechamento-nuvem (até a decisão) | 755 | 1.779.551 | 43.099.061 | 44.825 |

A sessão 1 rodou noutro contêiner (log ausente). Sessões 2 e 3 dividem o log; separadas por `--desde 2026-10-03T19:55:00Z`.
