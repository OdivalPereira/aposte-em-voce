// Diagnóstico por arquivo (T99). Só números e rótulos fixos: sem valores, nomes nem descrições.
// O tipo de saída não tem campo de texto livre, de modo que nada pessoal pode passar por aqui.
import { ROTULO_STATUS, type Motivo, type ResultadoArquivo, type SituacaoSaldo, type Status } from './tipos';

export interface DiagnosticoArquivo {
  /** "Arquivo 1", "Arquivo 2"...: o nome do arquivo pode ter nome de pessoa e não entra */
  rotulo: string;
  paginas: number;
  linhasCandidatas: number;
  lancamentosReconstruidos: number;
  conferenciaDeSaldo: SituacaoSaldo;
  /** linhas com saldo conferidas e divergentes (contagens); `null` sem saldo por linha */
  progressao: { verificadas: number; divergentes: number } | null;
  status: Status;
  statusRotulo: string;
  motivo: Motivo | null;
}

export function diagnosticar(resultados: ResultadoArquivo[]): DiagnosticoArquivo[] {
  return resultados.map((r, i) => ({
    rotulo: `Arquivo ${i + 1}`,
    paginas: r.paginas,
    linhasCandidatas: r.linhasCandidatas,
    lancamentosReconstruidos: r.lancamentos.length,
    conferenciaDeSaldo: r.conferencia.situacao,
    progressao: r.conferencia.progressao ? { verificadas: r.conferencia.progressao.verificadas, divergentes: r.conferencia.progressao.divergentes } : null,
    status: r.status,
    statusRotulo: ROTULO_STATUS[r.status],
    motivo: r.motivo,
  }));
}
