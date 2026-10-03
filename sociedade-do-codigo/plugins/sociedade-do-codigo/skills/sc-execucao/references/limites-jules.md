# Jules: limites, acesso e o que não está documentado

Experimental, não homologado (Q65). Situação em 23/09/2026: confirme nas fontes oficiais antes de dimensionar lotes.

## Limites por plano

Fonte: <https://jules.google/docs/usage-limits/> (consultada em 19/09/2026). Janela de 24 horas móveis.

| Plano | Tarefas por dia | Tarefas simultâneas |
|---|---|---|
| Jules (gratuito) | 15 | 3 |
| Jules no Pro | 100 | 15 |
| Jules no Ultra | 300 | 60 |

- No teto de 24 horas, o serviço recusa sessões novas até abrir vaga; as sessões em andamento continuam.
- A documentação não define o que conta como tarefa. `jules_cota.py` conta uma sessão criada como uma tarefa.
- O plano do usuário é configuração do ambiente. Cota diferente: use `--limite` com o valor declarado.

## Formas de acesso

| Caminho | O que a documentação oficial traz | Uso na Sociedade |
|---|---|---|
| Interface web | Criação manual de sessões | Só inspeção humana |
| CLI oficial | `jules login`; `jules remote new --repo <repo> --session "<prompt>"`; `jules remote list --session`; `jules remote pull --session <id>` | Caminho preferido; login é parada humana |
| API (alfa) | Base `https://jules.googleapis.com/v1alpha`; cabeçalho `X-Goog-Api-Key`; `GET /sessions?pageSize=<n>` | Chave só em variável de ambiente (`JULES_API_KEY`) |

## Regras

1. A chave nunca vai para arquivo, linha de comando visível ou relatório. Criar ou trocar chave é parada humana.
2. O Jules lê só o `AGENTS.md` da raiz do ramo remoto. A base precisa estar publicada antes do despacho.
3. Teto de 3 tarefas abertas (Q93, Q129); o perfil pode mudar o número. `verificar_lote.py` e `sc_passagem.py despachar-jules` recusam acima do teto.
4. Janela inicial de 45 minutos antes de intervir (Q48). Sem consulta em laço; a equipe segue em tarefas independentes.
5. Todo PR em rascunho. O especialista confere o diff e roda os testes antes de sugerir a integração ao coordenador.
6. Cota esgotada, falha ou demora sem progresso: o especialista assume a tarefa e registra o motivo.
7. Até três tentativas, cada uma com hipótese diferente; depois, a decisão volta ao usuário (Q12).

## O que não está documentado

- Se todo PR criado pelo Jules respeita o modo rascunho: peça na tarefa e confira no recebimento.
- Os estados intermediários de sessão na API (por isso `jules_cota.py` usa `createTime` em janela móvel).
- A paginação e a ordem de sessões antigas arquivadas.
