"""
Genome Analysis Service - Análisis Bioinformático de Genomas
Contiene todas las funciones de análisis genómico refactorizadas.

Análisis implementados:
- Conteo de codones en CDS (correcto biológicamente)
- Conteo de tripletes en genoma completo (exploratorio)
- Cálculo de RSCU (Relative Synonymous Codon Usage)
- GC por posición (GC1, GC2, GC3)
- Validación de CDS problemáticos
- Análisis de start/stop codons
- Compactación génica
- Espacios intergénicos
- Validación con literatura científica
"""

from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Optional
from Bio.Data import CodonTable
from Bio.SeqRecord import SeqRecord

import config
from models.genome import Genome
from models.gene import Gene, create_gene_from_feature
from services.cache_manager import get_cache_manager


class GenomeAnalysisService:
    """Servicio de análisis genómico."""
    
    def __init__(self):
        self.cache = get_cache_manager()
    
    # ================================================================
    # EXTRACCIÓN DE GENES
    # ================================================================
    
    def extract_genes_from_record(self, record: SeqRecord, genome_id: str) -> List[Gene]:
        """
        Extrae todos los genes (CDS) de un SeqRecord con IDs estables.
        
        Args:
            record: SeqRecord de BioPython
            genome_id: ID del genoma para cache
        
        Returns:
            Lista de genes ordenados por longitud (descendente)
        """
        # Intentar obtener del cache
        cached = self.cache.get_analysis(genome_id, 'genes')
        if cached:
            print(f"✓ Genes obtenidos del cache")
            # Reconstruir objetos Gene desde dict
            return [self._gene_from_dict(g) for g in cached]
        
        print(f"📊 Extrayendo genes de {genome_id}...")
        
        genes = []
        for idx, feature in enumerate(record.features):
            if feature.type == "CDS":
                try:
                    gene = create_gene_from_feature(feature, record.seq, idx)
                    genes.append(gene)
                except Exception as e:
                    print(f"⚠️ Error procesando feature {idx}: {e}")
                    continue
        
        # Ordenar por longitud
        genes_sorted = sorted(genes, key=lambda x: x.length, reverse=True)
        
        # Cachear como lista de dicts
        self.cache.cache_analysis(
            genome_id, 
            'genes', 
            [g.to_dict() for g in genes_sorted]
        )
        
        print(f"✓ Extraídos {len(genes_sorted)} genes")
        return genes_sorted
    
    def _gene_from_dict(self, data: Dict) -> Gene:
        """Reconstruye un Gene desde dict."""
        return Gene(
            id=data['id'],
            locus_tag=data['locus_tag'],
            gene=data['gene'],
            product=data['product'],
            protein_id=data['protein_id'],
            sequence="",  # No guardar secuencia completa en cache
            length=data['length'],
            start=data['start'],
            end=data['end'],
            strand=data['strand'],
            gc_content=data['gc_content'],
            codon_start=data['codon_start'],
            transl_table=data['transl_table'],
            start_codon=data['start_codon'],
            stop_codon=data['stop_codon'],
            is_partial=data['is_partial'],
            has_issues=data['has_issues'],
            issues=data['issues'],
            note=data['note']
        )
    
    # ================================================================
    # ANÁLISIS DE CODONES EN CDS
    # ================================================================
    
    def analyze_codons_in_cds(self, record: SeqRecord, genome_id: str) -> Dict[str, Any]:
        """
        Analiza codones SOLO en CDS (biológicamente correcto).
        
        Returns:
            Dict con:
                - codons: Counter de todos los codones
                - start_codons: Counter (ATG, GTG, TTG, OTROS)
                - stop_codons: Counter (TAA, TAG, TGA)
                - cds_problematic: Lista de CDS con problemas
                - statistics: Estadísticas de validación
        """
        # Intentar cache
        cached = self.cache.get_analysis(genome_id, 'codons_cds')
        if cached:
            print(f"✓ Análisis de codones CDS obtenido del cache")
            return cached
        
        print(f"🧬 Analizando codones en CDS (con detección de falsos)...")
        
        codon_counter = Counter()
        start_counter = Counter({"ATG": 0, "GTG": 0, "TTG": 0, "OTROS": 0})
        stop_counter = Counter({"TAA": 0, "TAG": 0, "TGA": 0})
        
        cds_problematic = []
        false_starts = []  # NUEVO: Codones de inicio falsos
        false_stops = []   # NUEVO: Codones de parada falsos
        
        total_cds = 0
        valid_cds = 0
        
        for feature in record.features:
            if feature.type != "CDS":
                continue
            
            total_cds += 1
            
            # Extraer CDS correctamente
            try:
                cds_info = self._extract_cds_correctly(feature, record)
                seq = cds_info['sequence']
                
                # Validar
                validation = self._validate_cds(cds_info)
                
                # Si tiene problemas, registrar
                if not validation['length_ok'] or validation['has_ambiguous']:
                    gene_name = feature.qualifiers.get("gene", ["Unknown"])[0]
                    locus_tag = feature.qualifiers.get("locus_tag", ["-"])[0]
                    
                    problems = []
                    if not validation['length_ok']:
                        problems.append("longitud no múltiplo de 3")
                    if validation['has_ambiguous']:
                        problems.append("contiene Ns")
                    if validation['is_partial']:
                        problems.append("parcial")
                    
                    cds_problematic.append({
                        'gene': gene_name,
                        'locus_tag': locus_tag,
                        'problems': problems,
                        'length': len(seq)
                    })
                
                # Si no es múltiplo de 3, no procesar
                if not validation['length_ok']:
                    continue
                
                valid_cds += 1
                
                # Dividir en codones
                codons = [seq[i:i+3] for i in range(0, len(seq), 3) 
                         if len(seq[i:i+3]) == 3]
                
                # NUEVO: Detectar codones falsos dentro del CDS
                locus_tag = feature.qualifiers.get("locus_tag", ["-"])[0]
                for idx, codon in enumerate(codons[1:-1], start=1):  # Excluir primero y último
                    # Start codons en medio del CDS (falsos)
                    if codon in ["ATG", "GTG", "TTG"]:
                        false_starts.append({
                            'locus_tag': locus_tag,
                            'position': idx,
                            'codon': codon
                        })
                    
                    # Stop codons antes del final (falsos)
                    if codon in ["TAA", "TAG", "TGA"]:
                        false_stops.append({
                            'locus_tag': locus_tag,
                            'position': idx,
                            'codon': codon
                        })
                
                # Contar todos los codones
                for codon in codons:
                    codon_counter[codon] += 1
                
                # Contar start codon (primer codón)
                if len(codons) > 0:
                    start = codons[0]
                    if start in ["ATG", "GTG", "TTG"]:
                        start_counter[start] += 1
                    else:
                        start_counter["OTROS"] += 1
                
                # Contar stop codon (último codón si no es parcial)
                if len(codons) > 0 and validation['has_stop']:
                    stop = codons[-1]
                    if stop in ["TAA", "TAG", "TGA"]:
                        stop_counter[stop] += 1
                
            except Exception as e:
                print(f"⚠️ Error procesando CDS: {e}")
                continue
        
        result = {
            'codons': dict(codon_counter),
            'start_codons': dict(start_counter),
            'stop_codons': dict(stop_counter),
            'cds_problematic': cds_problematic[:20],  # Primeros 20
            'false_starts': false_starts[:50],  # NUEVO: Primeros 50
            'false_stops': false_stops[:50],    # NUEVO: Primeros 50
            'statistics': {
                'total_cds': total_cds,
                'valid_cds': valid_cds,
                'problematic_cds': len(cds_problematic),
                'validity_rate': (valid_cds / total_cds * 100) if total_cds > 0 else 0,
                'false_starts_count': len(false_starts),  # NUEVO
                'false_stops_count': len(false_stops)     # NUEVO
            }
        }
        
        # Cachear
        self.cache.cache_analysis(genome_id, 'codons_cds', result)
        
        print(f"✓ Análisis completado: {valid_cds}/{total_cds} CDS válidos")
        print(f"✓ Codones falsos: {len(false_starts)} starts, {len(false_stops)} stops")
        return result
    
    def _extract_cds_correctly(self, feature, record) -> Dict[str, Any]:
        """Extrae CDS respetando codon_start y marcos de lectura."""
        # Extraer secuencia
        seq_complete = feature.extract(record.seq)
        
        # Obtener codon_start (1, 2, o 3)
        codon_start = int(feature.qualifiers.get("codon_start", [1])[0])
        
        # Ajustar por codon_start
        seq_adjusted = seq_complete[codon_start - 1:]
        
        # Obtener tabla genética
        transl_table = int(feature.qualifiers.get("transl_table", [11])[0])
        
        # Verificar si es parcial
        is_partial = "partial" in str(feature.location)
        
        return {
            'sequence': str(seq_adjusted),
            'sequence_original': str(seq_complete),
            'codon_start': codon_start,
            'transl_table': transl_table,
            'is_partial': is_partial,
            'length': len(seq_adjusted),
            'location': feature.location
        }
    
    def _validate_cds(self, cds_info: Dict) -> Dict[str, Any]:
        """Valida un CDS y detecta problemas."""
        seq = cds_info['sequence']
        
        validation = {
            'length_ok': len(seq) % 3 == 0,
            'has_ambiguous': 'N' in seq,
            'is_partial': cds_info['is_partial'],
            'has_stop': False,
            'start_codon': seq[:3] if len(seq) >= 3 else None,
            'stop_codon': seq[-3:] if len(seq) >= 3 else None
        }
        
        # Verificar stop final
        if len(seq) >= 3 and not cds_info['is_partial']:
            ultimo = seq[-3:]
            validation['has_stop'] = ultimo in ["TAA", "TAG", "TGA"]
        
        return validation
    
    # ================================================================
    # ANÁLISIS DE GENOMA COMPLETO (Exploratorio)
    # ================================================================
    
    def analyze_triplets_genome_wide(self, sequence: str, genome_id: str) -> Dict[str, Any]:
        """
        Cuenta TODOS los tripletes en el genoma completo (3 marcos).
        
        Returns:
            Dict con:
                - frame_0: Counter del marco 0
                - frame_1: Counter del marco 1
                - frame_2: Counter del marco 2
                - total: Counter suma de los 3 marcos
        """
        # Intentar cache
        cached = self.cache.get_analysis(genome_id, 'triplets_genome')
        if cached:
            # Convertir de nuevo a Counters
            return {
                'frame_0': Counter(cached['frame_0']),
                'frame_1': Counter(cached['frame_1']),
                'frame_2': Counter(cached['frame_2']),
                'total': Counter(cached['total'])
            }
        
        print(f"🔍 Analizando tripletes en genoma completo...")
        
        frames = {0: Counter(), 1: Counter(), 2: Counter()}
        
        # Contar en los 3 marcos
        for frame in range(3):
            for i in range(frame, len(sequence) - 2, 3):
                triplet = sequence[i:i+3]
                if len(triplet) == 3:
                    frames[frame][triplet] += 1
        
        # Total (suma de los 3 marcos)
        total = Counter()
        for frame_count in frames.values():
            total.update(frame_count)
        
        result = {
            'frame_0': dict(frames[0]),
            'frame_1': dict(frames[1]),
            'frame_2': dict(frames[2]),
            'total': dict(total)
        }
        
        # Cachear
        self.cache.cache_analysis(genome_id, 'triplets_genome', result)
        
        print(f"✓ Análisis de tripletes completado")
        return result
    
    # ================================================================
    # MÉTRICAS AVANZADAS
    # ================================================================
    
    def calculate_rscu(self, codon_counts: Dict[str, int]) -> Dict[str, float]:
        """
        Calcula RSCU (Relative Synonymous Codon Usage).
        
        RSCU = (frecuencia de codón X) / (frecuencia promedio de sus sinónimos)
        
        Args:
            codon_counts: Dict con conteo de codones
        
        Returns:
            Dict {codon: rscu_value}
        """
        # Tabla genética estándar bacteriana
        tabla = CodonTable.unambiguous_dna_by_id[11]
        
        # Agrupar codones por aminoácido
        codons_by_aa = defaultdict(list)
        for codon, aa in tabla.forward_table.items():
            codons_by_aa[aa].append(codon)
        
        # Calcular RSCU
        rscu = {}
        
        for aa, codons in codons_by_aa.items():
            # Frecuencia de cada codón sinónimo
            frequencies = [codon_counts.get(c, 0) for c in codons]
            total = sum(frequencies)
            
            if total == 0:
                continue
            
            # Frecuencia promedio
            average = total / len(codons)
            
            # RSCU para cada codón
            for i, codon in enumerate(codons):
                if average > 0:
                    rscu[codon] = frequencies[i] / average
                else:
                    rscu[codon] = 0.0
        
        return rscu
    
    def calculate_gc_by_position(self, codon_list: List[str]) -> Dict[str, float]:
        """
        Calcula GC1, GC2, GC3 (GC en cada posición del codón).
        
        Args:
            codon_list: Lista de codones de 3 nucleótidos
        
        Returns:
            Dict {"GC1": float, "GC2": float, "GC3": float}
        """
        pos1 = [c[0] for c in codon_list if len(c) == 3]
        pos2 = [c[1] for c in codon_list if len(c) == 3]
        pos3 = [c[2] for c in codon_list if len(c) == 3]
        
        def gc_content(bases):
            if not bases:
                return 0.0
            g = bases.count('G') + bases.count('g')
            c = bases.count('C') + bases.count('c')
            return (g + c) / len(bases) * 100
        
        return {
            "GC1": gc_content(pos1),
            "GC2": gc_content(pos2),
            "GC3": gc_content(pos3)
        }
    
    def analyze_codon_usage(self, record: SeqRecord, genome_id: str) -> Dict[str, Any]:
        """
        Análisis completo de uso de codones con métricas avanzadas.
        
        Returns:
            Dict con análisis completo incluyendo RSCU, GC por posición, etc.
        """
        # Obtener análisis CDS
        cds_analysis = self.analyze_codons_in_cds(record, genome_id)
        codons_cds = cds_analysis['codons']
        
        # Expandir codones para análisis por posición
        codon_list = []
        for codon, count in codons_cds.items():
            codon_list.extend([codon] * count)
        
        # GC por posición
        gc_position = self.calculate_gc_by_position(codon_list)
        
        # RSCU
        rscu = self.calculate_rscu(codons_cds)
        
        # Top 10 codones más usados
        top_codons = dict(sorted(codons_cds.items(), 
                                key=lambda x: x[1], 
                                reverse=True)[:10])
        
        # Top 10 menos usados (excluyendo stops)
        codons_no_stop = {k: v for k, v in codons_cds.items() 
                         if k not in ["TAA", "TAG", "TGA"]}
        bottom_codons = dict(sorted(codons_no_stop.items(), 
                                   key=lambda x: x[1])[:10])
        
        return {
            'total_count': sum(codons_cds.values()),
            'unique_codons': len(codons_cds),
            'gc_position': gc_position,
            'rscu': rscu,
            'top_10': top_codons,
            'bottom_10': bottom_codons,
            'start_codons': cds_analysis['start_codons'],
            'stop_codons': cds_analysis['stop_codons'],
            'cds_problematic': cds_analysis['cds_problematic'],
            'statistics': cds_analysis['statistics']
        }
    
    # ================================================================
    # COMPACTACIÓN GÉNICA
    # ================================================================
    
    def calculate_compactness(self, genome: Genome) -> Dict[str, Any]:
        """
        Calcula estadísticas de compactación del genoma.
        
        Args:
            genome: Objeto Genome
        
        Returns:
            Dict con estadísticas de compactación
        """
        return genome.get_statistics()['compactness']
    
    # ================================================================
    # ESPACIOS INTERGÉNICOS
    # ================================================================
    
    def analyze_intergenic_spaces(self, genome: Genome, 
                                  top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Analiza espacios intergénicos (regiones no codificantes).
        
        Args:
            genome: Objeto Genome
            top_n: Número de espacios más grandes a retornar
        
        Returns:
            Lista de espacios ordenados por tamaño
        """
        sequence = genome.sequence
        spaces = []
        
        # Ordenar genes por posición
        genes_sorted = sorted(genome.genes, key=lambda x: x.start)
        
        for i in range(len(genes_sorted) - 1):
            current_end = genes_sorted[i].end
            next_start = genes_sorted[i + 1].start
            
            if next_start > current_end:
                space_size = next_start - current_end
                space_seq = sequence[current_end:next_start]
                
                # Calcular GC del espacio
                g = space_seq.count('G') + space_seq.count('g')
                c = space_seq.count('C') + space_seq.count('c')
                gc = (g + c) / len(space_seq) * 100 if len(space_seq) > 0 else 0.0
                
                spaces.append({
                    'between_genes': f"{genes_sorted[i].gene} -> {genes_sorted[i+1].gene}",
                    'position': f"{current_end}-{next_start}",
                    'size': space_size,
                    'gc_content': round(gc, 2),
                    'sequence_snippet': space_seq[:100] if len(space_seq) > 0 else ""
                })
        
        # Ordenar por tamaño
        return sorted(spaces, key=lambda x: x['size'], reverse=True)[:top_n]
    
    # ================================================================
    # VALIDACIÓN CON LITERATURA
    # ================================================================
    
    def validate_with_literature(self, genome: Genome, 
                                codon_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida resultados contra valores esperados de la literatura.
        
        Referencias:
        - Blattner et al. (1997) "The complete genome sequence of E. coli K-12"
        - Nakamura et al. (2000) "Codon usage tabulated from GenBank"
        
        Args:
            genome: Objeto Genome
            codon_analysis: Resultado de analyze_codon_usage()
        
        Returns:
            Dict con validaciones
        """
        validations = {}
        
        # Validar longitud
        validations['length'] = {
            'value': genome.length,
            'expected': "4.5-4.7 Mb",
            'ok': 4_500_000 <= genome.length <= 4_700_000
        }
        
        # Validar GC
        validations['gc'] = {
            'value': round(genome.gc_content, 2),
            'expected': "50.5-51.0%",
            'ok': 50.5 <= genome.gc_content <= 51.0
        }
        
        # Validar número de genes
        validations['genes'] = {
            'value': genome.gene_count,
            'expected': "4,200-4,400",
            'ok': 4_200 <= genome.gene_count <= 4_400
        }
        
        # Validar start codons
        starts = codon_analysis['start_codons']
        total_start = sum(starts.values())
        
        if total_start > 0:
            prop_atg = (starts['ATG'] / total_start) * 100
            prop_gtg = (starts['GTG'] / total_start) * 100
            prop_ttg = (starts['TTG'] / total_start) * 100
            
            validations['start_atg'] = {
                'value': round(prop_atg, 2),
                'expected': "80-90%",
                'ok': 80 <= prop_atg <= 90
            }
            
            validations['start_gtg'] = {
                'value': round(prop_gtg, 2),
                'expected': "8-15%",
                'ok': 8 <= prop_gtg <= 15
            }
            
            validations['start_ttg'] = {
                'value': round(prop_ttg, 2),
                'expected': "1-5%",
                'ok': 1 <= prop_ttg <= 5
            }
        
        # Validar stop codons
        stops = codon_analysis['stop_codons']
        total_stop = sum(stops.values())
        
        if total_stop > 0:
            prop_taa = (stops['TAA'] / total_stop) * 100
            prop_tag = (stops['TAG'] / total_stop) * 100
            prop_tga = (stops['TGA'] / total_stop) * 100
            
            validations['stop_taa'] = {
                'value': round(prop_taa, 2),
                'expected': "60-65%",
                'ok': 60 <= prop_taa <= 65
            }
            
            validations['stop_tag'] = {
                'value': round(prop_tag, 2),
                'expected': "5-10%",
                'ok': 5 <= prop_tag <= 10
            }
            
            validations['stop_tga'] = {
                'value': round(prop_tga, 2),
                'expected': "25-35%",
                'ok': 25 <= prop_tga <= 35
            }
        
        return validations


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_analysis_service_instance = None

def get_analysis_service() -> GenomeAnalysisService:
    """
    Obtiene la instancia singleton del servicio de análisis.
    
    Returns:
        GenomeAnalysisService instance
    """
    global _analysis_service_instance
    
    if _analysis_service_instance is None:
        _analysis_service_instance = GenomeAnalysisService()
    
    return _analysis_service_instance


# ================================================================
# VALIDACIÓN CON LITERATURA CIENTÍFICA
# ================================================================

def validate_with_literature(genome_stats: dict) -> dict:
    """
    Valida estadísticas del genoma contra rangos esperados de literatura.
    
    Rangos basados en:
    - Blattner et al. (1997) - E. coli K-12 MG1655
    - Riley et al. (2006) - Genomas de E. coli
    - Serres et al. (2001) - Análisis genómico
    
    Returns:
        Dict con validaciones y alertas
    """
    validations = {
        'gene_count': {'status': 'unknown', 'expected': '4,200-4,600', 'found': 0, 'message': ''},
        'gc_content': {'status': 'unknown', 'expected': '50-52%', 'found': 0, 'message': ''},
        'genome_length': {'status': 'unknown', 'expected': '4.5-5.5 Mb', 'found': 0, 'message': ''},
        'start_codon_distribution': {'status': 'unknown', 'expected': 'ATG >83%', 'found': 0, 'message': ''},
        'coding_percentage': {'status': 'unknown', 'expected': '85-88%', 'found': 0, 'message': ''},
        'overall_status': 'pass',
        'warnings': [],
        'errors': []
    }
    
    # 1. Gene count (4200-4600 para E. coli K-12)
    gene_count = genome_stats.get('genome', {}).get('gene_count', 0)
    validations['gene_count']['found'] = gene_count
    
    if 4200 <= gene_count <= 4600:
        validations['gene_count']['status'] = 'pass'
        validations['gene_count']['message'] = 'Número de genes en rango esperado'
    elif 4000 <= gene_count < 4200 or 4600 < gene_count <= 4800:
        validations['gene_count']['status'] = 'warning'
        validations['gene_count']['message'] = 'Número de genes fuera del rango típico pero aceptable'
        validations['warnings'].append('Gene count slightly outside expected range')
    else:
        validations['gene_count']['status'] = 'error'
        validations['gene_count']['message'] = 'Número de genes significativamente diferente del esperado'
        validations['errors'].append('Gene count significantly different from expected')
        validations['overall_status'] = 'fail'
    
    # 2. GC Content (50-52% para E. coli)
    gc_content = genome_stats.get('genome', {}).get('gc_content', 0)
    validations['gc_content']['found'] = f"{gc_content}%"
    
    if 50 <= gc_content <= 52:
        validations['gc_content']['status'] = 'pass'
        validations['gc_content']['message'] = 'GC content en rango esperado para E. coli'
    elif 48 <= gc_content < 50 or 52 < gc_content <= 54:
        validations['gc_content']['status'] = 'warning'
        validations['gc_content']['message'] = 'GC content ligeramente fuera del rango'
        validations['warnings'].append('GC content outside typical range')
    else:
        validations['gc_content']['status'] = 'error'
        validations['gc_content']['message'] = 'GC content muy diferente del esperado (posible contaminación)'
        validations['errors'].append('GC content significantly different')
        validations['overall_status'] = 'fail'
    
    # 3. Genome length (4.5-5.5 Mb para E. coli)
    genome_length = genome_stats.get('genome', {}).get('length', 0)
    length_mb = genome_length / 1_000_000
    validations['genome_length']['found'] = f"{length_mb:.2f} Mb"
    
    if 4.5 <= length_mb <= 5.5:
        validations['genome_length']['status'] = 'pass'
        validations['genome_length']['message'] = 'Longitud del genoma en rango esperado'
    elif 4.2 <= length_mb < 4.5 or 5.5 < length_mb <= 5.8:
        validations['genome_length']['status'] = 'warning'
        validations['genome_length']['message'] = 'Longitud fuera del rango típico'
        validations['warnings'].append('Genome length outside typical range')
    else:
        validations['genome_length']['status'] = 'error'
        validations['genome_length']['message'] = 'Longitud muy diferente de lo esperado'
        validations['errors'].append('Genome length significantly different')
        validations['overall_status'] = 'fail'
    
    # 4. Start codon distribution (ATG should be >83% in E. coli)
    start_codons = genome_stats.get('codon_analysis', {}).get('cds', {}).get('start_codons', {})
    total_starts = sum(start_codons.values())
    atg_percentage = (start_codons.get('ATG', 0) / total_starts * 100) if total_starts > 0 else 0
    validations['start_codon_distribution']['found'] = f"{atg_percentage:.1f}% ATG"
    
    if atg_percentage >= 83:
        validations['start_codon_distribution']['status'] = 'pass'
        validations['start_codon_distribution']['message'] = 'Distribución de codones de inicio esperada'
    elif 80 <= atg_percentage < 83:
        validations['start_codon_distribution']['status'] = 'warning'
        validations['start_codon_distribution']['message'] = 'ATG ligeramente bajo'
        validations['warnings'].append('ATG usage lower than expected')
    else:
        validations['start_codon_distribution']['status'] = 'error'
        validations['start_codon_distribution']['message'] = 'Distribución de codones de inicio anormal'
        validations['errors'].append('Start codon distribution abnormal')
        validations['overall_status'] = 'fail'
    
    # 5. Coding percentage (85-88% para E. coli)
    coding_pct = genome_stats.get('compactness', {}).get('coding_percentage', 0)
    validations['coding_percentage']['found'] = f"{coding_pct}%"
    
    if 85 <= coding_pct <= 88:
        validations['coding_percentage']['status'] = 'pass'
        validations['coding_percentage']['message'] = 'Porcentaje de región codificante esperado'
    elif 82 <= coding_pct < 85 or 88 < coding_pct <= 90:
        validations['coding_percentage']['status'] = 'warning'
        validations['coding_percentage']['message'] = 'Región codificante fuera del rango típico'
        validations['warnings'].append('Coding percentage outside typical range')
    else:
        validations['coding_percentage']['status'] = 'error'
        validations['coding_percentage']['message'] = 'Porcentaje codificante muy diferente'
        validations['errors'].append('Coding percentage significantly different')
        validations['overall_status'] = 'fail'
    
    return validations


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    from services.ncbi_service import download_genome
    from models.genome import create_genome_from_seqrecord
    
    print("=== Test Genome Analysis Service ===\n")
    
    # Descargar genoma
    print("1. Descargando genoma...")
    record = download_genome("NC_000913.3")
    
    if record:
        # Crear objeto Genome
        genome = create_genome_from_seqrecord(record, "NC_000913.3")
        print(f"   ✓ Genoma cargado: {genome.length:,} bp")
        
        # Servicio de análisis
        service = get_analysis_service()
        
        # Extraer genes
        print("\n2. Extrayendo genes...")
        genes = service.extract_genes_from_record(record, "NC_000913.3")
        print(f"   ✓ Extraídos {len(genes)} genes")
        
        # Análisis de codones
        print("\n3. Analizando codones en CDS...")
        codon_analysis = service.analyze_codon_usage(record, "NC_000913.3")
        print(f"   ✓ Total codones: {codon_analysis['total_count']:,}")
        print(f"   ✓ GC3: {codon_analysis['gc_position']['GC3']:.2f}%")
        
        # Validación
        print("\n4. Validando con literatura...")
        validation = service.validate_with_literature(genome, codon_analysis)
        print(f"   ✓ Longitud OK: {validation['length']['ok']}")
        print(f"   ✓ GC OK: {validation['gc']['ok']}")
