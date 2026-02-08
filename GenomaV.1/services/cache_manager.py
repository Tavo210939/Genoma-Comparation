"""
Cache Manager - Sistema de Cache Persistente con SQLite
Maneja cache de genomas, proteínas, análisis y proteomas con TTL.

Características:
- 1 base de datos SQLite (cache.db) con múltiples tablas
- TTL (Time To Live) configurable por tipo de dato
- Invalidación automática de cache obsoleto
- Hashing de secuencias para detectar cambios
- Pipeline versioning para invalidar análisis antiguos
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

import config


class CacheManager:
    """Gestor centralizado de cache persistente."""
    
    def __init__(self, db_path: Path = config.CACHE_DB_PATH):
        """
        Inicializa el cache manager.
        
        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        self._ensure_db_exists()
    
    @contextmanager
    def _get_connection(self):
        """Context manager para manejar conexiones SQLite de forma segura."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _ensure_db_exists(self):
        """Crea las tablas si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla: proteins (cache de UniProt)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proteins (
                    accession TEXT PRIMARY KEY,
                    name TEXT,
                    organism TEXT,
                    sequence TEXT NOT NULL,
                    sequence_sha256 TEXT NOT NULL,
                    length INTEGER,
                    reviewed INTEGER,  -- 0/1 para boolean
                    metadata TEXT,  -- JSON con todas las anotaciones
                    fetched_at TEXT NOT NULL,
                    ttl_days INTEGER DEFAULT 30
                )
            """)
            
            # Índice para búsquedas rápidas por organismo
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_proteins_organism 
                ON proteins(organism)
            """)
            
            # Tabla: genomes (cache de NCBI)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS genomes (
                    accession TEXT PRIMARY KEY,
                    organism TEXT,
                    sequence TEXT NOT NULL,
                    features TEXT,  -- JSON con features del GenBank
                    fetched_at TEXT NOT NULL,
                    ttl_days INTEGER DEFAULT 180
                )
            """)
            
            # Tabla: analysis_cache (resultados de análisis computados)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    genome_id TEXT,
                    analysis_type TEXT,
                    pipeline_version TEXT,
                    result TEXT,  -- JSON con resultados
                    computed_at TEXT NOT NULL,
                    PRIMARY KEY (genome_id, analysis_type)
                )
            """)
            
            # Tabla: proteomes (proteoma traducido de un genoma)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proteomes (
                    genome_id TEXT PRIMARY KEY,
                    proteins TEXT NOT NULL,  -- JSON array de proteínas
                    protein_count INTEGER,
                    computed_at TEXT NOT NULL,
                    pipeline_version TEXT
                )
            """)
            
            conn.commit()
    
    # ================================================================
    # PROTEÍNAS (UniProt)
    # ================================================================
    
    def get_protein(self, accession: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una proteína del cache si existe y no ha expirado.
        
        Args:
            accession: UniProt accession (ej: P01308)
        
        Returns:
            Dict con datos de la proteína o None si no existe/expiró
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM proteins WHERE accession = ?
            """, (accession,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Verificar si expiró
            fetched_at = datetime.fromisoformat(row['fetched_at'])
            ttl = timedelta(days=row['ttl_days'])
            
            if datetime.now() - fetched_at > ttl:
                # Cache expirado, eliminar y retornar None
                cursor.execute("DELETE FROM proteins WHERE accession = ?", (accession,))
                conn.commit()
                return None
            
            # Cache válido, retornar datos
            return {
                'accession': row['accession'],
                'name': row['name'],
                'organism': row['organism'],
                'sequence': row['sequence'],
                'sequence_sha256': row['sequence_sha256'],
                'length': row['length'],
                'reviewed': bool(row['reviewed']),
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'fetched_at': row['fetched_at']
            }
    
    def cache_protein(self, accession: str, data: Dict[str, Any], 
                     ttl_days: int = config.CACHE_TTL_PROTEINS):
        """
        Guarda o actualiza una proteína en el cache.
        
        Args:
            accession: UniProt accession
            data: Dict con datos de la proteína
            ttl_days: Días antes de expirar
        """
        sequence = data.get('sequence', '')
        sequence_hash = hashlib.sha256(sequence.encode()).hexdigest()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO proteins 
                (accession, name, organism, sequence, sequence_sha256, length, 
                 reviewed, metadata, fetched_at, ttl_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                accession,
                data.get('name', ''),
                data.get('organism', ''),
                sequence,
                sequence_hash,
                data.get('length', len(sequence)),
                int(data.get('reviewed', False)),
                json.dumps(data.get('metadata', {})),
                datetime.now().isoformat(),
                ttl_days
            ))
    
    def search_proteins_by_organism(self, organism: str) -> List[str]:
        """
        Busca accessions de proteínas por organismo en cache.
        
        Args:
            organism: Nombre del organismo
        
        Returns:
            Lista de accessions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT accession FROM proteins 
                WHERE organism LIKE ?
            """, (f"%{organism}%",))
            
            return [row['accession'] for row in cursor.fetchall()]
    
    # ================================================================
    # GENOMAS (NCBI)
    # ================================================================
    
    def get_genome(self, accession: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un genoma del cache si existe y no ha expirado.
        
        Args:
            accession: GenBank accession (ej: NC_000913.3)
        
        Returns:
            Dict con datos del genoma o None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM genomes WHERE accession = ?
            """, (accession,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Verificar TTL
            fetched_at = datetime.fromisoformat(row['fetched_at'])
            ttl = timedelta(days=row['ttl_days'])
            
            if datetime.now() - fetched_at > ttl:
                cursor.execute("DELETE FROM genomes WHERE accession = ?", (accession,))
                conn.commit()
                return None
            
            return {
                'accession': row['accession'],
                'organism': row['organism'],
                'sequence': row['sequence'],
                'features': json.loads(row['features']) if row['features'] else [],
                'fetched_at': row['fetched_at']
            }
    
    def cache_genome(self, accession: str, data: Dict[str, Any],
                    ttl_days: int = config.CACHE_TTL_GENOMES):
        """
        Guarda o actualiza un genoma en el cache.
        
        Args:
            accession: GenBank accession
            data: Dict con datos del genoma
            ttl_days: Días antes de expirar
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO genomes
                (accession, organism, sequence, features, fetched_at, ttl_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                accession,
                data.get('organism', ''),
                data.get('sequence', ''),
                json.dumps(data.get('features', [])),
                datetime.now().isoformat(),
                ttl_days
            ))
    
    # ================================================================
    # ANÁLISIS (resultados computados)
    # ================================================================
    
    def get_analysis(self, genome_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un análisis del cache si existe y coincide la versión del pipeline.
        
        Args:
            genome_id: ID del genoma
            analysis_type: Tipo de análisis (ej: 'codons_cds', 'genes', etc)
        
        Returns:
            Dict con resultados o None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_cache 
                WHERE genome_id = ? AND analysis_type = ?
            """, (genome_id, analysis_type))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Verificar versión del pipeline
            if row['pipeline_version'] != config.PIPELINE_VERSION:
                # Pipeline cambió, invalidar cache
                cursor.execute("""
                    DELETE FROM analysis_cache 
                    WHERE genome_id = ? AND analysis_type = ?
                """, (genome_id, analysis_type))
                conn.commit()
                return None
            
            # Verificar TTL
            computed_at = datetime.fromisoformat(row['computed_at'])
            ttl = timedelta(days=config.CACHE_TTL_ANALYSIS)
            
            if datetime.now() - computed_at > ttl:
                cursor.execute("""
                    DELETE FROM analysis_cache 
                    WHERE genome_id = ? AND analysis_type = ?
                """, (genome_id, analysis_type))
                conn.commit()
                return None
            
            return json.loads(row['result'])
    
    def cache_analysis(self, genome_id: str, analysis_type: str, result: Dict[str, Any]):
        """
        Guarda un resultado de análisis en cache.
        
        Args:
            genome_id: ID del genoma
            analysis_type: Tipo de análisis
            result: Resultados a guardar
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_cache
                (genome_id, analysis_type, pipeline_version, result, computed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                genome_id,
                analysis_type,
                config.PIPELINE_VERSION,
                json.dumps(result),
                datetime.now().isoformat()
            ))
    
    def invalidate_analysis(self, genome_id: str, analysis_type: Optional[str] = None):
        """
        Invalida cache de análisis (útil al cambiar el pipeline).
        
        Args:
            genome_id: ID del genoma
            analysis_type: Tipo específico o None para todos
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if analysis_type:
                cursor.execute("""
                    DELETE FROM analysis_cache 
                    WHERE genome_id = ? AND analysis_type = ?
                """, (genome_id, analysis_type))
            else:
                cursor.execute("""
                    DELETE FROM analysis_cache WHERE genome_id = ?
                """, (genome_id,))
    
    # ================================================================
    # PROTEOMAS (proteínas traducidas del genoma)
    # ================================================================
    
    def get_proteome(self, genome_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el proteoma traducido de un genoma.
        
        Args:
            genome_id: ID del genoma
        
        Returns:
            Dict con proteínas traducidas o None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM proteomes WHERE genome_id = ?
            """, (genome_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Verificar versión del pipeline
            if row['pipeline_version'] != config.PIPELINE_VERSION:
                cursor.execute("DELETE FROM proteomes WHERE genome_id = ?", (genome_id,))
                conn.commit()
                return None
            
            return {
                'genome_id': row['genome_id'],
                'proteins': json.loads(row['proteins']),
                'protein_count': row['protein_count'],
                'computed_at': row['computed_at']
            }
    
    def cache_proteome(self, genome_id: str, proteins: List[Dict[str, Any]]):
        """
        Guarda el proteoma traducido de un genoma.
        
        Args:
            genome_id: ID del genoma
            proteins: Lista de proteínas traducidas
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO proteomes
                (genome_id, proteins, protein_count, computed_at, pipeline_version)
                VALUES (?, ?, ?, ?, ?)
            """, (
                genome_id,
                json.dumps(proteins),
                len(proteins),
                datetime.now().isoformat(),
                config.PIPELINE_VERSION
            ))
    
    # ================================================================
    # UTILIDADES
    # ================================================================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache.
        
        Returns:
            Dict con estadísticas
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Contar proteínas
            cursor.execute("SELECT COUNT(*) as count FROM proteins")
            stats['proteins_count'] = cursor.fetchone()['count']
            
            # Contar genomas
            cursor.execute("SELECT COUNT(*) as count FROM genomes")
            stats['genomes_count'] = cursor.fetchone()['count']
            
            # Contar análisis
            cursor.execute("SELECT COUNT(*) as count FROM analysis_cache")
            stats['analysis_count'] = cursor.fetchone()['count']
            
            # Contar proteomas
            cursor.execute("SELECT COUNT(*) as count FROM proteomes")
            stats['proteomes_count'] = cursor.fetchone()['count']
            
            # Tamaño del archivo DB
            stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats
    
    def clear_expired_cache(self):
        """
        Limpia todo el cache expirado de todas las tablas.
        
        Returns:
            Dict con número de items eliminados por tabla
        """
        deleted = {'proteins': 0, 'genomes': 0, 'analysis': 0}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Limpiar proteínas expiradas
            cursor.execute("""
                DELETE FROM proteins 
                WHERE datetime(fetched_at, '+' || ttl_days || ' days') < datetime('now')
            """)
            deleted['proteins'] = cursor.rowcount
            
            # Limpiar genomas expirados
            cursor.execute("""
                DELETE FROM genomes 
                WHERE datetime(fetched_at, '+' || ttl_days || ' days') < datetime('now')
            """)
            deleted['genomes'] = cursor.rowcount
            
            # Limpiar análisis expirados
            cursor.execute(f"""
                DELETE FROM analysis_cache 
                WHERE datetime(computed_at, '+{config.CACHE_TTL_ANALYSIS} days') < datetime('now')
            """)
            deleted['analysis'] = cursor.rowcount
            
            conn.commit()
        
        return deleted
    
    def clear_all_cache(self):
        """Limpia TODO el cache (usar con precaución)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM proteins")
            cursor.execute("DELETE FROM genomes")
            cursor.execute("DELETE FROM analysis_cache")
            cursor.execute("DELETE FROM proteomes")
            conn.commit()


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_cache_manager_instance = None

def get_cache_manager() -> CacheManager:
    """
    Obtiene la instancia singleton del cache manager.
    
    Returns:
        CacheManager instance
    """
    global _cache_manager_instance
    
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager()
    
    return _cache_manager_instance


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    # Crear instancia
    cache = get_cache_manager()
    
    # Ejemplo: guardar proteína
    protein_data = {
        'accession': 'P01308',
        'name': 'Insulin',
        'organism': 'Homo sapiens',
        'sequence': 'MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT',
        'length': 110,
        'reviewed': True,
        'metadata': {
            'signal_peptide': True,
            'disulfide_bonds': 3
        }
    }
    
    cache.cache_protein('P01308', protein_data)
    print("✓ Proteína guardada")
    
    # Recuperar
    cached = cache.get_protein('P01308')
    print(f"✓ Proteína recuperada: {cached['name']}")
    
    # Estadísticas
    stats = cache.get_cache_stats()
    print(f"✓ Estadísticas: {stats}")