import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Carrega variáveis de ambiente do docker-compose (ajuste conforme necessário)
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST')
ELASTICSEARCH_USERNAME = os.getenv('ELASTICSEARCH_USERNAME')
ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD')

# Conexão com o Elasticsearch
es = Elasticsearch(
    ELASTICSEARCH_HOST,
    basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD),
    verify_certs=False
)

def exibir_dados_indices():
    indice = os.getenv('ELASTICSEARCH_INDEX', 'licitacoes')
    # Verifica se o índice existe antes de buscar
    if not es.indices.exists(index=indice):
        print(f"Índice '{indice}' não existe no Elasticsearch.")
        return
    print(f'\nÍndice: {indice}')
    res = es.search(index=indice, body={"query": {"match_all": {}}, "size": 10})
    for doc in res['hits']['hits']:
        # Exibe o campo 'dados_completos' se existir, senão exibe o _source inteiro
        dados = doc['_source'].get('dados_completos')
        if dados:
            print(dados)
        else:
            print(doc['_source'])

if __name__ == "__main__":
    exibir_dados_indices()
