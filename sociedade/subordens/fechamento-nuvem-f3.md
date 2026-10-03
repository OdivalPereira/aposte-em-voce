# Subordem fechamento-nuvem · F3 (integridade do aceite, pacote)

**Estado: fechada, pronta para despachar** (rodada 2). F1 comitada em `793012a`, F2 em `e4dbadd`, ambas com portão aprovado. Contas do teto (Q168, linhas adicionadas, `git diff --numstat`): F1 193 em `S/` + 13 em `validar_pacote.py`; F2 486 em `src/`; soma 692 de 1.500, sobram cerca de 800. Estimativa desta fatia: cerca de 450. Cabe. Informe o `numstat` real no retorno; se a fatia passar de 800, pare e devolva.

Para: Elrond, **instância nova** (subagente `elrond`; não é a que fez a F2) · fatia 3 · **alto impacto**
De: Gandalf · Etapa fechamento-nuvem · Base da fatia: `e4dbadd` (F2; cabeça do ramo) · Worktree: `/root/.sociedade/trabalho/aposte-em-voce/fechamento-nuvem`
Só dados sintéticos. Nunca estime nem relate consumo. `S` = `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts`; `T` = `sociedade-do-codigo/tests`.

## Objetivo
Aceite não forjável: a conferência e o `decidir` só aceitam o que um script oficial gerou e o que um humano decidiu.

## Aceite (copiado da ordem e do backlog; copie o texto da B15 e da B17b integralmente na versão final)
- Os itens da **B15** e da **B17b** do backlog (`sociedade/nuvem/backlog.md`, só essas duas linhas):
  - B15: `decidir` exige atestado oficial do SHA, parecer do mesmo SHA e os checks; saem do legado `--exit-code`, `--veredito` sem arquivo e `--implementador` declarativo; `sc_rodada encerrar` exige o evento `decisao`; a conferência verifica o hash dos atestados e recusa atestado escrito à mão; (a) `--implementador Nome:Fornecedor` não sobrepõe o fornecedor do perfil e o fornecedor declarado pelo revisor é conferido (R-1); (b) `aceite` confere o hash do atestado e recusa atestado alterado na cauda (R-3); (c) `aceite` fica vermelho se o PR alterar `.github/workflows/` sem que a ordem o liste no escreva-só (R-3); (d) `decidir` recusa como decisor todos os nomes de papel e de modelo do perfil, não só "Claude" (R-3).
  - B17b: `atestado_aprovado` do `sc_conferir` aplica `forma_do_atestado` (recusa atestado avulso e `--area` parcial); `sc.py revisar` sem `--parecer` usa o worktree da etapa e leva ordem, atestado e perfil à cópia.
- As sondas DG-02 que estão em `expectedFailure` por causa da B15 (classe `SondaDG02RestoB15` em `T/adversarial/test_dg02_aceite_forjavel.py`, 8 testes) passam a verdes e **o decorador sai**; a sonda do achado E3 também (`conferir` recusa atestado avulso e atestado de `--area` parcial). As sondas `expectedFailure` de `T/adversarial/test_dg03_commit_amarrado.py` **não** são desta fatia.
- Se não couber, para e devolve o que passou no portão.

## Leia só (por trecho)
1. Backlog: só as linhas B15 e B17b.
2. `T/adversarial/test_dg02_aceite_forjavel.py` (classe `SondaDG02RestoB15`) e a sonda do E3 (`grep -rn 'E3\|forma_do_atestado' T/adversarial`).
3. `S/sc_status.py` (`forma_do_atestado`, ~linha 73 e 154), `S/sc_conferir.py` (`atestado_aprovado`) e `S/sc_ciclo.py` (`provas_do_aceite`, `decidir`, linhas ~190 a 250; o trecho de métricas é da F1, não mexa).
4. `S/sc_rodada.py` (`encerrar`, `evidencia`, `parecer`; só os trechos com `--exit-code`, `--veredito`, `--implementador`) e `S/sc.py` (só `cmd_revisar`).
5. `S/sc_registro.py`: só os pontos que o aceite exigir.

## Escreva só (lista da ordem + ampliação conferida por `grep`, a confirmar pelo Círdan)
Da ordem: `S/sc_ciclo.py` (exceto o trecho de métricas da F1), `S/sc_conferir.py`, `S/sc_status.py`, `S/sc_registro.py`, `S/sc_rodada.py`, `S/sc.py` (só `revisar`), `T/test_aceite_nao_forjavel.py` (novo), `T/adversarial/`.
**Lacuna achada por `grep` (atrito):** os argumentos legados que saem têm usos reais fora dessa lista: `grep -rc -e '--exit-code' -e '--veredito' -e '--implementador'` dá `T/test_rodada.py` (8), `T/test_ciclo.py` (1), `T/test_pacote2_desacoplamento_eficiencia.py` (2), `T/test_sc_rodada.py` (2), além de `S/sc_rodada.py` (3), `S/sc.py` (1) e `T/adversarial/test_dg02_aceite_forjavel.py` (14). Remover o argumento sem ajustar esses quatro testes quebra a suíte do pacote. Proposta: incluir `T/test_rodada.py`, `T/test_ciclo.py`, `T/test_pacote2_desacoplamento_eficiencia.py` e `T/test_sc_rodada.py` no escreva-só, **só para trocar a chamada do argumento legado pelo caminho oficial (arquivo de parecer, atestado do `entregar`)**, sem enfraquecer asserção. **Incluídos no escreva-só** (ampliação conferida por `grep`; o Círdan confirma ao despachar).
Proibido: `sociedade/`, `docs/`, `.claude/`, `src/`, `tests/` da raiz, os textos do pacote (F1) e `.github/` salvo decisão do Círdan para o item (c) (o item c pode exigir um passo no `aceite.yml`; se for o caso, pare e devolva a pergunta).

## Teste dirigido (saída curta)
Da pasta `sociedade-do-codigo`:
- `python3 -B -m unittest tests.test_aceite_nao_forjavel tests.adversarial.test_dg02_aceite_forjavel 2>&1 | tail -15`
- no fim, a suíte inteira: `python3 -B -m unittest discover -s tests 2>&1 | tail -8` e `python3 scripts/validar_pacote.py 2>&1 | tail -8`.
Cada item da B15 e da B17b tem um teste novo que falha no código atual (mostre a falha antes) e passa depois.

## Portão da fatia (rodado pelo Gandalf)
`python3 sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc.py entregar --etapa fechamento-nuvem --base e4dbadd --fatia 3 --pasta-projeto /root/.sociedade/trabalho/aposte-em-voce/fechamento-nuvem --pasta-sociedade /root/.sociedade/trabalho/aposte-em-voce/fechamento-nuvem/sociedade 2>&1 | tail -20`

## Economia e retorno
Mesmas regras da F1: leitura só do listado e por trecho; saída curta; conversa curta com estado em `sociedade/subordens/fechamento-nuvem-f3-estado.md`; sem `git commit/add/stash/checkout`; até 3 hipóteses por bloqueio (Q12); mudança de escopo ou de contrato volta ao Gandalf. Teto da etapa de 1.500 linhas de produto: informe `git diff --numstat -- S/`.
**Retorno até 2 KB no chat**; detalhe em `sociedade/subordens/fechamento-nuvem-f3-retorno.md`.
