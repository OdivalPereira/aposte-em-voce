// Passo 8 (seção 5.2) e status da seção 5.5. Em centavos inteiros e sem tolerância.
// Nunca altera lançamento para fechar a conta, nunca inventa saldo e nunca inventa horário.
import type { ConferenciaSaldo, Lancamento, Motivo, Status } from './tipos';

function assinado(l: Lancamento): number {
  return l.direcao === 'entrada' ? l.valorCentavos : -l.valorCentavos;
}

/** Percorre os lançamentos na ordem dada conferindo cada saldo de linha contra o saldo corrente. */
function progressao(lancamentos: Lancamento[], saldoInicial: number | null): { verificadas: number; divergentes: number } {
  let corrente = saldoInicial;
  let verificadas = 0;
  let divergentes = 0;
  for (const l of lancamentos) {
    if (corrente !== null) corrente += assinado(l);
    if (l.saldoCentavos !== null) {
      if (corrente !== null) {
        verificadas++;
        if (corrente !== l.saldoCentavos) divergentes++;
      }
      corrente = l.saldoCentavos; // reancora no que o documento informa; o lançamento não é alterado
    }
  }
  return { verificadas, divergentes };
}

/** Extrato em ordem decrescente (mais novo primeiro): a progressão se lê de trás para a frente. */
function progressaoInversa(lancamentos: Lancamento[], saldoFinal: number | null): { verificadas: number; divergentes: number } {
  // Lendo de trás para a frente, o saldo "anterior" de cada linha é o saldo da linha seguinte no documento.
  let verificadas = 0;
  let divergentes = 0;
  let proximo: number | null = saldoFinal;
  for (let i = 0; i < lancamentos.length; i++) {
    const l = lancamentos[i] as Lancamento;
    if (l.saldoCentavos !== null) {
      if (proximo !== null) {
        verificadas++;
        if (proximo !== l.saldoCentavos) divergentes++;
      }
      // saldo antes desta linha = saldo da linha − valor assinado
      proximo = l.saldoCentavos - assinado(l);
    } else if (proximo !== null) {
      proximo -= assinado(l);
    }
  }
  return { verificadas, divergentes };
}

export function conferirSaldo(lancamentos: Lancamento[], saldoInicial: number | null, saldoFinal: number | null): ConferenciaSaldo {
  let entradas = 0;
  let saidas = 0;
  for (const l of lancamentos) {
    if (l.direcao === 'entrada') entradas += l.valorCentavos;
    else saidas += l.valorCentavos;
  }
  const comSaldo = lancamentos.some((l) => l.saldoCentavos !== null);

  let prog: ConferenciaSaldo['progressao'] = null;
  if (comSaldo) {
    const direta = progressao(lancamentos, saldoInicial);
    prog = { ...direta, ordem: 'documento' };
    if (direta.divergentes > 0 || direta.verificadas === 0) {
      // Pode ser um extrato do mais novo para o mais antigo; só adota se fechar sem divergência.
      const inversa = progressaoInversa(lancamentos, saldoFinal);
      if (inversa.verificadas > 0 && inversa.divergentes === 0) {
        prog = { ...inversa, ordem: 'inversa' };
      }
    }
  }

  const equacao = saldoInicial !== null && saldoFinal !== null;
  const diferenca = equacao ? saldoFinal - (saldoInicial + entradas - saidas) : null;

  let situacao: ConferenciaSaldo['situacao'];
  if (equacao || (prog && prog.verificadas > 0)) {
    const equacaoOk = !equacao || diferenca === 0;
    const progOk = !prog || prog.divergentes === 0;
    situacao = equacaoOk && progOk ? 'fecha' : 'nao-fecha';
  } else {
    situacao = 'indisponivel';
  }
  return {
    situacao,
    saldoInicialCentavos: saldoInicial,
    saldoFinalCentavos: saldoFinal,
    entradasCentavos: entradas,
    saidasCentavos: saidas,
    diferencaCentavos: diferenca,
    progressao: prog,
  };
}

export interface EntradaStatus {
  linhasCandidatas: number;
  lancamentos: number;
  semDirecao: number;
  colunasIncertas: boolean;
  /** grupos "agrupado por dia" cujo total declarado não bate com a soma das linhas lidas */
  totaisDivergentes?: number;
  conferencia: ConferenciaSaldo;
}

export const MENSAGEM: Record<Motivo | 'ok', string> = {
  ok: 'Lemos este extrato e o saldo confere.',
  imagem: 'Este arquivo é uma imagem; nesta versão lemos só PDFs baixados do banco.',
  corrompido: 'Não conseguimos abrir este arquivo. Ele pode estar corrompido; tente baixar o extrato de novo.',
  'fatura-cartao': 'Parece fatura de cartão; nesta versão lemos extratos de conta.',
  'muito-grande': 'Este arquivo é grande demais (o limite é 30 MB). Baixe um período menor.',
  'muitas-paginas': 'Este arquivo tem páginas demais (o limite é 200). Baixe um período menor.',
  'senha-necessaria': 'Este PDF tem senha. Digite a senha para ler; ela é usada só no seu aparelho.',
  'senha-incorreta': 'A senha não abriu o arquivo. Tente de novo.',
  'sem-lancamentos': 'Não encontramos lançamentos neste arquivo. Ele pode não ser um extrato de conta.',
  'direcao-incerta': 'Não ficou claro, em algumas linhas, se o valor entrou ou saiu. Confira com atenção.',
  'colunas-incertas': 'Não ficou claro qual coluna é o valor e qual é o saldo. Confira com atenção.',
  'saldo-nao-fecha': 'Lemos lançamentos, mas o saldo não fecha. Pode haver linhas faltando; confira com atenção.',
  'linhas-nao-lidas': 'Algumas linhas não puderam ser lidas. Confira com atenção.',
  'total-do-dia-diverge': 'O total de algum dia não bate com as linhas lidas desse dia. Confira com atenção.',
};

/** Status da seção 5.5 para um arquivo que foi lido (os casos da 5.4 são decididos antes, em `index.ts`). */
export function decidirStatus(e: EntradaStatus): { status: Status; motivo: Motivo | null } {
  if (e.lancamentos === 0 && e.semDirecao === 0) return { status: 'nao-suportado', motivo: 'sem-lancamentos' };
  const saldo = e.conferencia.situacao;
  // Nas colunas incertas, só a conferência aritmética (progressão ou equação) confirma a leitura.
  const colunasConfirmadas = !e.colunasIncertas || (saldo === 'fecha' && (e.conferencia.progressao?.verificadas ?? 0) > 0);
  if (e.semDirecao > 0) return { status: 'ambigua', motivo: 'direcao-incerta' };
  if (e.colunasIncertas && !colunasConfirmadas) return { status: 'ambigua', motivo: 'colunas-incertas' };
  if ((e.totaisDivergentes ?? 0) > 0) return { status: 'ambigua', motivo: 'total-do-dia-diverge' };
  if (saldo === 'nao-fecha') return { status: 'parcial', motivo: 'saldo-nao-fecha' };
  const razao = e.linhasCandidatas === 0 ? 1 : e.lancamentos / e.linhasCandidatas;
  if (razao < 0.95) return { status: 'parcial', motivo: 'linhas-nao-lidas' };
  return { status: 'suficiente', motivo: null };
}
