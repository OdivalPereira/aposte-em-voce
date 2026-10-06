import { readFileSync } from 'node:fs';
import preact from '@preact/preset-vite';
import { defineConfig } from 'vite';

// Os cabeçalhos de segurança têm uma só fonte: vercel.json.
// O servidor de pré-visualização (usado pelo teste ponta a ponta) os repete,
// para que o teste rode sob a mesma CSP da produção.
function cabecalhosDoVercel(): Record<string, string> {
  const conf = JSON.parse(readFileSync(new URL('./vercel.json', import.meta.url), 'utf8')) as {
    headers: { headers: { key: string; value: string }[] }[];
  };
  const saida: Record<string, string> = {};
  for (const regra of conf.headers) for (const h of regra.headers) saida[h.key] = h.value;
  return saida;
}

export default defineConfig({
  plugins: [preact()],
  build: {
    target: 'es2022',
    sourcemap: false,
    rollupOptions: {
      input: {
        main: new URL('./index.html', import.meta.url).pathname,
        referencia: new URL('./referencia.html', import.meta.url).pathname,
      },
    },
  },
  worker: { format: 'es' },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, headers: cabecalhosDoVercel() },
});
