# Atritos com o método — sessões em nuvem

Formato: `| data | etapa | papel | comando ou passo | o que aconteceu | correção ou item do backlog |`.

Cada atrito é evidência para refinar a Sociedade (C06). Os do preparo foram observados ao instalar a 3.0.0 neste repositório em 03/10/2026.

| Data | Etapa | Papel | Comando ou passo | O que aconteceu | Correção ou item |
|---|---|---|---|---|---|
| 03/10/2026 | preparo | Claude (local) | `sc_init.py --nome "Aposte em Você"` | O identificador do projeto saiu `aposte-em-voc`: o acento truncou a palavra | Novo item: identificador com transliteração (junto do B08) |
| 03/10/2026 | preparo | Claude (local) | `sc_init.py` | O histórico registra "Adoção … v2.0.0" e o autor "Gandalf", com o pacote na 3.0.0 | B22 (DG-19) |
| 03/10/2026 | preparo | Claude (local) | `sc_init.py` | O registro grava `caminho_canonico` com caminho absoluto da máquina local, que na nuvem é outro (campo hoje só informativo) | Avaliar na B22 ou na B18 (portabilidade do registro) |
| 03/10/2026 | preparo | Claude (local) | `sc_init.py` | A tabela "Papel × ferramenta" sai toda "a definir"; foi preenchida à mão | Avaliar: `sc_init` aceitar a formação por parâmetro |
| 03/10/2026 | preparo | Claude (local) | `adapters/claude/settings.json.modelo` | O modelo nega `git push *`, o que impediria a sessão em nuvem de enviar o próprio ramo para o PR; foi reescrito para negar só a `main` | B05 e S5 (adaptadores) |
| 03/10/2026 | preparo | Claude (local) | `adapters/claude/agents/barbarvore.md` | Anunciado como "somente leitura", mas tem Bash (DG-31); os novos agentes declaram isso | S5 |
| 03/10/2026 | preparo | Claude (local) | Skills no Claude Code em nuvem | Plugins não carregam na nuvem; as skills foram ligadas em `.claude/skills/` por links simbólicos para a cópia do pacote | Conferir na sessão 1 se os links carregam; senão, ler o SKILL.md pelo caminho (CLAUDE.md) |
| 03/10/2026 | preparo (G0) | Claude (local) | `sc_rodada excecao --decisao-ref Q146` | Recusado: a referência exige hífen (`^[A-Za-z0-9]+-…`), e as decisões no formato Q não passam. Foi usado `DEC-Q146` | Novo item: aceitar o ID Q (junto da B15) |
| 03/10/2026 | preparo (G0) | Claude (local) | `sc_rodada encerrar --forcar` | Exigiu um `rodada.md` escrito à mão para uma etapa que o registro já tinha aberta (duas fontes de verdade; DG-01) | B01 (ciclo no `sc.py`) |
| 03/10/2026 | preparo (G0) | Claude (local) | `sc_rodada excecao --regra tarefas_pendentes` | O encerramento aceita a exceção `tarefas_pendentes`, mas o comando de exceção não reconhece a regra; foi usada `fatias_pendentes` | B01 e B15 (regras de exceção coerentes) |
| 03/10/2026 | preparo (G0) | Claude (local) | 3 × `sc_rodada excecao` no mesmo segundo | As três exceções saíram com o **mesmo ID** (`EXC-<timestamp em segundos>`) | B18 (registro: IDs únicos) |
| 03/10/2026 | preparo (G0) | Claude (local) | `sc.py estado` depois do encerramento | O painel mostra a ARR como "encerrada", sem dizer "sem aceite" nem exibir as exceções (DG-06) | B19 (painel honesto) |
| 03/10/2026 | preparo (G0) | Claude (local) | Encerramento | Foram 4 exceções e 1 encerramento forçado, mais 1 arquivo escrito à mão, para encerrar uma etapa sem aceite | B01 (`sc.py decidir --sem-aceite`) |
