import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from src.models.licitacao import db
from src.routes.search import search_bp
from src.utils.elasticsearch_service import get_elasticsearch_service

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
