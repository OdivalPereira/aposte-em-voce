## Parecer do Revisor Independente
- etapa: <ID>
- entrega: <commit congelado ou PR>
- commit: <SHA do commit revisado, 7 a 40 hexadecimais, igual ao head de base..head>
- base..head: <sha7>..<sha7>
- revisor: <papel e ferramenta> · fornecedor: <fornecedor> · sessão: <id>
- modelo: <modelo configurado> · esforço: <esforço configurado|não exposto>
- independência: <Nível A (fornecedor diferente), Nível B (sessão distinta) ou Nível C (mesmo fornecedor)>
- veredito: <aceitar, aceitar com ressalvas ou não aceitar>
- data: <dd/mm/aaaa hh:mm>

### Independência
Não implementei nem corrigi nada desta entrega. Implementação feita pelo fornecedor <fornecedor>; minha revisão é de fornecedor <diferente|igual: revisão interna>.

### Mapa da entrega
- Motivo da etapa: <defeito ou necessidade, com referência do plano>
- Superfícies de entrada: <comandos, opções, funções públicas>
- Estados e transições: <quais e quem muda>

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| <critério> | <comando executado e resultado, ou arquivo e trecho lido> | <executada, lida ou não verificada> |

### Matriz de cobertura
| Critério | L1 motivo | L2 ponta a ponta | L3 estados | L4 escape | L5 entradas | L6 concorrência | L7 fontes | L8 retorno |
|---|---|---|---|---|---|---|---|---|
| <critério> | <sonda, "lida" ou "n/a (motivo)"> | | | | | | | |

### Achados
*Um por linha, com severidade (bloqueador, relevante ou opcional) e lente. Escreva "nenhum" se não houver.*
- [<severidade>] <lente> · <descrição> (<arquivo:linha>)

### O que não verifiquei
*Sempre preencha.*
- <item>
