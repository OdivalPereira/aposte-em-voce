# Perfil de Aposte em Você

O método vem do núcleo indicado no `AGENTS.md`. Este perfil traz só o que é deste projeto.

## Missão
Site gratuito, aberto por link no celular, que ajuda adultos afetados por apostas a organizar o impacto financeiro e buscar ajuda, sem que nada saia do aparelho.

## Autoridades
- **Decide escopo, prioridade e publicação:** Odival
- **Decide gasto adicional:** Odival
- **Arquiteto (planeja, escreve ordens, organiza o contexto):** Círdan (ver tabela abaixo)

## Papel × ferramenta
*Quem ocupa cada papel aqui. Cada perfil ativa só os necessários (Q95). Troque o ocupante com `sc_rodada.py papel trocar`, que confere R1 a R4. Rótulos de papel reconhecidos: Arquiteto, Revisor Independente, Coordenador e os das especialidades abaixo.*

| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code (nuvem) | Anthropic | Claude Opus 5.5 | high | ativo | 2026-10-03 | sessão principal; emulação (Q147, C09) |
| Revisor Independente | Barbárvore | Claude Code (nuvem) | Anthropic | Claude Opus 5.5 | xhigh (completa) / high (reduzida) | ativo | 2026-10-03 | subagente isolado; emulação do GPT-6 Sol (C12, C27, C34) |
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Claude Sonnet 5.5 | high | ativo | 2026-10-03 | subagente por ordem; emulação do Gemini (C11) |
| Coleta e procedência | Aragorn | Claude Code (nuvem) | Anthropic | Claude Sonnet 5.5 | high | ativo | 2026-10-03 | subagente do Gandalf; emulação |
| Dados e persistência | Elrond | Claude Code (nuvem) | Anthropic | Claude Sonnet 5.5 | high | ativo | 2026-10-03 | subagente do Gandalf; emulação |
| Métodos e qualidade | Galadriel | Claude Code (nuvem) | Anthropic | Claude Sonnet 5.5 | high | ativo | 2026-10-03 | subagente do Gandalf; revisão interna de alto impacto (C17) |
| Interface e acessibilidade | Legolas | Claude Code (nuvem) | Anthropic | Claude Sonnet 5.5 | high | ativo | 2026-10-03 | subagente do Gandalf; emulação |
| Executor júnior em nuvem | Jules | Claude Code (nuvem) | Anthropic | Claude Haiku 4.5 | padrão | ativo | 2026-10-03 | subagente em segundo plano; emulação do Jules (C15) |
| Executores locais | Celebrimbor, Radagast, Faramir, Bilbo | Claude Code (nuvem) | Anthropic | Claude Haiku 4.5 | padrão | reserva | 2026-10-03 | uma fatia mecânica emulada (C16) |

## Modo emulação (Q147)
- **Emulação:** sim. Nesta sessão em nuvem, um só fornecedor (Anthropic) ocupa todos os papéis (R6, C12).
- O registro declara Anthropic em tudo. R1–R3 valem como aviso. O parecer do Barbárvore vale como aceite marcado "aceite em emulação", que nunca conta como revisão independente (D-RT-001).
- *O mecanismo (chave lida pelos scripts) é criado na etapa m0-destravar (backlog B02). Até lá, esta seção é a declaração.*
- Adaptador: um agente por papel em `.claude/agents/` (Q156).

## Equipe ativa
*Definição de papéis ativos no projeto (Q95). Papéis inativos não são carregados nem citados nas passagens.*

- **Papéis ativos:** Círdan, Barbárvore, Gandalf, Aragorn, Elrond, Galadriel, Legolas
- **Papéis ativos também:** Jules (C15)
- **Papéis em reserva:** executores locais (uma fatia emulada, C16)

## Identificadores de agente
*Identificadores canônicos para conferência de auto-revisão (A2-P08). Nomes, variantes e identificadores que correspondem à mesma entidade para evitar auto-revisão disfarçada.*

| Identificador | Papel | Nome | Variantes reconhecidas |
|---|---|---|---|
| cirdan | Arquiteto | Círdan | cirdan, cirdan-arquiteto, cirdan_architect |
| barbarvore | Revisor Independente | Barbárvore | barbarvore, barbarvore_reviewer, barbarvore2, barbarvore-revisor |
| gandalf | Coordenador | Gandalf | gandalf, gandalf_reviewer, gandalf2, gandalfrevisor, gandalf_coord |
| aragorn | Coleta e procedência | Aragorn | aragorn, aragorn_dev |
| elrond | Dados e persistência | Elrond | elrond, elrond_dev |
| galadriel | Métodos e qualidade | Galadriel | galadriel, galadriel_qa |
| legolas | Interface e acessibilidade | Legolas | legolas, legolas_ui |
| jules | Executor júnior em nuvem | Jules | jules, jules_agent |

## Conectores por papel
*Nas etapas de desenvolvimento nenhum agente alcança a produção (Q109). Conectores ativos declarados por papel.*

| Papel | Conectores autorizados | Ambiente |
|---|---|---|
| Arquiteto | nenhum conector de dados | isolado |
| Revisor Independente | nenhum conector de dados | isolado |
| Coordenador | git push autorizado | desenvolvimento |
| Especialistas (Aragorn, Elrond, Galadriel, Legolas) | ambiente local de desenvolvimento | desenvolvimento |
| Executor júnior em nuvem (Jules) | ambiente de execução em nuvem isolado | isolado |
| Executores locais (Celebrimbor, Radagast, Faramir, Bilbo) | máquina local, sem rede externa | local |

## Executores locais
*Módulo opcional (`modulos/executores-locais/` do pacote). Só se o projeto os usa. Um lugar único para máquina, modelo e comandos, para não divergir entre arquivos. Nada de segredo aqui.*

- **Máquina:** a definir (rode inventario_local.py)
- **Modelo local:** nenhum
- **Teto de recursos:** padrão; tentativas antes de escalar: 3
- **Limite de payload:** 50 linhas

| Papel | Comando | Pasta de saída | Escreve código próprio em |
|---|---|---|---|
| Celebrimbor | `nenhum` | `sociedade/saida` | não |
| Radagast | `nenhum` | `sociedade/saida` | não |
| Faramir | `nenhum` | `sociedade/saida` | não |
| Bilbo | `nenhum` | `sociedade/saida` | não |

## Papéis locais
*O que cada papel significa neste projeto, em 3 a 6 linhas. Papéis exclusivos do projeto entram aqui, com função e limites. Não crie cópia local das skills do núcleo.*

## Regras de domínio
Stack: TypeScript, Vite, Preact, PDF.js e pdf-lib; site estático na Vercel. Especificação: `docs/onda-1.md`, com os 10 princípios da seção 2. Regras do método: `sociedade/regras.md`. Backlog do método: `sociedade/nuvem/backlog.md`.

## Limites e paradas
- Só dados sintéticos no desenvolvimento. Extrato real nunca entra no repositório nem em prompt (Q24, Q57). Odival testa os extratos dele só no celular, na pré-visualização (N10).
- Merge na `main` e publicação em produção (Vercel) só com o "vai" de Odival (Q154, C55).
- Sem conectores MCP, credenciais nem contratação de serviços na sessão.
- O agente nunca estima nem relata consumo. Odival confere o saldo nas paradas; com US$ 10 de saldo, só roda a sessão final (C59, C60).
- Treinamento: desligado no Claude (Q120).

## Comandos
- Build: `npm run build`
- Testes: `npm test`
- Lint e tipos: `npm run lint`

## Estado
- Fonte dos eventos: `sociedade/registro.json` (só scripts gravam)
- Resumo de uma tela: `sociedade/estado.md` (gerado por `sc.py estado`)
- Ordens: `sociedade/ordens/`
- Pareceres e atestados: `sociedade/pareceres/`
