# Decisões Q146+ — rascunho do lote 1 (03/10/2026)

**Critério (C50):** só entram as respostas que mudam regra do método. As que apenas organizam a sessão em nuvem ficam no registro da entrevista.

**Destino depois de aprovadas:** transcritas no novo `sociedade/decisoes.md` enxuto. A tabela Q01–Q145 vai para `sociedade/arquivo/` (R5).

| Q | Data | Decisão | Origem | Substitui ou ajusta |
|---|---|---|---|---|
| Q146 | 03/10/2026 | A etapa ARR é encerrada **sem aceite**, por exceção registrada; a revisão independente da 3.0.0 não ocorreu. O conserto do ciclo da etapa vai para a sessão em nuvem | P13, C21 | — |
| Q147 | 03/10/2026 | **Modo emulação.** Com a chave `emulacao` no perfil, um único fornecedor pode ocupar todos os papéis. R1–R3 passam a valer como aviso, e o parecer interno do Barbárvore vale como aceite marcado "aceite em emulação", que nunca conta como revisão independente. Recurso permanente do pacote. Na sessão em nuvem, tudo é registrado como Anthropic | C12, C13, C43, C44 | Ajusta D-RT-001 e R1–R3, só com a chave ligada |
| Q148 | 03/10/2026 | **Prova dupla.** A etapa só fecha com o portão local amarrado (árvore limpa, comando e timeout do perfil canônico, testes maior que zero, commit no atestado) **e** o CI verde no mesmo SHA. A `main` protegida (GitHub Pro nos repositórios privados) exige os status `ci`, `portao` e `aceite` | C30, C42, R3, P29 | Ajusta Q67 e Q70 |
| Q149 | 03/10/2026 | **Cauda de governança.** O SHA revisado é o último commit de produto. Commits posteriores que só toquem `sociedade/` entram no mesmo PR e são `sem_alto` automaticamente | C41 | Ajusta Q145 |
| Q150 | 03/10/2026 | **Revisão proporcional ao risco.** Protocolo completo nas etapas de alto impacto; passo 0 e as lentes pertinentes nas triviais. A ordem define qual se aplica | C27 | Ajusta Q126 |
| Q151 | 03/10/2026 | **Ciclo da etapa no `sc.py`** (`abrir`, `decidir`). `sc_rodada`, `sc_passagem`, a calibração e os níveis ficam **deprecados**: saem da skill e dos documentos, mas não são removidos | C28 | Ajusta P16 (sem a remoção) |
| Q152 | 03/10/2026 | **Registro em cadeia de hash, com alerta** no painel quando a cadeia quebra ou diverge do último commit de governança | P15, C29 | — |
| Q153 | 03/10/2026 | **Metas por etapa:** até 12 comandos do método, 0 edições manuais em arquivos de controle, até 5 intervenções e 30 min de Odival. Acima da meta, vira item de correção | C35, C51 | **Substitui a Q89** (3 intervenções por dia) |
| Q154 | 03/10/2026 | **Integrar é o merge do PR, feito por Odival**, com a `main` protegida no servidor | C25, R3 | Detalha Q32 e Q68 |
| Q155 | 03/10/2026 | **Governança enxuta.** Os agentes leem uma página de regras (`regras.md`). Decisões novas só quando mudam regra; o histórico vai para `sociedade/arquivo/` | R5, C38, C50 | Ajusta Q142 (regras vigentes) |
| Q156 | 03/10/2026 | **Adaptador do Claude Code.** Um agente por papel em `.claude/agents/`, com modelo, esforço e ferramentas por papel. A delegação é conferida pelas transcrições dos subagentes (`sc.py sessao claude`) | C10, C14, C19, C34 | Estende Q28 ao Claude |
| Q157 | 03/10/2026 | **Commit amarrado e ordem com hash.** `ordem_aprovada` com SHA-256. O revisor recebe o commit do atestado, sem as instruções do candidato. Commit novo derruba o parecer | P14 | — |
| Q158 | 03/10/2026 | **Substituição declarada do executor.** Quando falta o executor, outro modelo executa, com evento no registro e no painel. O revisor continua de fornecedor diferente, salvo no modo emulação | P18 | Ajusta R3 |
| Q159 | 03/10/2026 | **Revisor indisponível: aceite condicional com salvaguardas.** A etapa fecha e pode ser integrada, mas não publicada (tag ou release) até a revisão chegar. No máximo 1 aceite condicional aberto por vez. Uma rejeição posterior reabre a etapa. O painel mostra a revisão devida e a idade dela | P24, C62 | **Substitui a Q14** |
| Q160 | 03/10/2026 | **A Q135 segue suspensa** até existir calibração do revisor com desenho que decide. Enquanto isso, o aceite vale com o parecer marcado "revisor não calibrado" no registro e no painel | P23, P28, C63 | Suspende a Q135 |
| Q161 | 03/10/2026 | **Delegação em revezamento no adaptador Claude.** No Claude Code, subagente não aciona subagente: o Gandalf escreve as subordens e o Círdan as despacha sem edição aos especialistas, devolvendo os retornos ao Gandalf. Evidência: o `gandalf.md` já tinha a ferramenta Agent e profundidade 3, então o limite é da plataforma; testar de novo se ela mudar | m0-destravar, proposta 1 | Ajusta Q156 |
| Q162 | 03/10/2026 | **Portão por área** (app e pacote) no perfil, na A1 com a B11 | m0-destravar, proposta 2 | — |
| Q163 | 03/10/2026 | **`sociedade/` canônica no worktree da etapa** durante a etapa | m0-destravar, proposta 3 | Ajusta Q60 |
| Q164 | 03/10/2026 | **Ajuste de integração do coordenador:** até 30 linhas de produto por etapa e sem lógica nova; acima disso, vira fatia delegada | m0-destravar, proposta 4 | Detalha Q28 |
| Q165 | 03/10/2026 | **Fatias em paralelo no mesmo worktree:** o especialista não comita; o coordenador comita por fatia e roda o portão num checkout limpo do commit. A base da fatia é o commit anterior a ela | a1-parser, P1 | Detalha Q60 e Q161 |
| Q166 | 03/10/2026 | **`sociedade/` canônica durante a etapa = a do worktree.** O portão ignora `sociedade/` e os arquivos do `.gitignore` na árvore suja; o `decidir` e o status conferem o `perfil_sha256` do atestado contra o perfil do commit julgado | a1-parser, P2 e ajuste 1 | Detalha Q163 |
| Q167 | 03/10/2026 | **Dados de teste com estrutura imitada:** o especialista dono do leitor desenha um layout de referência e o Jules só replica. A tarefa do Jules proíbe derivar o esperado do código sob teste e traz o comando exato | a1-parser, P3 (B13) | Detalha Q48 |
| Q168 | 03/10/2026 | **Linhas de produto contadas por script, por área** (linhas adicionadas sem brancos nem comentários; sem testes, gerador e fixtures) | a1-parser, P4 | Detalha Q87 |
| Q169 | 03/10/2026 | **Telas com referência visual.** Toda tela parte de uma referência visual aprovada por Odival; fatia com tela é sempre do Legolas; o PR traz capturas de cada tela em 360 px como entrega verificável, e a revisão as compara com a referência | a1-parser, P5 (Odival) | — |
