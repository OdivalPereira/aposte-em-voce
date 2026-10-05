# Retorno da Subordem d1b-robustez · F6 (Textos, regras e modelos)

**Especialista:** Galadriel (métodos e qualidade)  
**Etapa:** d1b-robustez · Fatia 6  
**Data:** 05/10/2026  
**Status:** Concluído com sucesso (aceite atendido)

---

## 1. O que foi feito

Atualização dos textos do método, modelos de adaptador/ordem e documentação das skills para refletir as decisões Q176–Q181, Q182 e os novos comportamentos dos comandos da F4 (`sc.py passar`, `revisar`, `decidir`), respeitando rigorosamente os limites estritos de bytes do pacote (`validar_pacote.py`):

1. **Q176 (Alto impacto por definição):**
   - Documentado que fatias que tocam registro, conferência, aceite, portão ou permissões exigem protocolo completo e revisão interna.
   - Refletido em `sociedade-do-codigo/SKILL.md`, `sc-execucao/SKILL.md`, `sc-papeis/SKILL.md` e `sc-revisao/SKILL.md`.

2. **Q177 (Estações do Círdan vs onde Gandalf para):**
   - Documentado que PR, `conferir --registrar`, cópia de revisão (`revisar`), `passar` e commits de governança são estações do Círdan (`CLAUDE.md`, `CLAUDE.md.modelo`, `sociedade-do-codigo/SKILL.md`, `sc-papeis/SKILL.md`).
   - Documentado onde o Gandalf para: no `entregar` final e paradas da ordem; Gandalf não faz PR, cópia de revisão nem governança (`sc-execucao/SKILL.md`, `ordem-modelo.md`).

3. **Q178 (Governança no início e integridade do worktree):**
   - Documentado que mudanças de perfil ou regras exigem commit de governança antes do despacho da ordem.
   - Documentado que `sc.py revisar` recusa preparar a cópia se `sociedade/perfil.md` ou `sociedade/regras.md` diferirem do HEAD.
   - Documentada a proibição de `git commit --amend`, `git reset` e `git push --force` no ramo de etapa (erros se corrigem com novo commit).

4. **Q179 (Momentos humanos registrados):**
   - Documentado que `sc.py decidir` exige `--motivo` obrigatório para `corrigir` e `rejeitar`.
   - Documentado que a reconferência em `sc.py revisar --parecer` grava `parecer-<etapa>-reconferencia.md` sem sobrescrever o primeiro parecer.

5. **Q180 (Conversas curtas e tetos de dimensão):**
   - Teto de cerca de 250 passos por rodada para Gandalf.
   - Teto de até 8 KB e uma única natureza por ordem, explicitado no modelo `ordem-modelo.md`.
   - Devolução de até 2 KB no chat com detalhe em arquivo de retorno.

6. **Q181 (Coordenador não edita lógica de produto):**
   - Gandalf escreve apenas estado, subordens e ajuste de integração até 30 linhas de produto por etapa sem lógica nova; depuração cabe aos especialistas.

7. **Q182 (Delegação no Antigravity):**
   - Delegação no Antigravity utiliza o agente instalado com o `TypeName` do especialista (`aragorn`, `elrond`, `galadriel`, `legolas`), nunca `self`.

8. **Comandos da F4 descritos:**
   - `sc.py passar`: exige `--por` (sem autor padrão), hora atual gravada no evento, `--nova-rodada --motivo` para repetição de destino.
   - `sc.py revisar`: recusa cópia se perfil/regras diferirem do HEAD; prepara cópia com dependências e testes sem rede.
   - `sc.py decidir`: exige `--motivo` para `corrigir` e `rejeitar`; segundo parecer grava `parecer-<etapa>-reconferencia.md`.

9. **Modelo de ordem (`ordem-modelo.md`):**
   - Incluída a seção `## Onde o Gandalf para`.
   - Explicitado o teto de 8 KB e uma única natureza em `## Paradas`.

---

## 2. Arquivos alterados

Exatamente os 7 arquivos do "Escreva só":
- `CLAUDE.md`
- `sociedade-do-codigo/adapters/claude/CLAUDE.md.modelo`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/SKILL.md`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sc-execucao/SKILL.md`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sc-papeis/SKILL.md`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sc-revisao/SKILL.md`
- `sociedade-do-codigo/plugins/sociedade-do-codigo/skills/sociedade-do-codigo/assets/ordem-modelo.md`

Nenhum arquivo fora da lista foi alterado.

---

## 3. Saída dos testes dirigidos

1. `python3 -B sociedade-do-codigo/scripts/validar_pacote.py`:
   - Código de saída: `0`
   - Saída: `pacote válido`
   - Carga do coordenador: 12.158 bytes (limite: 12.288 bytes)
   - Total Markdown das skills: 59.434 bytes (limite: 60.000 bytes)
   - SKILL.md individuais: todos < 6.000 bytes.

2. `python3 -B -m unittest discover -s sociedade-do-codigo/tests`:
   - Código de saída: `0`
   - Saída: `Ran 818 tests in 83.100s. OK (skipped=1, expected failures=5)`

---

## 4. O que não foi verificado

- Não foram executados testes fora de `sociedade-do-codigo/tests`.
- Não foi feita alteração de versão no pacote nem CHANGELOG (atribuição da fatia de Integração pelo Gandalf).
- Não foi feito commit nem push (vedado pelas regras da fatia).
