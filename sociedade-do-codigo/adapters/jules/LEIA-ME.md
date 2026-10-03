# Adaptador do Jules

Experimental, não homologado (Q65)

O Jules lê **somente** o `AGENTS.md` da raiz do repositório. Ele não enxerga skills, plugins nem pastas do seu computador. Por isso a adoção para ele é o bloco "Sociedade do Código" dentro do `AGENTS.md`, com a seção "Para o Jules" (módulo `jules` ligado).

## Passos

1. No projeto, gere ou atualize o bloco (simulação primeiro):

   ```
   python3 <pacote>/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_sync_agents_md.py --projeto . --perfil sociedade/perfil.md
   ```

   Confira o diff e repita com `--aplicar`.
2. Mantenha o `AGENTS.md` curto: o Jules o lê a cada tarefa.
3. Publique a branch de base no GitHub antes de despachar (o Jules trabalha do repositório remoto). Publicar é parada humana quando tem efeito (CI, prévia de deploy).
4. Monte o lote no modelo `sc-execucao/assets/tarefa-jules.md`, confira com `verificar_lote.py` e confirme a cota com `jules_cota.py`. Especialistas respondem pelo contrato e pela conferência do retorno; Gandalf coordena a fila compartilhada para evitar duplicatas e conflitos.
5. Conceda a janela inicial de espera de **45 minutos** antes de avaliar intervenção (Q48); a equipe avança em tarefas independentes enquanto aguarda.
6. Peça PR em rascunho e revise em sessão distinta antes de qualquer integração ou merge.

## Executores locais

O módulo `local` (Celebrimbor, Radagast, Faramir, Bilbo) **não** vale para o Jules: ele roda em nuvem e não alcança a sua máquina, o Ollama nem as suas pastas. Trabalho que precisa de executor local fica com o coordenador.

## Credencial

A chave da API do Jules é segredo do usuário. Fica em variável de ambiente (`JULES_API_KEY`). Este pacote nunca a grava, imprime nem a coloca em arquivo.
