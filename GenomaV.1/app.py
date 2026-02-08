"""
Aplicación Flask - Análisis Genómico de E. coli
Entry Point Principal

Esta es una aplicación Flask minimalista que:
- Registra Blueprints para organizar rutas
- Configura CORS si es necesario
- Maneja errores globales
- Proporciona endpoints de health check
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import config


def create_app():
    """
    Factory function para crear la aplicación Flask.
    
    Returns:
        Flask app configurada
    """
    app = Flask(__name__)
    
    # Configuración
    app.config['DEBUG'] = config.DEBUG
    app.config['JSON_SORT_KEYS'] = False  # Mantener orden de keys en JSON
    
    # CORS (si está habilitado)
    if config.CORS_ENABLED:
        CORS(app, origins=config.CORS_ORIGINS)
    
    # ================================================================
    # REGISTRAR BLUEPRINTS
    # ================================================================
    
    # Blueprints de genomas y genes (refactorizados)
    from routes.api_genomes import bp as genomes_bp
    from routes.api_genes import bp as genes_bp
    
    app.register_blueprint(genomes_bp, url_prefix='/api')
    app.register_blueprint(genes_bp, url_prefix='/api')
    
    # Blueprint de protein designer (nuevo)
    from routes.api_protein_designer import bp as protein_bp
    app.register_blueprint(protein_bp, url_prefix='/api/protein-designer')
    
    # ================================================================
    # RUTAS BÁSICAS
    # ================================================================
    
    @app.route('/')
    def index():
        """Ruta principal - info de la API."""
        return jsonify({
            'message': 'Análisis Genómico de E. coli - API',
            'version': config.PIPELINE_VERSION,
            'endpoints': {
                'genomes': '/api/genomes',
                'genes': '/api/genes',
                'gene_detail': '/api/genes/<gene_id>',
                'compare': '/api/genomes/compare',
                'stats': '/api/genomes/<genome_id>/stats',
                'config': '/api/config',
                'health': '/api/health',
                'cache_stats': '/api/cache/stats'
            },
            'documentation': 'https://github.com/tu-repo/docs'
        })
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        from services.cache_manager import get_cache_manager
        
        try:
            cache = get_cache_manager()
            stats = cache.get_cache_stats()
            
            return jsonify({
                'status': 'healthy',
                'version': config.PIPELINE_VERSION,
                'cache': {
                    'proteins': stats['proteins_count'],
                    'genomes': stats['genomes_count'],
                    'analysis': stats['analysis_count'],
                    'db_size_mb': round(stats['db_size_mb'], 2)
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/config')
    def get_config():
        """Retorna configuración actual (útil para debugging)."""
        if not config.DEBUG:
            return jsonify({'error': 'Config endpoint only available in DEBUG mode'}), 403
        
        return jsonify(config.get_config_dict())
    
    @app.route('/api/cache/stats')
    def cache_stats():
        """Estadísticas del cache."""
        from services.cache_manager import get_cache_manager
        
        cache = get_cache_manager()
        stats = cache.get_cache_stats()
        
        return jsonify(stats)
    
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_cache():
        """
        Limpia cache expirado o todo el cache.
        
        Query params:
            - all=true : Limpiar TODO el cache (precaución)
        """
        from services.cache_manager import get_cache_manager
        
        cache = get_cache_manager()
        clear_all = request.args.get('all', 'false').lower() == 'true'
        
        if clear_all:
            if not config.DEBUG:
                return jsonify({'error': 'Clear all cache only allowed in DEBUG mode'}), 403
            
            cache.clear_all_cache()
            return jsonify({'message': 'All cache cleared'})
        else:
            deleted = cache.clear_expired_cache()
            return jsonify({
                'message': 'Expired cache cleared',
                'deleted': deleted
            })
    
    # ================================================================
    # MANEJO DE ERRORES
    # ================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        """Handler para 404."""
        return jsonify({
            'error': 'Endpoint not found',
            'message': str(error)
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handler para 500."""
        return jsonify({
            'error': 'Internal server error',
            'message': str(error)
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handler global para excepciones no manejadas."""
        if config.DEBUG:
            # En debug, mostrar error completo
            import traceback
            return jsonify({
                'error': str(error),
                'type': type(error).__name__,
                'traceback': traceback.format_exc()
            }), 500
        else:
            # En producción, mensaje genérico
            return jsonify({
                'error': 'An error occurred',
                'message': 'Please contact support'
            }), 500
    
    # ================================================================
    # BEFORE/AFTER REQUEST
    # ================================================================
    
    @app.before_request
    def log_request():
        """Log de requests (solo en DEBUG)."""
        if config.DEBUG:
            print(f"→ {request.method} {request.path}")
    
    @app.after_request
    def add_headers(response):
        """Añade headers a todas las respuestas."""
        response.headers['X-API-Version'] = config.PIPELINE_VERSION
        return response
    
    return app


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == '__main__':
    # Crear app
    app = create_app()
    
    # Validar configuración
    print("=" * 60)
    print("🧬 Análisis Genómico de E. coli - API")
    print("=" * 60)
    print(f"Pipeline Version: {config.PIPELINE_VERSION}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Host: {config.HOST}:{config.PORT}")
    print(f"Cache Dir: {config.CACHE_DIR}")
    print(f"NCBI Email: {config.NCBI_EMAIL}")
    print("=" * 60)
    
    # Inicializar cache al arrancar
    print("\n📦 Inicializando cache...")
    from services.cache_manager import get_cache_manager
    cache = get_cache_manager()
    stats = cache.get_cache_stats()
    print(f"✓ Cache listo: {stats['genomes_count']} genomas, {stats['proteins_count']} proteínas")
    
    # Limpiar cache expirado al inicio
    print("\n🧹 Limpiando cache expirado...")
    deleted = cache.clear_expired_cache()
    print(f"✓ Eliminados: {deleted}")
    
    print("\n🚀 Iniciando servidor...\n")
    
    # Ejecutar
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )