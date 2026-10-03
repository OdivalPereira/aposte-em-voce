# Contrato: o que é do núcleo e o que é do projeto

O núcleo diz **como** a equipe trabalha. O projeto diz **o quê**, **para quem** e **até onde**. Nada do projeto entra no núcleo, e o projeto não copia o texto do núcleo: aponta para ele.

## Do núcleo (este pacote)

- Acionamento explícito e natural (Q17), precedência e paradas humanas.
- O pipeline de seis estações: pedido, ordem, execução, conferência, revisão e decisão.
- O registro de eventos (`registro.json`), o portão por commit e a conferência automática da ordem.
- Os papéis e seus limites (`sc-papeis`); os executores locais são módulo opcional.
- Como executar: fatias por subagente, Jules em tarefas mecânicas (`sc-execucao`).
- Como revisar: independência por fornecedor, protocolo, severidades, parecer (`sc-revisao`).
- Medição objetiva por script; nenhum agente estima consumo (Q141).

## Do projeto (só isto mora no repositório dele)

| Onde | O quê |
|---|---|
| `AGENTS.md` | Bloco de adoção gerado, stack e estrutura em poucas linhas, comandos de build e teste |
| Perfil (`sociedade/perfil.md` ou equivalente) | Missão, autoridades, papel × ferramenta, executores locais, papéis locais, regras de domínio, limites e paradas |
| `sociedade/registro.json` | Fonte estruturada e transacional de eventos da etapa (SC-E1) |
| `sociedade/estado.md` | Resumo de uma tela, gerado por `sc.py estado` |
| `sociedade/ordens/` | Ordens verificáveis de cada etapa |
| `sociedade/pareceres/` | `atestado-<ID>.json` (`sc.py entregar`) e `parecer-<ID>.md` (`sc.py revisar --parecer`) |
| `sociedade/evolucao.md` | Uma linha por etapa, gravada por `sc.py decidir aceitar` |
| Skills de domínio | Conhecimento que só faz sentido ali. Nome próprio, sem prefixo `sc-` e sem colidir com os papéis |

## Papéis locais

Um projeto **não** cria cópia local de `sc-papeis` nem das skills do núcleo. Ele descreve o que cada papel significa ali numa seção do perfil. Um especialista que só existe naquele projeto entra na mesma seção e, se precisar de método próprio, vira skill de domínio.

## Campos mínimos do perfil

Obrigatórios: **Missão**, **Autoridades**, **Papel × ferramenta**.
Recomendados: **Executores locais** (se houver), **Papéis locais**, **Regras de domínio**, **Limites e paradas**, **Comandos**.
`scripts/validar_perfil.py` confere o mínimo.

## Adoção declarada no `AGENTS.md`

O bloco gerado por `scripts/sc_sync_agents_md.py` é a **única** declaração de adoção:

```
<!-- sociedade-do-codigo:inicio nucleo=3.0.0 perfil=sociedade/perfil.md pasta=sociedade jules=sim sha=... -->
...
<!-- sociedade-do-codigo:fim -->
```

Só o texto entre os marcadores é gerenciado. O `sha` detecta edição manual: o script recusa sobrescrever um bloco alterado sem `--forcar`.

## Versão

- O projeto **fixa** a versão do núcleo no bloco. Atualizar é decisão do projeto: rode `sc_sync_agents_md.py` e leia o `CHANGELOG.md` antes.
- Só o usuário aprova mudança de método. Toda evolução registra, na avaliação, o que deu certo e o que deu errado.
