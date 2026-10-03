"""Módulo isolado de conciliação bancária para o piloto Palandir (SC-E4).

Demonstra regras contábeis, tratamento de 30-40 lançamentos, detecção de divergências,
lote 1:N (folha salarial), tarifas bancárias, provisões sem trânsito e retomada controlada (Q45, Q46).
"""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _to_decimal(val: Any) -> Decimal:
    return Decimal(str(val)).quantize(Decimal('0.01'))


def calcular_hash_dados(dados: Any) -> str:
    """Calcula hash SHA-256 estável sobre estrutura de dados."""
    payload = json.dumps(dados, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


class ConciliadorBancario:
    def __init__(self, extrato: List[Dict[str, Any]], razao: List[Dict[str, Any]]):
        self.extrato = extrato
        self.razao = razao
        self.hash_extrato = calcular_hash_dados(extrato)
        self.hash_razao = calcular_hash_dados(razao)
        
        # Estado de conciliação
        self.indice_progresso = 0
        self.conciliados_1_para_1: List[Dict[str, Any]] = []
        self.conciliados_1_para_n: List[Dict[str, Any]] = []
        self.divergencias_valor: List[Dict[str, Any]] = []
        self.pendencias_extrato: List[Dict[str, Any]] = []
        self.razao_consumido_ids = set()

    def salvar_checkpoint(self) -> Dict[str, Any]:
        """Exporta estado atual para permitir interrupção e retomada (Q46)."""
        return {
            'indice_progresso': self.indice_progresso,
            'hash_extrato': self.hash_extrato,
            'hash_razao': self.hash_razao,
            'conciliados_1_para_1': list(self.conciliados_1_para_1),
            'conciliados_1_para_n': list(self.conciliados_1_para_n),
            'divergencias_valor': list(self.divergencias_valor),
            'pendencias_extrato': list(self.pendencias_extrato),
            'razao_consumido_ids': sorted(list(self.razao_consumido_ids)),
        }

    def carregar_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Restaura estado prévio sem refazer trabalho ou duplicar lançamentos."""
        if checkpoint['hash_extrato'] != self.hash_extrato or checkpoint['hash_razao'] != self.hash_razao:
            raise ValueError('Checkpoint incompatível com os dados de extrato/razão carregados.')
        self.indice_progresso = checkpoint['indice_progresso']
        self.conciliados_1_para_1 = list(checkpoint['conciliados_1_para_1'])
        self.conciliados_1_para_n = list(checkpoint['conciliados_1_para_n'])
        self.divergencias_valor = list(checkpoint['divergencias_valor'])
        self.pendencias_extrato = list(checkpoint['pendencias_extrato'])
        self.razao_consumido_ids = set(checkpoint['razao_consumido_ids'])

    def processar_passo(self) -> bool:
        """Processa um lançamento do extrato bancário. Retorna True se processou, False se concluiu."""
        if self.indice_progresso >= len(self.extrato):
            return False

        item_extrato = self.extrato[self.indice_progresso]
        ext_id = item_extrato['id']
        ext_doc = item_extrato.get('documento', '')
        ext_valor_dec = abs(_to_decimal(item_extrato['valor']))
        ext_tipo = item_extrato['tipo']

        # 1. Caso especial: Folha consolidada (1:N)
        if ext_doc.startswith('FOLHA-') and item_extrato.get('categoria') == 'folha':
            filhos = [
                r for r in self.razao
                if r['id'] not in self.razao_consumido_ids
                and r.get('categoria') == 'folha'
                and r.get('documento', '').startswith(ext_doc)
            ]
            soma_filhos = sum((_to_decimal(f['valor']) for f in filhos), Decimal('0.00'))
            if filhos and soma_filhos == ext_valor_dec:
                for f in filhos:
                    self.razao_consumido_ids.add(f['id'])
                self.conciliados_1_para_n.append({
                    'extrato_id': ext_id,
                    'documento': ext_doc,
                    'valor_extrato': float(ext_valor_dec),
                    'razao_ids': [f['id'] for f in filhos],
                    'quantidade_itens': len(filhos)
                })
                self.indice_progresso += 1
                return True

        # 2. Busca exata 1:1 por documento e valor
        candidatos_doc = [
            r for r in self.razao
            if r['id'] not in self.razao_consumido_ids
            and r.get('documento') == ext_doc
        ]

        if candidatos_doc:
            match = next((c for c in candidatos_doc if abs(_to_decimal(c['valor'])) == ext_valor_dec), None)
            if match:
                self.razao_consumido_ids.add(match['id'])
                self.conciliados_1_para_1.append({
                    'extrato_id': ext_id,
                    'razao_id': match['id'],
                    'documento': ext_doc,
                    'valor': float(ext_valor_dec),
                    'status': 'conciliado_exato'
                })
                self.indice_progresso += 1
                return True
            else:
                # Documento confere mas valor difere (divergência / desconto / acréscimo)
                candidato = candidatos_doc[0]
                self.razao_consumido_ids.add(candidato['id'])
                self.divergencias_valor.append({
                    'extrato_id': ext_id,
                    'razao_id': candidato['id'],
                    'documento': ext_doc,
                    'valor_extrato': float(ext_valor_dec),
                    'valor_razao': float(_to_decimal(candidato['valor'])),
                    'diferenca': float(ext_valor_dec - _to_decimal(candidato['valor']))
                })
                self.indice_progresso += 1
                return True

        # 3. Se não achou por documento, tenta buscar por valor único não consumido (se aplicável)
        # Se for tarifa bancária ou não encontrado no razão:
        self.pendencias_extrato.append({
            'extrato_id': ext_id,
            'descricao': item_extrato['descricao'],
            'valor': float(_to_decimal(item_extrato['valor'])),
            'categoria': item_extrato.get('categoria', 'outros'),
            'motivo': 'tarifa_a_apropriar' if item_extrato.get('categoria') == 'tarifa' else 'sem_registro_contabil'
        })
        self.indice_progresso += 1
        return True

    def executar_ate_o_fim(self, limite_passos: Optional[int] = None) -> None:
        """Executa conciliação passo a passo até o final ou atingir limite de passos."""
        passos = 0
        while self.processar_passo():
            passos += 1
            if limite_passos is not None and passos >= limite_passos:
                break

    def obter_relatorio_final(self) -> Dict[str, Any]:
        """Gera o balanço e relatório final consolidado de conciliação."""
        pendencias_razao = [
            {
                'razao_id': r['id'],
                'documento': r.get('documento', ''),
                'valor': float(_to_decimal(r['valor'])),
                'historico': r.get('historico', ''),
                'categoria': r.get('categoria', '')
            }
            for r in self.razao
            if r['id'] not in self.razao_consumido_ids
        ]

        total_extrato = len(self.extrato)
        total_1_para_1 = len(self.conciliados_1_para_1)
        total_1_para_n = len(self.conciliados_1_para_n)
        total_divergencias = len(self.divergencias_valor)
        total_pend_extrato = len(self.pendencias_extrato)
        total_pend_razao = len(pendencias_razao)

        resultado = {
            'resumo': {
                'total_lancamentos_extrato': total_extrato,
                'total_conciliados_1_para_1': total_1_para_1,
                'total_conciliados_1_para_n': total_1_para_n,
                'total_divergencias_valor': total_divergencias,
                'total_pendencias_extrato': total_pend_extrato,
                'total_pendencias_razao': total_pend_razao,
                'taxa_conciliacao_automatica': round((total_1_para_1 + total_1_para_n) / total_extrato * 100, 2)
            },
            'detalhes': {
                'conciliados_1_para_1': self.conciliados_1_para_1,
                'conciliados_1_para_n': self.conciliados_1_para_n,
                'divergencias_valor': self.divergencias_valor,
                'pendencias_extrato': self.pendencias_extrato,
                'pendencias_razao': pendencias_razao
            },
            'integridade': {
                'hash_extrato': self.hash_extrato,
                'hash_razao': self.hash_razao
            }
        }
        resultado['integridade']['hash_resultado'] = calcular_hash_dados(resultado)
        return resultado
