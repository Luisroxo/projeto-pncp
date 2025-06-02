"""
Script para testar a indexação e busca de licitações no Elasticsearch.
Este script valida o funcionamento da integração com Elasticsearch.
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta

# Configurar o path para importar os módulos do projeto
sys.path.append('/home/ubuntu/modulo-encontrar')

from src.utils.elasticsearch_service import get_elasticsearch_service
from src.integrations.pncp_sync import PNCPSyncService
from src.models.licitacao import Licitacao, db

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_elasticsearch')

def test_elasticsearch_connection():
    """Testa a conexão com o Elasticsearch."""
    logger.info("Testando conexão com Elasticsearch...")
    
    es_service = get_elasticsearch_service()
    health = es_service.health_check()
    
    logger.info(f"Status do Elasticsearch: {health.get('status', 'desconhecido')}")
    logger.info(f"Detalhes: {json.dumps(health, indent=2)}")
    
    return health.get('status') in ['green', 'yellow']

def test_index_creation():
    """Testa a criação do índice de licitações."""
    logger.info("Testando criação do índice de licitações...")
    
    es_service = get_elasticsearch_service()
    result = es_service.create_index()
    
    logger.info(f"Resultado da criação do índice: {result}")
    
    return result

def test_document_indexing():
    """Testa a indexação de um documento de teste."""
    logger.info("Testando indexação de documento...")
    
    es_service = get_elasticsearch_service()
    
    # Cria um documento de teste
    test_doc = {
        'id': 999999,
        'id_externo': 'TEST_DOC_001',
        'fonte': 'TESTE',
        'objeto': 'Licitação de teste para validação do Elasticsearch',
        'descricao': 'Esta é uma licitação fictícia criada para testar a indexação no Elasticsearch',
        'valor_estimado': 100000.0,
        'modalidade': 'Pregão Eletrônico',
        'situacao': 'Em andamento',
        'data_publicacao': datetime.now().isoformat(),
        'data_abertura': (datetime.now() + timedelta(days=15)).isoformat(),
        'orgao_nome': 'Órgão de Teste',
        'orgao_id': '00000000000000',
        'municipio': 'Cidade de Teste',
        'uf': 'TE',
        'data_criacao': datetime.now().isoformat(),
        'data_atualizacao': datetime.now().isoformat()
    }
    
    # Indexa o documento
    result = es_service.index_document(test_doc['id'], test_doc)
    logger.info(f"Resultado da indexação: {result}")
    
    # Verifica se o documento foi indexado corretamente
    indexed_doc = es_service.get_document(test_doc['id'])
    
    if indexed_doc:
        logger.info("Documento recuperado com sucesso:")
        logger.info(f"{json.dumps(indexed_doc, indent=2)}")
        
        # Limpa o documento de teste
        es_service.delete_document(test_doc['id'])
        logger.info("Documento de teste removido")
        
        return True
    else:
        logger.error("Falha ao recuperar o documento indexado")
        return False

def test_search_functionality():
    """Testa a funcionalidade de busca."""
    logger.info("Testando funcionalidade de busca...")
    
    es_service = get_elasticsearch_service()
    
    # Cria alguns documentos de teste para busca
    test_docs = [
        {
            'id': 1000001,
            'id_externo': 'TEST_SEARCH_001',
            'fonte': 'TESTE',
            'objeto': 'Aquisição de computadores para escritório',
            'descricao': 'Compra de 50 computadores desktop para uso administrativo',
            'valor_estimado': 250000.0,
            'modalidade': 'Pregão Eletrônico',
            'situacao': 'Aberta',
            'data_publicacao': datetime.now().isoformat(),
            'data_abertura': (datetime.now() + timedelta(days=10)).isoformat(),
            'orgao_nome': 'Secretaria de Administração',
            'orgao_id': '11111111111111',
            'municipio': 'São Paulo',
            'uf': 'SP',
            'data_criacao': datetime.now().isoformat(),
            'data_atualizacao': datetime.now().isoformat()
        },
        {
            'id': 1000002,
            'id_externo': 'TEST_SEARCH_002',
            'fonte': 'TESTE',
            'objeto': 'Contratação de serviços de limpeza',
            'descricao': 'Serviços de limpeza para prédio administrativo',
            'valor_estimado': 120000.0,
            'modalidade': 'Tomada de Preços',
            'situacao': 'Aberta',
            'data_publicacao': datetime.now().isoformat(),
            'data_abertura': (datetime.now() + timedelta(days=20)).isoformat(),
            'orgao_nome': 'Secretaria de Infraestrutura',
            'orgao_id': '22222222222222',
            'municipio': 'Rio de Janeiro',
            'uf': 'RJ',
            'data_criacao': datetime.now().isoformat(),
            'data_atualizacao': datetime.now().isoformat()
        },
        {
            'id': 1000003,
            'id_externo': 'TEST_SEARCH_003',
            'fonte': 'TESTE',
            'objeto': 'Aquisição de material de escritório',
            'descricao': 'Compra de papel, canetas e outros materiais para escritório',
            'valor_estimado': 50000.0,
            'modalidade': 'Dispensa de Licitação',
            'situacao': 'Concluída',
            'data_publicacao': (datetime.now() - timedelta(days=30)).isoformat(),
            'data_abertura': (datetime.now() - timedelta(days=15)).isoformat(),
            'orgao_nome': 'Secretaria de Educação',
            'orgao_id': '33333333333333',
            'municipio': 'Belo Horizonte',
            'uf': 'MG',
            'data_criacao': datetime.now().isoformat(),
            'data_atualizacao': datetime.now().isoformat()
        }
    ]
    
    # Indexa os documentos de teste
    for doc in test_docs:
        es_service.index_document(doc['id'], doc)
    
    logger.info("Documentos de teste indexados")
    
    # Espera um momento para garantir que a indexação foi concluída
    import time
    time.sleep(1)
    
    # Testa busca por texto
    logger.info("Testando busca por texto...")
    text_search = es_service.search_text("computadores")
    
    logger.info(f"Resultados da busca por 'computadores': {json.dumps(text_search.get('hits', {}).get('total', {}), indent=2)}")
    
    # Testa busca com filtros
    logger.info("Testando busca com filtros...")
    filter_search = es_service.search_text(
        "material",
        filters={
            'uf': 'MG',
            'modalidade': 'Dispensa de Licitação'
        }
    )
    
    logger.info(f"Resultados da busca filtrada: {json.dumps(filter_search.get('hits', {}).get('total', {}), indent=2)}")
    
    # Limpa os documentos de teste
    for doc in test_docs:
        es_service.delete_document(doc['id'])
    
    logger.info("Documentos de teste removidos")
    
    # Verifica se as buscas retornaram resultados esperados
    text_search_success = text_search.get('hits', {}).get('total', {}).get('value', 0) > 0
    filter_search_success = filter_search.get('hits', {}).get('total', {}).get('value', 0) > 0
    
    return text_search_success and filter_search_success

def run_all_tests():
    """Executa todos os testes de validação."""
    logger.info("Iniciando testes de validação do Elasticsearch...")
    
    tests = [
        ("Conexão com Elasticsearch", test_elasticsearch_connection),
        ("Criação do índice", test_index_creation),
        ("Indexação de documento", test_document_indexing),
        ("Funcionalidade de busca", test_search_functionality)
    ]
    
    results = []
    
    for name, test_func in tests:
        logger.info(f"\n{'=' * 50}\nExecutando teste: {name}\n{'=' * 50}")
        try:
            result = test_func()
            status = "PASSOU" if result else "FALHOU"
            logger.info(f"Resultado: {status}")
            results.append((name, status))
        except Exception as e:
            logger.error(f"Erro durante o teste: {str(e)}")
            results.append((name, "ERRO"))
    
    logger.info("\n\n" + "=" * 50)
    logger.info("RESUMO DOS TESTES")
    logger.info("=" * 50)
    
    for name, status in results:
        logger.info(f"{name}: {status}")
    
    return all(status == "PASSOU" for _, status in results)

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        logger.info("\nTodos os testes passaram! O sistema de indexação e busca está funcionando corretamente.")
        sys.exit(0)
    else:
        logger.error("\nAlguns testes falharam. Verifique os logs para mais detalhes.")
        sys.exit(1)
