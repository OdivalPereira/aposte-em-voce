# Adaptador do Claude Code

Experimental, não homologado (Q65)

Arquivos-modelo. Nada aqui é aplicado sozinho: você (ou o script `instalar.py`) copia para o projeto ou para a sua pasta pessoal.

| Arquivo | Vai para | Para quê |
|---|---|---|
| `CLAUDE.md.modelo` | `CLAUDE.md` na raiz do projeto | Importa o `AGENTS.md` (única fonte de regras); o papel vem do perfil |
| `settings.json.modelo` | `.claude/settings.json` do projeto (mescle com o que já existir) | Registra o marketplace, habilita o plugin para quem confiar na pasta e nega push, merge e leitura de `.env` |
| `agents/barbarvore.md` | `.claude/agents/` do projeto ou `~/.claude/agents/` | Subagente somente leitura para a revisão independente |

Antes de usar `settings.json.modelo`: troque `OdivalPereira/sociedade-do-codigo` pelo endereço real do repositório do pacote. As regras `extraKnownMarketplaces` e `enabledPlugins` só valem depois que cada pessoa confia na pasta do projeto; as regras `deny` valem de imediato.

Se o projeto já tem `.claude/settings.json`, mescle as chaves à mão. Este pacote não sobrescreve configurações existentes.
