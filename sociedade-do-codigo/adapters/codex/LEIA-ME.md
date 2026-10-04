# Adaptador do Codex

Experimental, não homologado (Q65)

O Codex lê plugins por marketplace e skills por pasta. Duas formas, escolha uma.

## Papel na formação real

Na formação real da Sociedade do Código, o Codex é a ferramenta do **Barbárvore (revisor independente)**. Sendo de outro fornecedor (OpenAI), assegura a independência estrita exigida pelo método em relação aos implementadores (Anthropic/Google).

## Passagem entre ferramentas (Q175)

A revisão no Codex é acionada pelo usuário a partir da linha gerada por `sc.py passar --etapa <ID> --para barbarvore`, colada no Codex aberto na pasta da cópia descartável da etapa (`~/.sociedade/revisar/<projeto>/<etapa>`), numa conversa nova e com as memórias desligadas. A conferência lê o log da sessão (`sc.py sessao codex`). O revisor emite o parecer com hash e o usuário devolve o resultado ao Círdan.

## A. Plugin (recomendado)

1. Adicione o repositório do pacote como marketplace: `codex plugin marketplace add <dono>/<repo>` (ou, com clone local, `codex plugin marketplace add ./caminho-do-clone`).
2. Abra o navegador de plugins do Codex, escolha o marketplace "sociedade" e instale "sociedade-do-codigo".
3. Confira que as skills apareceram (`sociedade-do-codigo`, `sc-papeis`, `sc-execucao`, `sc-revisao`).

A sintaxe exata dos comandos muda entre versões; confirme com `codex plugin --help`.

## B. Só as skills, sem plugin

Copie a pasta de cada skill para `~/.agents/skills/` (todos os projetos) ou `.agents/skills/` (um projeto). O `scripts/instalar.py --alvo codex` faz isso com cópia de segurança e simulação prévia.

## Regras de entrada

O Codex lê o `AGENTS.md` do projeto. O bloco "Sociedade do Código" (gerado por `sc_sync_agents_md.py`) já carrega a adoção. Nada mais é preciso.

## Executores locais

Módulo opcional (`modulos/executores-locais/`). Antes do primeiro uso, rode `inventario_local.py` da skill `sc-execucao`.
