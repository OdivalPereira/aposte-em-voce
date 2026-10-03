# Compatibilidade: onde cada ferramenta lê o quê

Situação em 19/09/2026. **[doc]** = conferido na documentação oficial da ferramenta; **[conf]** = confirmar com `--help` ou documentação antes de depender.

## Skills (formato Agent Skills: pasta com `SKILL.md`)

| Ferramenta | Projeto | Usuário (global) |
|---|---|---|
| Claude Code | `.claude/skills/` [doc] | `~/.claude/skills/` [doc] |
| Codex | `.agents/skills/` [doc] | `~/.agents/skills/` [doc] |
| Antigravity 2.0 e IDE | `.agents/skills/` [doc] | `~/.gemini/config/skills/` [doc] |
| Antigravity CLI (`agy`) | `.agents/skills/` [doc] | `~/.gemini/antigravity-cli/skills/` [doc] |
| Jules | não documentado; lê só o `AGENTS.md` da raiz [doc] | não se aplica |

Atenção: o Antigravity 2.0/IDE e a CLI `agy` usam pastas globais **diferentes**. Instalar só em `~/.gemini/config` não alcança a CLI.

## Plugins

| Ferramenta | Manifesto | Instalar a partir deste repositório |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` no plugin e `.claude-plugin/marketplace.json` na raiz do repositório [doc] | `/plugin marketplace add <dono>/<repo>` e depois `/plugin install sociedade-do-codigo@sociedade` [doc] |
| Codex | `.codex-plugin/plugin.json` no plugin (campos `name`, `version`, `description`; `skills` aponta para `./skills/`) e `.agents/plugins/marketplace.json` na raiz do repositório [doc] | `codex plugin marketplace add <dono>/<repo>` [doc]; depois instale "sociedade-do-codigo" no navegador de plugins do Codex [doc]. A sintaxe de instalação direta por linha de comando não está na documentação: confirme com `codex plugin --help` |
| Antigravity (2.0, IDE e CLI) | `plugin.json` na raiz do plugin; o formato dele é um superconjunto do padrão Agent Plugins, então o `plugin.json` portátil deste pacote vale [doc] | `agy plugin install <caminho-local>/plugins/sociedade-do-codigo` [doc]; confirme a sintaxe com `agy plugin --help`. Locais: global `~/.gemini/config/plugins/` (as três variantes) e do projeto `.agents/plugins/` [doc] |
| Jules | não há | bloco no `AGENTS.md` (script `sc_sync_agents_md.py`) |

Repositório privado: use clone local e instale por caminho (Antigravity, Codex) ou deixe o Git do usuário autenticado (Claude Code e Codex usam as credenciais do Git da máquina) [conf].

Este pacote mantém o plugin **só com skills** porque a pasta `agents/` é lida por mais de uma ferramenta, cada uma com formato diferente (Claude Code e Antigravity). Os agentes ficam em `adapters/`.

## Regras de entrada

Todas leem `AGENTS.md` (Claude Code lê `CLAUDE.md`, que pode importar o `AGENTS.md` com `@AGENTS.md` [conf]). Mantenha o `AGENTS.md` curto: o Jules o lê ao trabalhar em cada tarefa.

## Subagentes e agentes

Formatos diferentes por ferramenta e sem padrão comum; os modelos ficam em `adapters/` e são instalados por `scripts/instalar.py --agentes` ou copiados à mão.

- Claude Code: Markdown com frontmatter (`name`, `description`, `tools` separado por vírgulas ou lista YAML, `model`); vale em `.claude/agents/` do projeto e em `~/.claude/agents/` [doc].
- Antigravity: Markdown com frontmatter (`name`, `description`, `subagent: true`, `mainAgent: false`, `model: inherit`, `tools` com os nomes de ferramenta do Antigravity); em `~/.gemini/config/agents/` no formato usado pelo projeto piloto [conf: a documentação de plugins cita uma pasta `agents/` de "modelos de subagente"].
- Codex e Jules: sem definição de agente neste pacote.

## MCP

Este pacote não configura MCP. O padrão de plugin tem um encaixe `mcp.json` para o futuro; ver `docs/decisoes.md`.
