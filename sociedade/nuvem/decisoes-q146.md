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
