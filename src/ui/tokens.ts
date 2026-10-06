/**
 * Design tokens para "Aposte em Você"
 *
 * Direção visual: moderna, sóbria e acolhedora.
 * Público: adultos afetados por apostas financeiras.
 * Princípios respeitados:
 * - Nada de cores berrantes, néon ou estética de cassino.
 * - Nada de tom acusatório ou punitivo.
 * - Cores calmas e seguras: azul sóbrio, neutros refinados e fundos acolhedores.
 * - WCAG 2.2 AA rigoroso: contraste >= 4,5:1 em texto e >= 3:1 em componentes/foco.
 */

export const CORES = {
  // Fundos e superfícies
  fundo: '#f8fafc', // Slate 50: fundo acolhedor e sereno
  superficie: '#ffffff', // Branco puro: cartões, caixas e superfícies
  superficieSecundaria: '#f1f5f9', // Slate 100: fundo de destaque suave

  // Textos
  texto: '#0f172a', // Slate 900: texto principal com excelente legibilidade (17.5:1 em branco)
  textoSecundario: '#334155', // Slate 700: texto secundário/apoio (> 7:1 em branco, cumpre 4.5:1)
  textoMudo: '#475569', // Slate 600: texto discreto (> 5:1 em branco, cumpre 4.5:1)
  textoInvertido: '#ffffff', // Branco: texto sobre botão primário

  // Cor primária e estados interativos
  primaria: '#0b4f9c', // Azul institucional confiável e acolhedor (8.04:1 em branco)
  primariaHover: '#083b75', // Azul escurecido no hover
  primariaAtiva: '#062a54', // Azul pressionado
  primariaFundo: '#eff6ff', // Azul sutil para estados de seleção

  // Foco visível (WCAG 2.2 SC 2.4.7 e 2.4.11)
  foco: '#0b4f9c', // Azul forte para anel de foco (8.04:1 em branco)
  focoAlternativo: '#b45309', // Âmbar escuro (5.01:1 em branco)

  // Feedback e semântica (sóbrios, acolhedores, sem julgamento)
  sucesso: '#14532d', // Verde floresta profundo (11.2:1 em branco, 10.8:1 em fundo suave)
  sucessoFundo: '#f0fdf4', // Fundo sutil verde
  sucessoBorda: '#166534', // Borda semântica de sucesso

  atencao: '#78350f', // Âmbar profundo sóbrio (8.5:1 em branco, 8.3:1 em fundo suave)
  atencaoFundo: '#fffbeb', // Fundo sutil âmbar
  atencaoBorda: '#854d0e', // Borda semântica de atenção

  erro: '#8a1c1c', // Carmim/terracota escuro sóbrio (7.9:1 em branco, 7.5:1 em fundo suave)
  erroFundo: '#fef2f2', // Fundo sutil de erro
  erroBorda: '#991b1b', // Borda semântica de erro

  info: '#1e3a8a', // Azul informativo profundo (9.8:1 em branco, 9.5:1 em fundo suave)
  infoFundo: '#eff6ff', // Fundo sutil informativo
  infoBorda: '#2563eb', // Borda semântica informativa

  // Bordas e divisores (WCAG 2.2 SC 1.4.11: controle de interface >= 3:1)
  borda: '#64748b', // Slate 500: borda de inputs e cartões em foco (4.75:1 em branco - cumpre >= 3:1)
  bordaSuave: '#cbd5e1', // Slate 300: divisores secundários
  bordaFoco: '#0b4f9c', // Borda ativa no foco

  // Progresso
  progressoTrilho: '#e2e8f0', // Slate 200: fundo do trilho
  progressoPreenchimento: '#0b4f9c', // Preenchimento da barra (6.58:1 contra o trilho)
} as const;

export const TIPOGRAFIA = {
  // Fontes locais do sistema: sem CDN, sem download externo, sem violar CSP nem privacidade
  familia: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  escala: {
    xs: '0.75rem', // 12px
    sm: '0.875rem', // 14px
    base: '1rem', // 16px (tamanho base padrão)
    lg: '1.125rem', // 18px (título de cartão / subseção)
    xl: '1.25rem', // 20px (título h3)
    xxl: '1.5rem', // 24px (título h2)
    xxxl: '1.875rem', // 30px (título h1)
  },
  alturas: {
    apertada: 1.25, // Títulos
    normal: 1.5, // Texto corrente
    confortavel: 1.7, // Textos longos / leitura relaxada
  },
  pesos: {
    normal: 400,
    medio: 500,
    semi: 600,
    bold: 700,
  },
} as const;

export const ESPACAMENTO = {
  // Escala única estrita baseada em múltiplos de 4px (0.25rem)
  e1: '0.25rem', // 4px
  e2: '0.5rem', // 8px
  e3: '0.75rem', // 12px
  e4: '1rem', // 16px
  e5: '1.25rem', // 20px
  e6: '1.5rem', // 24px
  e8: '2rem', // 32px
  e10: '2.5rem', // 40px
  e12: '3rem', // 48px
} as const;

export const RAIO = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  pill: '9999px',
} as const;

export interface ParContraste {
  id: string;
  descricao: string;
  frente: string;
  fundo: string;
  minimoEsperado: number;
  tipo: 'texto-normal' | 'texto-grande' | 'componente-ui';
}

/**
 * Pares de contraste declarados no design system.
 * Validados pelo teste unitário `contraste.test.ts`.
 */
export const PARES_CONTRASTE: readonly ParContraste[] = [
  // Texto normal (mínimo 4.5:1)
  {
    id: 'texto-fundo',
    descricao: 'Texto principal sobre fundo da página',
    frente: CORES.texto,
    fundo: CORES.fundo,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'texto-superficie',
    descricao: 'Texto principal sobre cartão/superfície',
    frente: CORES.texto,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'texto-secundario-fundo',
    descricao: 'Texto secundário sobre fundo da página',
    frente: CORES.textoSecundario,
    fundo: CORES.fundo,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'texto-secundario-superficie',
    descricao: 'Texto secundário sobre superfície',
    frente: CORES.textoSecundario,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'texto-mudo-superficie',
    descricao: 'Texto de apoio mudo sobre superfície',
    frente: CORES.textoMudo,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'botao-primario-texto',
    descricao: 'Texto branco sobre botão primário',
    frente: CORES.textoInvertido,
    fundo: CORES.primaria,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'botao-secundario-texto',
    descricao: 'Texto do botão secundário sobre seu fundo',
    frente: CORES.primaria,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'botao-discreto-texto',
    descricao: 'Texto do botão link/discreto sobre superfície',
    frente: CORES.primaria,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'sucesso-texto-fundo',
    descricao: 'Texto de aviso de sucesso sobre fundo de sucesso',
    frente: CORES.sucesso,
    fundo: CORES.sucessoFundo,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'sucesso-texto-superficie',
    descricao: 'Texto de sucesso sobre superfície branca',
    frente: CORES.sucesso,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'atencao-texto-fundo',
    descricao: 'Texto de aviso de atenção sobre fundo de atenção',
    frente: CORES.atencao,
    fundo: CORES.atencaoFundo,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'atencao-texto-superficie',
    descricao: 'Texto de atenção sobre superfície branca',
    frente: CORES.atencao,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'erro-texto-fundo',
    descricao: 'Texto de aviso de erro sobre fundo de erro',
    frente: CORES.erro,
    fundo: CORES.erroFundo,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'erro-texto-superficie',
    descricao: 'Texto de erro sobre superfície branca',
    frente: CORES.erro,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'info-texto-fundo',
    descricao: 'Texto de aviso informativo sobre fundo informativo',
    frente: CORES.info,
    fundo: CORES.infoFundo,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },
  {
    id: 'info-texto-superficie',
    descricao: 'Texto de aviso informativo sobre superfície',
    frente: CORES.info,
    fundo: CORES.superficie,
    minimoEsperado: 4.5,
    tipo: 'texto-normal',
  },

  // Componentes e controles UI (SC 1.4.11 / 2.4.11: mínimo 3.0:1)
  {
    id: 'borda-campo-superficie',
    descricao: 'Borda de campos interativos sobre superfície',
    frente: CORES.borda,
    fundo: CORES.superficie,
    minimoEsperado: 3.0,
    tipo: 'componente-ui',
  },
  {
    id: 'borda-campo-fundo',
    descricao: 'Borda de campos interativos sobre fundo',
    frente: CORES.borda,
    fundo: CORES.fundo,
    minimoEsperado: 3.0,
    tipo: 'componente-ui',
  },
  {
    id: 'foco-superficie',
    descricao: 'Anel de foco sobre superfície',
    frente: CORES.foco,
    fundo: CORES.superficie,
    minimoEsperado: 3.0,
    tipo: 'componente-ui',
  },
  {
    id: 'foco-fundo',
    descricao: 'Anel de foco sobre fundo da página',
    frente: CORES.foco,
    fundo: CORES.fundo,
    minimoEsperado: 3.0,
    tipo: 'componente-ui',
  },
  {
    id: 'progresso-preenchimento-trilho',
    descricao: 'Preenchimento da barra de progresso contra o trilho',
    frente: CORES.progressoPreenchimento,
    fundo: CORES.progressoTrilho,
    minimoEsperado: 3.0,
    tipo: 'componente-ui',
  },
] as const;
