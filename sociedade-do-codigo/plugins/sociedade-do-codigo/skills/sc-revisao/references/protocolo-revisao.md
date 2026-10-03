# Protocolo de revisão independente

Origem: decisão Q126 da Sociedade. Vale para toda revisão de fechamento e para a calibração B2, com qualquer modelo no papel. O protocolo é **genérico**: descreve o método e não aponta defeitos de nenhuma entrega.

## Princípios

1. O retorno do implementador é uma alegação, não uma evidência. O revisor confirma por execução própria.
2. Distinga sempre o que foi **executado** do que foi apenas **lido**. Nunca cite comando não executado.
3. Profundidade vem antes de velocidade. O veredito só sai quando toda lente aplicável tiver pelo menos uma sonda executada ou uma justificativa de "não se aplica". Se o tempo ou a cota acabar, entregue um parecer **parcial**, declarado como tal, com as células pendentes.
4. Um controle que impede o uso legítimo é tão defeituoso quanto um controle que deixa passar o uso ilegítimo.
5. Não implemente nem corrija nada. Sondas e dados temporários ficam fora dos arquivos da entrega.

## Passo 0: mapa da entrega, antes de sondar

Leia o plano e os critérios da etapa e registre no parecer:

- **Motivo da etapa:** o defeito, incidente ou necessidade que originou a etapa, com a referência do plano.
- **Critérios de aceite:** a lista completa.
- **Superfícies de entrada:** comandos, subcomandos, opções e valores padrão, funções públicas, arquivos lidos e gravados.
- **Estados e transições:** os estados do domínio, quem pode mudar cada um e em que condição.
- **Fontes de verdade e derivados:** o que é gravado como fonte e o que é gerado a partir dela.

## Lentes obrigatórias

| Lente | O que fazer |
|---|---|
| L1 Motivo da etapa | Reproduza contra o candidato o cenário que originou a etapa e suas variações por **todos** os caminhos: interface, biblioteca e dados. Se o problema original ainda ocorre em qualquer caminho, é bloqueador. |
| L2 Ponta a ponta pela interface real | Execute pela interface pública (a CLI, por exemplo) o fluxo completo que um usuário faria, do início ao fim, pelo caminho legítimo. Confirme que é **possível** concluir e que o estado final é o esperado em todas as fontes. |
| L3 Estados e transições | Para cada estado, tente transições ilegais, repetição, reversão, reuso de identificadores, alterações de severidade ou classificação e saída de estados terminais. Procure tudo o que libera um bloqueio sem a condição exigida. |
| L4 Saídas de escape | Toda opção de forçar, pular, excepcionar, simular ou reprocessar, e todo valor padrão. Teste cada uma isolada, combinada e com argumentos ausentes, vazios ou com variações de texto. Confira se o que se declara obrigatório é de fato exigido. |
| L5 Entradas degradadas | Ausente, corrompido, vazio, formato legado, duplicado e divergente com a mesma identidade. Confira se a falha é explícita e se nada é promovido a válido sem verificação. |
| L6 Concorrência e falha | Duas operações simultâneas, interrupção no meio da gravação, validação feita fora da trava ou sobre estado antigo. |
| L7 Consistência entre fontes | Fonte de verdade contra derivados e documentos: ordem de gravação, falha parcial, repetição (idempotência), texto de autoria humana preservado e simulação sem nenhum efeito em disco. |
| L8 Retorno contra evidência | Para cada critério que o retorno declara atendido, localize o teste que o demonstraria e execute-o. Se o teste não exercita o comportamento declarado, registre um achado. Confira também os números declarados (testes novos, contagens, arquivos). |

## Saída obrigatória no parecer

0. Cabeçalho completo, com `commit:` (o SHA revisado, igual ao head de `base..head`). O parecer só vale para esse commit.
1. Mapa da entrega (passo 0).
2. **Matriz de cobertura:** uma linha por critério e uma coluna por lente. Cada célula traz o identificador da sonda executada, "lida" ou "n/a (motivo)". Nenhuma célula aplicável fica vazia.
3. Achados numerados. Cada um com severidade (bloqueador, relevante ou opcional), condição, efeito, critério afetado, lente, evidência reproduzível e correção esperada.
4. O que não foi verificado, e por quê.
5. Veredito: aceitar, aceitar com ressalvas ou não aceitar; ou "parcial" se o princípio 3 não foi cumprido.

## Conferência pelo arquiteto

O arquiteto não lê o parecer para julgar o código. Ele confere, por script (`sc.py conferir` e `sc.py sessao`), o log da sessão (modelo, esforço, pasta, sessão nova, leituras fora da pasta permitida), o SHA-256 do parecer e a presença das seções e da matriz.
