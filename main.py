import os
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
from src.models.licitacao import db
from src.routes.search import search_bp
from src.utils.elasticsearch_service import get_elasticsearch_service
from src.integrations.pncp_sync import PNCPSyncService

# Carrega variáveis de ambiente do .env
load_dotenv()

app = Flask(__name__)

# Configurações do Flask
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///licitacoes_dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy com o app Flask
db.init_app(app)

# Cria as tabelas do banco de dados (se não existirem)
with app.app_context():
    db.create_all()
    # Cria o índice do Elasticsearch (se não existir)
    es_service = get_elasticsearch_service()
    es_service.create_index()

# Registra o blueprint da API de busca
app.register_blueprint(search_bp)

@app.route('/')
def index():
    return jsonify({"message": "API do Módulo Encontrar Licitações"})

@app.route('/sync', methods=['POST'])
def sync_licitacoes_api():
    data = request.get_json(force=True)
    data_inicial = data.get('dataInicial')
    data_final = data.get('dataFinal')
    codigo_modalidade = data.get('codigoModalidadeContratacao')
    pagina = int(data.get('pagina', 1))
    tamanho_pagina = int(data.get('tamanhoPagina', 10))

    if not (data_inicial and data_final and codigo_modalidade):
        return jsonify({
            'error': 'Parâmetros obrigatórios: dataInicial, dataFinal, codigoModalidadeContratacao'
        }), 400

    es_service = get_elasticsearch_service()
    indice = os.getenv('ELASTICSEARCH_INDEX', 'licitacoes')
    from_ = (pagina - 1) * tamanho_pagina
    try:
        res = es_service.client.search(
            index=indice,
            body={
                "query": {"match_all": {}},
                "from": from_,
                "size": tamanho_pagina
            }
        )
        total = res['hits']['total']['value'] if 'hits' in res and 'total' in res['hits'] else 0
        amostra = [doc['_source'] for doc in res['hits']['hits']]
    except Exception as e:
        total = 0
        amostra = [f"Erro ao buscar amostra: {str(e)}"]
    return jsonify({
        'quantidade': total,
        'amostra': amostra
    })

@app.route('/sync-ui')
def sync_ui():
    return send_from_directory('src/static', 'sync.html')

@app.route('/objeto-compra-ui')
def objeto_compra_ui():
    return send_from_directory('src/static', 'objeto_compra.html')

if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "reindexa":
        data_inicial = sys.argv[2] if len(sys.argv) > 2 else None
        data_final = sys.argv[3] if len(sys.argv) > 3 else None
        sync = PNCPSyncService()
        print(f"Reindexando licitações de {data_inicial} até {data_final}...")
        with app.app_context():
            sync.sync_licitacoes(data_inicial=data_inicial, data_final=data_final)
        print("Reindexação concluída.")
    else:
        app.run(debug=True, host='0.0.0.0', port=5001)
