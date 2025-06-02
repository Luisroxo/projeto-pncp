"""
Modelo de dados para licitações.
Este módulo define a estrutura de dados para armazenamento de licitações.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Index, text

# Inicialização do SQLAlchemy
db = SQLAlchemy()

class Licitacao(db.Model):
    """Modelo para armazenamento de licitações."""
    
    __tablename__ = 'licitacoes'
    
    # Campos de identificação
    id = db.Column(db.Integer, primary_key=True)
    id_externo = db.Column(db.String(100), unique=True, nullable=False, index=True)
    fonte = db.Column(db.String(20), nullable=False, index=True)  # PNCP, ComprasNet, etc.
    sequencial = db.Column(db.String(50), nullable=True)
    ano = db.Column(db.String(4), nullable=True)
    
    # Campos descritivos
    objeto = db.Column(db.Text, nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    valor_estimado = db.Column(db.Float, nullable=True)
    modalidade = db.Column(db.String(100), nullable=True, index=True)
    situacao = db.Column(db.String(50), nullable=True, index=True)
    
    # Campos temporais
    data_publicacao = db.Column(db.DateTime, nullable=True, index=True)
    data_abertura = db.Column(db.DateTime, nullable=True, index=True)
    data_criacao = db.Column(db.DateTime, default=datetime.now, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # Campos de localização
    orgao_nome = db.Column(db.String(255), nullable=True, index=True)
    orgao_id = db.Column(db.String(20), nullable=True, index=True)  # CNPJ ou código
    municipio = db.Column(db.String(100), nullable=True, index=True)
    uf = db.Column(db.String(2), nullable=True, index=True)
    
    # Campos para armazenamento de dados completos
    dados_completos = db.Column(db.Text, nullable=True)  # JSON como texto
    
    # Campos para indexação e busca
    indexado = db.Column(db.Boolean, default=False, nullable=False)
    data_indexacao = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos (serão implementados conforme necessário)
    # documentos = db.relationship('Documento', backref='licitacao', lazy=True)
    
    def __init__(self, **kwargs):
        """Inicializa uma nova licitação com os parâmetros fornecidos."""
        super(Licitacao, self).__init__(**kwargs)
    
    def __repr__(self):
        """Representação string da licitação."""
        return f'<Licitacao {self.id_externo}: {self.objeto[:30]}...>'
    
    def to_dict(self):
        """
        Converte o objeto Licitacao para um dicionário.
        
        Returns:
            Dicionário com os dados da licitação.
        """
        return {
            'id': self.id,
            'id_externo': self.id_externo,
            'fonte': self.fonte,
            'sequencial': self.sequencial,
            'ano': self.ano,
            'objeto': self.objeto,
            'descricao': self.descricao,
            'valor_estimado': self.valor_estimado,
            'modalidade': self.modalidade,
            'situacao': self.situacao,
            'data_publicacao': self.data_publicacao.isoformat() if self.data_publicacao else None,
            'data_abertura': self.data_abertura.isoformat() if self.data_abertura else None,
            'orgao_nome': self.orgao_nome,
            'orgao_id': self.orgao_id,
            'municipio': self.municipio,
            'uf': self.uf,
            'data_criacao': self.data_criacao.isoformat(),
            'data_atualizacao': self.data_atualizacao.isoformat()
        }
    
    @classmethod
    def create_indices(cls):
        """
        Cria índices adicionais para otimização de consultas.
        Esta função deve ser chamada após a criação das tabelas.
        """
        # Índice de texto para busca full-text (PostgreSQL)
        if db.engine.dialect.name == 'postgresql':
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_licitacoes_objeto_descricao ON licitacoes "
                "USING gin(to_tsvector('portuguese', objeto || ' ' || COALESCE(descricao, '')))"
            ))
            db.session.commit()


# Índices compostos para consultas comuns
Index('idx_licitacoes_modalidade_situacao', Licitacao.modalidade, Licitacao.situacao)
Index('idx_licitacoes_data_valor', Licitacao.data_abertura, Licitacao.valor_estimado)
Index('idx_licitacoes_uf_municipio', Licitacao.uf, Licitacao.municipio)


class LicitacaoFavorita(db.Model):
    """Modelo para armazenamento de licitações favoritas dos usuários."""
    
    __tablename__ = 'licitacoes_favoritas'
    
    id = db.Column(db.Integer, primary_key=True)
    licitacao_id = db.Column(db.Integer, db.ForeignKey('licitacoes.id'), nullable=False)
    usuario_id = db.Column(db.Integer, nullable=False)  # Referência ao usuário
    data_criacao = db.Column(db.DateTime, default=datetime.now, nullable=False)
    notas = db.Column(db.Text, nullable=True)
    
    # Relacionamento com a licitação
    licitacao = db.relationship('Licitacao', backref=db.backref('favoritos', lazy=True))
    
    # Índice composto para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('licitacao_id', 'usuario_id', name='uq_licitacao_usuario'),
    )
    
    def __repr__(self):
        """Representação string da licitação favorita."""
        return f'<LicitacaoFavorita {self.id}: Licitacao {self.licitacao_id}, Usuario {self.usuario_id}>'


class HistoricoBusca(db.Model):
    """Modelo para armazenamento do histórico de buscas dos usuários."""
    
    __tablename__ = 'historico_buscas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, index=True)  # Referência ao usuário
    termo_busca = db.Column(db.String(255), nullable=False)
    filtros = db.Column(db.Text, nullable=True)  # JSON como texto
    data_busca = db.Column(db.DateTime, default=datetime.now, nullable=False)
    resultados_count = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        """Representação string do histórico de busca."""
        return f'<HistoricoBusca {self.id}: "{self.termo_busca}" por Usuario {self.usuario_id}>'


class ConfiguracaoAlerta(db.Model):
    """Modelo para armazenamento de configurações de alertas de licitações."""
    
    __tablename__ = 'configuracoes_alertas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, index=True)  # Referência ao usuário
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    
    # Critérios de alerta
    palavras_chave = db.Column(db.String(255), nullable=True)
    modalidades = db.Column(db.String(255), nullable=True)  # Lista separada por vírgulas
    valor_minimo = db.Column(db.Float, nullable=True)
    valor_maximo = db.Column(db.Float, nullable=True)
    ufs = db.Column(db.String(100), nullable=True)  # Lista separada por vírgulas
    
    # Configurações de notificação
    email_ativo = db.Column(db.Boolean, default=True, nullable=False)
    push_ativo = db.Column(db.Boolean, default=False, nullable=False)
    sms_ativo = db.Column(db.Boolean, default=False, nullable=False)
    frequencia = db.Column(db.String(20), default='diaria', nullable=False)  # diaria, imediata, semanal
    
    # Metadados
    data_criacao = db.Column(db.DateTime, default=datetime.now, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        """Representação string da configuração de alerta."""
        return f'<ConfiguracaoAlerta {self.id}: "{self.nome}" para Usuario {self.usuario_id}>'
