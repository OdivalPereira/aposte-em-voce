# Subordem a1-parser · revisão interna da F1 (só a B11)

Para: Galadriel (Claude Code em nuvem, subagente `galadriel`) · revisão interna de alto impacto (C17, Q10)
De: Gandalf · Etapa a1-parser · Fatia revisada: F1, só a B11 (portão amarrado) · Base: `d86e90c` · Cabeça: `fce98d9` (a F2 está no meio, em `7ea0695` e `5ff94f7`; revise só o que é do pacote e do `.github/pull_request_template.md`: `git diff 5ff94f7..fce98d9`)
Worktree: `/root/.sociedade/trabalho/aposte-em-voce/a1-parser`. Só dados sintéticos. Nunca estime nem relate consumo.

## Objetivo
Revisar a B11 antes do portão, sem editar nada: o portão amarrado realmente não pode ser contornado, e as sondas provam o que dizem.

## Aceite da revisão
Parecer com achados classificados (bloqueante, importante, menor), cada um com arquivo, linha e como reproduzir. Veredito: "pode ir ao portão" ou "volta ao Aragorn". Procure especialmente:
- `--comando-teste` realmente recusado em todos os caminhos (inclusive abreviação de opção do argparse, como `--comando`, e variável de ambiente);
- árvore suja: arquivo rastreado modificado, novo não rastreado, removido, renomeado; subpasta de `sociedade/` fora do ignorado; `node_modules/` ignorado pelo `.gitignore` não conta, mas arquivo não ignorado em pasta de mesmo nome conta;
- 0 testes e "todos pulados" reprovam; timeout reprova; saída do Vitest e do Playwright lida corretamente (com e sem ANSI);
- o atestado grava por área comando, timeout, contagem, SHA-256 do perfil e commit; o perfil usado é o canônico (o da pasta de sociedade informada), não o do candidato;
- área por prefixo mais longo, `.github/` nas duas, `sociedade/` e `docs/` em nenhuma; `--area` desconhecida dá erro claro;
- NFC e `-z` (nome com espaço, acento em NFD, aspas) no atestado e no `arquivos_em`;
- B11a: nenhum comando grava no checkout principal; B11b e B11d (texto);
- `expectedFailure` removido só do que a B11 fecha; nenhum teste antigo apagado ou enfraquecido para passar.

## Leia só (até 5 caminhos)
1. `git diff 5ff94f7..fce98d9` (o diff da fatia, via Bash).
2. `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_pre_devolucao.py`.
3. `sociedade-do-codigo/tests/test_portao_amarrado.py` e `sociedade-do-codigo/tests/adversarial/`.
4. `sociedade-do-codigo/tests/test_sociedade_worktree.py`.
5. `sociedade/perfil.md`, seção "Portão por área".

## Escreva só
Nada no repositório. O parecer vai no retorno. Pode criar arquivos temporários só no diretório de rascunho da sessão para reproduzir achados.

## Teste dirigido
Reproduza cada achado com um comando (em cópia temporária fora do worktree, nunca no worktree): `python3 -B -m unittest discover -s tests -p 'test_portao_amarrado.py' -v` em `sociedade-do-codigo/` e a sua sonda manual.

## Portão da fatia
Não se aplica a esta subordem (o portão da F1 é do Gandalf, depois que as correções entrarem). O que você achar é corrigido dentro da própria fatia, por quem a fez (Aragorn); não nasce fatia nova (ajuste 3 da aprovação).

## Retorno (até 2 KB)
Veredito; lista de achados (classe, arquivo:linha, reprodução, correção sugerida em uma frase); o que ficou fora do escopo e vai para o Barbárvore ou o backlog; atritos com o método.
