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
| Arquiteto | Círdan | Claude Code | Anthropic | Claude Opus 5.5 | high | ativo | 2026-10-03 | formação real: fim da emulação em nuvem (andamento, C53) |
| Revisor Independente | Barbárvore | Codex | OpenAI | GPT-6 Sol | xhigh | ativo | 2026-10-03 | formação real: fim da emulação em nuvem (andamento, C53); revisor não calibrado (Q160) |
| Coordenador | Gandalf | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real: fim da emulação em nuvem (andamento, C53) |
| Coleta e procedência | Aragorn | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real (andamento, C53); edição manual: `papel trocar --papel execucao` não alterou esta linha (lacuna L2, corrigida na d1) |
| Dados e persistência | Elrond | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real (andamento, C53); edição manual: `papel trocar --papel execucao` não alterou esta linha (lacuna L2, corrigida na d1) |
| Métodos e qualidade | Galadriel | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real (andamento, C53); edição manual: `papel trocar --papel execucao` não alterou esta linha (lacuna L2, corrigida na d1) |
| Interface e acessibilidade | Legolas | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real (andamento, C53); edição manual: `papel trocar --papel execucao` não alterou esta linha (lacuna L2, corrigida na d1) |
| Executor júnior em nuvem | Jules | Jules | Google | a definir | padrão | espera | 2026-10-03 | formação real; sem uso na d1; ocupante a confirmar por Odival (lacuna L2) |
| Executores locais | Celebrimbor, Radagast, Faramir, Bilbo | máquina local | nenhum | nenhum | padrão | espera | 2026-10-03 | formação real; sem modelo local (lacuna L2) |

## Modo emulação (Q147)
- **Emulação:** não. Desligada em 03/10/2026, na abertura da d1-design, com a volta à formação real (andamento, C53). Edição manual, porque ainda não há comando (lacuna L1, corrigida na própria d1).
- Com a emulação desligada, R1–R3 valem em modo estrito, e o parecer do Barbárvore conta como revisão independente quando o fornecedor dele for diferente do de todos os implementadores (D-RT-001).
- A chave é lida pelos scripts (`sc_perfil.emulacao_ligada`): vale só a linha `- **Emulação:**` desta seção.

## Equipe ativa
*Definição de papéis ativos no projeto (Q95). Papéis inativos não são carregados nem citados nas passagens.*

- **Papéis ativos:** Círdan, Barbárvore, Gandalf, Aragorn, Elrond, Galadriel, Legolas
- **Papéis em espera:** Jules e executores locais (sem uso na d1; ocupante a confirmar por Odival)

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
- Merge na `main` só com o "sim" de Odival na conversa, sempre como merge commit (Q174). Publicação em produção (Vercel) só com o "vai" de Odival (C55).
- Sem conectores MCP, credenciais nem contratação de serviços na sessão.
- Nenhum agente estima consumo; medir pelo log é permitido (`sc.py sessao`, Q170). Odival confere o saldo nas paradas.
- Treinamento: desligado no Claude (Q120).

## Comandos
- Build: `npm run build`
- Testes: `npm test`
- Lint e tipos: `npm run lint`

## Portão por área
*Lida pelo `sc.py entregar` (B11, B11c). Comando e timeout só daqui; `--comando-teste` é recusado. A área de um caminho é a do prefixo mais longo; `.github/` conta para as duas; `sociedade/` e `docs/` não são de área nenhuma.*

| Área | Pasta | Testes | Timeout (s) | Prefixos |
|---|---|---|---|---|
| app | `.` | `npm test` | 900 | `*` (tudo fora de `sociedade-do-codigo/`, `sociedade/` e `docs/`) |
| pacote | `sociedade-do-codigo` | `python3 -B -m unittest discover -s tests` | 600 | `sociedade-do-codigo/` |

## Estado
- Fonte dos eventos: `sociedade/registro.json` (só scripts gravam)
- Resumo de uma tela: `sociedade/estado.md` (gerado por `sc.py estado`)
- Ordens: `sociedade/ordens/`
- Pareceres e atestados: `sociedade/pareceres/`
