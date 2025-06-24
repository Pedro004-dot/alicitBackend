from flask import Blueprint, request, current_app, jsonify
from controllers.rag_controller import RAGController

def create_rag_routes(rag_service):
    """Factory para criar rotas RAG"""
    
    rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')
    rag_controller = RAGController(rag_service)
    
    @rag_bp.route('/analisarDocumentos', methods=['POST', 'OPTIONS'])
    def analisar_documentos():
        """
        Endpoint principal para análise de documentos de licitação
        
        Body JSON:
        {
            "licitacao_id": "uuid",
            "query": "string (opcional)"
        }
        """
        if request.method == 'OPTIONS':
            return '', 204
        return rag_controller.analisar_documentos()
    
    @rag_bp.route('/query', methods=['POST', 'OPTIONS'])
    def query_licitacao():
        """
        Endpoint para fazer perguntas específicas sobre uma licitação
        
        Body JSON:
        {
            "licitacao_id": "uuid",
            "query": "string"
        }
        """
        if request.method == 'OPTIONS':
            return '', 204
        return rag_controller.query_licitacao()
    
    @rag_bp.route('/status', methods=['GET'])
    def status_licitacao():
        """
        Endpoint para verificar status de processamento
        
        Query params:
        - licitacao_id: UUID da licitação
        """
        return rag_controller.status_licitacao()
    
    @rag_bp.route('/cache/invalidate', methods=['POST', 'OPTIONS'])
    def invalidar_cache():
        """
        Endpoint para invalidar cache de uma licitação
        
        Body JSON:
        {
            "licitacao_id": "uuid"
        }
        """
        if request.method == 'OPTIONS':
            return '', 204
        return rag_controller.invalidar_cache()
    
    @rag_bp.route('/reprocessar', methods=['POST', 'OPTIONS'])
    def reprocessar_documentos():
        """
        Endpoint para forçar reprocessamento de documentos com extração recursiva
        
        Body JSON:
        {
            "licitacao_id": "uuid",
            "forcar_reprocessamento": true (opcional, padrão: true)
        }
        """
        if request.method == 'OPTIONS':
            return '', 204
        return rag_controller.reprocessar_documentos()
    
    @rag_bp.route('/vectorize', methods=['POST', 'OPTIONS'])
    def vectorize_documents():
        """
        Endpoint para vetorização de documentos (usado na preparação automática)
        
        Body JSON:
        {
            "licitacao_id": "uuid"
        }
        """
        if request.method == 'OPTIONS':
            return '', 204
            
        return rag_controller.vectorize_documents()
    
    return rag_bp

def create_rag_routes_lazy():
    """Factory para criar rotas RAG com lazy loading"""
    
    rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')
    
    def get_rag_controller():
        """Obter RAG controller com lazy loading"""
        from app import get_rag_service
        rag_service = get_rag_service(current_app)
        if rag_service is None:
            return None
        return RAGController(rag_service)
    
    def rag_not_available():
        """Resposta padrão quando RAG não está disponível"""
        return jsonify({
            'error': 'RAG service não disponível',
            'message': 'O serviço RAG não pôde ser inicializado. Verifique as configurações.',
            'status': 'service_unavailable'
        }), 503
    
    @rag_bp.route('/analisarDocumentos', methods=['POST', 'OPTIONS'])
    def analisar_documentos():
        if request.method == 'OPTIONS':
            return '', 204
        
        rag_controller = get_rag_controller()
        if rag_controller is None:
            return rag_not_available()
        return rag_controller.analisar_documentos()
    
    @rag_bp.route('/query', methods=['POST', 'OPTIONS'])
    def query_licitacao():
        if request.method == 'OPTIONS':
            return '', 204
            
        rag_controller = get_rag_controller()
        if rag_controller is None:
            return rag_not_available()
        return rag_controller.query_licitacao()
    
    @rag_bp.route('/status', methods=['GET'])
    def status_licitacao():
        rag_controller = get_rag_controller()
        if rag_controller is None:
            return rag_not_available()
        return rag_controller.status_licitacao()
    
    @rag_bp.route('/cache/invalidate', methods=['POST', 'OPTIONS'])
    def invalidar_cache():
        if request.method == 'OPTIONS':
            return '', 204
            
        rag_controller = get_rag_controller()
        if rag_controller is None:
            return rag_not_available()
        return rag_controller.invalidar_cache()
    
    @rag_bp.route('/reprocessar', methods=['POST', 'OPTIONS'])
    def reprocessar_documentos():
        if request.method == 'OPTIONS':
            return '', 204
            
        rag_controller = get_rag_controller()
        if rag_controller is None:
            return rag_not_available()
        return rag_controller.reprocessar_documentos()
    
    @rag_bp.route('/vectorize', methods=['POST', 'OPTIONS'])
    def vectorize_documents():
        """
        Endpoint para vetorização de documentos (usado na preparação automática)
        
        Body JSON:
        {
            "licitacao_id": "uuid"
        }
        """
        if request.method == 'OPTIONS':
            return '', 204
            
        rag_controller = get_rag_controller()
        if rag_controller is None:
            return rag_not_available()
        return rag_controller.vectorize_documents()
    
    return rag_bp 