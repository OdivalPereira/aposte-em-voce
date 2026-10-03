# Executores locais: limites e formatos

Experimental, não homologado (Q65). Resumo dos limites da 2.x; o texto completo está no histórico do Git (tag `v2.1.0`).

## Regras comuns

- Escrevem só na pasta de saída do perfil. Não tocam banco de produção nem pastas protegidas.
- Nada de conteúdo bruto na conversa: passam caminho, esquema e contagens.
- Modelo local só tria e classifica de forma reversível; não fecha valor, não decide regra, não aprova.
- Dinheiro em centavos ou `decimal.Decimal`, nunca `float`.
- Saída gravada de forma atômica, com SHA-256; reprocessar o mesmo conteúdo é ignorado e registrado.
- Sem registro físico de precedente, a resposta é "sem registro".
- Três tentativas com hipóteses diferentes; depois, escalam ao coordenador (Q12).

## Celebrimbor: leitura de arquivos

| Formato | Conferência obrigatória |
|---|---|
| OFX (`.ofx`, `.qfx`) | saldo inicial + movimentos = saldo final |
| CNAB 240 e 400 | sequência de registros e totais do trailer |
| CSV, TSV, XLSX | cabeçalho, número de colunas e tipos |
| SPED (`.txt`) | hierarquia de blocos e registro de encerramento |
| Balancetes e diários | soma dos débitos = soma dos créditos |
| PDF tabular | soma dos itens = total do documento |

Amostra mínima para reconhecer o formato: 15 linhas ou 2 páginas, com nomes e números anonimizados antes de chegar a qualquer modelo. O arquivo inteiro é processado só pelo Python local.

## Faramir: auditoria em duas camadas

- Camada 1, determinística: consultas em memória (SQLite `:memory:`, DuckDB se instalado), somas, cruzamentos e integridade referencial.
- Camada 2, opcional: modelo local pequeno, só no que sobrar, com saída em formato estrito. Sem modelo, o relatório diz "camada 2 não executada".
- Vereditos: `sem_ressalvas`, `requer_decisao_humana` (alertas estatísticos ou da camada 2) e `bloqueio_critico` (divergência de valor, duplicidade, total quebrado).

## Bilbo: memória do projeto

- `eventos_decisao.jsonl`: uma decisão humana por linha (autor, data UTC, contexto, situação, diretiva, hash).
- `regras_determinadas.json`: regras aprovadas pelo usuário, com padrão de entrada e saída determinística.
- Resumo para a ordem: até 30 linhas, só o que tem relação com o objeto da ordem, com referência de cada item.
- Perguntas de quantidade (saldo, data, contagem) vão a consulta determinística, nunca a busca por similaridade.
- Um projeto nunca lê a memória de outro.
