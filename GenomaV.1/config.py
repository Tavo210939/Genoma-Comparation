"""
Configuración Central del Proyecto
Análisis Genómico de E. coli + Diseño Genético In-Silico

Todas las configuraciones se manejan con variables de entorno
con valores por defecto sensatos para desarrollo.
"""

import os
from pathlib import Path

# ============================================================
# DIRECTORIOS BASE
# ============================================================

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).parent

# Directorio para cache persistente
CACHE_DIR = Path(os.getenv('CACHE_DIR', BASE_DIR / 'data'))
CACHE_DIR.mkdir(exist_ok=True)

# Directorio para tablas de codones pre-calculadas
CODON_TABLES_DIR = Path(os.getenv('CODON_TABLES_DIR', BASE_DIR / 'data' / 'codon_tables'))
CODON_TABLES_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# NCBI / ENTREZ
# ============================================================

NCBI_EMAIL = os.getenv('NCBI_EMAIL', 'bioinformatica@unsaac.edu.pe')
NCBI_API_KEY = os.getenv('NCBI_API_KEY', None)  # Opcional para rate limit mayor
NCBI_RETRIES = int(os.getenv('NCBI_RETRIES', 3))
NCBI_TIMEOUT = int(os.getenv('NCBI_TIMEOUT', 30))

# ============================================================
# UNIPROT
# ============================================================

UNIPROT_API_BASE = 'https://rest.uniprot.org'
UNIPROT_TIMEOUT = int(os.getenv('UNIPROT_TIMEOUT', 30))
UNIPROT_RETRIES = int(os.getenv('UNIPROT_RETRIES', 3))
UNIPROT_BATCH_SIZE = int(os.getenv('UNIPROT_BATCH_SIZE', 100))

# ============================================================
# CACHE / SQLite
# ============================================================

# Ruta a la base de datos de cache
CACHE_DB_PATH = CACHE_DIR / 'cache.db'

# TTL (Time To Live) en días
CACHE_TTL_PROTEINS = int(os.getenv('CACHE_TTL_PROTEINS', 30))      # 30 días
CACHE_TTL_GENOMES = int(os.getenv('CACHE_TTL_GENOMES', 180))       # 180 días
CACHE_TTL_ANALYSIS = int(os.getenv('CACHE_TTL_ANALYSIS', 7))       # 7 días

# Tamaño máximo del cache en MB
MAX_CACHE_SIZE_MB = int(os.getenv('MAX_CACHE_SIZE', 1000))

# Versión del pipeline (cambiar esto invalida cache de análisis)
PIPELINE_VERSION = os.getenv('PIPELINE_VERSION', '2.0.0')

# ============================================================
# UMBRALES DE SIMILITUD (Protein Comparison)
# ============================================================

# Umbrales para determinar "homolog_exists"
HOMOLOG_IDENTITY_THRESHOLD = float(os.getenv('HOMOLOG_IDENTITY', 60.0))      # ≥60%
HOMOLOG_COVERAGE_THRESHOLD = float(os.getenv('HOMOLOG_COVERAGE', 80.0))      # ≥80%
HOMOLOG_MIN_SCORE = int(os.getenv('HOMOLOG_MIN_SCORE', 100))

# Umbrales para "borderline" (baja confidence pero no cambia base_case)
BORDERLINE_IDENTITY_THRESHOLD = float(os.getenv('BORDERLINE_IDENTITY', 50.0))  # 50-60%
BORDERLINE_COVERAGE_THRESHOLD = float(os.getenv('BORDERLINE_COVERAGE', 70.0))  # 70-80%

# Umbrales para "no_homolog" (definitivamente no hay match)
NO_HOMOLOG_IDENTITY_THRESHOLD = float(os.getenv('NO_HOMOLOG_IDENTITY', 30.0))  # <30%
NO_HOMOLOG_COVERAGE_THRESHOLD = float(os.getenv('NO_HOMOLOG_COVERAGE', 50.0))  # <50%

# ============================================================
# PARÁMETROS DE COMPARACIÓN HÍBRIDA
# ============================================================

# K-mers para filtrado rápido
KMER_SIZE = int(os.getenv('KMER_SIZE', 3))  # Tripletes de aminoácidos

# Top N candidatos a alinear después del filtrado
TOP_CANDIDATES_FOR_ALIGNMENT = int(os.getenv('TOP_CANDIDATES', 50))

# Método de similitud para k-mers: 'jaccard' o 'cosine'
KMER_SIMILARITY_METHOD = os.getenv('KMER_SIMILARITY', 'jaccard')

# ============================================================
# CONFIGURACIÓN DE ALERTAS (Compatibility)
# ============================================================

ALERTS_CONFIG = {
    'glycosylation': {
        'level': 'RED',
        'message': 'Requiere glicosilación N/O-linked (no funcional en E. coli sin modificaciones)',
        'keywords': ['glycosylation', 'n-glycan', 'o-glycan']
    },
    'signal_peptide': {
        'level': 'YELLOW',
        'message': 'Proteína secretada - requiere verificación del sistema Sec de E. coli',
        'keywords': ['signal peptide', 'signal sequence']
    },
    'transmembrane': {
        'level': 'RED',
        'threshold': 3,  # >3 dominios transmembrana
        'message': 'Múltiples dominios transmembrana - alto riesgo de agregación en membrana',
        'keywords': ['transmembrane', 'membrane protein']
    },
    'disulfide_bonds': {
        'level': 'YELLOW',
        'message': 'Requiere formación de puentes disulfuro (posible en periplasma)',
        'keywords': ['disulfide bond', 'disulfide bridge']
    },
    'metal_binding': {
        'level': 'YELLOW',
        'message': 'Dependiente de iones metálicos específicos - verificar disponibilidad',
        'keywords': ['metal binding', 'zinc', 'iron', 'copper', 'magnesium']
    },
    'cofactor_required': {
        'level': 'YELLOW',
        'message': 'Requiere cofactores específicos - verificar biosíntesis en E. coli',
        'keywords': ['cofactor', 'heme', 'fad', 'nad', 'biotin']
    },
    'protease': {
        'level': 'RED',
        'message': 'Proteasa - riesgo de toxicidad celular',
        'keywords': ['protease', 'peptidase', 'endopeptidase']
    },
    'toxin': {
        'level': 'RED',
        'message': 'Toxina identificada - alto riesgo para la célula hospedera',
        'keywords': ['toxin', 'toxic', 'lethal']
    }
}

# Reglas de compatibility
# high_risk: ≥1 alerta RED
# conditions: ≥1 alerta YELLOW (sin RED)
# ok: sin alertas

# ============================================================
# OPTIMIZACIÓN DE CODONES
# ============================================================

# Genoma de referencia para tabla de codones por defecto
REFERENCE_GENOME_ID = 'NC_000913.3'  # E. coli K-12 MG1655

# Modo de optimización
CODON_OPTIMIZATION_MODE = os.getenv('CODON_OPT_MODE', 'dynamic')  # 'dynamic' o 'fixed'

# Umbral de codones raros (%) para reportar
RARE_CODON_THRESHOLD = float(os.getenv('RARE_CODON_THRESHOLD', 5.0))  # >5% de codones raros

# ============================================================
# FLASK / API
# ============================================================

DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('FLASK_PORT', 5000))

# CORS (si es necesario)
CORS_ENABLED = os.getenv('CORS_ENABLED', 'False').lower() == 'true'
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Rate limiting (requests por minuto)
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT', 60))

# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = os.getenv('LOG_FILE', None)  # None = solo consola

# ============================================================
# VALIDACIÓN AL IMPORTAR
# ============================================================

def validate_config():
    """Valida que la configuración esté correcta al arrancar la app."""
    
    errors = []
    
    # Validar email NCBI
    if '@' not in NCBI_EMAIL:
        errors.append(f"NCBI_EMAIL inválido: {NCBI_EMAIL}")
    
    # Validar umbrales
    if not (0 <= HOMOLOG_IDENTITY_THRESHOLD <= 100):
        errors.append(f"HOMOLOG_IDENTITY_THRESHOLD debe estar entre 0-100: {HOMOLOG_IDENTITY_THRESHOLD}")
    
    if not (0 <= HOMOLOG_COVERAGE_THRESHOLD <= 100):
        errors.append(f"HOMOLOG_COVERAGE_THRESHOLD debe estar entre 0-100: {HOMOLOG_COVERAGE_THRESHOLD}")
    
    # Validar K-mer size
    if not (2 <= KMER_SIZE <= 5):
        errors.append(f"KMER_SIZE debe estar entre 2-5: {KMER_SIZE}")
    
    # Validar directorios
    if not CACHE_DIR.exists():
        errors.append(f"CACHE_DIR no existe: {CACHE_DIR}")
    
    if errors:
        raise ValueError(f"Errores de configuración:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return True


# Validar al importar (en desarrollo)
if DEBUG:
    try:
        validate_config()
        print("✓ Configuración validada correctamente")
    except ValueError as e:
        print(f"⚠️  ADVERTENCIA: {e}")


# ============================================================
# HELPER: Obtener configuración como dict (para debugging)
# ============================================================

def get_config_dict():
    """Retorna configuración actual como diccionario (útil para /api/config)."""
    return {
        'pipeline_version': PIPELINE_VERSION,
        'cache_dir': str(CACHE_DIR),
        'ncbi_email': NCBI_EMAIL,
        'uniprot_api': UNIPROT_API_BASE,
        'thresholds': {
            'homolog_identity': HOMOLOG_IDENTITY_THRESHOLD,
            'homolog_coverage': HOMOLOG_COVERAGE_THRESHOLD,
            'borderline_identity': BORDERLINE_IDENTITY_THRESHOLD,
            'borderline_coverage': BORDERLINE_COVERAGE_THRESHOLD,
        },
        'comparison': {
            'kmer_size': KMER_SIZE,
            'top_candidates': TOP_CANDIDATES_FOR_ALIGNMENT,
            'similarity_method': KMER_SIMILARITY_METHOD,
        },
        'cache_ttl': {
            'proteins': CACHE_TTL_PROTEINS,
            'genomes': CACHE_TTL_GENOMES,
            'analysis': CACHE_TTL_ANALYSIS,
        }
    }