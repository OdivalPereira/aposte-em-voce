// Histórico contínuo (pedido de Odival): vários extratos mensais da mesma conta viram um histórico só.
// Função pura sobre os arquivos já lidos. Nenhum lançamento é alterado (5.2); a duplicidade segue a 5.3
// (a consolidação é a mesma de `consolidar.ts`). A conta é identificada por banco provável mais o
// identificador estrutural (`contaFinal`, no máximo 4 dígitos); nome da pessoa e número completo nunca entram.
import { consolidar } from './consolidar';
import type { ArquivoLido, Consolidado, Periodo } from './tipos';

export type TipoAviso = 'encadeamento' | 'encadeamento-nao-conferido' | 'sem-identificador';

export interface AvisoHistorico {
  tipo: TipoAviso;
  /** mês nomeado pelo aviso (aaaa-mm), quando há */
  mes: string | null;
  /** texto para a pessoa; só traz o mês (mm/aaaa), nunca valores */
  mensagem: string;
}

export interface Historico {
  bancoProvavel: string | null;
  /** "final 4821" ou `null` quando nada distingue a conta */
  contaFinal: string | null;
  /** arquivos em ordem de período (início, depois fim, depois nome) */
  arquivos: ArquivoLido[];
  /** menor e maior data de todos os lançamentos do histórico */
  periodo: Periodo;
  /** meses (aaaa-mm) com ao menos um arquivo, em ordem */
  mesesCobertos: string[];
  /** meses (aaaa-mm) entre o primeiro e o último coberto sem arquivo, em ordem */
  mesesFaltando: string[];
  avisos: AvisoHistorico[];
  consolidado: Consolidado;
}

export interface Historicos {
  historicos: Historico[];
  /** arquivos ignorados por serem o mesmo arquivo reenviado (mesmo hash) */
  repetidos: string[];
  /** arquivos que não entram em histórico (não suportados ou sem lançamentos lidos) */
  semHistorico: string[];
}

const mes = (dataIso: string) => dataIso.slice(0, 7);

function proximoMes(m: string): string {
  const ano = Number(m.slice(0, 4));
  const n = Number(m.slice(5, 7));
  return n === 12 ? `${String(ano + 1).padStart(4, '0')}-01` : `${String(ano).padStart(4, '0')}-${String(n + 1).padStart(2, '0')}`;
}

const mmaaaa = (m: string) => `${m.slice(5, 7)}/${m.slice(0, 4)}`;

function periodoDe(a: ArquivoLido): Periodo {
  return a.resultado.periodo as Periodo;
}

interface Grupo {
  banco: string | null;
  conta: string | null;
  arquivos: ArquivoLido[];
  /** o grupo reúne arquivos sem como distinguir a conta */
  semDistinguir: boolean;
}

/** Banco provável diferente nunca junta; dentro do banco, o identificador separa; sem identificador, junta com aviso. */
function agrupar(arquivos: ArquivoLido[]): Grupo[] {
  const porBanco = new Map<string, ArquivoLido[]>();
  for (const a of arquivos) {
    const chave = a.resultado.bancoProvavel ?? '';
    porBanco.set(chave, [...(porBanco.get(chave) ?? []), a]);
  }
  const grupos: Grupo[] = [];
  for (const [chave, lista] of porBanco) {
    const banco = chave === '' ? null : chave;
    const comId = new Map<string, ArquivoLido[]>();
    const semId: ArquivoLido[] = [];
    for (const a of lista) {
      const c = a.resultado.contaFinal;
      if (c) comId.set(c, [...(comId.get(c) ?? []), a]);
      else semId.push(a);
    }
    if (comId.size === 0) grupos.push({ banco, conta: null, arquivos: semId, semDistinguir: semId.length > 1 });
    else if (comId.size === 1) {
      const [[conta, ids]] = [...comId] as [[string, ArquivoLido[]]];
      grupos.push({ banco, conta, arquivos: [...ids, ...semId], semDistinguir: semId.length > 0 });
    } else {
      for (const [conta, ids] of comId) grupos.push({ banco, conta, arquivos: ids, semDistinguir: false });
      if (semId.length > 0) grupos.push({ banco, conta: null, arquivos: semId, semDistinguir: semId.length > 1 });
    }
  }
  return grupos;
}

function montar(g: Grupo): Historico {
  const arquivos = [...g.arquivos].sort((a, b) => periodoDe(a).inicio.localeCompare(periodoDe(b).inicio) || periodoDe(a).fim.localeCompare(periodoDe(b).fim) || a.nome.localeCompare(b.nome));

  const cobertos = new Set<string>();
  for (const a of arquivos) {
    const { inicio, fim } = periodoDe(a);
    for (let m = mes(inicio); m <= mes(fim); m = proximoMes(m)) cobertos.add(m);
  }
  const mesesCobertos = [...cobertos].sort();
  const mesesFaltando: string[] = [];
  const primeiro = mesesCobertos[0] as string;
  const ultimo = mesesCobertos[mesesCobertos.length - 1] as string;
  for (let m = primeiro; m <= ultimo; m = proximoMes(m)) if (!cobertos.has(m)) mesesFaltando.push(m);

  const avisos: AvisoHistorico[] = [];
  if (g.semDistinguir) {
    avisos.push({ tipo: 'sem-identificador', mes: null, mensagem: 'Não deu para distinguir a conta destes arquivos; eles foram reunidos num só histórico. Confira se são todos da mesma conta.' });
  }
  // Encadeamento: saldo final do mês N igual ao saldo inicial do mês seguinte, em centavos e sem tolerância.
  // Só vale entre arquivos de meses consecutivos; arquivos sobrepostos ou com mês faltando entre eles não se encadeiam.
  let ref: ArquivoLido | null = null;
  for (const a of arquivos) {
    if (ref) {
      const mesRef = mes(periodoDe(ref).fim);
      if (mes(periodoDe(a).inicio) === proximoMes(mesRef)) {
        const fim = ref.resultado.conferencia.saldoFinalCentavos;
        const ini = a.resultado.conferencia.saldoInicialCentavos;
        if (fim === null || ini === null) {
          avisos.push({ tipo: 'encadeamento-nao-conferido', mes: mesRef, mensagem: `Encadeamento de ${mmaaaa(mesRef)} não conferido: um dos extratos não traz o saldo.` });
        } else if (fim !== ini) {
          avisos.push({ tipo: 'encadeamento', mes: mesRef, mensagem: `O saldo final de ${mmaaaa(mesRef)} não é igual ao saldo inicial do mês seguinte. Nenhum lançamento foi alterado; confira se falta algum extrato.` });
        }
      }
    }
    if (!ref || periodoDe(a).fim > periodoDe(ref).fim) ref = a;
  }

  return {
    bancoProvavel: g.banco,
    contaFinal: g.conta,
    arquivos,
    periodo: { inicio: periodoDe(arquivos[0] as ArquivoLido).inicio, fim: arquivos.reduce((m, a) => (periodoDe(a).fim > m ? periodoDe(a).fim : m), '') },
    mesesCobertos,
    mesesFaltando,
    avisos,
    consolidado: consolidar(arquivos),
  };
}

export function agruparHistoricos(arquivos: ArquivoLido[]): Historicos {
  const repetidos: string[] = [];
  const semHistorico: string[] = [];
  const vistos = new Set<string>();
  const usaveis: ArquivoLido[] = [];
  for (const a of arquivos) {
    const r = a.resultado;
    if (r.status === 'nao-suportado' || !r.periodo) semHistorico.push(a.nome);
    else if (vistos.has(r.hash)) repetidos.push(a.nome);
    else {
      vistos.add(r.hash);
      usaveis.push(a);
    }
  }
  return { historicos: agrupar(usaveis).map(montar), repetidos, semHistorico };
}
