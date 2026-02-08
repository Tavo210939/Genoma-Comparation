"""
NCBI Service - Descarga y manejo de genomas desde NCBI GenBank
Usa Entrez API con cache persistente y manejo robusto de errores.

Funcionalidades:
- Búsqueda de genomas de E. coli
- Descarga de registros GenBank completos
- Cache automático con TTL
- Retry logic para errores de red
- Extracción de features (CDS) del GenBank
"""

import time
from typing import Optional, Dict, List, Any
from Bio import Entrez, SeqIO
from Bio.SeqRecord import SeqRecord

import config
from services.cache_manager import get_cache_manager


# Configurar Entrez
Entrez.email = config.NCBI_EMAIL
if config.NCBI_API_KEY:
    Entrez.api_key = config.NCBI_API_KEY


class NCBIService:
    """Servicio para interactuar con NCBI GenBank."""
    
    def __init__(self):
        self.cache = get_cache_manager()
        self.default_genomes = {
            "K-12 MG1655": "NC_000913.3",
            "K-12 W3110": "NC_007779.1",
            "O157:H7 EDL933": "NC_002695.2",
            "CFT073 (UPEC)": "NC_004431.1",
            "O157:H7 Sakai": "NC_002695.1",
        }
    
    def fetch_genome(self, accession: str, force_refresh: bool = False) -> Optional[SeqRecord]:
        """
        Descarga un genoma desde NCBI con cache.
        
        Args:
            accession: GenBank accession (ej: NC_000913.3)
            force_refresh: Forzar descarga aunque esté en cache
        
        Returns:
            SeqRecord de BioPython o None si falla
        """
        # Intentar obtener del cache primero
        if not force_refresh:
            cached = self.cache.get_genome(accession)
            if cached:
                print(f"✓ Genoma {accession} obtenido del cache")
                return self._cached_to_seqrecord(cached)
        
        # Descargar de NCBI
        print(f"📥 Descargando genoma {accession} desde NCBI...")
        
        for attempt in range(config.NCBI_RETRIES):
            try:
                handle = Entrez.efetch(
                    db="nucleotide",
                    id=accession,
                    rettype="gbwithparts",
                    retmode="text"
                )
                
                record = SeqIO.read(handle, "genbank")
                handle.close()
                
                # Guardar en cache
                self._cache_seqrecord(accession, record)
                
                print(f"✓ Genoma {accession} descargado y cacheado")
                return record
                
            except Exception as e:
                print(f"⚠️ Intento {attempt + 1}/{config.NCBI_RETRIES} falló: {e}")
                
                if attempt < config.NCBI_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                else:
                    print(f"❌ Error descargando {accession}: {e}")
                    return None
        
        return None
    
    def _cache_seqrecord(self, accession: str, record: SeqRecord):
        """Guarda un SeqRecord en el cache."""
        # Extraer features como JSON serializable
        features_data = []
        for feature in record.features:
            features_data.append({
                'type': feature.type,
                'location': str(feature.location),
                'qualifiers': {k: list(v) for k, v in feature.qualifiers.items()},
                'strand': feature.location.strand if hasattr(feature.location, 'strand') else None
            })
        
        data = {
            'accession': accession,
            'organism': record.annotations.get('organism', ''),
            'sequence': str(record.seq),
            'features': features_data
        }
        
        self.cache.cache_genome(accession, data)
    
    def _cached_to_seqrecord(self, cached: Dict[str, Any]) -> SeqRecord:
        """
        Reconstruye un SeqRecord desde datos cacheados.
        
        NOTA: Esto es una versión simplificada. Los features no se
        reconstruyen completamente para evitar complejidad.
        Para análisis completo, se recomienda force_refresh=True.
        """
        from Bio.Seq import Seq
        
        record = SeqRecord(
            Seq(cached['sequence']),
            id=cached['accession'],
            name=cached['accession'],
            description=f"Cached genome: {cached['organism']}"
        )
        
        # Agregar anotación de organismo
        record.annotations['organism'] = cached['organism']
        
        # TODO: Reconstruir features si es necesario
        # Por ahora, trabajamos con los datos JSON directamente
        
        return record
    
    def search_ecoli_genomes(self, max_results: int = 50) -> Dict[str, str]:
        """
        Busca genomas completos de E. coli en GenBank.
        
        Args:
            max_results: Número máximo de resultados
        
        Returns:
            Dict {nombre_descriptivo: accession}
        """
        try:
            print("🔍 Buscando genomas de E. coli en NCBI...")
            
            # Query para genomas completos RefSeq de E. coli
            search_query = (
                'Escherichia coli[Organism] AND '
                '(complete genome[Title] OR complete sequence[Title]) AND '
                'RefSeq[Filter]'
            )
            
            # Búsqueda
            handle = Entrez.esearch(
                db="nucleotide",
                term=search_query,
                retmax=max_results,
                sort="relevance"
            )
            record = Entrez.read(handle)
            handle.close()
            
            genome_ids = record["IdList"]
            
            if not genome_ids:
                print("⚠️ No se encontraron genomas, usando defaults")
                return self.default_genomes
            
            print(f"✓ Encontrados {len(genome_ids)} genomas")
            
            # Obtener información detallada
            handle = Entrez.efetch(
                db="nucleotide",
                id=",".join(genome_ids[:max_results]),
                rettype="gb",
                retmode="xml"
            )
            records = Entrez.read(handle)
            handle.close()
            
            genomes = {}
            for rec in records:
                try:
                    accession = rec['GBSeq_primary-accession']
                    definition = rec['GBSeq_definition']
                    
                    # Extraer nombre de cepa
                    import re
                    strain_match = re.search(r'strain ([A-Z0-9\-:]+)', definition, re.IGNORECASE)
                    strain = strain_match.group(1) if strain_match else "Unknown"
                    
                    # Crear nombre descriptivo
                    if "K-12" in definition and "MG1655" in definition:
                        name = "K-12 MG1655 (Referencia)"
                    elif "O157:H7" in definition:
                        name = f"O157:H7 {strain}"
                    elif "K-12" in definition:
                        name = f"K-12 {strain}"
                    else:
                        name = strain
                    
                    genomes[name] = accession
                    
                except Exception as e:
                    print(f"⚠️ Error procesando registro: {e}")
                    continue
            
            # Combinar con defaults
            genomes.update(self.default_genomes)
            
            print(f"✓ Total de genomas disponibles: {len(genomes)}")
            return genomes
            
        except Exception as e:
            print(f"❌ Error buscando genomas: {e}")
            return self.default_genomes
    
    def get_genome_info(self, accession: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información básica de un genoma sin descargarlo completo.
        
        Args:
            accession: GenBank accession
        
        Returns:
            Dict con info básica o None
        """
        try:
            handle = Entrez.esummary(db="nucleotide", id=accession)
            summary = Entrez.read(handle)
            handle.close()
            
            if not summary:
                return None
            
            record = summary[0]
            
            return {
                'accession': record.get('AccessionVersion', accession),
                'title': record.get('Title', ''),
                'organism': record.get('Organism', ''),
                'length': record.get('Length', 0),
                'create_date': record.get('CreateDate', ''),
                'update_date': record.get('UpdateDate', '')
            }
            
        except Exception as e:
            print(f"⚠️ Error obteniendo info de {accession}: {e}")
            return None
    
    def get_available_genomes(self) -> Dict[str, str]:
        """
        Retorna genomas disponibles (combina defaults + búsqueda).
        
        Returns:
            Dict {nombre: accession}
        """
        # Intentar búsqueda dinámica, fallback a defaults
        try:
            return self.search_ecoli_genomes()
        except:
            return self.default_genomes


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_ncbi_service_instance = None

def get_ncbi_service() -> NCBIService:
    """
    Obtiene la instancia singleton del servicio NCBI.
    
    Returns:
        NCBIService instance
    """
    global _ncbi_service_instance
    
    if _ncbi_service_instance is None:
        _ncbi_service_instance = NCBIService()
    
    return _ncbi_service_instance


# ================================================================
# FUNCIONES DE CONVENIENCIA
# ================================================================

def download_genome(accession: str, force_refresh: bool = False) -> Optional[SeqRecord]:
    """
    Función de conveniencia para descargar un genoma.
    
    Args:
        accession: GenBank accession
        force_refresh: Forzar descarga
    
    Returns:
        SeqRecord o None
    """
    service = get_ncbi_service()
    return service.fetch_genome(accession, force_refresh)


def get_ecoli_genomes() -> Dict[str, str]:
    """
    Función de conveniencia para obtener genomas disponibles.
    
    Returns:
        Dict {nombre: accession}
    """
    service = get_ncbi_service()
    return service.get_available_genomes()


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    print("=== Test NCBI Service ===\n")
    
    # Obtener servicio
    ncbi = get_ncbi_service()
    
    # Test 1: Descargar genoma
    print("1. Descargando genoma K-12 MG1655...")
    record = ncbi.fetch_genome("NC_000913.3")
    
    if record:
        print(f"   ✓ Descargado: {len(record.seq)} bp")
        print(f"   ✓ Features: {len(record.features)}")
    
    # Test 2: Obtener del cache (debe ser instantáneo)
    print("\n2. Obteniendo del cache...")
    record2 = ncbi.fetch_genome("NC_000913.3")
    if record2:
        print(f"   ✓ Cache funciona")
    
    # Test 3: Info básica
    print("\n3. Info básica del genoma...")
    info = ncbi.get_genome_info("NC_000913.3")
    if info:
        print(f"   ✓ Organismo: {info['organism']}")
        print(f"   ✓ Longitud: {info['length']:,} bp")
    
    # Test 4: Buscar genomas
    print("\n4. Buscando genomas de E. coli...")
    genomes = ncbi.get_available_genomes()
    print(f"   ✓ Encontrados: {len(genomes)} genomas")
    for name in list(genomes.keys())[:5]:
        print(f"      - {name}: {genomes[name]}")