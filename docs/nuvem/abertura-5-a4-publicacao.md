# Sessão 5 — etapa `a4-publicacao`

**Siga `docs/nuvem/protocolo-sessao.md`.**

| Campo | Conteúdo |
|---|---|
| Pedido | Linha `a4-publicacao` de `sociedade/nuvem/pedidos.md` |
| Especificação | `docs/onda-1.md`, seções 2, 13, linha `a4` da 15 e 16 |
| Backlog | **B21** (aceite protegido por mutação e teste das seis estações), **B22** (instalação e versões), **B23** (reabrir etapa; HEAD igual à base) |
| Alto impacto (Galadriel) | B21 |
| Revisão | **Reduzida** no app; nela, a lista de conferência dos 10 princípios da seção 2 é obrigatória (Q150) |

**O que esta etapa tem de especial:**

**Publicação (C55).** Na parada 2, cumpridas as condições da N8, peça o **"vai"** de Odival.
- A produção da Vercel sai do ramo `producao` (ver `docs/nuvem/checklist-odival.md`).
- **Quem cria ou atualiza o ramo `producao` a partir da `main` é Odival**, depois do merge. O agente não faz esse push.
- Domínio próprio, se o DNS estiver pronto; senão, o `.vercel.app`.
