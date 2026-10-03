# Ambiente Cloud `sociedade-nuvem` (Odival configura no app)

Configuração em **claude.ai/code → ambientes**, conferida na documentação em 03/10/2026. Não ponha segredo em variável nem no script, porque quem usa o ambiente lê os dois.

## Rede

**Custom**, com a opção **"Also include default list of common package managers"** marcada, mais estes domínios:

```text
*.gov.br
cvv.org.br
cdn.playwright.dev
playwright.download.prss.microsoft.com
playwright.azureedge.net
```

- `*.gov.br`: listas da Fazenda, Ministério da Saúde, autoexclusão, Planalto e conferência de links (Aragorn).
- Os servidores do Playwright: baixar o Chromium dos testes de ponta a ponta.
- GitHub passa por um proxy próprio e não precisa entrar na lista.

## Variáveis de ambiente

```dotenv
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
BASH_DEFAULT_TIMEOUT_MS=600000
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=3
```

- `BASH_DEFAULT_TIMEOUT_MS`: a suíte e o Playwright podem passar de 2 min.
- `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`: Círdan → Gandalf → especialista → Jules (o padrão já é 3; aqui fica explícito).

## Script de preparo

Termina em menos de 5 min, para entrar no cache, e sai com código 0:

```bash
#!/bin/bash
set -u
python3 --version
node --version
git --version
# Bibliotecas de sistema do Chromium para o Playwright (o navegador é baixado na sessão, na versão do projeto)
npx --yes playwright@latest install-deps chromium >/dev/null 2>&1 || true
echo "preparo ok"
```

## Na abertura de cada sessão

- **Repositório:** só o `OdivalPereira/aposte-em-voce`. Um repositório por sessão; com vários, as travas do `.claude/settings.json` deixam de valer.
- **Modelo:** Claude Opus 5.5. **Esforço:** high. **Fast mode:** desligado.
- **Modo de permissão:** o mais autônomo disponível. As regras `deny` do repositório continuam valendo.
- **Mensagem de abertura:** cole só uma linha:
  > Aciono a Sociedade do Código. Você é o Círdan. Siga `docs/nuvem/abertura-<N>-<etapa>.md`.
