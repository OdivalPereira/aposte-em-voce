---
name: sc-revisao
description: A revisão independente da Sociedade do Código (Barbárvore): independência por fornecedor, revisão única do candidato consolidado, protocolo com oito lentes e matriz de cobertura, três severidades, parecer com hash e limite de uma correção e uma reconferência. Use ao revisar o candidato de uma etapa ou ao reconferir uma correção.
metadata:
  versao: "3.0.0"
---
# Revisão independente

O revisor não implementou nada da entrega e não vai corrigi-la. Achou defeito, relata.

## 1. Independência

- O revisor é de fornecedor diferente de todos os implementadores da etapa (D-RT-001). Do mesmo fornecedor é revisão interna: registre como tal, e ela não vale como aceite.
- O revisor nunca integra, publica, faz push nem merge.
- Trabalhe numa cópia descartável do commit congelado (`sc.py revisar`), sem memória da ferramenta e sem ler pastas fora da cópia.

## 2. Quando

- Uma vez por etapa, no candidato consolidado (Q84), com as fatias de alto impacto como prioridade.
- No máximo uma correção e uma reconferência de escopo fechado (Q85). Na reconferência, achado novo só bloqueia se for regressão das correções.
- Reconferência de bloqueador: desfaça a correção numa cópia e confirme que o teste falha (Q86).

## 3. Como

Siga `references/protocolo-revisao.md`:
- passo 0, com o mapa da entrega;
- oito lentes obrigatórias;
- matriz de cobertura, com uma linha por critério e uma coluna por lente.

O veredito só sai com a matriz completa.

- Confira o atestado e o CI pelo hash; rode a suíte só se o atestado faltar, divergir ou o ambiente for diferente (Q70).
- Distinga sempre o que foi executado do que foi só lido. Nunca cite comando que não rodou.
- Economia: leia por trecho, rode com saída curta (`| tail`); o parecer vai em arquivo e o chat leva o veredito, até 2 KB.

## 4. Achados e parecer

| Severidade | Efeito |
|---|---|
| bloqueador | impede o encerramento |
| relevante | adia só com justificativa e concordância do usuário |
| opcional | vai para a fila, não segura nada |

- Escreva o parecer pelo modelo `assets/parecer-modelo.md` e confira com `scripts/lint_parecer.py <arquivo>`.
- O cabeçalho traz `- commit: <SHA revisado>` (7 a 40 hexadecimais, igual ao head de `base..head`); sem ele o lint reprova, e o parecer só vale para esse commit.
- Informe o SHA-256 do parecer na mensagem de retorno (Q103).
- O registro no `registro.json` é feito com `sc.py revisar --etapa <ID> --parecer <arquivo> --head <SHA>` (skill `sociedade-do-codigo`): ele roda o `lint_parecer`, confere que o `commit:` é o SHA revisado e grava o parecer. Fora do modo emulação, o registro recusa revisor do mesmo fornecedor de um implementador.

## Arquivos desta skill

- `references/protocolo-revisao.md`: o método obrigatório.
- `assets/parecer-modelo.md`: modelo do parecer.
- `scripts/lint_parecer.py`: confere estrutura e coerência do parecer.
