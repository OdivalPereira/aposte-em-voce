# Ordem <ID> — <entrega em uma frase>

Para: <papel> (<ferramenta>, <modelo>, esforço <x>) · CONVERSA NOVA
Etapa: <ID> · Base: <commit ou tag> · Worktree: <caminho> · Ramo: <ramo>
Especialistas: <nome por fatia> · Revisão interna: <fatias de alto impacto ou "nenhuma"> · Jules: <tarefas ou "nenhuma">

## Objetivo
<o que precisa existir no fim e como o usuário vai perceber>

## Leia só
1. `sociedade/planejamento.md`, seção da etapa corrente
2. `sociedade/perfil.md`
3. Decisões por ID, com busca em `sociedade/decisoes.md`: <IDs>
4. <outros caminhos, com intervalo quando grandes>

## Fatias
1. <nome> · especialista: <nome> · escreva só: <arquivos> · aceite: <critério observável>

## Paradas
- Teto da ordem: até 8 KB e uma única natureza (Q180).
- Teto de cerca de 1.500 linhas de produto por candidato (Q168).
- Mudança de escopo, de contrato ou instalação: volta ao arquiteto e ao usuário.

## Onde o Gandalf para
- No `entregar` final e paradas da ordem (Q177); não faz PR, cópias de revisão nem governança.
- Não edita lógica de produto (integração até 30 linhas sem lógica nova, Q164, Q181); teto de ~250 passos (Q180).

## Entregas verificáveis
Uma por linha: `ID | tipo | argumentos`. Tipos aceitos por `sc.py conferir`:
`commit_existe <ref>`, `arquivos_em <base>..<head> | <prefixo> [| <prefixo>...]`, `arquivo_existe <caminho>`,
`atestado_aprovado <arquivo> | <commit>`, `parecer_valido <arquivo>`, `hash_confere <arquivo> | <sha256>`,
`push_feito <ramo>`, `delegacoes antigravity | <id da conversa> | <mínimo>`, `conversa_nova antigravity | <id da conversa>`.

```entregas
E1 | commit_existe | <commit final>
E2 | arquivos_em | <base>..<commit final> | <prefixo permitido>
E3 | atestado_aprovado | sociedade/pareceres/atestado-<ID>.json | <commit final>
E4 | delegacoes | antigravity | <id da conversa> | <número de fatias>
E5 | conversa_nova | antigravity | <id da conversa>
E6 | push_feito | <ramo>
```

## Retorno
Até 2 KB no chat: veredito, lista de entregas preenchida, commits, atestado, tarefas do Jules com identificador e pendências. O detalhe vai para um arquivo de retorno em `sociedade/subordens/`.
