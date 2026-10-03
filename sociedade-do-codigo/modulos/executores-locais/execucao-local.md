# Registro de execução local

Experimental, não homologado (Q65)

Uma entrada por execução, no quadro de executores da devolutiva (ou onde o perfil indicar). Curto: se não couber em dez linhas, o que sobra vai para o arquivo de saída e aqui entra o caminho.

```
- papel: <Celebrimbor | Radagast | Faramir | Bilbo>
- quando: <dd/mm/aaaa hh:mm>
- comando: <comando exato, sem segredo>
- modelo local: <tag como aparece em `ollama list`, ou "não usado">
- camadas executadas: <1 | 1 e 2 | "camada 2 não executada" e o motivo>
- entrada: <caminho> · sha256 <primeiros 12 caracteres>
- saída: <caminho> · sha256 <primeiros 12 caracteres>
- resumo: <linhas lidas, rejeitadas, achados por severidade, campos extraídos>
- resultado: <concluído | ignorado, conteúdo idêntico | falhou: erro em uma linha | não executado>
```

Regras:

- Não invente modelo, versão nem tempo. Copie do ambiente ou escreva "não informado".
- "Não executado" é um resultado válido. Alegar execução sem comando e sem saída não é.
- O hash prova que o arquivo é o mesmo, não que o conteúdo é verdadeiro.
