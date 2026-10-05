---
name: sc-revisao
description: A revisão independente da Sociedade do Código (Barbárvore): independência por fornecedor, revisão única do candidato consolidado, protocolo com oito lentes e matriz de cobertura, três severidades, parecer com hash e limite de uma correção e uma reconferência. Use ao revisar o candidato de uma etapa ou ao reconferir uma correção.
metadata:
  versao: "3.3.0"
---
# Revisão independente

O revisor não implementou nada da entrega e não vai corrigi-la. Achou defeito, relata.

## 1. Independência

- O revisor é de fornecedor diferente de todos os implementadores da etapa (D-RT-001); interna não vale como aceite. Revisor nunca integra nem faz push.
- Cópia descartável do commit congelado (`sc.py revisar --etapa <ID> --base <c>`). Recusa preparar cópia se perfil ou regras diferirem do HEAD (Q178). Roda testes sem rede. Sem amend, reset ou force push (Q178).

## 2. Quando

- Uma vez por etapa no consolidado (Q84).
- Alto impacto por definição (Q176): toques em registro, conferência, aceite, portão ou permissões exigem protocolo completo e revisão interna.
- No máx. uma correção e uma reconferência (Q85). Reconferência em sessão nova grava parecer próprio sem sobrescrever o primeiro (Q179, Q180). Reversão nos bloqueadores (Q86).

## 3. Como

Siga `references/protocolo-revisao.md`:
- passo 0, com o mapa da entrega;
- oito lentes obrigatórias;
- matriz de cobertura, com uma linha por critério e uma coluna por lente.

O veredito só sai com a matriz completa.

- Confira o atestado e o CI pelo hash; rode a suíte só se o atestado faltar, divergir ou o ambiente for diferente (Q70).
- Distinga sempre o que foi executado do que foi só lido. Nunca cite comando que não rodou.
- Economia: leia por trecho, rode com saída curta (`| tail`); parecer em arquivo e chat com veredito até 2 KB (Q170).

## 4. Achados e parecer

| Severidade | Efeito |
|---|---|
| bloqueador | impede o encerramento |
| relevante | adia só com justificativa e concordância do usuário |
| opcional | vai para a fila, não segura nada |

- Escreva o parecer pelo modelo `assets/parecer-modelo.md` e confira com `scripts/lint_parecer.py <arquivo>`.
- Cabeçalho com `- commit: <SHA revisado>`. Informe o SHA-256 do parecer na mensagem de retorno (Q103).
- Registro: `sc.py revisar --etapa <ID> --parecer <arquivo> --head <SHA>`. Segundo parecer grava `parecer-<etapa>-reconferencia.md` sem sobrescrever o primeiro (Q179).
- Decisão: `sc.py decidir --etapa <ID> aceitar|corrigir|rejeitar|sem-aceite --por <nome>`; `corrigir` e `rejeitar` exigem `--motivo` (Q179).

## Arquivos desta skill

- `references/protocolo-revisao.md`: o método obrigatório.
- `assets/parecer-modelo.md`: modelo do parecer.
- `scripts/lint_parecer.py`: confere estrutura e coerência do parecer.
