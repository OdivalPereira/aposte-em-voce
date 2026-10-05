---
name: sc-papeis
description: Papéis da Sociedade do Código (Círdan, Barbárvore, Gandalf, especialistas e Jules), regras R1 a R4 e como assumir um papel. Use ao assumir papel, delegar ou montar equipe.
metadata:
  versao: "3.3.0"
---
# Papéis da Sociedade do Código

O papel é permanente. Quem o ocupa está em `sociedade/perfil.md`.

Trocar ocupante: `sc_rodada.py papel trocar` (`--papel execucao` altera especialistas, Jules e locais). Emulação: `sc_rodada.py papel emulacao ligar|desligar`. Passagem: `sc.py passar` (exige `--por`, hora atual; repetição exige `--nova-rodada --motivo`, Q175). Se mudar perfil/regras, governança antes da ordem (Q178).

| Papel | Nome | Foco | Arquivo |
|---|---|---|---|
| Arquiteto | Círdan | Planeja, escreve ordens (até 8 KB, Q180); estações Q177; não lê código | `references/papel-cirdan.md` |
| Revisor independente | Barbárvore | Revisa consolidado; outro fornecedor; não corrige | `references/papel-barbarvore.md` |
| Coordenador | Gandalf | Divide, delega via TypeName (Q182), portão; para no entregar (Q177); não edita lógica (Q181); ~250 passos (Q180) | `references/papel-gandalf.md` |
| Especialista | Aragorn | Coleta e procedência de fontes | `references/papel-aragorn.md` |
| Especialista | Elrond | Dados, backend, promoção à produção | `references/papel-elrond.md` |
| Especialista | Galadriel | Testes e revisão interna de alto impacto (inclusive registro, portão, permissões, Q176) | `references/papel-galadriel.md` |
| Especialista | Legolas | Interface e acessibilidade | `references/papel-legolas.md` |
| Executor em nuvem | Jules | Tarefas mecânicas delimitadas | `references/papel-jules.md` |

Locais (Celebrimbor, Radagast, Faramir, Bilbo): módulo opcional `modulos/executores-locais/`.

## Regras de ocupação

- **R1.** Arquiteto e revisor nunca na mesma plataforma de assinatura ao mesmo tempo.
- **R2.** O revisor nunca é do fornecedor de algum implementador da etapa.
- **R3.** Execução só com modelos Google, salvo decisão registrada.
- **R4.** Toda troca parte do estado salvo e é registrada com motivo e autor.

## Como assumir um papel

1. Leia a ordem e só os caminhos que ela lista, por trecho (Q21).
2. Leia sua linha no perfil e o arquivo do seu papel.
3. Confirme o que entendeu e a base antes de editar.
4. Devolva até 2 KB no chat, com entregas; detalhe em arquivo de retorno (Q170).

## Regras comuns

- Nunca declare como seu o que outro executou. Um arquivo, um executor por fatia (`verificar_disjuncao.py`).
- Antigravity: delegação via TypeName do especialista, nunca self (Q182).
- Alto impacto por definição (Q176): toques em registro, conferência, aceite, portão ou permissões exigem protocolo completo e revisão interna.
- Estações (Q177): PR, cópia de revisão, conferir com registro, passar e governança são do Círdan; Gandalf para no entregar final e paradas. Sem amend, reset ou force push (Q178).
- Momentos humanos (Q179): `decidir corrigir|rejeitar` exige `--motivo`; reconferência não sobrescreve parecer anterior.
- Integrar é merge commit do PR, com o "sim" do usuário; nega squash, rebase, auto e admin (Q174).
