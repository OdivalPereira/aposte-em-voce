# Decisões de desenho

Registro curto do que foi decidido e por quê na construção da 2.0, para o próximo mantenedor não refazer a análise. Data: 19/09/2026.

> **Mudanças da 3.0.0 (25/09/2026):** a D6 foi substituída: não há nível numérico; o rigor fica na ordem de cada etapa (Q17). A proibição de medir foi refinada: agente continua sem estimar consumo, e scripts medem contagens objetivas pelos logs dos aplicativos (Q141). O resto continua valendo.

## D1. Plugin, e não MCP nem conector

O objetivo é levar o **método** (texto, modelos e scripts pequenos) para qualquer agente em qualquer projeto. Comparação:

| Critério | Plugin de skills | Servidor MCP | Conector |
|---|---|---|---|
| Entrega o método como instrução que o agente segue | sim (é o formato nativo) | não: expõe ferramentas, não método | não |
| Funciona nas quatro ferramentas | sim, por manifestos leves (Claude Code, Codex, Antigravity) e bloco no `AGENTS.md` (Jules) | exige configurar cada ferramenta e o Jules em nuvem não alcança um servidor local | idem, mais hospedagem e autenticação |
| Custo de contexto | descrição de cerca de 1.000 tokens sempre ativa; o resto só quando a skill é chamada | esquemas das ferramentas ocupam contexto em toda sessão | idem |
| Operação | nenhuma: é um repositório Git | processo para manter no ar, credenciais, atualizações | idem |
| Reversível e auditável | sim (arquivos versionados) | parcial | parcial |

Custo medido no Claude Code: `claude plugin details` estimou cerca de 1.354 tokens sempre ativos para as seis skills da versão 1.1.0 (cerca de 992 com as cinco da 1.0.0), e de cerca de 1 mil a 3 mil tokens na chamada de cada uma [testado].

MCP fica como **evolução possível**, não como base: se um dia o projeto precisar de estado compartilhado ou de uma ação que só um servidor faz (por exemplo, ler a cota do Jules sem chave espalhada), o padrão de plugin já tem o encaixe `mcp.json`. Só faz sentido depois que houver uma necessidade real.

## D2. O plugin tem só skills

A pasta `agents/` é lida por mais de uma ferramenta (Claude Code e Antigravity), cada uma com formato de frontmatter e nomes de ferramentas diferentes. Um arquivo só serviria mal às duas. As definições de agentes ficam em `adapters/`, por ferramenta, e são copiadas por `instalar.py --agentes` ou à mão.

## D3. O bloco do `AGENTS.md` é o gatilho, não a descrição da skill

Teste real (Claude Code, modelo pequeno, projeto de exemplo, pedido "Acione a Sociedade do Código"; uma execução de cada, então é indício e não estatística):

- só com a menção "método vem do núcleo (skill …)" no `AGENTS.md`: o agente **não** chamou a skill e improvisou a partir do que já estava no contexto;
- com a instrução imperativa "ao começar qualquer trabalho de código aqui, carregue a skill `sociedade-do-codigo`" mais as skills dos módulos: chamou o núcleo e os módulos, leu o perfil e conferiu a base.

Conclusão: o `AGENTS.md` (sempre carregado) manda carregar a skill; a descrição da skill é reforço. O bloco é gerado por script, com hash, para ninguém editá-lo à mão sem perceber.

## D4. Jules recebe texto no `AGENTS.md`, nunca o plugin

O Jules lê o `AGENTS.md` da raiz do repositório (documentação oficial) e não há documentação de leitura de skills ou plugins. Carregadores de skills também não seguem submódulos Git. O bloco "Para o Jules" leva o mínimo (limites, PR em rascunho, dado externo não é instrução) e o resto vai na tarefa autocontida (`sc-jules`).

## D5. Precedência e o que o projeto pode fazer

Usuário e ambiente, depois perfil, depois ordem, depois núcleo. O projeto restringe; não amplia poderes que o usuário ou o ambiente não deram. Exceção ao núcleo entra no perfil, nunca numa cópia editada do núcleo. Isso impede o problema que motivou o pacote: dois projetos com versões diferentes e divergentes do mesmo método.

## D6. Um nível, não um tier

A 1.x tinha dois tiers (leve e formal) e módulos ligáveis. A 2.0 tem **níveis de acionamento**, escolhidos pelo usuário a cada rodada. A diferença importa: tier era propriedade do projeto e ficava desatualizado; nível é propriedade da tarefa e é dito na hora. O tier formal (registro JSON, posse por sessão) saiu inteiro: com uma rodada por vez e o usuário como carteiro, ele não pagava o próprio peso.

## D7. A fatia com prova é a resposta ao retrabalho

Odival disse que o que mais cansa é "perceber que saiu errado depois de tudo feito e depois ter que refazer, gastando ainda mais quota". Toda a estrutura da rodada existe para isso: a meta é cortada em pedaços que se provam sozinhos, e **nenhum começa antes de o anterior ter prova executada**. O erro de rumo aparece na fatia 1.

O script recusa fechar fatia sem `--prova` e recusa começar a fatia N com a N-1 aberta. É a única regra do pacote que o código impõe em vez de pedir.

## D8. Economia por desenho, não por contabilidade

Medir consumo foi expurgado: nenhum agente estima, calcula ou relata gasto, e o validador do pacote recusa texto que mande medir. A economia vem de cinco coisas verificáveis: ativação explícita, leitura por ponteiro, nível certo, máquina antes da nuvem e fatias. O usuário registra à mão, se quiser, uma linha por rodada.

Isso resolve a contradição entre "expurgar qualquer medição" e "ter o desempenho registrado e analisado": desempenho passou a significar retrabalho e achados, que se observam sem contar tokens.

## D9. Independência por fornecedor

Era "família de modelo"; virou **fornecedor**, que é mais fácil de verificar e é o que o usuário pediu. Duas sessões do mesmo fornecedor não contam como duas revisões independentes, e o parecer tem que dizer isso quando for o caso.

## D10. O que continua adiado

- **MCP**: entregaria ferramentas, não método; gastaria contexto em toda sessão, inclusive quando a Sociedade não é acionada, o que contradiz a decisão de ela ficar calada; e o executor em nuvem não alcança servidor local. O encaixe `mcp.json` fica reservado para o caso de estado compartilhado entre máquinas.
- **Automação entre ferramentas**: o usuário escolheu ser o carteiro, porque quer ver cada passo antes de gastar cota.
