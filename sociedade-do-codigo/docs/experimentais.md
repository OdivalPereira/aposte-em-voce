# Recursos experimentais

Experimentais, não homologados (Q65). Ficam no pacote, fora do caminho de leitura dos agentes (Q140). Uso em projeto real exige homologação própria.

| Recurso | Onde | O que faz |
|---|---|---|
| Executores locais | `modulos/executores-locais/`; scripts em `sc-execucao/scripts/` | Celebrimbor, Radagast, Faramir e Bilbo: leitura de arquivos, coleta web, auditoria e memória na máquina local |
| Portão do Jules | `sc_jules_portao.py`, `sc_passagem.py despachar-jules` e `auditar-jules` | Conferência local de PRs do Jules e teto de tarefas abertas (padrão 3, Q93) |
| Fatias paralelas | `sc_rodada.py fatia <N> --paralelo --arquivos ...` | Fatias com arquivos disjuntos abertas ao mesmo tempo |
| Calibração do gatilho | `sc_calibrar_gatilho.py`, `sc_rodada.py calibrar` | Avaliação retrospectiva de fatores de rigor a partir de rodadas concluídas |
| Simulação contábil | `tests/fixtures/conciliacao/` | Conciliação fictícia de 35 lançamentos, usada nos testes |

Nenhum deles foi usado numa etapa real até a 3.0.0. O que não for usado em três etapas reais é candidato a sair do pacote.
