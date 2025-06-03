"""
Cliente de API para integração com o Portal Nacional de Contratações Públicas (PNCP).
Este módulo implementa a comunicação com a API do PNCP para obtenção de dados de licitações.
"""

import requests
import logging
import time
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional, Union

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pncp_client')

class PNCPClient:
    """Cliente para API do Portal Nacional de Contratações Públicas."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa o cliente da API do PNCP.
        
        Args:
            config: Dicionário com configurações do cliente.
                   Valores padrão serão usados se não fornecidos.
        """
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'https://pncp.gov.br/api/consulta')
        self.request_timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 2)
        self.session = requests.Session()
        
        # Headers padrão
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'LicitacoesApp/1.0'
        })
        
        logger.info(f"PNCPClient inicializado com base_url: {self.base_url}")
    
    def _make_request(self, endpoint: str, params: Dict = None, method: str = 'GET') -> Dict:
        """
        Realiza uma requisição à API do PNCP com tratamento de erros e retentativas.
        
        Args:
            endpoint: Endpoint da API a ser acessado.
            params: Parâmetros da requisição.
            method: Método HTTP (GET, POST, etc).
            
        Returns:
            Resposta da API como dicionário.
            
        Raises:
            Exception: Se a requisição falhar após todas as tentativas.
        """
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Requisição {method} para {url} com params: {params}")
                
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=self.request_timeout
                    )
                elif method.upper() == 'POST':
                    response = self.session.post(
                        url, 
                        json=params, 
                        timeout=self.request_timeout
                    )
                else:
                    raise ValueError(f"Método HTTP não suportado: {method}")
                
                # Verifica se a resposta foi bem-sucedida
                response.raise_for_status()
                
                # Tenta processar a resposta como JSON
                try:
                    return response.json()
                except ValueError:
                    logger.warning(f"Resposta não é um JSON válido: {response.text[:100]}...")
                    return {"raw_content": response.text}
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt+1}/{self.max_retries} falhou: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Espera antes de tentar novamente, com backoff exponencial
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Aguardando {wait_time}s antes da próxima tentativa")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Todas as tentativas falharam para {url}")
                    raise Exception(f"Falha ao acessar API do PNCP: {str(e)}")
    
    def fetch_licitacoes(self, params: Dict = None) -> List[Dict]:
        """
        Busca licitações no PNCP com os parâmetros especificados.
        
        Args:
            params: Parâmetros de busca para filtrar licitações.
                   Exemplos: dataInicial, dataFinal, codigoModalidadeContratacao, pagina.
                   
        Returns:
            Lista de licitações encontradas.
        """
        try:
            # Novo endpoint v1
            endpoint = 'v1/contratacoes/publicacao'
            result = self._make_request(endpoint, params)

            # Verifica se a resposta contém a estrutura esperada
            if 'content' in result:
                licitacoes = result.get('content', [])
                logger.info(f"Encontradas {len(licitacoes)} licitações (campo 'content')")
                return licitacoes
            elif 'data' in result:
                licitacoes = result.get('data', [])
                logger.info(f"Encontradas {len(licitacoes)} licitações (campo 'data')")
                return licitacoes
            else:
                logger.warning(f"Resposta não contém o campo 'content' nem 'data': {result.keys()}")
                return []
        except Exception as e:
            logger.error(f"Erro ao buscar licitações: {str(e)}")
            return []
    
    def fetch_licitacao_details(self, sequencial: str, ano: str) -> Dict:
        """
        Busca detalhes de uma licitação específica pelo sequencial e ano.
        
        Args:
            sequencial: Número sequencial da licitação.
            ano: Ano da licitação.
            
        Returns:
            Detalhes da licitação.
        """
        try:
            endpoint = f"contratacoes/publicacao/{sequencial}/{ano}"
            return self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da licitação {sequencial}/{ano}: {str(e)}")
            return {}
    
    def fetch_atas_registro_preco(self, params: Dict = None) -> List[Dict]:
        """
        Busca atas de registro de preço no PNCP.
        
        Args:
            params: Parâmetros de busca para filtrar atas.
            
        Returns:
            Lista de atas encontradas.
        """
        try:
            result = self._make_request('atas', params)
            
            if 'content' in result:
                atas = result.get('content', [])
                logger.info(f"Encontradas {len(atas)} atas de registro de preço")
                return atas
            else:
                logger.warning(f"Resposta não contém o campo 'content': {result.keys()}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar atas de registro de preço: {str(e)}")
            return []
    
    def fetch_contratos(self, params: Dict = None) -> List[Dict]:
        """
        Busca contratos no PNCP.
        
        Args:
            params: Parâmetros de busca para filtrar contratos.
            
        Returns:
            Lista de contratos encontrados.
        """
        try:
            result = self._make_request('contratos', params)
            
            if 'content' in result:
                contratos = result.get('content', [])
                logger.info(f"Encontrados {len(contratos)} contratos")
                return contratos
            else:
                logger.warning(f"Resposta não contém o campo 'content': {result.keys()}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar contratos: {str(e)}")
            return []
    
    def search_combined(self, query: str, params: Dict = None) -> Dict[str, List]:
        """
        Realiza uma busca combinada por licitações, atas e contratos.
        
        Args:
            query: Termo de busca.
            params: Parâmetros adicionais para a busca.
            
        Returns:
            Dicionário com resultados agrupados por tipo.
        """
        search_params = params or {}
        search_params['q'] = query
        
        results = {
            'licitacoes': [],
            'atas': [],
            'contratos': []
        }
        
        try:
            # Busca licitações
            results['licitacoes'] = self.fetch_licitacoes(search_params)
            
            # Busca atas
            results['atas'] = self.fetch_atas_registro_preco(search_params)
            
            # Busca contratos
            results['contratos'] = self.fetch_contratos(search_params)
            
            total_results = sum(len(items) for items in results.values())
            logger.info(f"Busca combinada por '{query}' retornou {total_results} resultados")
            
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca combinada: {str(e)}")
            return results


# Exemplo de uso
if __name__ == "__main__":
    # Configuração de exemplo
    config = {
        'base_url': 'https://pncp.gov.br/api/consulta',
        'timeout': 30,
        'max_retries': 3
    }
    
    # Inicializa o cliente
    client = PNCPClient(config)
    
    # Exemplo: buscar licitações publicadas nos últimos 7 dias
    from datetime import datetime, timedelta
    
    data_inicio = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    params = {
        'dataPublicacaoInicio': data_inicio
    }
    
    licitacoes = client.fetch_licitacoes(params)
    print(f"Encontradas {len(licitacoes)} licitações nos últimos 7 dias")
    
    # Exibe as 5 primeiras licitações
    for i, licitacao in enumerate(licitacoes[:5]):
        print(f"\nLicitação {i+1}:")
        print(f"Objeto: {licitacao.get('objeto', 'N/A')}")
        print(f"Órgão: {licitacao.get('razaoSocialContratante', 'N/A')}")
        print(f"Valor estimado: R$ {licitacao.get('valorTotal', 'N/A')}")
        print(f"Data de abertura: {licitacao.get('dataAbertura', 'N/A')}")
