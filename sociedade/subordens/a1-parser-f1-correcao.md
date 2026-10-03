# Subordem a1-parser · F1c (correção da F1/B11, achados da revisão interna)

Para: Aragorn (Claude Code em nuvem, subagente `aragorn`) · correção dentro da própria fatia (ajuste 3 da aprovação)
De: Gandalf · Etapa a1-parser · Base da correção: `5959e28` (ramo `etapa/a1-parser`; F1 em `fce98d9`) · Worktree: `/root/.sociedade/trabalho/aposte-em-voce/a1-parser`
Prefixos: `S = sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`; `T = sociedade-do-codigo/tests`. Só dados sintéticos. Nunca estime nem relate consumo.

## Objetivo e aceite
Corrigir os achados 1 a 4 e os dois menores do 5, cada um com sonda que falha antes e passa depois (em `T/test_portao_amarrado.py`, `T/adversarial/` ou teste novo no mesmo escopo).
1. **BLOQUEIA, atestado avulso contorna o DG-09.** `S/sc_status.py:90-112` (`verificar_portao`) e `S/sc_ciclo.py:199-226` (`_atestado`, usado pelo `decidir aceitar`) aceitam qualquer atestado APROVADO. Reprodução: `sc_pre_devolucao.py --etapa a1 --base B --comando-teste true --saida-json .../atestado-a1.json` sem `--portao-por-area` dá APROVADO 1.2.0 sem `portao`; commitado, `verificar_portao` dá ok. Correção: os dois exigem a forma 1.3.0 completa: `portao.modo == 'por_area'`, `portao.commit == commit`, áreas não vazias e todas ok. Sonda: atestado avulso recusado no `decidir` e no status.
2. **CORRIGIR, `--area X` grava APROVADO sem as demais áreas tocadas** (`S/sc_pre_devolucao.py:530`; teste em `T/test_portao_amarrado.py:281`). Correção: o atestado grava `areas_tocadas` (todas as áreas que `base..HEAD` toca) e `cobertura_completa` (verdadeiro só se todas rodaram e passaram); o status e o `decidir` exigem `cobertura_completa`. `--area` continua útil para rodar uma área só, mas o atestado resultante não aceita decisão.
3. **CORRIGIR, renomeação esconde a origem.** `git diff --name-only -z -M` em `S/sc_pre_devolucao.py:145` e `S/sc_conferir.py:53`: `git mv pacote/x src_x` roda só `app`; `git mv sociedade/n docs/n` não acusa a violação do Q60. Correção: `--no-renames` nos dois. Sondas: os dois casos.
4. **CORRIGIR, o perfil vale do disco e nada o compara.** **Não** reprove no portão por diferença entre o perfil do disco e o HEAD: durante a etapa o perfil da `sociedade/` do worktree fica sem commit por desenho. Correção decidida (Círdan): o atestado já grava `perfil_sha256`; o `decidir` e o `sc_status.verificar_portao` exigem que ele seja igual ao SHA-256 do `sociedade/perfil.md` no commit ou árvore que estão julgando (no status do Actions, o head do PR, que terá o perfil no commit de governança). Sonda: perfil trocado no disco só para rodar o portão e restaurado depois: o `decidir` recusa. Se o `status.yml` precisar mudar de formato para ler o hash, a escrita em `.github/workflows/status.yml` está permitida.
5. **MENOR, só estes dois:** (a) `falhos > 0` com código 0 reprova; (b) arquivo com `assume-unchanged` ou `skip-worktree` conta como árvore suja (conferir por `git ls-files -v`). Os demais menores (killpg/SIGKILL no Windows; build e lint sem timeout e rodando com só uma área; arquivo ignorado presente entra no teste) **não** entram: backlog.

## Fora desta subordem (backlog/Barbárvore)
`npm test` do candidato pode imprimir contagem falsa (limite do método); governança commitada no meio da etapa entra em `base..HEAD`; `sc.py ordem` grava no checkout principal (intencional). Nota: "perfil canônico" (ordem) e "sociedade/ do worktree" (B11a) divergem no texto; não mude a definição, só cite no retorno se algo o obrigar.

## Leia só (até 5 caminhos)
1. `S/sc_status.py` (`verificar_portao`) e `S/sc_ciclo.py` (`_atestado`, `decidir`).
2. `S/sc_pre_devolucao.py` (portão por área, atestado 1.3.0, `obter_arquivos_candidato`).
3. `S/sc_conferir.py` (em torno da linha 53).
4. `T/test_portao_amarrado.py` e `T/adversarial/test_dg09_portao_amarrado.py`.
5. `T/adversarial/_cenario.py` e `.github/workflows/status.yml` (só se o formato do atestado mudar).

## Escreva só
`S/sc_status.py`, `S/sc_ciclo.py`, `S/sc_pre_devolucao.py`, `S/sc_conferir.py`, os testes deles (`T/test_portao_amarrado.py`, `T/test_sociedade_worktree.py`, `T/test_ciclo.py`, `T/test_status.py`, se precisar ajustar fixtures de atestado para o formato 1.3.0 sem enfraquecer), `T/adversarial/`, `.github/workflows/status.yml` (só se o atestado mudar de formato) e `sociedade-do-codigo/CHANGELOG.md` (uma linha por correção). Nada mais: não toque em `src/`, `package.json`, `sociedade/`, `docs/`, `.claude/` nem no app.

## Teste dirigido
Em `sociedade-do-codigo/`: `python3 -B -m unittest discover -s tests -p 'test_portao_amarrado.py' -v`, `python3 -B -m unittest discover -s tests/adversarial -t . -v` (ou o equivalente que funcionou na F1), a suíte `python3 -B -m unittest discover -s tests` e `python3 -B scripts/validar_pacote.py`. Nenhum teste apagado, pulado ou enfraquecido; atestados de fixture ajustados ao formato 1.3.0 são permitidos se a razão estiver no retorno.

## Regras de trabalho
Sem `git commit`, `add`, `stash` nem `checkout` (o Gandalf comita). Até 3 hipóteses diferentes por bloqueio, cada uma registrada; depois pare e devolva (Q12). Mudança de escopo ou de contrato do atestado além do pedido: pare e devolva.

## Portão da fatia (rodado pelo Gandalf, sem `--comando-teste`)
`python3 sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc.py entregar --etapa a1-parser --base 5959e28 --fatia 1c --pasta-projeto /root/.sociedade/trabalho/aposte-em-voce/a1-parser --pasta-sociedade /root/.sociedade/trabalho/aposte-em-voce/a1-parser/sociedade`

## Retorno (até 2 KB)
Arquivos alterados; o que mudou em cada achado (uma frase) e a sonda de cada um; contagem da suíte e do validador; linhas de produto novas; hipóteses tentadas; pendências e atritos com o método.
