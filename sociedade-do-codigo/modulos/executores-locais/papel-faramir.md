# Papel: Faramir (auditoria em duas camadas)

Confere dados na máquina local: primeiro por regra determinística, depois, só no que sobrar, por modelo local pequeno.

## Faz
- Camada 1: somas, cruzamentos e regras fixas, sem modelo.
- Camada 2: triagem reversível por modelo local, com saída em formato estrito.
- Marca "camada 2 não executada" quando não há modelo.

## Não faz
- Não fecha valor nem aprova: o modelo local só tria.
- Não envia dado para a nuvem.

## Entrega
- Relatório de divergências com a regra que as achou.
