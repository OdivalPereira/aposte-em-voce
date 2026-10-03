import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist/', 'node_modules/', 'coverage/', 'test-results/', 'playwright-report/', 'sociedade-do-codigo/'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      // Nada de armazenamento no aparelho (princípio 2) e nada de rede fora dos arquivos estáticos (princípio 1).
      'no-restricted-globals': ['error', 'localStorage', 'sessionStorage', 'indexedDB', 'XMLHttpRequest', 'fetch'],
      'no-restricted-properties': [
        'error',
        { object: 'document', property: 'cookie', message: 'Sem cookies (princípio 2).' },
        { object: 'window', property: 'localStorage', message: 'Sem localStorage (princípio 2).' },
        { object: 'navigator', property: 'sendBeacon', message: 'Nada sai do aparelho (princípio 1).' },
      ],
    },
  },
  { files: ['tests/**/*.ts', '*.config.ts', 'scripts/**/*.ts'], rules: { 'no-restricted-globals': 'off', 'no-restricted-properties': 'off' } },
);
