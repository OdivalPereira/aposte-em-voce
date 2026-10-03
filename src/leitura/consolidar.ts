// Passo 9 (seção 5.3): consolidar os arquivos e tratar duplicidades.
//  - cada lançamento guarda a origem (arquivo e página);
//  - chave = data, valor em centavos, direção e descrição normalizada;
//  - entre arquivos de períodos sobrepostos, a mesma chave conta uma vez ("aparece em dois extratos");
//  - dentro do mesmo arquivo, chaves iguais são operações distintas e ficam;
//  - o mesmo arquivo reenviado (mesmo hash) não duplica nada.
import { chaveDeDuplicidade } from './reconstruir';
import type { ArquivoLido, Consolidado, LancamentoConsolidado, Periodo } from './tipos';

function sobrepoe(a: Periodo | null, b: Periodo | null): boolean {
  return !!a && !!b && a.inicio <= b.fim && b.inicio <= a.fim;
}

export function consolidar(arquivos: ArquivoLido[]): Consolidado {
  const repetidos: string[] = [];
  const semLancamentos: string[] = [];
  const vistos = new Set<string>();
  const mantidos: LancamentoConsolidado[] = [];
  const chaves: string[] = [];
  /** índice do arquivo → período, para decidir se dois arquivos se sobrepõem (nomes podem repetir) */
  const periodoDe = new Map<number, Periodo | null>();
  /** por lançamento mantido: índices dos arquivos em que ele aparece */
  const emArquivos: number[][] = [];

  for (const [idx, arq] of arquivos.entries()) {
    const r = arq.resultado;
    if (r.status === 'nao-suportado') {
      semLancamentos.push(arq.nome);
      continue;
    }
    if (vistos.has(r.hash)) {
      repetidos.push(arq.nome);
      continue;
    }
    vistos.add(r.hash);
    periodoDe.set(idx, r.periodo);

    const consumidos = new Set<number>(); // cada lançamento já mantido casa com no máximo um deste arquivo
    for (const l of r.lancamentos) {
      const chave = chaveDeDuplicidade(l);
      let casou = -1;
      for (let i = 0; i < mantidos.length; i++) {
        if (chaves[i] !== chave || consumidos.has(i)) continue;
        if ((emArquivos[i] as number[]).some((f) => sobrepoe(periodoDe.get(f) ?? null, r.periodo))) {
          casou = i;
          break;
        }
      }
      if (casou >= 0) {
        consumidos.add(casou);
        const m = mantidos[casou] as LancamentoConsolidado;
        m.apareceEmDoisExtratos = true;
        m.origens.push({ arquivo: arq.nome, pagina: l.pagina });
        (emArquivos[casou] as number[]).push(idx);
      } else {
        mantidos.push({ ...l, origens: [{ arquivo: arq.nome, pagina: l.pagina }], apareceEmDoisExtratos: false });
        chaves.push(chave);
        emArquivos.push([idx]);
        consumidos.add(mantidos.length - 1); // lançamento novo deste arquivo: não casa com o próximo igual do mesmo arquivo
      }
    }
  }

  mantidos.sort((a, b) => a.data.localeCompare(b.data));
  let entradas = 0;
  let saidas = 0;
  for (const l of mantidos) {
    if (l.direcao === 'entrada') entradas += l.valorCentavos;
    else saidas += l.valorCentavos;
  }
  return { lancamentos: mantidos, entradasCentavos: entradas, saidasCentavos: saidas, repetidos, semLancamentos };
}
