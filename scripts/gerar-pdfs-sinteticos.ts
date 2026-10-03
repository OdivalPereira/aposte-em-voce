#!/usr/bin/env node
// Gerador de PDFs sintéticos para testes de leitura (F3)
// Os dados de origem estão na tabela CASOS; PDFs e JSON esperado são gerados a partir deles.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { gerarPdf, gerarPdfSemTexto } from '../tests/unit/auxiliar/pdf-sintetico.js';
import { gerarPdfComSenha } from '../tests/unit/auxiliar/pdf-com-senha.js';
import { COLUNAS_PADRAO, pagina, PASSO } from '../tests/unit/auxiliar/montar.js';
import type { PaginaTexto, ResultadoArquivo, ItemTexto } from '../src/leitura/tipos.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const FIXTURES_PDFS = join(__dirname, '../tests/fixtures/pdfs');
const FIXTURES_ESPERADO = join(__dirname, '../tests/fixtures/esperado');

function calcularHash(bytes: Uint8Array): string {
  return createHash('sha256').update(bytes).digest('hex');
}

// Interface para dados de origem de um caso
interface DadosOrigem {
  nome: string;
  paginas: PaginaTexto[];
  // Dados esperados derivados da definição do caso
  layoutNome?: string;
  periodo?: { inicio: string; fim: string };
  saldoInicialCentavos?: number;
  saldoFinalCentavos?: number;
  entradasCentavos: number;
  saidasCentavos: number;
  linhasCandidatas: number;
  paginas_count: number;
  // Lançamentos esperados (antes de qualquer processamento do F2)
  lancamentosEsperados: Array<{
    data: string;
    hora: null;
    valorCentavos: number;
    direcao: 'entrada' | 'saida';
    descricao: string;
    pagina: number;
    saldoCentavos: number | null;
  }>;
  // Status pretendido
  statusPretendido: 'suficiente' | 'parcial' | 'ambigua' | 'nao-suportado';
  motivoPretendido: null | string;
  bancoProvavelPretendido: null | string;
  // Gerador customizado (opcional)
  gerador?: (paginas: PaginaTexto[]) => Promise<Uint8Array>;
  // Senha (se houver)
  senha?: string;
}

/**
 * Calcula a conferência de saldo a partir dos dados.
 * Retorna null se não há saldos iniciais e finais.
 */
function calcularConferencia(dados: DadosOrigem): ResultadoArquivo['conferencia'] {
  const temSaldos = dados.saldoInicialCentavos !== undefined && dados.saldoFinalCentavos !== undefined;

  if (!temSaldos) {
    return {
      situacao: 'indisponivel',
      saldoInicialCentavos: null,
      saldoFinalCentavos: null,
      entradasCentavos: dados.entradasCentavos,
      saidasCentavos: dados.saidasCentavos,
      diferencaCentavos: null,
    };
  }

  const saldoInicial = dados.saldoInicialCentavos!;
  const saldoFinal = dados.saldoFinalCentavos!;
  const diferencaCentavos = saldoFinal - (saldoInicial + dados.entradasCentavos - dados.saidasCentavos);

  const situacao = diferencaCentavos === 0 ? 'fecha' : 'nao-fecha';

  return {
    situacao,
    saldoInicialCentavos: saldoInicial,
    saldoFinalCentavos: saldoFinal,
    entradasCentavos: dados.entradasCentavos,
    saidasCentavos: dados.saidasCentavos,
    diferencaCentavos: diferencaCentavos === 0 ? 0 : null,
  };
}

/**
 * Gera o JSON esperado a partir dos dados de origem.
 * Não inclui: hash, mensagem, conferencia.progressao
 */
function gerarEsperado(dados: DadosOrigem): Omit<ResultadoArquivo, 'hash' | 'mensagem' | 'versao'> {
  // Calcular período a partir dos lançamentos
  let periodo: { inicio: string; fim: string } | null = null;
  if (dados.lancamentosEsperados.length > 0) {
    const datas = dados.lancamentosEsperados.map(l => l.data).sort();
    periodo = { inicio: datas[0]!, fim: datas[datas.length - 1]! };
  }

  return {
    status: dados.statusPretendido,
    motivo: dados.motivoPretendido,
    bancoProvavel: dados.bancoProvavelPretendido,
    periodo,
    paginas: dados.paginas_count,
    linhasCandidatas: dados.linhasCandidatas,
    lancamentos: dados.lancamentosEsperados,
    conferencia: calcularConferencia(dados),
  };
}

// ============================================================================
// CASOS - Dados de origem para cada PDF de teste
// ============================================================================

const CASOS: DadosOrigem[] = [];

// 1. Layout Nubank (limpo)
CASOS.push({
  nome: 'nubank-limpo',
  layoutNome: 'Nubank',
  periodo: { inicio: '2026-09-02', fim: '2026-09-25' },
  saldoInicialCentavos: 1004550,
  saldoFinalCentavos: 1253835,
  entradasCentavos: 550000,
  saidasCentavos: 301115,
  linhasCandidatas: 8,
  paginas_count: 1,
  bancoProvavelPretendido: 'Nubank',
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-02', hora: null, valorCentavos: 4550, direcao: 'saida', descricao: 'COMPRA NO DÉBITO - PADARIA FICTICIA', pagina: 1, saldoCentavos: 1000000 },
    { data: '2026-09-03', hora: null, valorCentavos: 120000, direcao: 'saida', descricao: 'PIX ENVIADO PARA PESSOA FICTICIA', pagina: 1, saldoCentavos: 880000 },
    { data: '2026-09-05', hora: null, valorCentavos: 250000, direcao: 'entrada', descricao: 'PIX RECEBIDO DE EMPRESA FICTICIA', pagina: 1, saldoCentavos: 1130000 },
    { data: '2026-09-07', hora: null, valorCentavos: 85000, direcao: 'saida', descricao: 'PAGAMENTO DE BOLETO FICTICIO', pagina: 1, saldoCentavos: 1045000 },
    { data: '2026-09-10', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'SAQUE ATM BANCO FICTICIO', pagina: 1, saldoCentavos: 995000 },
    { data: '2026-09-15', hora: null, valorCentavos: 300000, direcao: 'entrada', descricao: 'TRANSFERÊNCIA RECEBIDA', pagina: 1, saldoCentavos: 1295000 },
    { data: '2026-09-20', hora: null, valorCentavos: 28575, direcao: 'saida', descricao: 'PAGAMENTO CONTA LUZ', pagina: 1, saldoCentavos: 1266425 },
    { data: '2026-09-25', hora: null, valorCentavos: 12590, direcao: 'saida', descricao: 'COMPRA ONLINE LOJA FICTICIA', pagina: 1, saldoCentavos: 1253835 },
  ],
  paginas: [
    pagina({
      antes: ['EXTRATO DO PERÍODO', '01/09/2026 a 30/09/2026'],
      colunas: COLUNAS_PADRAO,
      linhas: [
        ['02/09/2026', 'COMPRA NO DÉBITO - PADARIA FICTICIA', '45,50', '10.000,00'],
        ['03/09/2026', 'PIX ENVIADO PARA PESSOA FICTICIA', '1.200,00', '8.800,00'],
        ['05/09/2026', 'PIX RECEBIDO DE EMPRESA FICTICIA', '2.500,00', '11.300,00'],
        ['07/09/2026', 'PAGAMENTO DE BOLETO FICTICIO', '850,00', '10.450,00'],
        ['10/09/2026', 'SAQUE ATM BANCO FICTICIO', '500,00', '9.950,00'],
        ['15/09/2026', 'TRANSFERÊNCIA RECEBIDA', '3.000,00', '12.950,00'],
        ['20/09/2026', 'PAGAMENTO CONTA LUZ', '285,75', '12.664,25'],
        ['25/09/2026', 'COMPRA ONLINE LOJA FICTICIA', '125,90', '12.538,35'],
      ],
      depois: ['SALDO ANTERIOR: 10.045,50', 'SALDO FINAL: 12.538,35'],
    }),
  ],
});

// 2. Layout Mercado Pago (limpo)
CASOS.push({
  nome: 'mercado-pago-limpo',
  layoutNome: 'Mercado Pago',
  periodo: { inicio: '2026-09-05', fim: '2026-09-20' },
  saldoInicialCentavos: 500000,
  saldoFinalCentavos: 453450,
  entradasCentavos: 255000,
  saidasCentavos: 301550,
  linhasCandidatas: 5,
  paginas_count: 1,
  bancoProvavelPretendido: 'Mercado Pago',
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 85000, direcao: 'entrada', descricao: 'PAGAMENTO RECEBIDO LOJA X', pagina: 1, saldoCentavos: 585000 },
    { data: '2026-09-08', hora: null, valorCentavos: 1550, direcao: 'saida', descricao: 'TAXA OPERACIONAL', pagina: 1, saldoCentavos: 583450 },
    { data: '2026-09-10', hora: null, valorCentavos: 120000, direcao: 'entrada', descricao: 'PAGAMENTO RECEBIDO LOJA Y', pagina: 1, saldoCentavos: 703450 },
    { data: '2026-09-15', hora: null, valorCentavos: 300000, direcao: 'saida', descricao: 'SAQUE PARA CONTA', pagina: 1, saldoCentavos: 403450 },
    { data: '2026-09-20', hora: null, valorCentavos: 50000, direcao: 'entrada', descricao: 'PAGAMENTO RECEBIDO LOJA Z', pagina: 1, saldoCentavos: 453450 },
  ],
  paginas: [pagina({ antes: ['MERCADO PAGO 01/09 A 30/09'], colunas: [{ titulo: 'Data', x: 40 }, { titulo: 'Histórico', x: 130 }, { titulo: 'Débito', x: 380, dir: true }, { titulo: 'Crédito', x: 480, dir: true }, { titulo: 'Saldo', x: 540, dir: true }], linhas: [['02/09/2026', 'SALDO ANTERIOR', '', '', '5.000,00'], ['05/09/2026', 'PAGAMENTO RECEBIDO LOJA X', '', '850,00', '5.850,00'], ['08/09/2026', 'TAXA OPERACIONAL', '15,50', '', '5.834,50'], ['10/09/2026', 'PAGAMENTO RECEBIDO LOJA Y', '', '1.200,00', '7.034,50'], ['15/09/2026', 'SAQUE PARA CONTA', '3.000,00', '', '4.034,50'], ['20/09/2026', 'PAGAMENTO RECEBIDO LOJA Z', '', '500,00', '4.534,50']], depois: ['SALDO FINAL: 4.534,50'] })],
});

// 3. Layout PicPay
CASOS.push({
  nome: 'picpay-limpo',
  layoutNome: 'PicPay',
  periodo: { inicio: '2026-09-15', fim: '2026-09-25' },
  saldoInicialCentavos: 200000,
  saldoFinalCentavos: 232500,
  entradasCentavos: 57500,
  saidasCentavos: 25000,
  linhasCandidatas: 4,
  paginas_count: 1,
  bancoProvavelPretendido: 'PicPay',
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-15', hora: null, valorCentavos: 50000, direcao: 'entrada', descricao: 'TRANSFERÊNCIA RECEBIDA DE PESSOA FICTICIA', pagina: 1, saldoCentavos: 250000 },
    { data: '2026-09-18', hora: null, valorCentavos: 20000, direcao: 'saida', descricao: 'PAGAMENTO CONTA FICTICIA', pagina: 1, saldoCentavos: 230000 },
    { data: '2026-09-22', hora: null, valorCentavos: 5000, direcao: 'saida', descricao: 'RECARGA DE CELULAR', pagina: 1, saldoCentavos: 225000 },
    { data: '2026-09-25', hora: null, valorCentavos: 7500, direcao: 'entrada', descricao: 'DEVOLUÇÃO PAGAMENTO', pagina: 1, saldoCentavos: 232500 },
  ],
  paginas: [pagina({ antes: ['PICPAY 15/09 A 30/09'], colunas: COLUNAS_PADRAO, linhas: [['15/09/2026', 'TRANSFERÊNCIA RECEBIDA DE PESSOA FICTICIA', '500,00', '2.500,00'], ['18/09/2026', 'PAGAMENTO CONTA FICTICIA', '200,00', '2.300,00'], ['22/09/2026', 'RECARGA DE CELULAR', '50,00', '2.250,00'], ['25/09/2026', 'DEVOLUÇÃO PAGAMENTO', '75,00', '2.325,00']], depois: ['SALDO INICIAL: 2.000,00', 'SALDO FINAL: 2.325,00'] })],
});

// 4. Layout Inter
CASOS.push({
  nome: 'inter-limpo',
  layoutNome: 'Inter',
  periodo: { inicio: '2026-09-10', fim: '2026-09-25' },
  saldoInicialCentavos: 800000,
  saldoFinalCentavos: 1054550,
  entradasCentavos: 355550,
  saidasCentavos: 100000,
  linhasCandidatas: 5,
  paginas_count: 1,
  bancoProvavelPretendido: 'Inter',
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-10', hora: null, valorCentavos: 150000, direcao: 'entrada', descricao: 'TRANSFERÊNCIA RECEBIDA', pagina: 1, saldoCentavos: 950000 },
    { data: '2026-09-12', hora: null, valorCentavos: 65000, direcao: 'saida', descricao: 'COMPRA COM CARTÃO', pagina: 1, saldoCentavos: 885000 },
    { data: '2026-09-15', hora: null, valorCentavos: 200000, direcao: 'entrada', descricao: 'DEPÓSITO', pagina: 1, saldoCentavos: 1085000 },
    { data: '2026-09-18', hora: null, valorCentavos: 35000, direcao: 'saida', descricao: 'PIX ENVIADO', pagina: 1, saldoCentavos: 1050000 },
    { data: '2026-09-25', hora: null, valorCentavos: 4550, direcao: 'entrada', descricao: 'JUROS CREDITADOS', pagina: 1, saldoCentavos: 1054550 },
  ],
  paginas: [pagina({ antes: ['INTER 10/09 A 30/09'], colunas: [{ titulo: 'Data', x: 40 }, { titulo: 'Descrição', x: 130 }, { titulo: 'Entrada', x: 430, dir: true }, { titulo: 'Saída', x: 480, dir: true }, { titulo: 'Saldo', x: 540, dir: true }], linhas: [['', 'SALDO ANTERIOR', '', '', '8.000,00'], ['10/09/2026', 'TRANSFERÊNCIA RECEBIDA', '1.500,00', '', '9.500,00'], ['12/09/2026', 'COMPRA COM CARTÃO', '', '650,00', '8.850,00'], ['15/09/2026', 'DEPÓSITO', '2.000,00', '', '10.850,00'], ['18/09/2026', 'PIX ENVIADO', '', '350,00', '10.500,00'], ['25/09/2026', 'JUROS CREDITADOS', '45,50', '', '10.545,50']], depois: ['SALDO FINAL: 10.545,50'] })],
});

// 5. Layout Caixa Tem
CASOS.push({
  nome: 'caixa-tem-limpo',
  layoutNome: 'Caixa Tem',
  periodo: { inicio: '2026-09-05', fim: '2026-09-18' },
  saldoInicialCentavos: 120000,
  saldoFinalCentavos: 123000,
  entradasCentavos: 100000,
  saidasCentavos: 97000,
  linhasCandidatas: 4,
  paginas_count: 1,
  bancoProvavelPretendido: 'Caixa Tem',
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 100000, direcao: 'entrada', descricao: 'BENEFÍCIO RECEBIDO', pagina: 1, saldoCentavos: 220000 },
    { data: '2026-09-08', hora: null, valorCentavos: 35000, direcao: 'saida', descricao: 'SAQUE', pagina: 1, saldoCentavos: 185000 },
    { data: '2026-09-12', hora: null, valorCentavos: 12000, direcao: 'saida', descricao: 'PAGAMENTO DE CONTA', pagina: 1, saldoCentavos: 173000 },
    { data: '2026-09-18', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'TRANSFERÊNCIA ENVIADA', pagina: 1, saldoCentavos: 123000 },
  ],
  paginas: [pagina({ antes: ['CAIXA TEM 01/09 A 30/09'], colunas: COLUNAS_PADRAO, linhas: [['01/09/2026', 'SALDO ANTERIOR', '', '', '1.200,00'], ['05/09/2026', 'BENEFÍCIO RECEBIDO', '1.000,00', '', '2.200,00'], ['08/09/2026', 'SAQUE', '-350,00', '', '1.850,00'], ['12/09/2026', 'PAGAMENTO DE CONTA', '-120,00', '', '1.730,00'], ['18/09/2026', 'TRANSFERÊNCIA ENVIADA', '-500,00', '', '1.230,00']], depois: ['SALDO FINAL: 1.230,00'] })],
});

// 6. Layout Caixa
CASOS.push({
  nome: 'caixa-limpo',
  layoutNome: 'Caixa',
  periodo: { inicio: '2026-09-20', fim: '2026-09-28' },
  saldoInicialCentavos: 1500000,
  saldoFinalCentavos: 1555000,
  entradasCentavos: 505000,
  saidasCentavos: 450000,
  linhasCandidatas: 4,
  paginas_count: 1,
  bancoProvavelPretendido: 'Caixa',
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-20', hora: null, valorCentavos: 500000, direcao: 'entrada', descricao: 'TRANSFERÊNCIA RECEBIDA', pagina: 1, saldoCentavos: 2000000 },
    { data: '2026-09-22', hora: null, valorCentavos: 300000, direcao: 'saida', descricao: 'PAGAMENTO FATURA', pagina: 1, saldoCentavos: 1700000 },
    { data: '2026-09-25', hora: null, valorCentavos: 150000, direcao: 'saida', descricao: 'SAQUE ATM', pagina: 1, saldoCentavos: 1550000 },
    { data: '2026-09-28', hora: null, valorCentavos: 5000, direcao: 'entrada', descricao: 'JUROS', pagina: 1, saldoCentavos: 1555000 },
  ],
  paginas: [pagina({ antes: ['CAIXA 20/09 A 30/09'], colunas: [{ titulo: 'Data', x: 40 }, { titulo: 'Lançamento', x: 130 }, { titulo: 'Débito', x: 400, dir: true }, { titulo: 'Crédito', x: 480, dir: true }, { titulo: 'Saldo', x: 540, dir: true }], linhas: [['', 'SALDO INICIAL', '', '', '15.000,00'], ['20/09/2026', 'TRANSFERÊNCIA RECEBIDA', '', '5.000,00', '20.000,00'], ['22/09/2026', 'PAGAMENTO FATURA', '3.000,00', '', '17.000,00'], ['25/09/2026', 'SAQUE ATM', '1.500,00', '', '15.500,00'], ['28/09/2026', 'JUROS', '', '50,00', '15.550,00']], depois: ['SALDO FINAL: 15.550,00'] })],
});

// 7. Difficult: Description in 2 lines
CASOS.push({
  nome: 'dificil-descricao-duas-linhas',
  periodo: { inicio: '2026-09-05', fim: '2026-09-10' },
  saldoInicialCentavos: 500000,
  saldoFinalCentavos: 650000,
  entradasCentavos: 0,
  saidasCentavos: 150000,
  linhasCandidatas: 2,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 100000, direcao: 'saida', descricao: 'PAGAMENTO LOJA FICTICÍA LTDA RESPEITO AOS CLIENTES', pagina: 1, saldoCentavos: 600000 },
    { data: '2026-09-10', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'TRANSFER PESSOA FICTICIA NOME SOBRENOME', pagina: 1, saldoCentavos: 650000 },
  ],
  paginas: [pagina({ antes: ['EXTRATO TESTE'], colunas: COLUNAS_PADRAO, linhas: [['01/09/2026', 'SALDO ANTERIOR', '', '', '5.000,00'], ['05/09/2026', 'PAGAMENTO LOJA FICTICÍA LTDA\nRESPEITO AOS CLIENTES', '1.000,00', '', '6.000,00'], ['10/09/2026', 'TRANSFER PESSOA FICTICIA\nNOME SOBRENOME', '500,00', '', '6.500,00']], depois: ['SALDO FINAL: 6.500,00'] })],
});

// 8. Difficult: Repeated header
CASOS.push({
  nome: 'dificil-cabecalho-repetido',
  periodo: { inicio: '2026-09-05', fim: '2026-09-15' },
  saldoInicialCentavos: 100000,
  saldoFinalCentavos: 115000,
  entradasCentavos: 0,
  saidasCentavos: 85000,
  linhasCandidatas: 3,
  paginas_count: 2,
  bancoProvavelPretendido: null,
  statusPretendido: 'parcial',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 20000, direcao: 'saida', descricao: 'PIX ENVIADO', pagina: 1, saldoCentavos: 80000 },
    { data: '2026-09-10', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'PIX RECEBIDO', pagina: 2, saldoCentavos: 130000 },
    { data: '2026-09-15', hora: null, valorCentavos: 15000, direcao: 'saida', descricao: 'PAGAMENTO', pagina: 2, saldoCentavos: 115000 },
  ],
  paginas: [
    pagina({ numero: 1, antes: ['PÁGINA 1'], colunas: COLUNAS_PADRAO, cabecalho: true, linhas: [['01/09/2026', 'SALDO ANTERIOR', '', '1.000,00'], ['05/09/2026', 'PIX ENVIADO', '200,00', '800,00']], depois: ['Continua na próxima página'] }),
    pagina({ numero: 2, antes: ['PÁGINA 2'], colunas: COLUNAS_PADRAO, cabecalho: true, linhas: [['10/09/2026', 'PIX RECEBIDO', '500,00', '1.300,00'], ['15/09/2026', 'PAGAMENTO', '150,00', '1.150,00']], depois: ['SALDO FINAL: 1.150,00'] })
  ],
});

// 9. Difficult: Negative sign
CASOS.push({
  nome: 'dificil-sinal-negativo',
  periodo: { inicio: '2026-09-05', fim: '2026-09-15' },
  saldoInicialCentavos: 500000,
  saldoFinalCentavos: 520000,
  entradasCentavos: 100000,
  saidasCentavos: 80000,
  linhasCandidatas: 3,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'SAQUE', pagina: 1, saldoCentavos: 450000 },
    { data: '2026-09-10', hora: null, valorCentavos: 100000, direcao: 'entrada', descricao: 'DEPÓSITO', pagina: 1, saldoCentavos: 550000 },
    { data: '2026-09-15', hora: null, valorCentavos: 30000, direcao: 'saida', descricao: 'CHEQUE COMPENSADO', pagina: 1, saldoCentavos: 520000 },
  ],
  paginas: [pagina({ antes: ['SINAL NEGATIVO'], colunas: [{ titulo: 'Data', x: 40 }, { titulo: 'Descrição', x: 130 }, { titulo: 'Valor (R$)', x: 430, dir: true }, { titulo: 'Saldo (R$)', x: 540, dir: true }], linhas: [['01/09/2026', 'SALDO ANTERIOR', '5.000,00', '5.000,00'], ['05/09/2026', 'SAQUE', '-500,00', '4.500,00'], ['10/09/2026', 'DEPÓSITO', '1.000,00', '5.500,00'], ['15/09/2026', 'CHEQUE COMPENSADO', '-300,00', '5.200,00']], depois: ['SALDO FINAL: 5.200,00'] })],
});

// 10. Difficult: C/D column
CASOS.push({
  nome: 'dificil-coluna-cd',
  periodo: { inicio: '2026-09-05', fim: '2026-09-15' },
  saldoInicialCentavos: 500000,
  saldoFinalCentavos: 504000,
  entradasCentavos: 30000,
  saidasCentavos: 26000,
  linhasCandidatas: 3,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 25000, direcao: 'saida', descricao: 'PIX ENVIADO', pagina: 1, saldoCentavos: 475000 },
    { data: '2026-09-10', hora: null, valorCentavos: 30000, direcao: 'entrada', descricao: 'PIX RECEBIDO', pagina: 1, saldoCentavos: 505000 },
    { data: '2026-09-15', hora: null, valorCentavos: 1000, direcao: 'saida', descricao: 'TAXA', pagina: 1, saldoCentavos: 504000 },
  ],
  paginas: [pagina({ antes: ['COLUNA D/C'], colunas: [{ titulo: 'Data', x: 40 }, { titulo: 'Descrição', x: 130 }, { titulo: 'Valor (R$)', x: 420, dir: true }, { titulo: 'D/C', x: 470, dir: true }, { titulo: 'Saldo (R$)', x: 540, dir: true }], linhas: [['05/09/2026', 'PIX ENVIADO', '250,00', 'D', '4.750,00'], ['10/09/2026', 'PIX RECEBIDO', '300,00', 'C', '5.050,00'], ['15/09/2026', 'TAXA', '10,00', 'D', '5.040,00']], depois: ['SALDO ANTERIOR: 5.000,00', 'SALDO FINAL: 5.040,00'] })],
});

// 11. Difficult: Balance per line
CASOS.push({
  nome: 'dificil-saldo-por-linha',
  periodo: { inicio: '2026-09-03', fim: '2026-09-15' },
  saldoInicialCentavos: 1000000,
  saldoFinalCentavos: 1055000,
  entradasCentavos: 0,
  saidasCentavos: 355000,
  linhasCandidatas: 4,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'parcial',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-03', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'COMPRA', pagina: 1, saldoCentavos: 950000 },
    { data: '2026-09-05', hora: null, valorCentavos: 200000, direcao: 'saida', descricao: 'DEPÓSITO', pagina: 1, saldoCentavos: 1150000 },
    { data: '2026-09-10', hora: null, valorCentavos: 100000, direcao: 'saida', descricao: 'SAQUE', pagina: 1, saldoCentavos: 1050000 },
    { data: '2026-09-15', hora: null, valorCentavos: 5000, direcao: 'saida', descricao: 'JUROS', pagina: 1, saldoCentavos: 1055000 },
  ],
  paginas: [pagina({ antes: ['SALDO POR LINHA'], colunas: COLUNAS_PADRAO, linhas: [['', 'SALDO ANTERIOR', '', '10.000,00'], ['03/09/2026', 'COMPRA', '500,00', '9.500,00'], ['05/09/2026', 'DEPÓSITO', '2.000,00', '11.500,00'], ['10/09/2026', 'SAQUE', '1.000,00', '10.500,00'], ['15/09/2026', 'JUROS', '50,00', '10.550,00']], depois: ['SALDO FINAL: 10.550,00'] })],
});

// 12. Difficult: No balance
CASOS.push({
  nome: 'dificil-sem-saldo',
  periodo: { inicio: '2026-09-05', fim: '2026-09-15' },
  // Sem saldos iniciais e finais
  entradasCentavos: 50000,
  saidasCentavos: 80000,
  linhasCandidatas: 3,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'parcial',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 30000, direcao: 'saida', descricao: 'PIX ENVIADO', pagina: 1, saldoCentavos: null },
    { data: '2026-09-10', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'PIX RECEBIDO', pagina: 1, saldoCentavos: null },
    { data: '2026-09-15', hora: null, valorCentavos: 2000, direcao: 'saida', descricao: 'TAXA', pagina: 1, saldoCentavos: null },
  ],
  paginas: [pagina({ antes: ['SEM SALDO'], colunas: [{ titulo: 'Data', x: 40 }, { titulo: 'Descrição', x: 130 }, { titulo: 'Valor (R$)', x: 430, dir: true }], linhas: [['05/09/2026', 'PIX ENVIADO', '300,00'], ['10/09/2026', 'PIX RECEBIDO', '500,00'], ['15/09/2026', 'TAXA', '20,00']], depois: ['FIM DO EXTRATO'] })],
});

// 13. Difficult: Date without year
CASOS.push({
  nome: 'dificil-data-sem-ano',
  periodo: { inicio: '2026-09-15', fim: '2026-09-25' },
  saldoInicialCentavos: 500000,
  saldoFinalCentavos: 505000,
  entradasCentavos: 0,
  saidasCentavos: 35000,
  linhasCandidatas: 3,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'parcial',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-15', hora: null, valorCentavos: 10000, direcao: 'saida', descricao: 'PIX ENVIADO', pagina: 1, saldoCentavos: 490000 },
    { data: '2026-09-20', hora: null, valorCentavos: 20000, direcao: 'saida', descricao: 'PIX RECEBIDO', pagina: 1, saldoCentavos: 510000 },
    { data: '2026-09-25', hora: null, valorCentavos: 5000, direcao: 'saida', descricao: 'TAXA', pagina: 1, saldoCentavos: 505000 },
  ],
  paginas: [pagina({ antes: ['EXTRATO 15 SET A 30 SET'], colunas: COLUNAS_PADRAO, linhas: [['15 SET', 'PIX ENVIADO', '100,00', '4.900,00'], ['20 SET', 'PIX RECEBIDO', '200,00', '5.100,00'], ['25 SET', 'TAXA', '50,00', '5.050,00']], depois: ['SALDO ANTERIOR: 5.000,00', 'SALDO FINAL: 5.050,00'] })],
});

// 14. Difficult: PDF with password (should succeed with password)
CASOS.push({
  nome: 'dificil-protegido-aes',
  senha: 'senha-teste-123',
  periodo: { inicio: '2026-09-10', fim: '2026-09-20' },
  saldoInicialCentavos: 300000,
  saldoFinalCentavos: 400000,
  entradasCentavos: 0,
  saidasCentavos: 200000,
  linhasCandidatas: 2,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'parcial',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-10', hora: null, valorCentavos: 150000, direcao: 'saida', descricao: 'DEPÓSITO', pagina: 1, saldoCentavos: 450000 },
    { data: '2026-09-20', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'SAQUE', pagina: 1, saldoCentavos: 400000 },
  ],
  gerador: async (paginas) => gerarPdfComSenha(paginas, 'senha-teste-123'),
  paginas: [pagina({ antes: ['PROTEGIDO'], colunas: COLUNAS_PADRAO, linhas: [['01/09/2026', 'SALDO INICIAL', '', '3.000,00'], ['10/09/2026', 'DEPÓSITO', '1.500,00', '4.500,00'], ['20/09/2026', 'SAQUE', '500,00', '4.000,00']], depois: ['SALDO FINAL: 4.000,00'] })],
});

// 15. Difficult: PDF image-only
CASOS.push({
  nome: 'dificil-somente-imagem',
  gerador: async () => gerarPdfSemTexto(),
  entradasCentavos: 0,
  saidasCentavos: 0,
  linhasCandidatas: 0,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'nao-suportado',
  motivoPretendido: 'imagem',
  lancamentosEsperados: [],
  paginas: [],
});

// 16. Difficult: Same file twice (for hash checking)
CASOS.push({
  nome: 'dificil-mesmo-arquivo-duas-vezes',
  periodo: { inicio: '2026-09-05', fim: '2026-09-10' },
  saldoInicialCentavos: 100000,
  saldoFinalCentavos: 130000,
  entradasCentavos: 0,
  saidasCentavos: 30000,
  linhasCandidatas: 2,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'suficiente',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 10000, direcao: 'saida', descricao: 'TRANSAÇÃO A', pagina: 1, saldoCentavos: 110000 },
    { data: '2026-09-10', hora: null, valorCentavos: 20000, direcao: 'saida', descricao: 'TRANSAÇÃO B', pagina: 1, saldoCentavos: 130000 },
  ],
  paginas: [pagina({ antes: ['EXEMPLO'], colunas: COLUNAS_PADRAO, linhas: [['05/09/2026', 'TRANSAÇÃO A', '100,00', '1.100,00'], ['10/09/2026', 'TRANSAÇÃO B', '200,00', '1.300,00']], depois: ['SALDO ANTERIOR: 1.000,00', 'SALDO FINAL: 1.300,00'] })],
});

// 17. Difficult: Overlapping periods
CASOS.push({
  nome: 'dificil-periodos-sobrepostos',
  periodo: { inicio: '2026-09-05', fim: '2026-09-15' },
  saldoInicialCentavos: 200000,
  saldoFinalCentavos: 210000,
  entradasCentavos: 0,
  saidasCentavos: 90000,
  linhasCandidatas: 3,
  paginas_count: 1,
  bancoProvavelPretendido: null,
  statusPretendido: 'parcial',
  motivoPretendido: null,
  lancamentosEsperados: [
    { data: '2026-09-05', hora: null, valorCentavos: 50000, direcao: 'saida', descricao: 'TRANSAÇÃO 1', pagina: 1, saldoCentavos: 250000 },
    { data: '2026-09-10', hora: null, valorCentavos: 30000, direcao: 'saida', descricao: 'TRANSAÇÃO 2', pagina: 1, saldoCentavos: 220000 },
    { data: '2026-09-15', hora: null, valorCentavos: 10000, direcao: 'saida', descricao: 'TRANSAÇÃO 3', pagina: 1, saldoCentavos: 210000 },
  ],
  paginas: [pagina({ numero: 1, antes: ['PERÍODO 1: 01/09 A 15/09'], colunas: COLUNAS_PADRAO, linhas: [['05/09/2026', 'TRANSAÇÃO 1', '500,00', '2.500,00'], ['10/09/2026', 'TRANSAÇÃO 2', '300,00', '2.200,00'], ['15/09/2026', 'TRANSAÇÃO 3', '100,00', '2.100,00']], depois: ['SALDO ANTERIOR: 2.000,00', 'SALDO FINAL: 2.100,00'] })],
});

// ============================================================================
// Geração de PDFs e JSONs esperados
// ============================================================================

async function gerarArquivos() {
  console.log(`Gerando ${CASOS.length} PDFs e JSONs esperados...`);

  // Criar diretórios se não existirem
  mkdirSync(FIXTURES_PDFS, { recursive: true });
  mkdirSync(FIXTURES_ESPERADO, { recursive: true });

  for (const caso of CASOS) {
    try {
      // Gerar PDF
      let bytes: Uint8Array;
      if (caso.gerador) {
        bytes = await caso.gerador(caso.paginas);
      } else {
        bytes = await gerarPdf(caso.paginas);
      }

      const hash = calcularHash(bytes);
      const pdfPath = join(FIXTURES_PDFS, `${caso.nome}.pdf`);
      writeFileSync(pdfPath, bytes);

      // Gerar JSON esperado (sem hash, versao, mensagem e sem progressao em conferencia)
      const esperado = gerarEsperado(caso);
      const resultado: Omit<ResultadoArquivo, 'versao' | 'hash' | 'mensagem'> = {
        status: esperado.status,
        motivo: esperado.motivo,
        bancoProvavel: esperado.bancoProvavel,
        periodo: esperado.periodo,
        paginas: esperado.paginas,
        linhasCandidatas: esperado.linhasCandidatas,
        lancamentos: esperado.lancamentos,
        conferencia: esperado.conferencia,
      };

      const jsonPath = join(FIXTURES_ESPERADO, `${caso.nome}.json`);
      writeFileSync(jsonPath, JSON.stringify(resultado, null, 2));

      console.log(`✓ ${caso.nome}`);
    } catch (erro) {
      console.error(`✗ ${caso.nome}: ${erro}`);
    }
  }

  console.log('Pronto!');
}

gerarArquivos().catch(console.error);
