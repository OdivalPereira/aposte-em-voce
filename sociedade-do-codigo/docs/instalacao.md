# Instalação

Instalar mexe na configuração das suas ferramentas. Por isso este pacote **não instala nada sozinho**: você roda os comandos abaixo. Legenda: **[doc]** conferido na documentação oficial, **[testado]** executado no ambiente de construção, **[conf]** confirme com `--help` antes.

## 0. Pré-requisito: um repositório para o pacote

1. Crie no GitHub um repositório (privado serve), por exemplo `OdivalPereira/sociedade-do-codigo`, e suba o conteúdo desta pasta.
2. Se o nome for outro, ajuste `repository` em `pacote.json` e `repo` em `adapters/claude/settings.json.modelo`, e rode `python3 scripts/gen_manifests.py --escrever`.
3. Repositório privado: Claude Code e Codex usam as credenciais do Git da máquina [conf]. Se preferir não usar marketplace, clone o repositório e instale por caminho local.

## 1. Claude Code

```
/plugin marketplace add OdivalPereira/sociedade-do-codigo
/plugin install sociedade-do-codigo@sociedade
```

Na linha de comando: `claude plugin marketplace add <dono>/<repo>` e `claude plugin install sociedade-do-codigo@sociedade` [doc] [testado com marketplace local]. Para conferir: `claude plugin list` e `claude plugin details sociedade-do-codigo` (deve listar 4 skills).

As skills aparecem com o prefixo do plugin (`sociedade-do-codigo:sc-execucao` etc.).

**Por projeto** (para toda a equipe habilitar ao confiar na pasta): mescle `adapters/claude/settings.json.modelo` em `.claude/settings.json` e copie `adapters/claude/CLAUDE.md.modelo` para `CLAUDE.md` [doc]. As regras `extraKnownMarketplaces` e `enabledPlugins` só valem depois que cada pessoa confia na pasta; as regras `deny` (push, merge de PR, leitura de `.env`) valem de imediato.

**Revisor independente (Barbárvore):** copie `adapters/claude/agents/barbarvore.md` para `.claude/agents/` (projeto) ou `~/.claude/agents/` (pessoal) [doc]. Só vale como revisão independente se o Claude não for fornecedor de nenhum implementador da etapa.

## 2. Codex

```
codex plugin marketplace add OdivalPereira/sociedade-do-codigo
```

Depois abra o navegador de plugins do Codex, escolha o marketplace "sociedade" e instale "sociedade-do-codigo" [doc]. A sintaxe de instalação direta por linha de comando não está na documentação: confirme com `codex plugin --help` [conf]. Com clone local: `codex plugin marketplace add ./caminho-do-clone` [doc].

O Codex lê o `AGENTS.md` do projeto **até 32 KiB por padrão** (`project_doc_max_bytes`); acima disso, corta [doc]. Em `AGENTS.md` longo, grave o bloco de adoção com `--posicao inicio`, para ele não ser cortado.

Sem plugin: `python3 scripts/instalar.py --alvo codex` (copia para `~/.agents/skills`).

## 3. Antigravity (2.0, IDE e CLI `agy`)

```
agy plugin install <caminho-do-clone>/plugins/sociedade-do-codigo
```

[doc] para o comando; confirme a sintaxe com `agy plugin --help` [conf]. O plugin fica em `~/.gemini/config/plugins/` e vale para as três variantes; por projeto, em `.agents/plugins/` [doc]. O formato de plugin do Antigravity é um superconjunto do padrão Agent Plugins, e o `plugin.json` deste pacote segue esse padrão [doc].

Se o comando recusar o manifesto, use o instalador de reserva, que copia as skills para as pastas de skills. **Elas são diferentes** entre as variantes: `~/.gemini/config/skills` (2.0 e IDE) e `~/.gemini/antigravity-cli/skills` (CLI):

```
python3 scripts/instalar.py --alvo antigravity,antigravity-cli --agentes           # simula
python3 scripts/instalar.py --alvo antigravity,antigravity-cli --agentes --aplicar # executa
```

`--agentes` copia os agentes de `adapters/antigravity/agents/` para `~/.gemini/config/agents/` (só para o Antigravity 2.0 e IDE; a CLI não tem pasta de agentes neste pacote). Os nomes de ferramenta nesses arquivos (`view_file`, `grep_search`, `run_command`, `replace_file_content`) vêm do projeto piloto: ajuste se a sua versão usar outros [conf].

## 4. Jules

Não lê plugins nem skills. Grave o bloco de adoção no `AGENTS.md` da raiz, com o módulo `jules`:

```
python3 <pacote>/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_sync_agents_md.py \
  --projeto . --perfil sociedade/perfil.md
```

Veja `adapters/jules/LEIA-ME.md`.

## 5. Instalador de reserva (`scripts/instalar.py`)

- **Simula por padrão.** Sem `--aplicar` não altera nada.
- Só escreve em `.claude/skills`, `.claude/agents`, `.agents/skills`, `.gemini/config/skills`, `.gemini/config/agents`, `.gemini/antigravity-cli/skills` e `.sociedade-do-codigo/` dentro da sua pasta pessoal. Não toca em MCP, credenciais nem arquivos de configuração das ferramentas.
- Não sobrescreve o que você alterou (nem o que já existia sem ter sido instalado por ele) sem `--substituir`, e sempre guarda antes uma cópia em `~/.sociedade-do-codigo/backup/<data-hora>/`.
- Recusa caminhos que passem por link simbólico (por exemplo, `~/.claude` gerenciado por um gerenciador de dotfiles). Nesse caso use o plugin.
- Desfazer: `python3 scripts/instalar.py --alvo <alvos> --agentes --remover --aplicar` remove só o que ele instalou e não foi alterado.

## 6. Conferir depois de instalar

1. Numa pasta de teste com um `AGENTS.md` que tenha o bloco, faça primeiro uma **pergunta comum** ("o que faz este projeto?"). O esperado é resposta direta, **sem carregar skill e sem escrever arquivo**.
2. Depois diga: "Acione a Sociedade do Código. Meta: trocar o texto do rodapé." O esperado é carregar a skill, perguntar o que falta e **não** editar nada antes de existir uma ordem aprovada.
3. Se ele não carregar a skill na segunda pergunta, a instalação não está visível para aquela ferramenta, ou o gatilho condicionado à frase não pegou: confira a pasta ou o plugin, e me avise, porque o gatilho é o ponto não verificado desta versão.

Executores locais (módulo opcional, `modulos/executores-locais/`): antes da primeira execução, rode o inventário na máquina onde os executores vão rodar. Ele só lê:

```
python3 <pacote>/plugins/sociedade-do-codigo/skills/sc-execucao/scripts/inventario_local.py
python3 <pacote>/plugins/sociedade-do-codigo/skills/sc-execucao/scripts/inventario_local.py --exigir servidor,modelo:qwen,py:duckdb --caminho modules/parsers
```

Ele mostra processador, memória, Ollama (binário, servidor e modelos), bibliotecas Python por papel, navegadores do Playwright e os caminhos pedidos, e sai com código 1 se uma exigência falhar. As bibliotecas são vistas pelo Python que roda o script: use o Python do ambiente virtual do projeto, se houver. Instalar biblioteca ou baixar modelo continua sendo decisão sua.

## 7. Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| A ferramenta usa uma versão antiga do núcleo | Skill de mesmo nome já instalada no projeto ou na pasta global (por exemplo uma cópia do núcleo anterior), que pode ter precedência sobre a do plugin | Remova ou renomeie a cópia antiga (veja `docs/migracao-*.md`) |
| O agente não carrega a skill quando você aciona | O `AGENTS.md` não tem o bloco, está além do limite lido pela ferramenta, ou a frase de ativação saiu diferente | Rode `sc_sync_agents_md.py` (com `--posicao inicio` em arquivo longo) |
| `instalar.py` acusa CONFLITO | Você alterou a cópia instalada, ou havia uma skill de mesmo nome | Compare, e use `--substituir` só se quiser trocar (há backup) |
| O agente aciona a Sociedade sozinho, sem você pedir | O bloco foi editado à mão, ou a ferramenta ignora a condição | Rode `sc_sync_agents_md.py --verificar` e me avise |
| `agy` ou `codex` recusa o manifesto | Sintaxe ou versão diferente da documentada | Use `instalar.py` e me avise para ajustar `gen_manifests.py` |
