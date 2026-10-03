<!--
Modelo de tarefa Jules. Uma tarefa por bloco "Tarefa:". Vários blocos no mesmo arquivo formam um lote.
Cada rótulo em uma linha (valor na mesma linha ou em itens "- " logo abaixo).
Apague este comentário ao usar. Confira com scripts/verificar_lote.py.
-->
Tarefa: <slug-curto>
Classe: <R0 ou R1>
Repositório e base: <dono/repo> · branch <nome> @ <sha7> (já publicada no GitHub)
Objetivo: <uma frase>
Arquivos permitidos: <caminho ou pasta ou padrão, separados por vírgula>
Não tocar: <caminhos proibidos; segredos, migrações, autenticação e cobrança, salvo se a classe e a ordem permitirem>
Comportamento a preservar: <o que não pode mudar>
Como provar que está pronto: <comandos exatos, por exemplo o comando de teste do arquivo alterado>
Tamanho esperado: até 5 arquivos e cerca de 150 linhas alteradas; se estourar, pare e explique
Retorno: PR em rascunho; diga o que testou e o que não testou
Fora de escopo: <lista>

<!--
Exemplo de lote (dois blocos com arquivos disjuntos):

Tarefa: testes-formatador-datas
Classe: R0
Repositório e base: dono/repo · branch principal @ a1b2c3d (já publicada no GitHub)
Objetivo: cobrir com testes de comportamento a função formatarData.
Arquivos permitidos: src/utils/formatarData.test.ts
Não tocar: src/utils/formatarData.ts, .env, migrações
Comportamento a preservar: a função existente não muda.
Como provar que está pronto: npm test -- src/utils/formatarData.test.ts
Tamanho esperado: até 1 arquivo e cerca de 80 linhas
Retorno: PR em rascunho; diga o que testou e o que não testou
Fora de escopo: alterar a função ou suas dependências

Tarefa: aria-botao-menu
Classe: R1
Repositório e base: dono/repo · branch principal @ a1b2c3d (já publicada no GitHub)
Objetivo: dar nome acessível e estado expandido ao botão do menu móvel.
Arquivos permitidos: src/components/MenuMovel.tsx, src/components/MenuMovel.test.tsx
Não tocar: estilos globais, .env
Comportamento a preservar: aparência e navegação atuais.
Como provar que está pronto: npm test -- src/components/MenuMovel.test.tsx
Tamanho esperado: até 2 arquivos e cerca de 60 linhas
Retorno: PR em rascunho; diga o que testou e o que não testou
Fora de escopo: redesenho do menu
-->
