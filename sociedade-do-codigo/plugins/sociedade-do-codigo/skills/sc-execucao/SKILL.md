---
name: sc-execucao
description: Como o coordenador executa uma etapa: fatias delegadas a especialistas por subagente, tarefas mecânicas do Jules, subordem autocontida, disjunção e portão por fatia. Use ao dividir etapa, delegar fatia ou receber resultado.
metadata:
  versao: "3.1.0"
---
# Execução de uma etapa

Vale para o coordenador e os especialistas.

## 1. Fatias e subordens

- Fatia é o menor pedaço que se prova sozinho. Revisar e integrar não são fatias.
- O coordenador abre conversa nova no worktree da etapa, acionado por `sc.py passar` (Q175).
- Se a etapa mudar o perfil (ocupante ou emulação), crie o worktree antes da ordem.
- Cada fatia vai a um especialista por `invoke_subagent`, com subordem autocontida:
  - objetivo e critério de aceite da fatia;
  - "leia só": até 5 caminhos, com linhas em arquivo grande;
  - "escreva só": arquivos da fatia, sem sobreposição;
  - comando de teste dirigido com saída curta (`| tail`, `-q`);
  - estado e retorno em arquivo (2 KB no chat). Correção por agente novo (Q171).
- Antes de despachar, confira disjunção: `verificar_disjuncao.py` (skill `sociedade-do-codigo`).
- Delegação que falha é parada: registre e devolva. Não faça trabalho solo.

## 2. Portão por fatia e integração

- Durante a fatia, rode só testes dirigidos.
- Ao fechar a fatia: commit e `sc.py entregar --etapa <ID> --base <commit anterior>`.
- Fim da etapa: `sc.py entregar --etapa <ID> --base <base>` e atestado em `sociedade/pareceres/`.
- Fatia de alto impacto (Q10) recebe revisão interna da Galadriel por subagente (Q92).
- Integrar na branch principal é após a decisão, por merge commit com o "sim" do usuário (Q174).

## 3. Jules

- Só tarefas mecânicas: fixtures, testes de apoio, referências, renomeações (Q93, Q129).
- Nunca regra crítica, migração, autenticação, cobrança ou dado real.
- Especialista monta tarefa por `assets/tarefa-jules.md`, confere lote por `scripts/verificar_lote.py` e confere retorno. Teto de 3 tarefas, janela de 45 min (Q48). PR em rascunho, sem merge automático. Publicar é parada humana.

## 4. Máquina local

Arquivo grande e dado local ficam com executores locais (`modulos/executores-locais/`). Instalar biblioteca ou modelo é parada humana.

## 5. Retorno do coordenador

Até 2 KB no chat (Q170): veredito, entregas, commits, atestado, Jules e pendências. O detalhe vai para `sociedade/subordens/<ordem>-<fatia>-retorno.md`.

## Arquivos desta skill

- `references/limites-jules.md`: limites por plano.
- `assets/tarefa-jules.md`: modelo de tarefa autocontida.
- `scripts/verificar_lote.py`, `scripts/jules_cota.py`: conferência do lote e contagem de tarefas.
- `scripts/inventario_local.py`: inventário da máquina antes do módulo local.
