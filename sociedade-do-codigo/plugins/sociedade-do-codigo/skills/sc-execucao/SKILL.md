---
name: sc-execucao
description: Como o coordenador executa uma etapa: fatias delegadas a especialistas, tarefas do Jules, subordem autocontida, disjunção e portão por fatia. Use ao dividir etapa, delegar fatia ou receber resultado.
metadata:
  versao: "3.3.0"
---
# Execução de uma etapa

Vale para o coordenador e os especialistas.

## 1. Fatias e subordens

- Fatia se prova sozinha. Revisar e integrar não são fatias.
- Gandalf abre conversa nova no worktree (`sc.py passar`, Q175), teto ~250 passos/rodada (Q180). Ordem até 8 KB e uma natureza só.
- Se mudar perfil/regras, governança antes da ordem (Q178).
- Antigravity: delegação via TypeName do especialista, nunca self (Q182).
- Fatia vai a especialista por `invoke_subagent` com subordem autocontida:
  - objetivo e aceite;
  - "leia só": até 5 caminhos, com linhas em arquivo grande;
  - "escreva só": arquivos da fatia, sem sobreposição (`verificar_disjuncao.py`);
  - teste dirigido curto; retorno em arquivo (2 KB no chat). Correção por agente novo (Q171).
- Delegação que falha é parada. Não faça trabalho solo.
- Coordenador não edita lógica (Q181): só estado, subordens e integração até 30 linhas (Q164); depuração é do especialista.

## 2. Portão por fatia e integração

- Na fatia: testes dirigidos. Ao fechar: commit e `sc.py entregar --etapa <ID> --base <anterior>`.
- Fim da etapa: `sc.py entregar --etapa <ID> --base <base>` e atestado em `sociedade/pareceres/`.
- Alto impacto por definição (Q176): fatias de registro, conferência, aceite, portão ou permissões exigem protocolo completo e revisão interna (Galadriel).
- Onde Gandalf para (Q177): no entregar final e paradas da ordem; não faz PR nem governança (do Círdan). Sem amend, reset ou force push (Q178).
- Integrar é após decisão do usuário, por merge commit (`gh pr merge <n> --merge`, Q174).

## 3. Jules

- Só tarefas mecânicas (Q93, Q129). Nunca regra crítica, migração, credencial ou dado real.
- Especialista monta tarefa (`assets/tarefa-jules.md`), confere lote (`scripts/verificar_lote.py`) e retorno. Teto 3 tarefas, janela 45 min (Q48). Sem merge automático.

## 4. Máquina local

Arquivo grande e dado local ficam com executores locais (`modulos/executores-locais/`). Instalar é parada humana.

## 5. Retorno do coordenador

Até 2 KB no chat (Q170, Q180): veredito, entregas, commits, atestado, Jules e pendências. Detalhe em arquivo de retorno.

## Arquivos desta skill

- `references/limites-jules.md`: limites por plano.
- `assets/tarefa-jules.md`: modelo de tarefa autocontida.
- `scripts/verificar_lote.py`, `scripts/jules_cota.py`: conferência do lote e contagem de tarefas.
- `scripts/inventario_local.py`: inventário da máquina antes do módulo local.
