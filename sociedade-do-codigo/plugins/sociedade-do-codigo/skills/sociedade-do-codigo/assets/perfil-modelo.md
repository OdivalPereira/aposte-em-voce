# Perfil de <Projeto>

O método vem do núcleo indicado no `AGENTS.md`. Este perfil traz só o que é deste projeto. Apague as linhas em itálico ao preencher.

## Missão
*Uma ou duas frases: para quem o projeto existe e qual resultado importa.*

## Autoridades
- **Decide escopo, prioridade e publicação:** <pessoa>
- **Decide gasto adicional:** <pessoa>
- **Arquiteto (planeja, escreve ordens, organiza o contexto):** <nome do papel e ferramenta>

## Papel × ferramenta
*Quem ocupa cada papel aqui. Cada perfil ativa só os necessários (Q95). Troque o ocupante com `sc_rodada.py papel trocar`, que confere R1 a R4. Rótulos de papel reconhecidos: Arquiteto, Revisor Independente, Coordenador e os das especialidades abaixo.*

| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | planejamento e arbitragem |
| Revisor Independente | Barbárvore | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | revisão independente |
| Coordenador | Gandalf | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | coordenação e integração |
| Coleta e procedência | Aragorn | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | especialidade de coleta |
| Dados e persistência | Elrond | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | especialidade de dados |
| Métodos e qualidade | Galadriel | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | especialidade de métodos |
| Interface e acessibilidade | Legolas | <plataforma> | <fornecedor> | <modelo> | <esforço> | ativo | <data> | especialidade de interface |
| Executor júnior em nuvem | Jules | <plataforma> | <fornecedor> | <modelo> | <esforço> | reserva | <data> | tarefas mecânicas isoladas |
| Executores locais | <nomes> | <plataforma> | <fornecedor> | <modelo> | <esforço> | espera | <data> | sob demanda |

## Equipe ativa
*Definição de papéis ativos no projeto (Q95). Papéis inativos não são carregados nem citados nas passagens.*

- **Papéis ativos:** <papéis ativos no projeto>
- **Papéis em reserva:** <papéis em reserva, ex.: Jules>
- **Papéis em espera:** <papéis em espera, ex.: executores locais>

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

- **Máquina:** <resultado de `inventario_local.py`>
- **Modelo local:** <tag, ou "nenhum">
- **Teto de recursos:** <threads e memória>; tentativas antes de escalar: <3 por padrão>
- **Limite de payload:** <50 linhas ou 2.000 tokens, por padrão>

| Papel | Comando | Pasta de saída | Escreve código próprio em |
|---|---|---|---|
| Celebrimbor | `<comando>` | `<pasta>` | `<pasta autorizada ou "não">` |
| Radagast | `<comando>` | `<pasta>` | `<pasta autorizada ou "não">` |
| Faramir | `<comando>` | `<pasta>` | não |
| Bilbo | `<comando>` | `<pasta>` | não |

## Papéis locais
*O que cada papel significa neste projeto, em 3 a 6 linhas. Papéis exclusivos do projeto entram aqui, com função e limites. Não crie cópia local das skills do núcleo.*

## Regras de domínio
*Regras de negócio, leiautes, formatos, cálculos. Se forem longas, aponte o arquivo ou a skill de domínio que as contém.*

## Limites e paradas
*O que exige confirmação humana além das paradas do núcleo. Aqui também: o que nunca pode ir para prompt de modelo em nuvem (dado pessoal, dado de cliente, documento de terceiro) e, por plataforma, se o uso das conversas para treinamento está desligado.*

## Comandos
- Build: `<comando>`
- Testes: `<comando>`
- Lint e tipos: `<comando>`

## Estado
- Fonte dos eventos: `sociedade/registro.json` (só scripts gravam)
- Resumo de uma tela: `sociedade/estado.md` (gerado por `sc.py estado`)
- Ordens: `sociedade/ordens/`
- Pareceres e atestados: `sociedade/pareceres/`
