"""
Instruções para instalação e configuração do Elasticsearch para o módulo "Encontrar" licitações.
"""

# Configuração do Elasticsearch para o Módulo "Encontrar" Licitações

Este documento fornece instruções detalhadas para instalar e configurar o Elasticsearch, necessário para o funcionamento do módulo de busca de licitações.

## 1. Instalação via Docker (Recomendado)

A maneira mais simples de configurar o Elasticsearch é usando Docker:

```bash
# Criar um volume para persistência dos dados
docker volume create elasticsearch-data

# Iniciar o Elasticsearch
docker run -d \
  --name elasticsearch \
  -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -v elasticsearch-data:/usr/share/elasticsearch/data \
  elasticsearch:8.8.0
```

## 2. Instalação Nativa

Se preferir instalar diretamente no sistema:

### Ubuntu/Debian:
```bash
# Instalar dependências
sudo apt-get update
sudo apt-get install openjdk-11-jdk

# Adicionar repositório Elasticsearch
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
sudo sh -c 'echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" > /etc/apt/sources.list.d/elastic-8.x.list'
sudo apt-get update

# Instalar Elasticsearch
sudo apt-get install elasticsearch

# Configurar e iniciar o serviço
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch
```

## 3. Configuração do Elasticsearch

Edite o arquivo de configuração do Elasticsearch:

```bash
# Se instalado via Docker, entre no container:
docker exec -it elasticsearch bash
vi /usr/share/elasticsearch/config/elasticsearch.yml

# Se instalado nativamente:
sudo vi /etc/elasticsearch/elasticsearch.yml
```

Configurações recomendadas:
```yaml
# Configurações básicas
cluster.name: licitacoes-cluster
node.name: node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch

# Configurações de rede
network.host: 0.0.0.0
http.port: 9200

# Configurações de memória
bootstrap.memory_lock: true

# Desabilitar segurança para desenvolvimento
xpack.security.enabled: false

# Configurações para análise em português
analysis:
  analyzer:
    portuguese_analyzer:
      type: custom
      tokenizer: standard
      filter: [lowercase, portuguese_stop, portuguese_stemmer]
  filter:
    portuguese_stop:
      type: stop
      stopwords: _portuguese_
    portuguese_stemmer:
      type: stemmer
      language: portuguese
```

## 4. Verificação da Instalação

Após a instalação, verifique se o Elasticsearch está funcionando:

```bash
curl http://localhost:9200
```

Você deve receber uma resposta JSON com informações sobre o cluster.

## 5. Configuração do Módulo "Encontrar"

Após instalar o Elasticsearch, atualize a configuração do módulo:

1. Edite o arquivo de configuração em `src/config.py` para apontar para o Elasticsearch:

```python
# Configuração do Elasticsearch
ELASTICSEARCH_HOSTS = ['http://localhost:9200']
ELASTICSEARCH_INDEX = 'licitacoes'
```

2. Execute o script de teste para verificar a conexão:

```bash
cd /home/ubuntu/modulo-encontrar
source venv/bin/activate
python test_elasticsearch.py
```

## 6. Inicialização do Índice

Para inicializar o índice de licitações:

```bash
cd /home/ubuntu/modulo-encontrar
source venv/bin/activate
python -c "from src.utils.elasticsearch_service import get_elasticsearch_service; es = get_elasticsearch_service(); es.create_index()"
```

## 7. Sincronização Inicial

Para realizar a primeira sincronização e indexação de licitações:

```bash
cd /home/ubuntu/modulo-encontrar
source venv/bin/activate
python -c "from src.integrations.pncp_sync import PNCPSyncService; sync = PNCPSyncService(); sync.sync_licitacoes()"
```

## Solução de Problemas

### Erro de Conexão Recusada
Se você receber o erro "Connection refused", verifique:
- Se o Elasticsearch está em execução
- Se a porta 9200 está acessível
- Se há algum firewall bloqueando a conexão

### Erro de Memória
Se o Elasticsearch falhar por falta de memória:
- Ajuste as configurações de memória no arquivo elasticsearch.yml
- Reduza o valor de ES_JAVA_OPTS para se adequar ao seu ambiente

### Logs do Elasticsearch
Para verificar os logs:
```bash
# Docker
docker logs elasticsearch

# Nativo
sudo journalctl -u elasticsearch
```
