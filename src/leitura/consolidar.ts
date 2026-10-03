// Passo 9 (seção 5.3): consolidar os arquivos e tratar duplicidades.
//  - cada lançamento guarda a origem (arquivo e página);
//  - chave = data, valor em centavos, direção e descrição normalizada;
//  - entre arquivos de períodos sobrepostos, a mesma chave conta uma vez ("aparece em dois extratos").
//    Não há teste de sobreposição à parte: a data faz parte da chave, então duas operações só têm a mesma
//    chave se têm a mesma data, e dois arquivos que a têm em comum já se sobrepõem por definição;
//  - dentro do mesmo arquivo, chaves iguais são operações distintas e ficam;
//  - o mesmo arquivo reenviado (mesmo hash) não duplica nada.
import { chaveDeDuplicidade } from './reconstruir';
import type { ArquivoLido, Consolidado, LancamentoConsolidado } from './tipos';

export function consolidar(arquivos: ArquivoLido[]): Consolidado {
  const repetidos: string[] = [];
  const semLancamentos: string[] = [];
  const vistos = new Set<string>();
  const mantidos: LancamentoConsolidado[] = [];
  const chaves: string[] = [];

  for (const arq of arquivos) {
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

    const consumidos = new Set<number>(); // cada lançamento já mantido casa com no máximo um deste arquivo
    for (const l of r.lancamentos) {
      const chave = chaveDeDuplicidade(l);
      let casou = -1;
      for (let i = 0; i < mantidos.length; i++) {
        if (chaves[i] === chave && !consumidos.has(i)) {
          casou = i;
          break;
        }
      }
      if (casou >= 0) {
        consumidos.add(casou);
        const m = mantidos[casou] as LancamentoConsolidado;
        m.apareceEmDoisExtratos = true;
        m.origens.push({ arquivo: arq.nome, pagina: l.pagina });
      } else {
        mantidos.push({ ...l, origens: [{ arquivo: arq.nome, pagina: l.pagina }], apareceEmDoisExtratos: false });
        chaves.push(chave);
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
