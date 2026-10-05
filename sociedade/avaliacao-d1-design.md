# Avaliação da d1-design (primeira etapa na formação real)

Feita pelo Círdan em 05/10/2026, a partir do registro, do parecer, dos retornos e dos logs (`sc.py sessao`). É a origem das decisões Q176–Q181.

## Resultado
Etapa **rejeitada** por Odival (EVT-000048), com o limite Q85 esgotado: houve uma correção e uma reconferência, e três bloqueadores persistiram (A01 `sc_conferir`, A02 `sc_registro`, A03 `sc_rodada`), além de uma regressão relevante (A06 nas permissões). O visual (F1, F2) ficou sem achado aberto: A04, foco visível, foi resolvido.

## O que funcionou
- A formação real rodou de ponta a ponta: Gandalf no Antigravity com 7 delegações, Barbárvore no Codex com independência nível A.
- Revisão forte: 6 achados com sondas reproduzíveis e reversão (Q86), inclusive um defeito de acessibilidade que o portão não pegava.
- O limite Q85 segurou: sem laço, e a decisão voltou a Odival.
- Portão com 956 testes nas duas áreas e CI verde em todos os SHAs.

## O que falhou, com a causa
| # | Falha | Causa | Decisão |
|---|---|---|---|
| 1 | Os bloqueadores ficaram todos nos scripts de integridade (F5), que foram junto com as telas, sem revisão interna e com revisão reduzida | Planejamento do Círdan | Q176 |
| 2 | O Gandalf fez estações do Círdan: rodou `passar` duas vezes em nome do Círdan (EVT-34 retrodatado para a hora do `abrir`), preparou as cópias do revisor e fez o commit de governança; não houve PR | A ordem não dizia onde o Gandalf para | Q177 |
| 3 | As cópias do revisor saíram com o perfil antigo (emulação ligada, revisor Anthropic) | Governança sem commit até a cauda, por plano do Círdan | Q178 |
| 4 | Amend e reset depois do push; commit `0fff4f8` descartado (push forçado) | Sem regra de ramo para o Antigravity | Q178 |
| 5 | Decisões "sem motivo informado"; aprovação visual sem registro; a reconferência sobrescreveu o primeiro parecer | O script aceita; não há regra | Q179 |
| 6 | O revisor não rodou o app: a cópia veio sem as dependências | `revisar` não prepara o ambiente | d1b (P2) |
| 7 | A correção criou uma regressão (A06) e não fechou A01–A03 | A correção não usou as sondas do revisor como aceite | Q181 |
| 8 | As 7 delegações foram conversas separadas, mas com `TypeName = self`: clones do Gandalf com o papel no texto. Os agentes instalados (`legolas`, `elrond`, `galadriel`) nunca foram usados, e a conferência contou as 7 como válidas | A ordem não dizia qual agente invocar; o `conferir` não olha o tipo | Q182 |

## Retrabalho e consumo (medidos pelo log)
| Medida | d1 | Meta a partir da d1b |
|---|---|---|
| Conversas do Gandalf | 1 conversa para execução, correção e decisão: 712 passos, 203 comandos, 19 rodadas de teste. A duração (36 h) não é medida: inclui a espera pelas respostas de Odival | Uma conversa por rodada, até ~250 passos (Q180) |
| Edições de lógica pelo Gandalf | 7 (`sc_conferir.py` 3, `sc_sessao.py` 4) e 47 `python -c` avulsos | 0; só integração até 30 linhas (Q181) |
| Releitura | `sc_conferir.py` lido 12 vezes pelo Gandalf | Lê só estado e retorno |
| Barbárvore | Revisão e reconferência na mesma sessão: 18,9 milhões de tokens de entrada para 141 mil de saída | Reconferência em sessão nova, só com achados e diff (Q180) |
| Tamanho da ordem | 16 KB, com 5 fatias de duas naturezas | Até 8 KB, uma natureza (Q180) |
| Consumo do Antigravity | n/d: o log local não expõe tokens | Passos e releituras como indicador |
