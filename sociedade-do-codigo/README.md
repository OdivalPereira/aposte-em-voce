# Sociedade do Código

Versão 3.0.0 · 25/09/2026

Uma equipe de agentes de IA de fornecedores diferentes trabalhando no mesmo projeto, com um processo que se confere sozinho. Este pacote traz o método (quatro skills), os scripts que conferem cada passo e os adaptadores para Claude Code, Codex e Antigravity.

## Como funciona

Toda etapa passa por seis estações. Você entra em três delas; nas outras, cada passo deixa uma prova que um script consegue conferir.

```
 VOCÊ          ARQUITETO          EQUIPE                  SCRIPT              REVISOR               VOCÊ
 1 Pedido ──▶  2 Ordem     ──▶    3 Execução       ──▶    4 Conferência ──▶   5 Revisão      ──▶    6 Decisão
 uma frase     o que entregar,    fatias delegadas        feito ou não        outro fornecedor,     aceitar,
               o que ler,         por subagente;          feito, pelo Git     uma vez só,           publicar ou
               como conferir      portão por commit       e pelos logs        com protocolo         corrigir
               (você aprova)      e atestado              → estado.html       → parecer com hash
```

- **Você** pede, aprova a ordem e decide olhando o `estado.html`, sem ler documentos.
- **Arquiteto (Círdan)** planeja e escreve a ordem. Não revisa código.
- **Equipe (Gandalf e especialistas)** executa. O Gandalf divide e delega; cada fatia passa no portão.
- **Script** confere a ordem contra os commits, os atestados e os logs dos aplicativos.
- **Revisor (Barbárvore)** é sempre de fornecedor diferente de quem implementou, e nunca corrige.

## Papéis

| Papel | Nome | Faz |
|---|---|---|
| Arquiteto | Círdan | Planeja com você, escreve ordens, cuida do contexto |
| Revisor independente | Barbárvore | Revisa o candidato consolidado; não corrige |
| Coordenador | Gandalf | Divide, delega, integra, roda o portão |
| Especialistas | Aragorn, Elrond, Galadriel, Legolas | Coleta, dados, qualidade, interface |
| Executor em nuvem | Jules | Tarefas mecânicas delimitadas |

Quem ocupa cada papel (plataforma, modelo, esforço) fica no `sociedade/perfil.md` de cada projeto. Trocar é um comando (`sc_rodada.py papel trocar`), que confere as regras R1 a R4.

## Instalação

| Ferramenta | Comando |
|---|---|
| Claude Code | `/plugin marketplace add <dono>/<repo>` e `/plugin install sociedade-do-codigo@sociedade` |
| Codex | `codex plugin marketplace add <dono>/<repo>`, depois instale no navegador de plugins |
| Antigravity | `agy plugin install <clone>/plugins/sociedade-do-codigo` |
| Sem plugin | `python3 scripts/instalar.py --alvo claude,codex,antigravity,antigravity-cli` (simula; `--aplicar` executa) |
| Executor em nuvem | não lê plugin: use o bloco no `AGENTS.md` |

Detalhes em `docs/instalacao.md`.

## Adotar num projeto

```
python3 <skill>/scripts/sc_init.py --nome "Meu projeto" --missao "..." --aplicar
python3 <skill>/scripts/sc_sync_agents_md.py --projeto . --ponteiros --aplicar
```

O primeiro cria `sociedade/perfil.md`, `sociedade/registro.json` e o bloco no `AGENTS.md`. O segundo cria `CLAUDE.md` e `GEMINI.md` apontando para o `AGENTS.md`. Depois, preencha a tabela de papéis do perfil. `<skill>` é a pasta `plugins/sociedade-do-codigo/skills/sociedade-do-codigo`.

## Uma etapa, na prática

Uma etapa fecha só com quatro comandos do ciclo (`abrir`, `entregar`, `revisar`, `decidir`); `ordem`, `conferir`, `sessao` e `estado` completam as estações.

```
sc.py ordem --etapa soma                           # arquiteto: cria a ordem a partir do modelo
sc.py abrir --etapa soma --ordem sociedade/ordens/soma.md --base <commit>   # abre a etapa no registro
sc.py entregar --etapa soma --base <commit>        # equipe: portão sobre base..HEAD, atestado
sc.py conferir --ordem sociedade/ordens/soma.md --registrar
sc.py sessao claude --sessao <id>                  # delegações e conversa nova, pelo log
sc.py revisar --etapa soma --base <commit>         # cópia descartável para o revisor
sc.py revisar --etapa soma --parecer parecer.md --head <commit>   # registra o parecer (lint e commit conferidos)
sc.py decidir --etapa soma aceitar --por "Seu Nome"               # decisão, métricas e encerramento
sc.py estado                                       # sociedade/estado.md e estado.html
```

- O ID da etapa nova usa minúsculas, números e `-` (até 40 caracteres).
- `decidir` exige atestado aprovado e parecer válido do mesmo SHA; `--por` é obrigatório se `git config user.name` não existir (não há nome padrão). Com o modo emulação ligado no perfil, o aceite sai marcado "aceite em emulação", com independência "não".
- Commit de produto depois do SHA revisado derruba o parecer. Commits só de `sociedade/` não.
- `decidir` não publica status: `portao` e `aceite` são jobs do GitHub Actions no PR. O comando mostra o commit de `sociedade/` e o push que faltam.

## O que há no repositório

```
pacote.json, VERSION           nome, descrição e versão (fonte única)
plugins/sociedade-do-codigo/   o plugin: quatro skills e os manifestos gerados
adapters/                      instalação e agentes por ferramenta
modulos/executores-locais/     módulo opcional (máquina local)
scripts/                       gen_manifests.py, instalar.py, validar_pacote.py
docs/                          instalação, decisões de desenho, recursos experimentais
tests/                         testes de comportamento (biblioteca padrão)
```

Recursos experimentais, fora do caminho de leitura dos agentes: `docs/experimentais.md`.

## Verificação

- Testes: `python3 -B -m unittest discover -s tests`.
- Validador: `python3 scripts/validar_pacote.py`. Confere formato das skills, manifestos, segredos, termos proibidos e, desde a 3.0.0, a estrutura que antes era testada por frases: tamanho de cada papel e de cada skill, carga de leitura do coordenador (até 12 KB), caminhos absolutos, links e termos de regras revogadas.
- CI: `.github/workflows/testes.yml` na raiz do repositório roda os dois em todo push de `main` e dos ramos de etapa.

Não verificado pelo pacote: se um agente real segue o método. Isso é conferido a cada etapa, pelo log do aplicativo (`sc.py sessao`).

## Manutenção

```
python3 scripts/gen_manifests.py --escrever   # regenera manifestos
python3 scripts/validar_pacote.py             # valida tudo
python3 -B -m unittest discover -s tests      # testes
```

Versão nova: ajuste `VERSION` e o `metadata.versao` das quatro skills, registre no `CHANGELOG.md`, regenere e valide.

## Limites deliberados

- Sem servidor e sem MCP. O painel é um HTML gerado (`sc.py estado`).
- Nenhum agente estima consumo. Medir pelo log é permitido: `sc.py sessao claude` soma, por agente e modelo, as contagens do log, e o `decidir` as grava.
- O pacote não altera credenciais, MCP, modelos nem permissões, e não grava segredos.
- Licença: `UNLICENSED` até você escolher outra em `pacote.json`.
