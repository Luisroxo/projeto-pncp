"""
API de busca de licitações utilizando Elasticsearch.
Este módulo implementa endpoints para busca de licitações.
"""

import logging
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify
from datetime import datetime
import json

from src.utils.elasticsearch_service import get_elasticsearch_service
from src.models.licitacao import Licitacao, db

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('search_api')

# Criação do blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

# Obtém o serviço de Elasticsearch
es_service = get_elasticsearch_service()

@search_bp.route('/licitacoes', methods=['GET'])
def search_licitacoes():
    """
    Endpoint para busca de licitações.
    
    Query params:
        q: Termo de busca (texto livre)
        modalidade: Filtro por modalidade
        uf: Filtro por UF
        valor_min: Valor mínimo estimado
        valor_max: Valor máximo estimado
        data_abertura_min: Data mínima de abertura (formato ISO)
        data_abertura_max: Data máxima de abertura (formato ISO)
        page: Página de resultados (default: 1)
        size: Tamanho da página (default: 10)
    
    Returns:
        JSON com resultados da busca.
    """
    try:
        # Parâmetros de busca
        termo = request.args.get('q', '')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 10))
        
        # Calcula o índice inicial para paginação
        from_index = (page - 1) * size
        
        # Constrói filtros
        filters = {}
        
        # Filtro de modalidade
        if 'modalidade' in request.args:
            filters['modalidade'] = request.args.get('modalidade')
        
        # Filtro de UF
        if 'uf' in request.args:
            filters['uf'] = request.args.get('uf')
        
        # Filtro de valor mínimo
        if 'valor_min' in request.args:
            try:
                filters['valor_min'] = float(request.args.get('valor_min'))
            except ValueError:
                pass
        
        # Filtro de valor máximo
        if 'valor_max' in request.args:
            try:
                filters['valor_max'] = float(request.args.get('valor_max'))
            except ValueError:
                pass
        
        # Filtro de data de abertura mínima
        if 'data_abertura_min' in request.args:
            filters['data_abertura_min'] = request.args.get('data_abertura_min')
        
        # Filtro de data de abertura máxima
        if 'data_abertura_max' in request.args:
            filters['data_abertura_max'] = request.args.get('data_abertura_max')
        
        # Executa a busca
        results = es_service.search_text(
            text=termo,
            filters=filters,
            size=size,
            from_=from_index
        )
        
        # Processa os resultados
        hits = results.get('hits', {})
        total = hits.get('total', {}).get('value', 0)
        items = []
        
        for hit in hits.get('hits', []):
            source = hit.get('_source', {})
            score = hit.get('_score', 0)
            
            # Adiciona o score ao item
            source['_score'] = score
            
            items.append(source)
        
        # Registra a busca no histórico (opcional, implementar conforme necessidade)
        
        # Retorna os resultados formatados
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'size': size,
                'pages': (total + size - 1) // size,
                'items': items
            }
        })
        
    except Exception as e:
        logger.error(f"Erro na busca de licitações: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@search_bp.route('/licitacoes/<int:licitacao_id>', methods=['GET'])
def get_licitacao(licitacao_id):
    """
    Endpoint para obter detalhes de uma licitação específica.
    
    Args:
        licitacao_id: ID da licitação.
    
    Returns:
        JSON com detalhes da licitação.
    """
    try:
        # Busca a licitação no banco de dados
        licitacao = Licitacao.query.get(licitacao_id)
        
        if not licitacao:
            return jsonify({
                'success': False,
                'error': 'Licitação não encontrada'
            }), 404
        
        # Converte para dicionário
        licitacao_dict = licitacao.to_dict()
        
        # Se houver dados completos em JSON, adiciona ao resultado
        if licitacao.dados_completos:
            try:
                dados_completos = json.loads(licitacao.dados_completos)
                licitacao_dict['dados_completos'] = dados_completos
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': licitacao_dict
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter licitação {licitacao_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@search_bp.route('/modalidades', methods=['GET'])
def get_modalidades():
    """
    Endpoint para obter lista de modalidades disponíveis.
    
    Returns:
        JSON com lista de modalidades.
    """
    try:
        # Consulta agregada para obter modalidades distintas
        query = {
            "size": 0,
            "aggs": {
                "modalidades": {
                    "terms": {
                        "field": "modalidade.keyword",
                        "size": 100
                    }
                }
            }
        }
        
        results = es_service.search(query)
        
        modalidades = []
        for bucket in results.get('aggregations', {}).get('modalidades', {}).get('buckets', []):
            modalidades.append({
                'nome': bucket.get('key'),
                'count': bucket.get('doc_count')
            })
        
        return jsonify({
            'success': True,
            'data': modalidades
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter modalidades: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@search_bp.route('/ufs', methods=['GET'])
def get_ufs():
    """
    Endpoint para obter lista de UFs disponíveis.
    
    Returns:
        JSON com lista de UFs.
    """
    try:
        # Consulta agregada para obter UFs distintas
        query = {
            "size": 0,
            "aggs": {
                "ufs": {
                    "terms": {
                        "field": "uf",
                        "size": 30
                    }
                }
            }
        }
        
        results = es_service.search(query)
        
        ufs = []
        for bucket in results.get('aggregations', {}).get('ufs', {}).get('buckets', []):
            ufs.append({
                'sigla': bucket.get('key'),
                'count': bucket.get('doc_count')
            })
        
        return jsonify({
            'success': True,
            'data': ufs
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter UFs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@search_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Endpoint para obter estatísticas gerais das licitações.
    
    Returns:
        JSON com estatísticas.
    """
    try:
        # Consulta agregada para obter estatísticas
        query = {
            "size": 0,
            "aggs": {
                "valor_total": {
                    "sum": {
                        "field": "valor_estimado"
                    }
                },
                "valor_medio": {
                    "avg": {
                        "field": "valor_estimado"
                    }
                },
                "valor_max": {
                    "max": {
                        "field": "valor_estimado"
                    }
                },
                "valor_min": {
                    "min": {
                        "field": "valor_estimado"
                    }
                },
                "por_situacao": {
                    "terms": {
                        "field": "situacao.keyword",
                        "size": 10
                    }
                },
                "por_mes": {
                    "date_histogram": {
                        "field": "data_publicacao",
                        "calendar_interval": "month",
                        "format": "yyyy-MM"
                    }
                }
            }
        }
        
        results = es_service.search(query)
        
        aggs = results.get('aggregations', {})
        
        stats = {
            'total_licitacoes': results.get('hits', {}).get('total', {}).get('value', 0),
            'valor_total': aggs.get('valor_total', {}).get('value', 0),
            'valor_medio': aggs.get('valor_medio', {}).get('value', 0),
            'valor_max': aggs.get('valor_max', {}).get('value', 0),
            'valor_min': aggs.get('valor_min', {}).get('value', 0),
            'por_situacao': [
                {
                    'situacao': bucket.get('key'),
                    'count': bucket.get('doc_count')
                }
                for bucket in aggs.get('por_situacao', {}).get('buckets', [])
            ],
            'por_mes': [
                {
                    'mes': bucket.get('key_as_string'),
                    'count': bucket.get('doc_count')
                }
                for bucket in aggs.get('por_mes', {}).get('buckets', [])
            ]
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@search_bp.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificar a saúde do serviço de busca.
    
    Returns:
        JSON com status de saúde.
    """
    try:
        # Verifica a saúde do Elasticsearch
        es_health = es_service.health_check()
        # Corrige serialização do ObjectApiResponse
        if hasattr(es_health, 'body'):
            es_health_json = es_health.body
        else:
            es_health_json = es_health
        # Verifica a conexão com o banco de dados
        db_health = True
        try:
            db.session.execute("SELECT 1")
        except:
            db_health = False
        return jsonify({
            'success': True,
            'data': {
                'elasticsearch': es_health_json,
                'database': {
                    'status': 'ok' if db_health else 'error'
                },
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
