## Parecer do Revisor Independente
- etapa: d1-design
- entrega: candidato corrigido 87c81143729f; reconferência reduzida de escopo fechado (Q85/Q86)
- commit: 87c81143729f
- base..head: c927e5d170d8..87c81143729f
- revisor: Barbárvore (Codex), revisor não calibrado (Q160) · fornecedor: OpenAI · sessão: 01a10b7e-de44-7a01-8982-a9a390460127
- modelo: GPT-6 Sol (designação humana; configuração efetiva não exposta) · esforço: xhigh (designação humana)
- independência: Nível A (fornecedor diferente dos implementadores declarados)
- veredito: não aceitar
- data: 05/10/2026 07:27 (America/Campo_Grande)

### Independência

Não implementei nem corrigi nada desta entrega. A ordem designa Gandalf e especialistas no Antigravity, fornecedor Google; a revisão usa Codex, fornecedor OpenAI. O perfil copiado ainda declara a formação anterior, Anthropic, também diferente de OpenAI. A designação explícita do usuário e da ordem rege esta reconferência, sem marca de emulação. Não auditei a identidade efetiva das sessões dos implementadores.

Esta reconferência ocorreu na mesma sessão de revisão indicada acima. Não afirmo que foi criada outra conversa ou que o modelo/esforço efetivos foram medidos. Após a instrução de reconferência, confirmei por `pwd` a pasta `/home/odival/.sociedade/trabalho/d1-design/reconferencia-d1-design`; não consultei memórias nem conteúdo de outras pastas para fundamentar este parecer. Os dados das sondas são sintéticos, e as gravações ficaram em `revisao-saida/`.

A cópia tem commits locais sintéticos: HEAD `42edf582c1243ad0c247a3d12ca24b6deb2b8368`, intitulado “candidato (87c8114)”, e base `85f006cbea96f2bb7fcdee413a85abd286656cfe`, intitulada “base (c927e5d)”. O cabeçalho usa os SHAs originais exigidos pelo usuário. Eles coincidem com commit/base do atestado copiado; os 77 hashes de artefatos desse atestado conferem com os arquivos inspecionados, sem divergência. Isso verifica os artefatos enumerados, sem equivaler à verificação do objeto Git original inteiro.

### Mapa da entrega

**Motivo da etapa.** A ordem `sociedade/ordens/d1-design.md`, seções Objetivo, F1/F2, F3 e F5, pede referência visual e aplicação em T08/T09/T99, com acessibilidade e comportamento preservado, e prepara a Sociedade para a formação real. O motivo desta reconferência é verificar a correção dos seis achados do parecer anterior, após a decisão “corrigir”.

**Limite Q85.** A lista completa de aceite desta reconferência é C-R01 a C-R06 abaixo. Não reabri os demais critérios da etapa. Os achados deste parecer são persistências de A01–A03 e regressão da correção de A06; não há bloqueador novo alheio às correções.

**Superfícies de entrada.** C-R01 usa `conferir_item` para E7 `delegacoes antigravity @etapa 5` e E8 `conversa_nova antigravity @etapa`, o resolver, o evento de passagem e bases/transcripts sintéticos. C-R02/C-R03/C-R05 usam o parser público `sc_rodada.main`: `papel emulacao ligar|desligar --motivo --autor --pasta --aplicar` e `papel trocar --papel execucao|coordenador --para --fornecedor --modelo --motivo --autor --pasta --aplicar`. C-R04 usa o input `escolher-pdf`, suas labels, `Extratos`, `EstadoVazio` e os três arquivos CSS importados. C-R06 usa os padrões `ask/deny` dos dois JSONs de permissões.

**Estados e transições.** Uma conversa só pode provar E7/E8 quando pertence à pasta da etapa, começa depois da passagem e não é ausente/ambígua. Eventos íntegros podem ser recarregados; conteúdo alterado não pode adquirir validade ao omitir a prova de integridade. O comando pode ligar a emulação; desligá-la exige R1–R3 válidas no estado que será gravado. Trocar a execução altera os ocupantes ativos; falha de persistência não deve deixar perfil e registro divergentes. Em T08, vazio e com arquivos devem mostrar o foco no controle visível por teclado. Merge commit legítimo exige autorização humana; squash/rebase/auto/admin devem permanecer proibidos.

**Fontes de verdade e derivados.** `perfil.md` guarda ocupantes/emulação; `registro.json` guarda os eventos e a passagem. Os logs e resumos de conversa são evidência externa à etapa, aqui representados por fixtures locais; E7/E8 são resultados derivados dessa evidência. TSX e CSS determinam o indicador de foco; o HTML da sonda é uma representação isolada dessa estrutura. As configurações JSON são a fonte das regras; a comparação de padrões é derivada e não executa o motor de permissões do Claude. O atestado declara resultados do executor, sujeitos a confirmação independente.

### Critérios e evidências

| Critério do aceite | Evidência | Estado |
|---|---|---|
| C-R01 — A01: @etapa exige identidade exata da pasta, início posterior à passagem e recusa ausência/ambiguidade (F5/L8; C31/C32 anteriores). | `python3 -B revisao-saida/sondas.py`, R01: caso legítimo passa; pasta errada, prefixo, horário ausente/anterior, ausência e ambiguidade são recusados. Porém R01-identidade aceita a conversa de outra pasta quando uma mensagem do corpo cita a pasta da etapa. A01 permanece. | executada |
| C-R02 — A02: escrita e leitura verificáveis da cadeia, inclusive adulteração/legado (F5/L1; C25 anterior). | Mesmo comando, R02: evento novo contém hash/prev_hash; adulteração simples e adulteração após evento legado são recusadas. Remover hash/prev_hash e alterar o motivo do último evento novo é aceito. A02 permanece. | executada |
| C-R03 — A03: emulação não desliga com R1–R3 violadas, inclusive intercalação (F5/L1; C23 anterior). | Mesmo comando, R03: troca antes da segunda validação é detectada. Troca depois dela e antes da escrita conclui junto com o desligamento, ambas com código 0; estado final emulacao=false e duas violações de R3. A03 permanece. | executada |
| C-R04 — A04: foco visível no seletor de PDF vazio/com arquivos, em 320/360 px (F1/F2; C07 anterior). | R04: navegador local, Tab, DOM equivalente e CSS copiado. Quatro casos com outline solid 3px, offset 2px; quatro reversões com outline-style none. Estrutura confirmada em TSX. Corrigido no DOM/CSS testado; a execução no app completo não foi confirmada. | executada |
| C-R05 — A05: falha na gravação do evento preserva perfil e registro, em emulação e troca (C23/C25/C27 anteriores). | `python3 -B revisao-saida/sondas.py`, R05: OSError injetado em Registro.aplicar_mutacao nos dois comandos; ambos retornam erro e preservam os bytes das duas fontes. Resolvido na falha sequencial testada. | executada |
| C-R06 — A06: aliases proibidos cobertos nas duas configurações e merge commit legítimo preservado (F3/Q174; C21 anterior). | Mesmo comando, R06-aliases: -s/-r e formas longas correspondem a deny, --merge/-m simples não. `permissoes-regressao.json`: --merge com --repo ou --subject também corresponde a deny nas duas configurações. Aliases corrigidos com regressão estática de alcance. | executada |

### Matriz de cobertura

Cada identificador abaixo remete às execuções descritas nesta seção. “Lida” delimita uma inspeção de fonte, sem alegar execução do app/motor indisponível.

| Critério | L1 motivo | L2 ponta a ponta | L3 estados | L4 escape | L5 entradas | L6 concorrência | L7 fontes | L8 retorno |
|---|---|---|---|---|---|---|---|---|
| C-R01 | R01-variantes | R01 via conferir_item e medição | R01-anterior-passagem/ambigua | R01-identidade | R01-sem-tempo/ausente/prefixo | n/a (correção de resolução, sem gravação concorrente) | R01: passagem/log contra E7/E8 | E69 + R01-identidade + Q86-A01 |
| C-R02 | R02-adulteracao | R02: CLI e recarga | R02-integro/adulterado | R02-omissao | R02-legado/omissao | n/a (adulteração após gravação concluída) | R02: conteúdo contra elo/hash | E69 + R02-omissao + Q86-A02 |
| C-R03 | R03-apos-revalidacao | R03: duas operações CLI | R03: ligado para desligado | R03: troca enquanto ligado | n/a (entradas válidas; defeito de intercalação) | R03-antes/apos-revalidacao | R03: perfil/registro e R3 finais | E69 + R03 + Q86-A03 |
| C-R04 | R04-vazio/arquivos | R04 teclado no DOM isolado; app lida | R04: vazio/com arquivos | n/a (sem opção de exceção) | n/a (foco não depende do conteúdo de PDF) | n/a (sem persistência concorrente) | R04 + TSX/CSS lidos | R04 + Q86-A04; e2e lido |
| C-R05 | R05-emulacao/troca | R05: CLI até erro | R05: falha e restauração | n/a (sem opção de escape da correção) | R05: falha de armazenamento injetada | R05: falha entre gravações | R05: bytes das duas fontes | E69 + R05 |
| C-R06 | R06-aliases | R06 comparação estática; motor lido | n/a (regras sem estado persistente) | R06: aliases e --repo/--subject | R06: variações de opções | n/a (configurações estáticas) | R06: projeto e modelo | R06 + permissões-regressao |

**Execuções e resultados.**

R01/R02/R03/R05/R06 estão em `revisao-saida/sondas.py`. A execução consolidada teve **11 métodos de teste, quatro falhas, zero erros e zero pulados**. As falhas são A01-identidade, A02-hash-omitido, A03-após-última-validação e A06-caminho-legítimo. Os resultados estruturados e rastros estão em `sondas-candidato.json` e `sondas-candidato.log`. Não confundo esses quatro métodos com o total de variantes/subtestes.

E69 é a execução própria de todos os testes de `test_formacao_real`, `test_emulacao`, `test_troca_papel`, `test_conferir_l8`, mais os dois métodos `test_cadeia_hash_*` de `test_registro`: **69 testes, zero falhas, zero erros e zero pulados**. Registrei o resumo/rastro em `testes-existentes.json` e `testes-existentes.log`. Foram usados temporários dentro de `revisao-saida/fixtures/` e home isolada; os testes não consultaram logs pessoais como evidência.

L8: os testes novos de A01 cobrem os negativos originais e passam; não cobrem a menção incidental no corpo. Os dois de hash cobrem adulteração de conteúdo/prev_hash, mas não a remoção dos campos do último evento. `test_revalidacao_estrita_r1_r3_concorrente_ao_desligar_emulacao` (test_emulacao.py:524–545) começa com R3 já violada e não intercala operações; sua aprovação não demonstra fechamento de A03. O novo e2e de foco foi lido em `tests/e2e/leitura.spec.ts`; não foi executado nesta cópia.

O atestado APROVADO declara app 191 testes/7 pulados e pacote 765/1 pulado, total 956/8. São contagens declaradas, sem reexecução integral aqui. Conferi **77 hashes**, todos iguais. `npm test` foi tentado nesta cópia e falhou por `vitest: not found`; isso é limitação do ambiente, não achado contra a entrega.

### Falsificação das correções (Q86)

Desfiz cada correção de bloqueador em cópia de sonda, sem tocar na entrega. As reversões de A01–A03 são remoções localizadas sobre os scripts atuais, e A04 restaura o posicionamento antigo do input e retira o seletor adicional no DOM/CSS isolado. Não são checkouts do commit anterior, cujo objeto não está nesta cópia. `reversoes/manifesto.json` registra os hashes das cópias; `sonda-ui/manifesto.json` registra os artefatos visuais.

| Bloqueador original | Teste com correção no candidato | Mesmo teste após desfazer a correção |
|---|---|---|
| A01 | R01-variantes-originais passa: caso legítimo aceito e seis variantes negativas recusadas. | `python3 -B revisao-saida/sondas.py --scripts revisao-saida/reversoes/A01/scripts --somente test_A01_variantes_originais`: código 1, quatro subtestes falham (pasta errada, prefixo, sem horário e anterior à passagem). |
| A02 | R02-adulteracao e R02-legado passam: adulteração recusada. | `python3 -B revisao-saida/sondas.py --scripts revisao-saida/reversoes/A02/scripts --somente test_A02_adulteracao,test_A02_legado`: código 1, dois testes falham; conteúdo adulterado aceito. |
| A03 | R03-entre-validacoes passa: a segunda validação recusa o desligamento. | `python3 -B revisao-saida/sondas.py --scripts revisao-saida/reversoes/A03/scripts --somente test_A03_entre_validacoes`: código 1, um teste falha; emulação desliga com R3 violada. |
| A04 | R04: Tab mostra outline solid 3px/offset 2px na label dos quatro cenários. | R04-revertido: mesmo Tab foca input oculto, mas outline-style=none em quatro de quatro cenários; o predicado de foco visível falha. |

Resultados de reversão em `reversoes/resultados.json`, `sondas-A01.json/log`, `sondas-A02.json/log`, `sondas-A03.json/log` e `sonda-ui/resultados.json`. As invocações Python foram executadas com o caminho absoluto do diretório de scripts; as formas relativas da tabela reproduzem a mesma seleção a partir desta pasta.

Para reproduzir R04: servir `revisao-saida/sonda-ui/` localmente, abrir `index.html`, entrar em cada iframe de 320/360 px, focar o botão “Início da sonda” e pressionar Tab. Medir `document.activeElement`, `:focus-visible` e os estilos computados da label. Os oito casos executados tiveram input focado, opacity=0, largura=1px, sem overflow horizontal; só os quatro candidatos tiveram outline-style=solid. O servidor 127.0.0.1:8766 e a aba temporária foram encerrados.

Q86 mostra que as correções têm efeito mensurável. Não prova resolução integral: os contraexemplos R01-identidade, R02-omissão e R03-após-revalidação ainda falham no próprio candidato.

### Achados

- [bloqueador] A01 — L1/L2/L4/L5/L7/L8: persiste a aceitação de conversa de outra pasta por menção incidental no corpo (sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_conferir.py:240–258).

    **Condição:** primeiro USER_INPUT cita a ordem e declara pasta “e8-outro”, sem campos estruturados de workspace. Uma mensagem posterior do assistente diz “Outro caminho citado como referência: [pasta e8]”. Timestamp é válido e há cinco delegações. **Efeito:** E7 retorna “feito, 5 delegações” e E8 “feito, 1 ordem na conversa”; a referência textual foi promovida a identidade de workspace. **Critério:** C-R01/F5-L8. **Evidência reproduzível:** R01-identidade, executar `python3 -B revisao-saida/sondas.py --somente test_A01_identidade_corpo`. **Correção esperada:** obter identidade confiável da pasta, recusar declaração divergente e não usar qualquer citação no corpo como substituto; teste deve percorrer conferir_item e medição. Os negativos antigos foram corrigidos, mas a condição principal de A01 permanece em outro caminho da correção.

- [bloqueador] A02 — L1/L4/L5/L7/L8: omitir hash/prev_hash do último evento novo permite adulteração aceita (sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_registro.py:208–222).

    **Condição:** executar papel emulacao ligar, alterar dados.motivo do evento recém-gravado e apagar seus campos hash e prev_hash. **Efeito:** Registro recarrega sem ErroRegistroCorrompido; a condição “se há hash” permite tratar evento novo adulterado como legado. **Critério:** C-R02/C25/F5-L1. **Evidência reproduzível:** R02-omissao, `python3 -B revisao-saida/sondas.py --somente test_A02_hash_omitido`. **Correção esperada:** distinguir formato legado de eventos que obrigatoriamente pertencem à cadeia e rejeitar omissão da prova exigida, inclusive na cauda; preservar compatibilidade legítima por regra explícita de formato/migração. A escrita e a detecção de alteração simples foram corrigidas; o critério de integridade ainda permite escape.

- [bloqueador] A03 — L1/L2/L3/L6/L7/L8: a segunda validação continua fora da proteção da atualização, mantendo a janela de estado antigo (sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_rodada.py:1603–1613).

    **Condição:** uma troca pública de execução para Anthropic se intercala depois da segunda validação e antes de atualizar_emulacao gravar. **Efeito:** troca e desligamento retornam 0; perfil final tem emulação desligada e dois ocupantes fora do Google, acusados por R3. **Critério:** C-R03/C23. **Evidência reproduzível:** R03-apos-revalidacao, `python3 -B revisao-saida/sondas.py --somente test_A03_apos_ultima_validacao`. A sonda usa intercalação determinística de duas invocações reais do parser/comandos públicos, por hook no limite de gravação; não alega execução de dois processos simultâneos. **Correção esperada:** serializar sob proteção comum leitura, validação e atualização das fontes em ambos os caminhos, com recusa ou estado final válido. O teste atual chamado “concorrente” começa inválido e não exercita a janela. É a persistência do bloqueador original.

- [relevante] A06 — L1/L2/L4/L7/L8: a correção dos aliases amplia deny para opções legítimas de merge commit (.claude/settings.json:15–17; sociedade-do-codigo/adapters/claude/settings.json.modelo:22–24).

    **Condição:** `gh pr merge 123 --merge --repo Organizacao/Projeto` ou `gh pr merge 123 --merge --subject "Etapa d1"`. **Efeito observado:** na comparação estática dos padrões, ambos correspondem a ask e também a deny: --repo contém -r e --subject contém -s. As regras novas não delimitam o argumento curto. **Critério:** C-R06/F3/Q174; preservar o caminho legítimo exigido pelo princípio 4. **Evidência:** R06 e os quatro resultados em `permissoes-regressao.json`, um por comando/configuração. **Correção esperada:** delimitar opções proibidas sem bloquear opções legítimas e confirmar no motor real, sem efetuar merge. A05 está resolvido na falha testada; A06 não está encerrado devido a esta regressão da correção. Não alego rejeição efetiva pelo motor Claude, que não foi executado.

### O que não verifiquei

1. App Preact completo e o novo e2e de foco: dependências ausentes; npm test falhou por vitest indisponível. A04 tem confirmação independente no DOM/CSS equivalente, não aceite integral do app, CSP, upload ou leitores de tela.
2. Motor de permissões Claude e interpretação efetiva de comandos: apenas JSONs e correspondência de padrões foram verificados. Não houve instalação, login, merge, push ou mudança de permissão.
3. Falha durante o próprio rollback, crash de processo e duas gravações em processos do sistema: R05 verifica a falha sequencial do evento; R03 verifica a intercalação determinística que reproduz o bloqueador original. Não extrapolo garantias transacionais.
4. Portão integral, build/lint, CI remoto, aprovação visual e execução/sessões reais dos implementadores. O atestado foi lido e os 77 hashes conferidos; suas contagens integrais não foram reexecutadas.
5. Demais critérios/arquivos da etapa, além de A01–A06 e regressões dessas correções: fora do escopo fechado Q85. O parecer anterior não foi revalidado integralmente.
6. Configuração efetiva do modelo/esforço e prova por logs de independência das sessões: não expostas pelas ferramentas desta revisão. A designação humana foi registrada como tal.
7. Integração, publicação, registro de aceite e alterações de produto: não realizados. A conferência final do estado local não mostrou mudanças fora de revisao-saida.

### Veredito fundamentado

**Não aceitar.** A01 e A02 ainda aceitam evidência que deveriam recusar, e A03 ainda permite desligar a emulação com R3 violada. A05 passou nas falhas injetadas; A04 mostrou correção efetiva no DOM/CSS isolado, com a limitação do app declarada; os aliases de A06 foram cobertos, mas a correção trouxe alcance indevido nas duas configurações.

Esta é a reconferência de escopo fechado após a única correção, conforme Q85/Q86. As reversões dos quatro bloqueadores originais demonstram sensibilidade das sondas; três bloqueadores continuam no candidato. Não autorizo nova rodada automática de correção/reconferência nem integração. A decisão seguinte cabe ao fluxo humano da Sociedade.
