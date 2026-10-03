---
name: sc-execucao
description: Como o coordenador da Sociedade do Código executa uma etapa: fatias delegadas a especialistas por subagente, tarefas mecânicas para o Jules, subordem autocontida, disjunção de arquivos e portão por fatia. Use ao dividir uma etapa, delegar uma fatia ou receber o resultado de um especialista ou do Jules.
metadata:
  versao: "3.0.0"
---
# Execução de uma etapa

Vale para o coordenador e os especialistas.

## 1. Fatias e subordens

- Fatia é o menor pedaço da entrega que se prova sozinho. Revisar e integrar não são fatias.
- Cada fatia vai a um especialista em sessão separada (`invoke_subagent` no Antigravity), com uma subordem autocontida:
  - objetivo e critério de aceite da fatia;
  - "leia só": até 5 caminhos, com intervalo de linhas em arquivo grande;
  - "escreva só": os arquivos da fatia, sem sobreposição com outra fatia;
  - comando de teste dirigido, com saída curta (`| tail`, `-q`);
  - arquivos do estado e do retorno (2 KB no chat). Fatia que cresce: estado em arquivo, devolução e agente novo.
- Antes de despachar, confira a disjunção: `verificar_disjuncao.py` (skill `sociedade-do-codigo`).
- Delegação que falha é parada: registre e devolva. O coordenador não faz o trabalho no lugar do especialista.

## 2. Portão por fatia

- Durante a fatia, rode só os testes dirigidos.
- Ao fechar a fatia: commit e `sc.py entregar --etapa <ID> --base <commit anterior>`.
- No fim da etapa: `sc.py entregar --etapa <ID> --base <base da etapa>` e o atestado vai para `sociedade/pareceres/`.
- Fatia de alto impacto (Q10) recebe revisão interna da Galadriel, também por subagente (Q92).

## 3. Jules

- Só tarefas mecânicas e delimitadas: fixtures, testes de apoio, atualização de referências, renomeações (Q93, Q129).
- Nunca regra crítica, migração, autenticação, cobrança ou dado real.
- O especialista monta a tarefa pelo modelo `assets/tarefa-jules.md`, confere o lote com `scripts/verificar_lote.py` e confere o retorno. O coordenador evita duplicação.
- Teto de 3 tarefas abertas. Janela inicial de 45 minutos antes de intervir (Q48). PR em rascunho, nunca merge automático.
- A base precisa estar publicada no remoto: o Jules não vê commit local. Publicar é parada humana.

## 4. Máquina local

Arquivo grande, conversão, extração e dado que não pode sair da máquina ficam com os executores locais, módulo opcional do pacote (`modulos/executores-locais/`). Instalar biblioteca ou modelo é parada humana.

## 5. Retorno do coordenador

Até 2 KB no chat (revisa a Q99): veredito, lista de entregas, commits, atestado, tarefas do Jules e pendências. O detalhe vai para `sociedade/subordens/<ordem>-<fatia>-retorno.md`.

## Arquivos desta skill

- `references/limites-jules.md`: limites por plano, com data e fonte.
- `assets/tarefa-jules.md`: modelo de tarefa autocontida.
- `scripts/verificar_lote.py`, `scripts/jules_cota.py`: conferência do lote e contagem de tarefas das últimas 24 horas (só leitura).
- `scripts/inventario_local.py`: inventário da máquina (só leitura), antes do primeiro uso do módulo local.
