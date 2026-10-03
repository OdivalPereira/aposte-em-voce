#!/usr/bin/env python3
"""Calibração empírica determinística do gatilho de rigor da Sociedade do Código.

Avalia retrospectivamente o histórico de etapas e rodadas em registro.json
para calcular a acurácia preditiva dos 5 fatores heurísticos de elevação de rigor (Q22):
1. Volume de arquivos tocados (> 3 arquivos);
2. Novos contratos de dados ou alterações de schema/interfaces públicas;
3. Complexidade algorítmica ou concorrência;
4. Persistência física e mutação de estado em disco;
5. Criticidade sistêmica (integridade, segurança ou regras financeiras).

Calcula a matriz de confusão (VPs, FPs, FNs, VNs), taxas de sobrecarga cerimonial,
risco de defeito residual não contido e eficácia preditiva de cada fator individual.

Sem dependências externas: usa apenas a biblioteca padrão do Python.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from sc_registro import carregar_dados_registro, derivar_estado
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sc_registro import carregar_dados_registro, derivar_estado
    except Exception:
        carregar_dados_registro = None
        derivar_estado = None

FATORES_NOMES = [
    'volume_arquivos',
    'novos_contratos',
    'complexidade',
    'persistencia',
    'criticidade'
]

PALAVRAS_CHAVE_FATORES = {
    'novos_contratos': re.compile(r'\b(contrato|interface|schema|protocolo|layout|assinatura|api|formato)\b', re.I),
    'complexidade': re.compile(r'\b(algoritmo|parser|maquina\s+de\s+estados|concorr[êe]ncia|transa[çc][ãa]o|complexidade|regras?\s+de\s+neg[óo]cio|auditoria)\b', re.I),
    'persistencia': re.compile(r'\b(banco|persist[êe]ncia|disco|arquivo|sqlite|json|estado|muta[çc][ãa]o|grav|escrita)\b', re.I),
    'criticidade': re.compile(r'\b(seguran[çc]a|autentica[çc][ãa]o|autoriza[çc][ãa]o|financeir[oa]|saldo|integridade|inviol[áa]vel|cripto|chave|permiss[ãa]o)\b', re.I),
}


def extrair_fatores_etapa(etapa: Dict[str, Any], limiar_arquivos: int = 3) -> Dict[str, bool]:
    """Extrai ou avalia a ativação dos 5 fatores heurísticos para uma etapa."""
    # Se a etapa possui anotação explícita de fatores, respeite-a
    if 'fatores_rigor' in etapa and isinstance(etapa['fatores_rigor'], dict):
        res = {}
        for f in FATORES_NOMES:
            res[f] = bool(etapa['fatores_rigor'].get(f, False))
        return res

    texto_completo = []
    texto_completo.append(str(etapa.get('objetivo', '')))
    for t_id, t in etapa.get('tarefas', {}).items():
        texto_completo.append(str(t.get('descricao', '')))
        texto_completo.append(str(t.get('tipo', '')))
    for c_id, c in etapa.get('criterios', {}).items():
        texto_completo.append(str(c_id))
    corpo_texto = ' '.join(texto_completo)

    # 1. Volume de arquivos
    arquivos_citados = set()
    for t in etapa.get('tarefas', {}).values():
        if isinstance(t.get('arquivos'), list):
            arquivos_citados.update(t['arquivos'])
    # Heurística textual para caminhos de arquivo caso não estejam estruturados
    for match in re.findall(r'[\w./-]+\.(?:py|md|json|ts|js|html|css|sql|sh)', corpo_texto):
        arquivos_citados.add(match)
    f_vol = len(arquivos_citados) > limiar_arquivos

    # 2. Novos contratos
    f_contratos = bool(PALAVRAS_CHAVE_FATORES['novos_contratos'].search(corpo_texto)) or (etapa.get('classificacao_impacto') == 'alto')

    # 3. Complexidade algorítmica
    f_complexidade = bool(PALAVRAS_CHAVE_FATORES['complexidade'].search(corpo_texto))

    # 4. Persistência
    f_persistencia = bool(PALAVRAS_CHAVE_FATORES['persistencia'].search(corpo_texto))

    # 5. Criticidade sistêmica
    f_criticidade = bool(PALAVRAS_CHAVE_FATORES['criticidade'].search(corpo_texto))

    return {
        'volume_arquivos': f_vol,
        'novos_contratos': f_contratos,
        'complexidade': f_complexidade,
        'persistencia': f_persistencia,
        'criticidade': f_criticidade,
    }


def avaliar_desfecho_etapa(etapa: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia o desfecho real de qualidade e retrabalho da etapa."""
    achados = etapa.get('achados', {})
    bloqueadores = [a for a in achados.values() if a.get('severidade') == 'bloqueador']
    relevantes = [a for a in achados.values() if a.get('severidade') == 'relevante']
    opcionais = [a for a in achados.values() if a.get('severidade') == 'opcional']

    pareceres = etapa.get('pareceres', [])
    rejeicoes = [p for p in pareceres if p.get('veredito') == 'nao_aceitar']
    aceites_com_ressalva = [p for p in pareceres if p.get('veredito') == 'aceitar_com_ressalvas']

    # Uma etapa demandou rigor elevado de fato se apresentou defeitos impeditivos
    # ou complexidade que justificou intervenção sênior
    necessitou_rigor = (
        len(bloqueadores) > 0 or
        len(rejeicoes) > 0 or
        len(relevantes) >= 2 or
        len(pareceres) > 1
    )

    return {
        'necessitou_rigor': necessitou_rigor,
        'total_bloqueadores': len(bloqueadores),
        'total_relevantes': len(relevantes),
        'total_opcionais': len(opcionais),
        'total_pareceres': len(pareceres),
        'total_rejeicoes': len(rejeicoes),
        'total_ressalvas': len(aceites_com_ressalva),
    }


def calibrar_gatilho_rigor(
    registro_dados: Dict[str, Any],
    limiar_fatores: int = 2,
    etapas_filtro: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Processa dados do registro e executa a calibração retrospectiva."""
    if derivar_estado is not None:
        estado = derivar_estado(registro_dados)
        etapas_map = estado.get('etapas', {})
    else:
        etapas_map = {}

    if not etapas_map:
        return {
            'sucesso': False,
            'motivo': 'Nenhuma etapa encontrada no registro para calibração.',
            'total_etapas': 0
        }

    vp = 0  # Rigor elevado e de fato necessário (bloqueadores contidos)
    fp = 0  # Rigor elevado mas desnecessário (etapa trivial, zero defeitos)
    fn = 0  # Rigor baixo mas sofreu defeitos bloqueadores não antecipados
    vn = 0  # Rigor baixo e etapa limpa (eficiência sem sobrecarga)

    detalhes_etapas = []
    estatisticas_fatores = {f: {'presente_em_vp': 0, 'presente_em_fp': 0, 'presente_em_fn': 0, 'total': 0} for f in FATORES_NOMES}

    for e_id, etapa in etapas_map.items():
        if etapas_filtro and e_id not in etapas_filtro:
            continue

        fatores = extrair_fatores_etapa(etapa)
        total_fatores_ativos = sum(1 for ativo in fatores.values() if ativo)

        # Regra do gatilho: elevação de rigor se atingir o limiar de fatores
        # ou se o nível declarado originalmente for >= 2
        nivel_num = int(etapa.get('nivel', '2')) if str(etapa.get('nivel', '2')).isdigit() else 2
        elevou_rigor_predito = (total_fatores_ativos >= limiar_fatores) or (nivel_num >= 2)

        desfecho = avaliar_desfecho_etapa(etapa)
        necessitou_rigor = desfecho['necessitou_rigor']

        classificacao = ''
        if elevou_rigor_predito and necessitou_rigor:
            vp += 1
            classificacao = 'VP'
            for f, ativo in fatores.items():
                if ativo:
                    estatisticas_fatores[f]['presente_em_vp'] += 1
                    estatisticas_fatores[f]['total'] += 1
        elif elevou_rigor_predito and not necessitou_rigor:
            fp += 1
            classificacao = 'FP'
            for f, ativo in fatores.items():
                if ativo:
                    estatisticas_fatores[f]['presente_em_fp'] += 1
                    estatisticas_fatores[f]['total'] += 1
        elif not elevou_rigor_predito and necessitou_rigor:
            fn += 1
            classificacao = 'FN'
            for f, ativo in fatores.items():
                if ativo:
                    estatisticas_fatores[f]['presente_em_fn'] += 1
                    estatisticas_fatores[f]['total'] += 1
        else:
            vn += 1
            classificacao = 'VN'
            for f, ativo in fatores.items():
                if ativo:
                    estatisticas_fatores[f]['total'] += 1

        detalhes_etapas.append({
            'etapa_id': e_id,
            'nivel': etapa.get('nivel', '2'),
            'fatores': fatores,
            'total_fatores_ativos': total_fatores_ativos,
            'elevou_rigor_predito': elevou_rigor_predito,
            'necessitou_rigor_real': necessitou_rigor,
            'classificacao': classificacao,
            'bloqueadores': desfecho['total_bloqueadores'],
            'relevantes': desfecho['total_relevantes'],
            'rejeicoes': desfecho['total_rejeicoes'],
        })

    total_analisado = vp + fp + fn + vn
    if total_analisado == 0:
        return {
            'sucesso': False,
            'motivo': 'Nenhuma etapa atendeu aos filtros para análise.',
            'total_etapas': 0
        }

    sensibilidade = vp / (vp + fn) if (vp + fn) > 0 else 1.0
    especificidade = vn / (vn + fp) if (vn + fp) > 0 else 1.0
    precisao = vp / (vp + fp) if (vp + fp) > 0 else 1.0
    acuracia = (vp + vn) / total_analisado if total_analisado > 0 else 1.0
    taxa_sobrecarga = fp / (fp + vn) if (fp + vn) > 0 else 0.0
    taxa_risco_residual = fn / (fn + vp) if (fn + vp) > 0 else 0.0

    # Avaliação diagnóstica de recomendações
    recomendacoes = []
    if taxa_risco_residual > 0.15:
        recomendacoes.append(
            f'ALERTA DE RISCO RESIDUAL ({taxa_risco_residual:.1%}): O gatilho atual permitiu que etapas com defeitos bloqueadores operassem com rigor insuficiente. Recomenda-se reduzir o limiar de ativação para {max(1, limiar_fatores - 1)} fatores.'
        )
    elif taxa_sobrecarga > 0.40:
        recomendacoes.append(
            f'ALERTA DE SOBRECARGA CERIMONIAL ({taxa_sobrecarga:.1%}): Muitas etapas triviais foram elevadas desnecessariamente. Recomenda-se elevar o limiar de ativação para {limiar_fatores + 1} fatores.'
        )
    else:
        recomendacoes.append(
            f'CALIBRAÇÃO ADEQUADA: Equilíbrio consistente entre proteção contra defeitos ({sensibilidade:.1%} sensibilidade) e controle de sobrecarga cerimonial ({especificidade:.1%} especificidade).'
        )

    # Identifica fator com maior correlação positiva com achados reais
    fator_destaque = None
    max_precisao_fator = -1.0
    for f, stats in estatisticas_fatores.items():
        if stats['total'] > 0:
            prec = stats['presente_em_vp'] / stats['total']
            if prec > max_precisao_fator:
                max_precisao_fator = prec
                fator_destaque = f

    if fator_destaque:
        recomendacoes.append(
            f'FATOR MAIS PREDITIVO: "{fator_destaque}" apresentou a maior correlação com a detecção real de defeitos ({max_precisao_fator:.1%} de precisão).'
        )

    return {
        'sucesso': True,
        'total_etapas': total_analisado,
        'limiar_fatores': limiar_fatores,
        'matriz_confusao': {
            'verdadeiros_positivos': vp,
            'falsos_positivos': fp,
            'falsos_negativos': fn,
            'verdadeiros_negativos': vn,
        },
        'metricas': {
            'sensibilidade': round(sensibilidade, 4),
            'especificidade': round(especificidade, 4),
            'precisao': round(precisao, 4),
            'acuracia': round(acuracia, 4),
            'taxa_sobrecarga_cerimonial': round(taxa_sobrecarga, 4),
            'taxa_risco_residual': round(taxa_risco_residual, 4),
        },
        'estatisticas_fatores': estatisticas_fatores,
        'recomendacoes': recomendacoes,
        'detalhes_etapas': detalhes_etapas,
    }


def formatar_relatorio_texto(res: Dict[str, Any]) -> str:
    """Formata o resultado da calibração em relatório textual legível."""
    if not res.get('sucesso'):
        return f"FALHA NA CALIBRAÇÃO: {res.get('motivo')}"

    mc = res['matriz_confusao']
    met = res['metricas']

    linhas = [
        "==================================================================",
        "  CALIBRAÇÃO EMPÍRICA DO GATILHO DE RIGOR (REGRA DOS 5 FATORES)  ",
        "==================================================================",
        f"Etapas analisadas: {res['total_etapas']} | Limiar de ativação: >= {res['limiar_fatores']} fatores",
        "",
        "--- MATRIZ DE CONFUSÃO DE RIGOR ---",
        f"  [VP] Rigor elevado necessário (defeitos prevenidos):  {mc['verdadeiros_positivos']}",
        f"  [FP] Sobrecarga cerimonial (rigor alto dispensável):  {mc['falsos_positivos']}",
        f"  [FN] Risco residual não contido (rigor insuficiente):  {mc['falsos_negativos']}",
        f"  [VN] Eficiência equilibrada (rigor baixo limpo):       {mc['verdadeiros_negativos']}",
        "",
        "--- INDICADORES ANALÍTICOS DE EFICÁCIA ---",
        f"  Sensibilidade (Recall):           {met['sensibilidade']:.1%}",
        f"  Especificidade:                   {met['especificidade']:.1%}",
        f"  Precisão preditiva:               {met['precisao']:.1%}",
        f"  Acurácia global:                  {met['acuracia']:.1%}",
        f"  Taxa de Sobrecarga Cerimonial:    {met['taxa_sobrecarga_cerimonial']:.1%}",
        f"  Taxa de Risco de Defeito Residual:{met['taxa_risco_residual']:.1%}",
        "",
        "--- RECOMENDAÇÕES DE GOVERNANÇA ---"
    ]
    for r in res.get('recomendacoes', []):
        linhas.append(f"  • {r}")

    linhas.append("")
    linhas.append("--- DETALHAMENTO POR ETAPA ---")
    linhas.append(f"{'Etapa':<10} {'Nível':<6} {'Fatores':<8} {'Predição':<10} {'Real':<8} {'Classif':<8} {'Achados (B/R)'}")
    linhas.append("-" * 66)
    for d in res.get('detalhes_etapas', []):
        pred_txt = "Elevado" if d['elevou_rigor_predito'] else "Normal"
        real_txt = "Crítico" if d['necessitou_rigor_real'] else "Limpo"
        ach_txt = f"{d['bloqueadores']}b / {d['relevantes']}r"
        linhas.append(
            f"{d['etapa_id']:<10} {d['nivel']:<6} {d['total_fatores_ativos']:<8} {pred_txt:<10} {real_txt:<8} {d['classificacao']:<8} {ach_txt}"
        )

    linhas.append("==================================================================")
    return "\n".join(linhas)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--registro',
        default='sociedade/registro.json',
        help='Caminho do arquivo registro.json (padrão: sociedade/registro.json)'
    )
    parser.add_argument(
        '--limiar-fatores',
        type=int,
        default=2,
        help='Limiar mínimo de fatores ativos para recomendar elevação de nível (padrão: 2)'
    )
    parser.add_argument(
        '--formato',
        choices=['texto', 'json'],
        default='texto',
        help='Formato de saída do relatório (padrão: texto)'
    )
    parser.add_argument(
        '--saida',
        help='Arquivo de destino para gravar o relatório'
    )
    parser.add_argument(
        '--etapas',
        nargs='*',
        help='Lista de IDs de etapas para filtrar a calibração'
    )

    args = parser.parse_args(argv)
    p_reg = Path(args.registro)

    if not p_reg.is_file():
        print(f"ERRO: Arquivo de registro não encontrado: {p_reg}", file=sys.stderr)
        return 2

    try:
        if carregar_dados_registro is not None:
            dados = carregar_dados_registro(p_reg)
        else:
            dados = json.loads(p_reg.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"ERRO ao carregar registro.json: {e}", file=sys.stderr)
        return 1

    resultado = calibrar_gatilho_rigor(
        dados,
        limiar_fatores=args.limiar_fatores,
        etapas_filtro=args.etapas
    )

    if args.formato == 'json':
        conteudo = json.dumps(resultado, indent=2, ensure_ascii=False)
    else:
        conteudo = formatar_relatorio_texto(resultado)

    if args.saida:
        p_saida = Path(args.saida)
        p_saida.parent.mkdir(parents=True, exist_ok=True)
        p_saida.write_text(conteudo, encoding='utf-8')
        print(f"Relatório de calibração gravado em: {args.saida}")
    else:
        print(conteudo)

    return 0 if resultado.get('sucesso', False) else 1


if __name__ == '__main__':
    sys.exit(main())
