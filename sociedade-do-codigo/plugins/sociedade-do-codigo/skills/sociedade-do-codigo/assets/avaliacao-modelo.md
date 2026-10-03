# Modelo de Avaliação da Rodada / Etapa

Este documento define o padrão para o arquivo `sociedade/avaliacao.md`, preenchido ao término de cada rodada ou etapa da Sociedade do Código.

---

## 1. Distinção Canônica de Métricas

O método da Sociedade do Código estabelece uma fronteira clara e intransigente entre duas categorias de métricas:

### ❌ Proibição Absoluta da Regra Antitoken (Consumo de IA)
Regra inviolável: nenhum agente deve medir, calcular, estimar ou relatar métricas de IA. É terminantemente proibido:
- Proibido qualquer estimativa ou contagem de tokens (entrada, saída ou raciocínio);
- Proibido calcular ou relatar custos financeiros decorrentes de inferência de inteligência artificial;
- Proibido registrar consumo ou aferir limites percentuais de cotas de APIs de modelos;
- Sem medição de tempo de resposta ou latência de inferência de LLMs.

> **Razão fundamental:** A contabilidade de inferência incentiva atalhos de contexto e degrada o rigor metodológico. A economia do método decorre de sua arquitetura disciplinada (ponteiros cirúrgicos de leitura, fatias provadas, parsers locais e revisão independente), nunca de contabilidade de infraestrutura.

### ✅ Métricas Permitidas e Incentivadas (Eficácia do Processo de Software)
São permitidas e recomendadas métricas objetivas de engenharia de software para avaliação e melhoria contínua do fluxo de trabalho:
- **Fatias entregues vs planejadas:** total de fatias concluídas com prova executada em relação ao plano inicial;
- **Taxa de retrabalho por fatia:** número de ciclos de devolução ou correções necessárias antes da aprovação final;
- **Densidade e severidade de achados:** contagem de apontamentos do Revisor Independente classificados em bloqueador, relevante ou opcional;
- **Taxa de sucesso de tarefas assíncronas:** proporção de tarefas remotas aceitas sem rejeição por quebra de contrato;
- **Aderência à primeira passagem (First-Time-Right):** percentual de fatias aprovadas sem necessidade de retificação;
- **Hipóteses exploradas:** quantidade de hipóteses técnicas conceituais formuladas antes da resolução de defeitos (regra das 3 hipóteses);
- **Atestados determinísticos:** conformidade física comprovada via script de pré-devolução com código de saída zero.

---

## 2. Formulário Padrão (`sociedade/avaliacao.md`)

```markdown
# Avaliação da Etapa: [ID da Etapa]
- **Objetivo da etapa:** [Meta em uma frase]
- **Data de encerramento:** [AAAA-MM-DD]
- **Nível adotado:** [1 | 2 | 3 | adaptativo]
- **Coordenador:** Gandalf
- **Implementadores:** [Lista de especialistas participantes]
- **Revisor Independente:** [Nome do agente revisor e fornecedor]

---

### Eficácia do Processo de Engenharia de Software
| Indicador de Eficácia | Valor Observado | Meta / Referência |
|---|---|---|
| Fatias concluídas com prova executada | X de Y | 100% |
| Taxa de retrabalho (devoluções de fatia) | N devoluções | 0 |
| Achados do Revisor Independente | B bloqueadores / R relevantes / O opcionais | 0 bloqueadores no fechamento |
| Tarefas assíncronas aceitas | N aceitas de M submetidas | >= 80% |
| Fatias aprovadas na primeira passagem (FTR) | N / Total (%) | >= 80% |
| Atestado de pré-devolução físico | Aprovado (código de saída 0) | Compulsório |

---

### Síntese Qualitativa da Rodada
1. **O que deu certo:**
   - [Descrição sucinta de decisões técnicas e práticas que aceleraram o resultado]
2. **O que deu errado ou apresentou atrito:**
   - [Descrição sucinta de gargalos, falhas ou atritos operacionais encontrados]
3. **Retrabalhos e correções:**
   - [Registro de itens que precisaram ser refeitos e o motivo do retrabalho]
4. **O que mudar no método ou nas skills do projeto:**
   - [Sugestões concretas de melhoria em regras, perfis, testes ou scripts]
5. **Observações de infraestrutura e cotas (preenchimento manual exclusivo do usuário):**
   - [Linha reservada para o operador humano anotar percepções manuais de infraestrutura, se desejar. Proibido preenchimento por agentes.]
```
