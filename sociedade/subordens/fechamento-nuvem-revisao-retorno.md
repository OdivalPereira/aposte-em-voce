# Retorno da revisão interna (Galadriel), F2 + F3 — gravado pelo Círdan a partir da devolução

Executado: vitest unit 141 OK; tsc e eslint limpos; unittest 733 OK (1 pulado, 5 xfail dg03). e2e não executado.
Veredito: F2 e F3 podem ir ao portão; nada bloqueia.

F2: (1) backlog: grupo com total declarado e 0 linhas não é conferido (intencional, LEIAME item 8); (2) **corrigir na fatia**: `contaDoTexto` aceita data, CPF e 5 dígitos; (3) backlog: banco nulo num mês e "Nubank" em outro geram 2 históricos sem aviso.
F3: (1) importante: `atestado_hash` é SHA sem chave; atestado reescrito com hash recalculado passa no `decidir` e no `conferir`. **Texto corrigir na fatia** ("adulteração detectada"); resto vai ao backlog (registro do hash pelo `entregar` ou reexecução do portão). (2) backlog: `sc_rodada fatia --fechar --prova` e `sc_passagem` gravam exit_code 0 fixo. (3) backlog: `_nome_do_perfil` por igualdade exata. (4) backlog: `verificar_workflows` só cobre `.github/workflows/`. (5) **corrigir na fatia**: teste de `encerrar --forcar` sem decisão; helper de `test_status` usa o código sob teste. (6) nota: o job `aceite` usa o `sc_status.py` da base; a B15 só vale após o merge.
Sem achado: encadeamento, meses faltando, mesmo hash, 5.3, assinatura sem dados; 21 de 23 testes novos falham no código anterior; recusas confirmadas.
