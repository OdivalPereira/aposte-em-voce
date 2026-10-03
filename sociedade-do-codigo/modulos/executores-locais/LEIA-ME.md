# Módulo opcional: executores locais

Experimental, não homologado (Q65). Fora do caminho de leitura dos agentes (Q140).

Quatro papéis que rodam na máquina do usuário, sem modelo em nuvem: Celebrimbor (leitura de arquivos e extração), Radagast (coleta web), Faramir (auditoria em duas camadas) e Bilbo (memória e contexto prévio). Servem para tarefas pesadas ou com dado que não pode sair da máquina.

## Quando ativar
- Só quando uma tarefa concreta exigir e o perfil do projeto listar o papel como ativo (Q95).
- Modelo local só com decisão do usuário (Q23, Q94).

## Como usar
1. Rode `inventario_local.py` (skill `sc-execucao`, pasta `scripts/`) e confira se o que o perfil declara existe na máquina.
2. Preencha a seção "Executores locais" do perfil: comandos, pasta de saída e teto de recursos.
3. Para agentes no Antigravity, copie `agents/*.md` deste módulo para `~/.gemini/config/agents/`.
4. Registre cada execução pelo modelo `execucao-local.md`.

## Arquivos
- `papel-celebrimbor.md`, `papel-radagast.md`, `papel-faramir.md`, `papel-bilbo.md`: o que cada um faz e não faz.
- `limites-locais.md`: limites e formatos dos executores (resumo da 2.x, sem revisão independente).
- `execucao-local.md`: registro de uma execução.
- `agents/`: definições de subagente para o Antigravity.
