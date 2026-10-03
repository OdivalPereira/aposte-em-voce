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
