# Módulo "Encontrar" Licitações: Busca Inteligente e Integrada

Este projeto implementa um módulo robusto e eficiente para buscar e encontrar licitações públicas, com foco na integração com o Portal Nacional de Contratações Públicas (PNCP) e um sistema de busca avançada utilizando Elasticsearch. O objetivo é centralizar e facilitar o acesso a oportunidades de negócio com o governo.

## Visão Geral

O módulo "Encontrar" foi projetado para:

*   **Automatizar a coleta de dados:** Sincroniza automaticamente as licitações publicadas no PNCP.
*   **Otimizar a busca:** Utiliza Elasticsearch para indexação e busca textual rápida, com análise semântica em português.
*   **Oferecer flexibilidade:** Disponibiliza uma API RESTful completa para consultas personalizadas, filtros e agregações.
*   **Facilitar a análise:** Fornece endpoints para obter estatísticas e insights sobre as licitações.

## Funcionalidades Principais

*   **Sincronização com PNCP:**
    *   Busca periódica (configurável) por novas licitações e atualizações no PNCP.
    *   Armazenamento estruturado dos dados no banco de dados local (PostgreSQL ou SQLite).
    *   Mantém registro da última sincronização para buscar apenas dados novos.
*   **Indexação com Elasticsearch:**
    *   Indexação automática de cada licitação sincronizada.
    *   Mapeamento otimizado para busca em campos relevantes (objeto, descrição, órgão, etc.).
    *   Análise de texto em português (stopwords, stemming) para buscas mais precisas.
*   **API RESTful (`/api/search`):**
    *   **Busca de Licitações (`/licitacoes`):**
        *   Busca textual livre (`q=termo`) em múltiplos campos com relevância.
        *   Filtros por `modalidade`, `uf`, `valor_min`, `valor_max`, `data_abertura_min`, `data_abertura_max`.
        *   Paginação dos resultados (`page`, `size`).
    *   **Detalhes da Licitação (`/licitacoes/<id>`):**
        *   Recupera informações completas de uma licitação específica pelo seu ID interno.
    *   **Agregações e Listas:**
        *   Lista de `modalidades` distintas encontradas (`/modalidades`).
        *   Lista de `UFs` distintas encontradas (`/ufs`).
    *   **Estatísticas (`/stats`):**
        *   Dados agregados como valor total, médio, mínimo e máximo das licitações.
        *   Contagem de licitações por situação e por mês de publicação.
    *   **Health Check (`/health`):**
        *   Verifica o status da conexão com Elasticsearch e banco de dados.

## Estrutura do Projeto

```plaintext
modulo-encontrar/
├── src/
│   ├── integrations/  # Lógica de integração com fontes externas (PNCPClient, PNCPSyncService)
│   ├── models/        # Definições dos modelos de dados (Licitacao, etc. usando SQLAlchemy)
│   ├── routes/        # Definição dos endpoints da API (Flask Blueprints - search.py)
│   ├── utils/         # Módulos utilitários (ElasticsearchService)
│   ├── static/        # (Opcional) Arquivos estáticos para frontend
│   └── templates/     # (Opcional) Templates HTML para frontend
├── venv/              # Ambiente virtual Python (ignorado)
├── .env               # (Opcional) Arquivo para variáveis de ambiente
├── .gitignore         # Configuração de arquivos a serem ignorados pelo Git
├── requirements.txt   # Lista de dependências Python do projeto
├── ELASTICSEARCH_SETUP.md # Guia detalhado para instalar e configurar o Elasticsearch
├── test_elasticsearch.py  # Script para validar a integração com Elasticsearch
└── README.md          # Este arquivo de documentação
```

## Pré-requisitos

*   **Python:** Versão 3.9 ou superior.
*   **pip:** Gerenciador de pacotes Python.
*   **Git:** Sistema de controle de versão.
*   **Elasticsearch:** Versão 8.x. **Fundamental para a funcionalidade de busca.** Consulte o `ELASTICSEARCH_SETUP.md` para instruções detalhadas de instalação (Docker recomendado).
*   **Banco de Dados:** PostgreSQL é recomendado para produção. SQLite pode ser usado para desenvolvimento/testes (requer pequeno ajuste na configuração).

## Instalação e Configuração

1.  **Clone o Repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO_GITHUB>
    cd modulo-encontrar
    ```

2.  **Ambiente Virtual:**
    ```bash
    python -m venv venv
    # Linux/macOS:
    source venv/bin/activate
    # Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    ```

3.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure o Elasticsearch:**
    *   **Instale e inicie o Elasticsearch 8.x.** Siga **obrigatoriamente** as instruções detalhadas no arquivo `ELASTICSEARCH_SETUP.md`.
    *   Verifique se o Elasticsearch está acessível (normalmente em `http://localhost:9200`).

5.  **Configure o Banco de Dados:**
    *   **PostgreSQL (Recomendado):**
        *   Instale e configure um servidor PostgreSQL.
        *   Crie um banco de dados para a aplicação.
        *   Defina a variável de ambiente `DATABASE_URL` (veja passo 6) ou ajuste a configuração no código.
    *   **SQLite (Para Desenvolvimento):**
        *   Edite o arquivo `src/config.py` (crie-o se não existir) e defina:
          ```python
          SQLALCHEMY_DATABASE_URI = 'sqlite:///licitacoes_dev.db'
          ```

6.  **Variáveis de Ambiente (Opcional, mas recomendado):**
    *   Crie um arquivo `.env` na raiz do projeto:
      ```dotenv
      # Exemplo para PostgreSQL
      DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_banco

      # Exemplo para Elasticsearch (se não for localhost:9200)
      ELASTICSEARCH_HOSTS=http://seu_host_elasticsearch:9200

      # Chave secreta para Flask (gere uma chave segura)
      SECRET_KEY=sua_chave_secreta_aqui
      ```
    *   O código tentará carregar essas variáveis usando `python-dotenv`.

## Execução da Aplicação (Exemplo Básico com Flask)

Como este é um módulo, ele precisa ser integrado a uma aplicação Flask principal.

1.  **Crie um arquivo `main.py` na raiz do projeto:**
    ```python
    import os
    from flask import Flask, jsonify
    from dotenv import load_dotenv
    from src.models.licitacao import db # Importa a instância db
    from src.routes.search import search_bp # Importa o blueprint da API de busca
    from src.utils.elasticsearch_service import get_elasticsearch_service

    # Carrega variáveis de ambiente do .env
    load_dotenv()

    app = Flask(__name__)

    # Configurações do Flask
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
    # Configuração do Banco de Dados (prioriza variável de ambiente)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///licitacoes_dev.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa o SQLAlchemy com o app Flask
    db.init_app(app)

    # Cria as tabelas do banco de dados (se não existirem)
    with app.app_context():
        db.create_all()
        # Cria o índice do Elasticsearch (se não existir)
        es_service = get_elasticsearch_service({
            'hosts': [os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200')]
        })
        es_service.create_index()

    # Registra o blueprint da API de busca
    app.register_blueprint(search_bp)

    @app.route('/')
    def index():
        return jsonify({"message": "API do Módulo Encontrar Licitações"})

    if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5001) # Use uma porta diferente se a 5000 estiver ocupada
    ```

2.  **Inicie o Serviço Elasticsearch:** Certifique-se de que ele esteja rodando.

3.  **Execute a Aplicação Flask:**
    ```bash
    # Certifique-se que o ambiente virtual está ativo
    # source venv/bin/activate
    python main.py
    ```
    A API estará acessível em `http://localhost:5001` (ou a porta configurada).

## Sincronização e Indexação

*   **Sincronização Manual:** Para buscar e indexar licitações do PNCP imediatamente:
    ```bash
    python -c "from src.integrations.pncp_sync import PNCPSyncService; sync = PNCPSyncService(); sync.sync_licitacoes()"
    ```
*   **Sincronização Agendada:** O `PNCPSyncService` possui métodos (`start_scheduled_sync`, `stop_scheduled_sync`) para rodar a sincronização periodicamente em background usando a biblioteca `schedule`. **Nota:** A execução de tarefas agendadas de longa duração pode ser restrita em alguns ambientes. Para produção, considere usar um sistema de filas de tarefas como Celery (já incluído nas dependências) ou um agendador externo (cron).

## Uso da API

A API está disponível no prefixo `/api/search`.

**Exemplo: Buscar licitações contendo "software" na UF de SP**
```bash
curl "http://localhost:5001/api/search/licitacoes?q=software&uf=SP&size=5"
```

**Exemplo: Obter detalhes da licitação com ID 123**
```bash
curl "http://localhost:5001/api/search/licitacoes/123"
```

**Exemplo: Listar modalidades disponíveis**
```bash
curl "http://localhost:5001/api/search/modalidades"
```

**Exemplo: Obter estatísticas gerais**
```bash
curl "http://localhost:5001/api/search/stats"
```

## Testes

O script `test_elasticsearch.py` valida a conexão, criação de índice, indexação e busca no Elasticsearch. **Requer que o Elasticsearch esteja em execução.**

```bash
python test_elasticsearch.py
```

## Troubleshooting

*   **`ConnectionRefusedError` para Elasticsearch:** Verifique se o serviço Elasticsearch está rodando e acessível na URL configurada (`http://localhost:9200` por padrão). Consulte `ELASTICSEARCH_SETUP.md`.
*   **`ModuleNotFoundError`:** Certifique-se de que o ambiente virtual está ativo (`source venv/bin/activate`) e que todas as dependências foram instaladas (`pip install -r requirements.txt`).
*   **Problemas de Banco de Dados:** Verifique a string de conexão (`DATABASE_URL` ou `SQLALCHEMY_DATABASE_URI`) e se o servidor de banco de dados está acessível.
*   **Logs:** Verifique os logs da aplicação Flask e do Elasticsearch para mensagens de erro detalhadas.

## Como Contribuir

1.  Faça um fork do projeto.
2.  Crie uma branch para sua feature (`git checkout -b feature/minha-feature`).
3.  Faça commit das suas alterações (`git commit -am 'Adiciona minha feature'`).
4.  Faça push para a branch (`git push origin feature/minha-feature`).
5.  Abra um Pull Request detalhando suas modificações.

