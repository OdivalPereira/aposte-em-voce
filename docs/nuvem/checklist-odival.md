# Checklist de Odival — sessões em nuvem

## Antes da sessão 1

- [ ] **Créditos:** conferir no app o saldo e a **validade**. Se os 90 dias contarem de 19/05/2026, podem já ter vencido. Confirmar que não há **uso extra nem recarga automática**: são só os US$ 100 (N5).
- [ ] **GitHub Pro** assinado (R3), para proteger também a `main` dos repositórios privados.
- [ ] Repositório **`OdivalPereira/aposte-em-voce`** criado e enviado, com a proteção da `main` (o Claude faz com a sua confirmação, na conversa local):
  - PR obrigatório;
  - status obrigatórios `ci`, `portao` e `aceite`;
  - sem force push e sem apagar o ramo.
- [ ] **Claude GitHub App** instalado no `aposte-em-voce`.
- [ ] **Ambiente Cloud** `sociedade-nuvem` criado conforme `docs/nuvem/ambiente.md`.
- [ ] **DG-36 contido** (C54): tratado no projeto de campo privado, conforme a conversa local.

## Antes da sessão 2 (`a1-parser`)

- [ ] **Vercel:** projeto ligado ao `aposte-em-voce` com **pré-visualização por PR**.
- [ ] **Vercel:** em *Settings → Git → Production Branch*, use **`producao`**, para que os merges na `main` **não** publiquem produção antes da A4 (C55).

## Depois da sessão 2

- [ ] Testar **os seus extratos** na pré-visualização, pelo celular, na tela de diagnóstico. Relatar por banco: leu, parcial ou falhou. Colar o relato na abertura da sessão 3 (C45).

## Antes da publicação (sessão 5)

- [ ] **Domínio `.com.br`** registrado no registro.br e apontado para a Vercel (N12).
- [ ] **`contato@<domínio>`** encaminhado para o seu Gmail (N21).
- [ ] No "vai": criar ou atualizar o ramo **`producao`** a partir da `main`. Isso publica.

## Em cada parada

- [ ] **Parada 1:** ler a ordem e responder "aprovo" ou com ajustes.
- [ ] **Parada 2:** ler o estado no chat ou no PR e responder aceitar, corrigir ou rejeitar; depois **fazer o merge** do PR.
- [ ] Conferir o **saldo**. Se chegar a **US$ 10**, avisar a sessão e abrir só a **sessão 6, final** (C60).

## Depois da nuvem (conversa local com o Claude)

- [ ] Devolver a cópia do pacote ao repositório `sociedade-do-codigo` (C40).
- [ ] Instalar a 4.0.0 no Claude Code, no Codex e no Antigravity (C53).
