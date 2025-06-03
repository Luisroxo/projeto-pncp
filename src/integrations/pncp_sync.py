"""
Serviço de sincronização e indexação de licitações do PNCP.
Este módulo implementa a sincronização periódica com o PNCP e a indexação dos dados.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import os
import threading
import schedule

from src.integrations.pncp_client import PNCPClient
from src.models.licitacao import Licitacao, db
from src.utils.elasticsearch_service import get_elasticsearch_service

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pncp_sync')

class PNCPSyncService:
    """Serviço para sincronização e indexação de dados do PNCP."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa o serviço de sincronização.
        
        Args:
            config: Dicionário com configurações do serviço.
                   Valores padrão serão usados se não fornecidos.
        """
        self.config = config or {}
        self.client = PNCPClient(self.config.get('pncp_client', {}))
        self.sync_interval = self.config.get('sync_interval', 30)  # minutos
        self.last_sync_file = self.config.get('last_sync_file', 'last_sync.json')
        self.is_running = False
        self.scheduler_thread = None
        
        # Inicializa o serviço de Elasticsearch
        es_config = self.config.get('elasticsearch', {})
        self.es_service = get_elasticsearch_service(es_config)
        
        # Garante que o índice existe
        self.es_service.create_index()
        
        logger.info(f"PNCPSyncService inicializado com intervalo de {self.sync_interval} minutos")
    
    def get_last_sync_timestamp(self) -> Optional[str]:
        """
        Obtém o timestamp da última sincronização.
        
        Returns:
            Timestamp da última sincronização no formato ISO ou None se não houver.
        """
        try:
            if os.path.exists(self.last_sync_file):
                with open(self.last_sync_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_sync')
            return None
        except Exception as e:
            logger.error(f"Erro ao ler timestamp da última sincronização: {str(e)}")
            return None
    
    def update_last_sync_timestamp(self) -> None:
        """Atualiza o timestamp da última sincronização para o momento atual."""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.last_sync_file, 'w') as f:
                json.dump({'last_sync': timestamp}, f)
            logger.info(f"Timestamp de sincronização atualizado: {timestamp}")
        except Exception as e:
            logger.error(f"Erro ao atualizar timestamp de sincronização: {str(e)}")
    
    def sync_licitacoes(self, data_inicial=None, data_final=None, codigo_modalidade=6, pagina=1) -> int:
        """
        Sincroniza licitações do PNCP com o banco de dados local, buscando todas as páginas.
        """
        try:
            params = {}
            hoje = datetime.now()
            if data_inicial:
                if isinstance(data_inicial, str) and len(data_inicial) == 8:
                    params['dataInicial'] = data_inicial
                else:
                    params['dataInicial'] = datetime.strptime(data_inicial, '%Y-%m-%d').strftime('%Y%m%d')
            else:
                last_sync = self.get_last_sync_timestamp()
                if last_sync:
                    data_inicial_dt = datetime.strptime(last_sync[:10], '%Y-%m-%d')
                else:
                    data_inicial_dt = hoje - timedelta(days=30)
                params['dataInicial'] = data_inicial_dt.strftime('%Y%m%d')

            if data_final:
                if isinstance(data_final, str) and len(data_final) == 8:
                    params['dataFinal'] = data_final
                else:
                    params['dataFinal'] = datetime.strptime(data_final, '%Y-%m-%d').strftime('%Y%m%d')
            else:
                params['dataFinal'] = hoje.strftime('%Y%m%d')

            params['codigoModalidadeContratacao'] = self.config.get('codigo_modalidade', codigo_modalidade)

            total_count = 0
            pagina_atual = 1
            total_paginas = None
            while True:
                params['pagina'] = pagina_atual
                self.client.session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                })
                logger.info(f"Sincronizando página {pagina_atual} com params: {params}")
                # Chama a API e pega o JSON completo
                result = self.client._make_request('v1/contratacoes/publicacao', params)
                licitacoes = result.get('data', [])
                if total_paginas is None:
                    total_paginas = result.get('totalPaginas', 1)
                    logger.info(f"Total de páginas a processar: {total_paginas}")
                logger.info(f"Página {pagina_atual}: {len(licitacoes)} licitações retornadas.")
                if not licitacoes:
                    logger.info(f"Nenhuma licitação encontrada na página {pagina_atual}.")
                    break
                count = 0
                for licitacao_data in licitacoes:
                    try:
                        licitacao_id = None
                        numero_controle = licitacao_data.get('numeroControlePNCP')
                        if numero_controle:
                            licitacao_id = str(numero_controle)
                        elif licitacao_data.get('id'):
                            licitacao_id = str(licitacao_data['id'])
                        else:
                            logger.warning(f"Licitação sem identificador único: {licitacao_data}")
                            continue
                        existing = Licitacao.query.filter_by(id_externo=licitacao_id).first()
                        if existing:
                            self._update_licitacao(existing, licitacao_data)
                            logger.debug(f"Licitação atualizada: {licitacao_id}")
                        else:
                            self._create_licitacao(licitacao_id, licitacao_data)
                            logger.debug(f"Nova licitação criada: {licitacao_id}")
                        count += 1
                    except Exception as e:
                        logger.error(f"Erro ao processar licitação {licitacao_data.get('id', 'N/A')}: {str(e)}")
                total_count += count
                logger.info(f"Página {pagina_atual} processada. {count} licitações indexadas.")
                if pagina_atual >= total_paginas:
                    logger.info(f"Última página alcançada ({pagina_atual}/{total_paginas}). Encerrando.")
                    break
                pagina_atual += 1
            self.update_last_sync_timestamp()
            logger.info(f"Sincronização concluída. {total_count} licitações processadas.")
            return total_count
        except Exception as e:
            logger.error(f"Erro durante sincronização de licitações: {str(e)}")
            return 0
    
    def _create_licitacao(self, licitacao_id: str, licitacao_data: Dict) -> Licitacao:
        """
        Cria uma nova licitação no banco de dados.
        
        Args:
            licitacao_id: ID único da licitação.
            licitacao_data: Dados da licitação do PNCP.
            
        Returns:
            Objeto Licitacao criado.
        """
        try:
            # Extrai e formata os dados
            objeto = licitacao_data.get('objeto', '')
            descricao = licitacao_data.get('descricao', '')
            
            # Converte strings de data para objetos datetime
            data_publicacao = None
            # Ajusta para buscar datas do PNCP
            if 'dataPublicacaoPncp' in licitacao_data:
                try:
                    data_publicacao = datetime.fromisoformat(licitacao_data['dataPublicacaoPncp'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataPublicacaoPncp')}")
            elif 'dataPublicacao' in licitacao_data:
                try:
                    data_publicacao = datetime.fromisoformat(licitacao_data['dataPublicacao'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataPublicacao')}")
            elif 'dataInclusao' in licitacao_data:
                try:
                    data_publicacao = datetime.fromisoformat(licitacao_data['dataInclusao'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataInclusao')}")
            
            data_abertura = None
            if 'dataAbertura' in licitacao_data:
                try:
                    data_abertura = datetime.fromisoformat(licitacao_data['dataAbertura'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataAbertura')}")
            
            # Cria o objeto Licitacao
            licitacao = Licitacao(
                id_externo=licitacao_id,
                fonte='PNCP',
                sequencial=licitacao_data.get('sequencial'),
                ano=licitacao_data.get('ano'),
                objeto=objeto,
                descricao=descricao,
                valor_estimado=licitacao_data.get('valorTotal'),
                modalidade=licitacao_data.get('modalidade', {}).get('nome', 'Não especificada'),
                situacao=licitacao_data.get('situacao'),
                data_publicacao=data_publicacao,
                data_abertura=data_abertura,
                orgao_nome=licitacao_data.get('razaoSocialContratante'),
                orgao_id=licitacao_data.get('cnpjContratante'),
                municipio=licitacao_data.get('municipio', {}).get('nome'),
                uf=licitacao_data.get('municipio', {}).get('uf'),
                dados_completos=json.dumps(licitacao_data)
            )
            
            # Salva no banco de dados
            db.session.add(licitacao)
            db.session.commit()
            
            # Indexa a licitação
            self._index_licitacao(licitacao)
            
            return licitacao
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar licitação {licitacao_id}: {str(e)}")
            raise
    
    def _update_licitacao(self, licitacao: Licitacao, licitacao_data: Dict) -> Licitacao:
        """
        Atualiza uma licitação existente no banco de dados.
        
        Args:
            licitacao: Objeto Licitacao a ser atualizado.
            licitacao_data: Novos dados da licitação do PNCP.
            
        Returns:
            Objeto Licitacao atualizado.
        """
        try:
            # Atualiza os campos básicos
            licitacao.objeto = licitacao_data.get('objeto', licitacao.objeto)
            licitacao.descricao = licitacao_data.get('descricao', licitacao.descricao)
            licitacao.valor_estimado = licitacao_data.get('valorTotal', licitacao.valor_estimado)
            licitacao.situacao = licitacao_data.get('situacao', licitacao.situacao)
            
            # Atualiza datas se fornecidas
            # Corrige: tenta na ordem dataPublicacaoPncp, dataPublicacao, dataInclusao
            data_publicacao = licitacao.data_publicacao
            if 'dataPublicacaoPncp' in licitacao_data:
                try:
                    data_publicacao = datetime.fromisoformat(licitacao_data['dataPublicacaoPncp'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataPublicacaoPncp')}")
            elif 'dataPublicacao' in licitacao_data:
                try:
                    data_publicacao = datetime.fromisoformat(licitacao_data['dataPublicacao'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataPublicacao')}")
            elif 'dataInclusao' in licitacao_data:
                try:
                    data_publicacao = datetime.fromisoformat(licitacao_data['dataInclusao'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataInclusao')}")
            licitacao.data_publicacao = data_publicacao

            if 'dataAbertura' in licitacao_data:
                try:
                    licitacao.data_abertura = datetime.fromisoformat(licitacao_data['dataAbertura'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Formato de data inválido: {licitacao_data.get('dataAbertura')}")
            
            # Atualiza dados completos
            licitacao.dados_completos = json.dumps(licitacao_data)
            
            # Atualiza data de modificação
            licitacao.data_atualizacao = datetime.now()
            
            # Salva no banco de dados
            db.session.commit()
            
            # Reindexar a licitação
            self._index_licitacao(licitacao)
            
            return licitacao
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar licitação {licitacao.id_externo}: {str(e)}")
            raise
    
    def _index_licitacao(self, licitacao: Licitacao) -> None:
        """
        Indexa uma licitação no Elasticsearch para busca rápida.
        
        Args:
            licitacao: Objeto Licitacao a ser indexado.
        """
        try:
            # Converte o objeto Licitacao para um dicionário
            licitacao_dict = licitacao.to_dict()

            # Inclui o JSON original da API PNCP no campo 'dados_completos' (como dict)
            if hasattr(licitacao, 'dados_completos') and licitacao.dados_completos:
                try:
                    import json
                    licitacao_dict['dados_completos'] = json.loads(licitacao.dados_completos)
                except Exception:
                    licitacao_dict['dados_completos'] = licitacao.dados_completos  # fallback para string

            # Indexa no Elasticsearch
            success = self.es_service.index_document(licitacao.id, licitacao_dict)
            
            if success:
                # Atualiza os campos de indexação no modelo
                licitacao.indexado = True
                licitacao.data_indexacao = datetime.now()
                db.session.commit()
                logger.debug(f"Licitação {licitacao.id_externo} indexada com sucesso")
            else:
                logger.warning(f"Falha ao indexar licitação {licitacao.id_externo}")
            
        except Exception as e:
            logger.error(f"Erro ao indexar licitação {licitacao.id_externo}: {str(e)}")
            # Não propaga a exceção para não interromper o fluxo de sincronização
    
    def start_scheduled_sync(self) -> None:
        """Inicia a sincronização agendada em segundo plano."""
        if self.is_running:
            logger.warning("Serviço de sincronização já está em execução")
            return
        
        def run_scheduler():
            self.is_running = True
            logger.info(f"Iniciando serviço de sincronização agendada a cada {self.sync_interval} minutos")
            
            # Agenda a sincronização periódica
            schedule.every(self.sync_interval).minutes.do(self.sync_licitacoes)
            
            # Executa uma sincronização inicial
            self.sync_licitacoes()
            
            # Loop principal do agendador
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        
        # Inicia o agendador em uma thread separada
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop_scheduled_sync(self) -> None:
        """Para a sincronização agendada."""
        if not self.is_running:
            logger.warning("Serviço de sincronização não está em execução")
            return
        
        logger.info("Parando serviço de sincronização agendada")
        self.is_running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None


# Exemplo de uso
if __name__ == "__main__":
    # Configuração de exemplo
    config = {
        'pncp_client': {
            'base_url': 'https://pncp.gov.br/api/consulta',
            'timeout': 30
        },
        'elasticsearch': {
            'hosts': ['http://localhost:9200'],
            'index_name': 'licitacoes'
        },
        'sync_interval': 30,  # minutos
        'last_sync_file': 'last_sync.json'
    }
    
    # Inicializa o serviço
    sync_service = PNCPSyncService(config)
    
    # Executa uma sincronização manual
    num_synced = sync_service.sync_licitacoes()
    print(f"Sincronizadas {num_synced} licitações")
    
    # Ou inicia o serviço de sincronização agendada
    # sync_service.start_scheduled_sync()
    
    # Para parar o serviço
    # import time
    # time.sleep(60)  # Executa por 1 minuto
    # sync_service.stop_scheduled_sync()
