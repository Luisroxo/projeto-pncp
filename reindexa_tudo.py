# Script para reindexar todas as licitações já salvas no banco local para o Elasticsearch
# Garante que o campo objetoCompra será indexado corretamente

from src.models.licitacao import Licitacao, db
from src.utils.elasticsearch_service import get_elasticsearch_service
from flask import Flask
import os

# Garante que o diretório instance existe
#os.makedirs('instance', exist_ok=True)

app = Flask(__name__)
# Corrige o caminho do banco de dados para o local correto
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/luis_/OneDrive/Documentos/Meu projetos/projeto-pncp/instance/licitacoes_dev.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
es_service = get_elasticsearch_service()

with app.app_context():
    try:
        licitacoes = Licitacao.query.all()
        print(f"Reindexando {len(licitacoes)} licitações...")
        for lic in licitacoes:
            doc = lic.to_dict()
            es_service.index_document(lic.id, doc)
        print("Reindexação completa!")
    except Exception as e:
        import traceback
        print('ERRO AO ACESSAR O BANCO OU REINDEXAR:')
        traceback.print_exc()
