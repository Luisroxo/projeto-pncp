"""Serviço de conexão e operações com Elasticsearch.
Este módulo implementa a conexão e operações básicas com o Elasticsearch."""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError
import os
from dotenv import load_dotenv

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('elasticsearch_service')

class ElasticsearchService:
    """Serviço para operações com Elasticsearch."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa o serviço de Elasticsearch.
        
        Args:
            config: Dicionário com configurações do serviço.
                   Valores padrão serão usados se não fornecidos.
        """
        # Carrega variáveis do .env
        load_dotenv()
        self.config = config or {}
        self.hosts = self.config.get('hosts') or [os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')]
        self.index_name = self.config.get('index_name') or os.getenv('ELASTICSEARCH_INDEX', 'licitacoes')
        self.username = self.config.get('username') or os.getenv('ELASTICSEARCH_USERNAME')
        self.password = self.config.get('password') or os.getenv('ELASTICSEARCH_PASSWORD')
        self.client = None
        self.connect()
        
    def connect(self) -> None:
        """Estabelece conexão com o Elasticsearch."""
        try:
            es_kwargs = {
                'hosts': self.hosts,
                'retry_on_timeout': True,
                'max_retries': 3
            }
            if self.username and self.password:
                es_kwargs['basic_auth'] = (self.username, self.password)
            self.client = Elasticsearch(**es_kwargs)
            logger.info(f"Conectado ao Elasticsearch: {self.hosts}")
        except Exception as e:
            logger.error(f"Erro ao conectar ao Elasticsearch: {str(e)}")
            raise
    
    def create_index(self) -> bool:
        """
        Cria o índice de licitações se não existir.
        
        Returns:
            True se o índice foi criado ou já existia, False em caso de erro.
        """
        try:
            # Verifica se o índice já existe
            if self.client.indices.exists(index=self.index_name):
                logger.info(f"Índice '{self.index_name}' já existe")
                return True
            
            # Definição do mapeamento do índice
            mappings = {
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        "id_externo": {"type": "keyword"},
                        "fonte": {"type": "keyword"},
                        "sequencial": {"type": "keyword"},
                        "ano": {"type": "keyword"},
                        "objeto": {
                            "type": "text",
                            "analyzer": "portuguese",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            }
                        },
                        "descricao": {
                            "type": "text",
                            "analyzer": "portuguese"
                        },
                        "valor_estimado": {"type": "float"},
                        "modalidade": {"type": "keyword"},
                        "situacao": {"type": "keyword"},
                        "data_publicacao": {"type": "date"},
                        "data_abertura": {"type": "date"},
                        "orgao_nome": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            }
                        },
                        "orgao_id": {"type": "keyword"},
                        "municipio": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            }
                        },
                        "uf": {"type": "keyword"},
                        "data_criacao": {"type": "date"},
                        "data_atualizacao": {"type": "date"}
                    }
                },
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "portuguese": {
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "portuguese_stop",
                                    "portuguese_stemmer"
                                ]
                            }
                        },
                        "filter": {
                            "portuguese_stop": {
                                "type": "stop",
                                "stopwords": "_portuguese_"
                            },
                            "portuguese_stemmer": {
                                "type": "stemmer",
                                "language": "portuguese"
                            }
                        }
                    }
                }
            }
            
            # Cria o índice com o mapeamento
            self.client.indices.create(index=self.index_name, body=mappings)
            logger.info(f"Índice '{self.index_name}' criado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar índice '{self.index_name}': {str(e)}")
            return False
    
    def index_document(self, doc_id: Union[str, int], document: Dict[str, Any]) -> bool:
        """
        Indexa um documento no Elasticsearch.
        
        Args:
            doc_id: ID do documento.
            document: Documento a ser indexado.
            
        Returns:
            True se indexado com sucesso, False caso contrário.
        """
        try:
            # Garante que o índice existe
            if not self.client.indices.exists(index=self.index_name):
                self.create_index()
            
            # Indexa o documento
            self.client.index(
                index=self.index_name,
                id=doc_id,
                document=document
            )
            logger.debug(f"Documento {doc_id} indexado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao indexar documento {doc_id}: {str(e)}")
            return False
    
    def delete_document(self, doc_id: Union[str, int]) -> bool:
        """
        Remove um documento do índice.
        
        Args:
            doc_id: ID do documento a ser removido.
            
        Returns:
            True se removido com sucesso, False caso contrário.
        """
        try:
            self.client.delete(
                index=self.index_name,
                id=doc_id
            )
            logger.debug(f"Documento {doc_id} removido com sucesso")
            return True
            
        except NotFoundError:
            logger.warning(f"Documento {doc_id} não encontrado para remoção")
            return False
        except Exception as e:
            logger.error(f"Erro ao remover documento {doc_id}: {str(e)}")
            return False
    
    def search(self, query: Dict[str, Any], size: int = 10, from_: int = 0) -> Dict[str, Any]:
        """
        Realiza uma busca no índice.
        
        Args:
            query: Query de busca no formato Elasticsearch.
            size: Número máximo de resultados.
            from_: Índice inicial para paginação.
            
        Returns:
            Resultados da busca.
        """
        try:
            results = self.client.search(
                index=self.index_name,
                body=query,
                size=size,
                from_=from_
            )
            return results
            
        except Exception as e:
            logger.error(f"Erro ao realizar busca: {str(e)}")
            return {"error": str(e)}
    
    def search_text(self, text: str, fields: List[str] = None, filters: Dict[str, Any] = None, 
                   size: int = 10, from_: int = 0) -> Dict[str, Any]:
        """
        Realiza uma busca textual simplificada.
        
        Args:
            text: Texto a ser buscado.
            fields: Campos onde buscar (default: objeto e descrição).
            filters: Filtros adicionais.
            size: Número máximo de resultados.
            from_: Índice inicial para paginação.
            
        Returns:
            Resultados da busca.
        """
        if fields is None:
            fields = ["objeto^3", "descricao^2", "orgao_nome", "municipio"]
        
        # Constrói a query
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": text,
                                "fields": fields,
                                "type": "best_fields",
                                "operator": "and",
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"data_abertura": {"order": "asc"}}
            ]
        }
        
        # Adiciona filtros se fornecidos
        if filters:
            filter_clauses = []
            
            # Filtro de modalidade
            if 'modalidade' in filters:
                filter_clauses.append({"term": {"modalidade.keyword": filters['modalidade']}})
            
            # Filtro de UF
            if 'uf' in filters:
                filter_clauses.append({"term": {"uf": filters['uf']}})
            
            # Filtro de valor mínimo
            if 'valor_min' in filters:
                filter_clauses.append({"range": {"valor_estimado": {"gte": filters['valor_min']}}})
            
            # Filtro de valor máximo
            if 'valor_max' in filters:
                filter_clauses.append({"range": {"valor_estimado": {"lte": filters['valor_max']}}})
            
            # Filtro de data de abertura mínima
            if 'data_abertura_min' in filters:
                filter_clauses.append({"range": {"data_abertura": {"gte": filters['data_abertura_min']}}})
            
            # Filtro de data de abertura máxima
            if 'data_abertura_max' in filters:
                filter_clauses.append({"range": {"data_abertura": {"lte": filters['data_abertura_max']}}})
            
            # Adiciona os filtros à query
            if filter_clauses:
                query["query"]["bool"]["filter"] = filter_clauses
        
        # Executa a busca
        return self.search(query, size=size, from_=from_)
    
    def get_document(self, doc_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Recupera um documento pelo ID.
        
        Args:
            doc_id: ID do documento.
            
        Returns:
            Documento encontrado ou None.
        """
        try:
            result = self.client.get(
                index=self.index_name,
                id=doc_id
            )
            return result['_source']
            
        except NotFoundError:
            logger.warning(f"Documento {doc_id} não encontrado")
            return None
        except Exception as e:
            logger.error(f"Erro ao recuperar documento {doc_id}: {str(e)}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica o status de saúde do Elasticsearch.
        
        Returns:
            Informações de saúde do cluster.
        """
        try:
            return self.client.cluster.health()
        except Exception as e:
            logger.error(f"Erro ao verificar saúde do Elasticsearch: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton para acesso global ao serviço
_instance = None

def get_elasticsearch_service(config: Dict[str, Any] = None) -> ElasticsearchService:
    """
    Obtém a instância singleton do serviço Elasticsearch.
    
    Args:
        config: Configurações opcionais para inicialização.
        
    Returns:
        Instância do ElasticsearchService.
    """
    global _instance
    if _instance is None:
        _instance = ElasticsearchService(config)
    return _instance
