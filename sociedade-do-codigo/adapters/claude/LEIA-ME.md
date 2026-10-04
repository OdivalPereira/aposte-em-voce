# Adaptador do Claude Code

Experimental, não homologado (Q65)

Arquivos-modelo. Nada aqui é aplicado sozinho: você (ou o script `instalar.py`) copia para o projeto ou para a sua pasta pessoal.

## Papel na formação real

Na formação real da Sociedade do Código, o Claude Code é a ferramenta do **Círdan (arquiteto)**:
- Planeja com o usuário e redige ordens verificáveis;
- Não implementa nem corrige produto, não executa suítes e não lê código do candidato em revisão;
- Não despacha subagentes locais para outros papéis (Gandalf e especialistas no Antigravity, Barbárvore no Codex).

(Caso um projeto utilize o Claude Code como revisor independente, há o subagente somente leitura `agents/barbarvore.md`.)

## Passagem entre ferramentas (Q175)

A cada passo a ser executado em outra ferramenta (Gandalf no Antigravity ou Barbárvore no Codex), o Círdan executa `sc.py passar --etapa <ID> --para gandalf|barbarvore`, apresenta ao usuário a pasta e a linha exatas a colar, e aguarda o retorno sem prosseguir sozinho.

## Integração (Q174)

Integrar é o merge do PR na branch principal, sempre como merge commit (`gh pr merge <n> --merge`), configurado como `ask`. O Círdan só executa a integração após o "sim" explícito do usuário na conversa. Merge direto, squash, rebase, auto e admin são proibidos (`deny`).

## Arquivos-modelo

| Arquivo | Vai para | Para quê |
|---|---|---|
| `CLAUDE.md.modelo` | `CLAUDE.md` na raiz do projeto | Instruções do Círdan na formação real; aponta para `AGENTS.md` |
| `settings.json.modelo` | `.claude/settings.json` do projeto | Registra marketplace, habilita plugin e define travas de merge (Q174) |
| `agents/barbarvore.md` | `.claude/agents/` ou `~/.claude/agents/` | Subagente somente leitura se o Claude for o revisor independente |

Antes de usar `settings.json.modelo`: troque `OdivalPereira/sociedade-do-codigo` pelo endereço real do repositório do pacote. As regras `extraKnownMarketplaces` e `enabledPlugins` só valem depois que cada pessoa confia na pasta do projeto; as regras `deny` e `ask` valem de imediato.

Se o projeto já tem `.claude/settings.json`, mescle as chaves à mão. Este pacote não sobrescreve configurações existentes.
