# Adaptador do Antigravity (2.0, IDE e CLI `agy`)

Experimental, não homologado (Q65). As regras de cada papel estão só na skill `sc-papeis`; este arquivo trata de instalação.

## Plugin (skills do núcleo)

`agy plugin install <caminho-do-pacote>/plugins/sociedade-do-codigo` (confirme a sintaxe com `agy plugin --help`). O plugin fica em `~/.gemini/config/plugins/` (as três variantes) ou, por projeto, em `.agents/plugins/`.

## Alternativa: só as skills

| Variante | Skills globais |
|---|---|
| Antigravity 2.0 e IDE | `~/.gemini/config/skills/` |
| CLI `agy` | `~/.gemini/antigravity-cli/skills/` |
| Qualquer uma, por projeto | `.agents/skills/` |

`scripts/instalar.py --alvo antigravity,antigravity-cli` copia para as duas pastas globais, com simulação prévia e cópia de segurança.

## Subagentes dos especialistas

`agents/` traz Aragorn, Elrond, Galadriel e Legolas no formato de subagente do Antigravity (`subagent: true`, `model: inherit`). Instale com `scripts/instalar.py --agentes --alvo antigravity`, que copia para `~/.gemini/config/agents/`. Cada agente só aponta para o arquivo do seu papel na skill `sc-papeis`.

- O coordenador (Gandalf) é o agente principal da conversa. Ele delega por `invoke_subagent`; a conferência confere pelo log (`sc.py sessao antigravity`).
- Não há revisor neste adaptador: revisão de outro modelo Google é revisão interna (Galadriel), nunca independente (D-RT-001).
- Executores locais: módulo opcional `modulos/executores-locais/`, com agentes próprios.

## Entrada

O Antigravity lê o `AGENTS.md` do projeto. `GEMINI.md`, se existir, só aponta para ele (Q62).

## Modelo

Execução com Gemini 3.8 Flash, esforço high; modelo Pro só depois de duas falhas na mesma tarefa (Q91). Os subagentes herdam o modelo da conversa. Modelos Claude ou gpt-oss dentro do Antigravity mudam o fornecedor do implementador (R3): só com decisão registrada.
