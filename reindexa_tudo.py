# Script para reindexar todas as licitações já salvas no banco local para o Elasticsearch
# Garante que o campo objetoCompra será indexado corretamente

from src.models.licitacao import Licitacao, db
from src.utils.elasticsearch_service import get_elasticsearch_service
from flask import Flask
import os
import sys
from datetime import datetime

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
        # Uso: python reindexa_tudo.py 20250501 20250531 [campo_data]
        data_inicial = None
        data_final = None
        campo_data = 'data_publicacao'  # padrão
        if len(sys.argv) >= 3:
            data_inicial = datetime.strptime(sys.argv[1], "%Y%m%d")
            data_final = datetime.strptime(sys.argv[2], "%Y%m%d")
            if len(sys.argv) >= 4:
                campo_data = sys.argv[3]
            print(f"Filtrando licitações de {data_inicial.date()} até {data_final.date()} pelo campo '{campo_data}'")
            # Monta filtro dinâmico
            from sqlalchemy import and_
            licitacoes = Licitacao.query.filter(
                getattr(Licitacao, campo_data) >= data_inicial,
                getattr(Licitacao, campo_data) <= data_final
            ).all()
        else:
            licitacoes = Licitacao.query.all()
        print(f"Reindexando {len(licitacoes)} licitações...")
        for lic in licitacoes:
            doc = lic.to_dict()
            # Inclui o campo dados_completos como objeto JSON, se existir
            if hasattr(lic, 'dados_completos') and lic.dados_completos:
                try:
                    import json
                    doc['dados_completos'] = json.loads(lic.dados_completos)
                except Exception:
                    doc['dados_completos'] = lic.dados_completos  # fallback para string
            es_service.index_document(lic.id, doc)
        print("Reindexação completa!")
    except Exception as e:
        import traceback
        print('ERRO AO ACESSAR O BANCO OU REINDEXAR:')
        traceback.print_exc()
