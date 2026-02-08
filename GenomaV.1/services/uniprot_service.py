"""
UniProt Service - Búsqueda y descarga de proteínas desde UniProt
Usa la API REST de UniProt con cache persistente.

API Documentation: https://www.uniprot.org/help/api
"""

import requests
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

import config
from models.protein import Protein
from services.cache_manager import get_cache_manager
from utils.sequence_utils import sequence_hash


class UniProtService:
    """Servicio para interactuar con UniProt API."""
    
    def __init__(self):
        self.base_url = config.UNIPROT_API_BASE
        self.cache = get_cache_manager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GenomeAnalysisTool/2.0 (bioinformatica@unsaac.edu.pe)'
        })
    
    # ================================================================
    # BÚSQUEDA DE PROTEÍNAS
    # ================================================================
    
    def search_proteins(self, 
                       query: str,
                       organism: Optional[str] = None,
                       reviewed: Optional[bool] = None,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        Busca proteínas en UniProt.
        
        Args:
            query: Término de búsqueda (nombre, función, etc)
            organism: Filtro por organismo (ej: "Homo sapiens")
            reviewed: Solo proteínas revisadas (Swiss-Prot)
            limit: Número máximo de resultados
        
        Returns:
            Lista de candidatos con info básica
        
        Example:
            >>> service.search_proteins("insulin", organism="Homo sapiens")
            [{'accession': 'P01308', 'name': 'Insulin', ...}, ...]
        """
        try:
            # Construir query
            search_query = query
            
            if organism:
                search_query += f" AND organism_name:{organism}"
            
            if reviewed is not None:
                search_query += f" AND reviewed:{'true' if reviewed else 'false'}"
            
            # Parámetros de la API
            params = {
                'query': search_query,
                'format': 'json',
                'size': limit,
                'fields': 'accession,id,protein_name,organism_name,length,reviewed,protein_existence,gene_names'
            }
            
            # Request
            url = f"{self.base_url}/uniprotkb/search"
            
            print(f"🔍 Buscando '{query}' en UniProt...")
            
            response = self._make_request('GET', url, params=params)
            
            if not response or 'results' not in response:
                print("⚠️ No se encontraron resultados")
                return []
            
            results = response['results']
            print(f"✓ Encontrados {len(results)} resultados")
            
            # Formatear resultados
            candidates = []
            for result in results:
                candidate = self._format_search_result(result)
                candidates.append(candidate)
            
            return candidates
            
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            return []
    
    def _format_search_result(self, result: Dict) -> Dict[str, Any]:
        """Formatea un resultado de búsqueda."""
        protein_name = result.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', 'Unknown')
        
        # Extraer genes
        genes = []
        if 'genes' in result:
            for gene in result['genes']:
                if 'geneName' in gene:
                    genes.append(gene['geneName'].get('value', ''))
        
        return {
            'accession': result.get('primaryAccession', ''),
            'id': result.get('uniProtkbId', ''),
            'name': protein_name,
            'organism': result.get('organism', {}).get('scientificName', ''),
            'length': result.get('sequence', {}).get('length', 0),
            'reviewed': result.get('entryType', '') == 'UniProtKB reviewed (Swiss-Prot)',
            'protein_existence': result.get('proteinExistence', ''),
            'gene_names': genes,
            'score': 1.0  # Placeholder para relevancia
        }
    
    # ================================================================
    # DESCARGA DE PROTEÍNA ESPECÍFICA
    # ================================================================
    
    def fetch_protein(self, accession: str, force_refresh: bool = False) -> Optional[Protein]:
        """
        Descarga una proteína específica de UniProt.
        
        Args:
            accession: UniProt accession (ej: P01308)
            force_refresh: Forzar descarga (ignora cache)
        
        Returns:
            Protein object o None
        """
        # Intentar obtener del cache
        if not force_refresh:
            cached = self.cache.get_protein(accession)
            if cached:
                print(f"✓ Proteína {accession} obtenida del cache")
                return self._protein_from_cache(cached)
        
        # Descargar de UniProt
        print(f"📥 Descargando proteína {accession} desde UniProt...")
        
        try:
            url = f"{self.base_url}/uniprotkb/{accession}.json"
            
            response = self._make_request('GET', url)
            
            if not response:
                print(f"❌ No se pudo descargar {accession}")
                return None
            
            # Parsear a Protein object
            protein = self._parse_uniprot_json(response)
            
            # Guardar en cache
            self._cache_protein(protein)
            
            print(f"✓ Proteína {accession} descargada y cacheada")
            return protein
            
        except Exception as e:
            print(f"❌ Error descargando {accession}: {e}")
            return None
    
    def fetch_protein_fasta(self, accession: str) -> Optional[str]:
        """
        Descarga la secuencia FASTA de una proteína.
        
        Args:
            accession: UniProt accession
        
        Returns:
            String FASTA o None
        """
        try:
            url = f"{self.base_url}/uniprotkb/{accession}.fasta"
            
            response = self._make_request('GET', url, raw=True)
            
            if response:
                return response.text
            return None
            
        except Exception as e:
            print(f"❌ Error descargando FASTA: {e}")
            return None
    
    # ================================================================
    # PARSEO DE JSON DE UNIPROT
    # ================================================================
    
    def _parse_uniprot_json(self, data: Dict) -> Protein:
        """
        Parsea el JSON completo de UniProt y extrae anotaciones.
        
        Args:
            data: JSON de UniProt
        
        Returns:
            Protein object completo
        """
        # Identificación básica
        accession = data.get('primaryAccession', '')
        
        protein_name = data.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', 'Unknown')
        
        organism = data.get('organism', {}).get('scientificName', '')
        
        # Secuencia
        sequence = data.get('sequence', {}).get('value', '')
        length = data.get('sequence', {}).get('length', 0)
        
        # Calidad
        reviewed = data.get('entryType', '') == 'UniProtKB reviewed (Swiss-Prot)'
        protein_existence = self._parse_protein_existence(data.get('proteinExistence', ''))
        
        # Genes
        genes = []
        if 'genes' in data:
            for gene in data['genes']:
                if 'geneName' in gene:
                    genes.append(gene['geneName'].get('value', ''))
        
        # Función
        function = self._extract_function(data)
        ec_number = self._extract_ec_number(data)
        
        # Localización subcelular
        subcellular_location = self._extract_subcellular_location(data)
        
        # Péptido señal
        has_signal, signal_range = self._extract_signal_peptide(data)
        
        # Dominios transmembrana
        tm_regions, tm_count = self._extract_transmembrane_regions(data)
        
        # PTMs
        has_glyco, glyco_sites = self._extract_glycosylation(data)
        has_disulfide, disulfide_count = self._extract_disulfide_bonds(data)
        
        # Cofactores y metales
        cofactors = self._extract_cofactors(data)
        metal_binding = self._extract_metal_binding(data)
        
        # Keywords
        keywords = self._extract_keywords(data)
        
        # GO terms
        go_terms = self._extract_go_terms(data)
        
        # Crear proteína
        protein = Protein(
            accession=accession,
            name=protein_name,
            organism=organism,
            sequence=sequence,
            length=length,
            reviewed=reviewed,
            protein_existence=protein_existence,
            gene_names=genes,
            function=function,
            ec_number=ec_number,
            subcellular_location=subcellular_location,
            has_signal_peptide=has_signal,
            signal_peptide_range=signal_range,
            transmembrane_regions=tm_regions,
            transmembrane_count=tm_count,
            has_glycosylation=has_glyco,
            glycosylation_sites=glyco_sites,
            has_disulfide_bonds=has_disulfide,
            disulfide_bond_count=disulfide_count,
            cofactors=cofactors,
            metal_binding=metal_binding,
            keywords=keywords,
            go_terms=go_terms,
            metadata=data  # JSON completo
        )
        
        return protein
    
    def _extract_function(self, data: Dict) -> str:
        """Extrae la función de la proteína."""
        comments = data.get('comments', [])
        for comment in comments:
            if comment.get('commentType') == 'FUNCTION':
                texts = comment.get('texts', [])
                if texts:
                    return texts[0].get('value', '')
        return ""
    
    def _extract_ec_number(self, data: Dict) -> Optional[str]:
        """Extrae número EC si es enzima."""
        protein_desc = data.get('proteinDescription', {})
        rec_name = protein_desc.get('recommendedName', {})
        ec_numbers = rec_name.get('ecNumbers', [])
        
        if ec_numbers:
            return ec_numbers[0].get('value', None)
        return None
    
    def _extract_subcellular_location(self, data: Dict) -> List[str]:
        """Extrae localización subcelular."""
        locations = []
        comments = data.get('comments', [])
        
        for comment in comments:
            if comment.get('commentType') == 'SUBCELLULAR_LOCATION':
                for loc_data in comment.get('subcellularLocations', []):
                    location = loc_data.get('location', {}).get('value', '')
                    if location:
                        locations.append(location)
        
        return locations
    
    def _extract_signal_peptide(self, data: Dict) -> tuple:
        """Extrae información de péptido señal."""
        features = data.get('features', [])
        
        for feature in features:
            if feature.get('type') == 'Signal':
                location = feature.get('location', {})
                start = location.get('start', {}).get('value', '')
                end = location.get('end', {}).get('value', '')
                return True, f"{start}-{end}"
        
        return False, None
    
    def _extract_transmembrane_regions(self, data: Dict) -> tuple:
        """Extrae regiones transmembrana."""
        regions = []
        features = data.get('features', [])
        
        for feature in features:
            if feature.get('type') == 'Transmembrane':
                location = feature.get('location', {})
                start = location.get('start', {}).get('value', 0)
                end = location.get('end', {}).get('value', 0)
                regions.append({'start': start, 'end': end})
        
        return regions, len(regions)
    
    def _extract_glycosylation(self, data: Dict) -> tuple:
        """Extrae sitios de glicosilación."""
        sites = []
        features = data.get('features', [])
        
        for feature in features:
            if 'Glycosylation' in feature.get('type', ''):
                location = feature.get('location', {})
                position = location.get('start', {}).get('value', 0)
                glyco_type = feature.get('type', '')
                sites.append({'position': position, 'type': glyco_type})
        
        return len(sites) > 0, sites
    
    def _extract_disulfide_bonds(self, data: Dict) -> tuple:
        """Extrae puentes disulfuro."""
        count = 0
        features = data.get('features', [])
        
        for feature in features:
            if feature.get('type') == 'Disulfide bond':
                count += 1
        
        return count > 0, count
    
    def _extract_cofactors(self, data: Dict) -> List[str]:
        """Extrae cofactores."""
        cofactors = []
        comments = data.get('comments', [])
        
        for comment in comments:
            if comment.get('commentType') == 'COFACTOR':
                for cofactor in comment.get('cofactors', []):
                    name = cofactor.get('name', '')
                    if name:
                        cofactors.append(name)
        
        return cofactors
    
    def _extract_metal_binding(self, data: Dict) -> List[str]:
        """Extrae metales unidos."""
        metals = set()
        features = data.get('features', [])
        
        for feature in features:
            if feature.get('type') == 'Metal binding':
                description = feature.get('description', '')
                # Extraer metal del description
                for metal in ['Zinc', 'Iron', 'Copper', 'Magnesium', 'Calcium']:
                    if metal.lower() in description.lower():
                        metals.add(metal)
        
        return list(metals)
    
    def _extract_keywords(self, data: Dict) -> List[str]:
        """Extrae keywords."""
        keywords = []
        for kw in data.get('keywords', []):
            keywords.append(kw.get('name', ''))
        return keywords
    
    def _extract_go_terms(self, data: Dict) -> List[str]:
        """Extrae Gene Ontology terms."""
        go_terms = []
        refs = data.get('uniProtKBCrossReferences', [])
        
        for ref in refs:
            if ref.get('database') == 'GO':
                go_id = ref.get('id', '')
                if go_id:
                    go_terms.append(go_id)
        
        return go_terms
    
    def _parse_protein_existence(self, pe_text: str) -> int:
        """Convierte texto de protein existence a número."""
        pe_map = {
            'Evidence at protein level': 1,
            'Evidence at transcript level': 2,
            'Inferred from homology': 3,
            'Predicted': 4,
            'Uncertain': 5
        }
        return pe_map.get(pe_text, 5)
    
    # ================================================================
    # CACHE
    # ================================================================
    
    def _cache_protein(self, protein: Protein):
        """Guarda proteína en cache."""
        data = {
            'accession': protein.accession,
            'name': protein.name,
            'organism': protein.organism,
            'sequence': protein.sequence,
            'length': protein.length,
            'reviewed': protein.reviewed,
            'metadata': protein.metadata
        }
        
        self.cache.cache_protein(protein.accession, data)
    
    def _protein_from_cache(self, cached: Dict) -> Protein:
        """Reconstruye Protein desde cache."""
        metadata = cached.get('metadata', {})
        
        # Si tenemos metadata completo, parsear
        if metadata:
            return self._parse_uniprot_json(metadata)
        
        # Si no, crear versión simplificada
        return Protein(
            accession=cached['accession'],
            name=cached['name'],
            organism=cached['organism'],
            sequence=cached['sequence'],
            length=cached['length'],
            reviewed=cached['reviewed']
        )
    
    # ================================================================
    # UTILIDADES
    # ================================================================
    
    def _make_request(self, method: str, url: str, params: Dict = None, raw: bool = False):
        """
        Hace request a UniProt con retry logic.
        
        Args:
            method: GET o POST
            url: URL completa
            params: Parámetros
            raw: Si retornar Response crudo
        
        Returns:
            JSON dict o Response object
        """
        for attempt in range(config.UNIPROT_RETRIES):
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=config.UNIPROT_TIMEOUT)
                else:
                    response = self.session.post(url, data=params, timeout=config.UNIPROT_TIMEOUT)
                
                response.raise_for_status()
                
                if raw:
                    return response
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Intento {attempt + 1}/{config.UNIPROT_RETRIES} falló: {e}")
                
                if attempt < config.UNIPROT_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
        
        return None


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_uniprot_service_instance = None

def get_uniprot_service() -> UniProtService:
    """
    Obtiene la instancia singleton del servicio UniProt.
    
    Returns:
        UniProtService instance
    """
    global _uniprot_service_instance
    
    if _uniprot_service_instance is None:
        _uniprot_service_instance = UniProtService()
    
    return _uniprot_service_instance


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    print("=== Test UniProt Service ===\n")
    
    service = get_uniprot_service()
    
    # Test 1: Búsqueda
    print("1. Buscando 'insulin' en Homo sapiens...")
    results = service.search_proteins("insulin", organism="Homo sapiens", limit=5)
    
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['accession']}: {result['name']}")
    
    # Test 2: Descarga
    if results:
        accession = results[0]['accession']
        print(f"\n2. Descargando {accession}...")
        protein = service.fetch_protein(accession)
        
        if protein:
            print(f"   ✓ Nombre: {protein.name}")
            print(f"   ✓ Longitud: {protein.length} aa")
            print(f"   ✓ Reviewed: {protein.reviewed}")
            print(f"   ✓ Has signal peptide: {protein.has_signal_peptide}")
            print(f"   ✓ Transmembrane domains: {protein.transmembrane_count}")
            print(f"   ✓ Complexity score: {protein.get_complexity_score()}/100")