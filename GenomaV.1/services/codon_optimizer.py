"""
Codon Optimizer Service - Optimización de codones para E. coli
Recodifica secuencias de DNA para mejorar expresión en el hospedero.

Estrategia:
1. Calcular uso de codones del genoma hospedero (RSCU)
2. Para cada aminoácido, seleccionar codón más frecuente
3. Mantener la secuencia de proteína idéntica
4. Calcular métricas de mejora

Modos:
- Dinámico: Calcula RSCU del genoma seleccionado
- Fijo: Usa tabla pre-calculada de E. coli K-12 MG1655
"""

import json
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
from pathlib import Path
from Bio.Data import CodonTable

import config
from models.design_proposal import CodonOptimization
from utils.sequence_utils import translate_dna, gc_content


class CodonOptimizerService:
    """
    Servicio de optimización de codones.
    
    Optimiza secuencias de DNA para expresión en E. coli.
    """
    
    def __init__(self):
        self.codon_table = CodonTable.unambiguous_dna_by_id[11]  # Bacteria
        self.reference_rscu = None
    
    # ================================================================
    # OPTIMIZACIÓN PRINCIPAL
    # ================================================================
    
    def optimize_sequence(self,
                         protein_sequence: str,
                         genome_id: str = None,
                         genome_rscu: Dict[str, float] = None) -> CodonOptimization:
        """
        Optimiza una secuencia de proteína para expresión en E. coli.
        
        Args:
            protein_sequence: Secuencia de aminoácidos
            genome_id: ID del genoma (para obtener RSCU dinámico)
            genome_rscu: RSCU pre-calculado (opcional)
        
        Returns:
            CodonOptimization con secuencias original y optimizada
        """
        print(f"\n🧬 Optimizando codones para {len(protein_sequence)} aminoácidos...")
        
        # PASO 1: Obtener RSCU del hospedero
        if genome_rscu:
            rscu = genome_rscu
            print(f"   ✓ Usando RSCU proporcionado")
        elif genome_id and config.CODON_OPTIMIZATION_MODE == 'dynamic':
            rscu = self._get_genome_rscu(genome_id)
            print(f"   ✓ RSCU calculado dinámicamente de {genome_id}")
        else:
            rscu = self._load_reference_rscu()
            print(f"   ✓ Usando tabla de referencia E. coli K-12 MG1655")
        
        # PASO 2: Crear tabla de codones preferidos
        preferred_codons = self._build_preferred_codon_table(rscu)
        
        # PASO 3: Generar secuencia original (reverse translation naive)
        original_dna = self._reverse_translate_naive(protein_sequence)
        
        # PASO 4: Generar secuencia optimizada
        optimized_dna = self._reverse_translate_optimized(
            protein_sequence,
            preferred_codons
        )
        
        # PASO 5: Calcular métricas
        print(f"   📊 Calculando métricas...")
        
        original_metrics = self._calculate_sequence_metrics(original_dna, rscu)
        optimized_metrics = self._calculate_sequence_metrics(optimized_dna, rscu)
        
        # PASO 6: Contar cambios
        changes = sum(1 for o, n in zip(original_dna, optimized_dna) if o != n)
        
        # Crear resultado
        optimization = CodonOptimization(
            original_sequence=original_dna,
            optimized_sequence=optimized_dna,
            original_gc=original_metrics['gc'],
            original_gc3=original_metrics['gc3'],
            rare_codons_original=original_metrics['rare_codons_pct'],
            optimized_gc=optimized_metrics['gc'],
            optimized_gc3=optimized_metrics['gc3'],
            rare_codons_optimized=optimized_metrics['rare_codons_pct'],
            changes_count=changes,
            rscu_distance=optimized_metrics['rscu_distance'],
            codon_usage_similarity=optimized_metrics['codon_similarity']
        )
        
        print(f"✓ Optimización completada:")
        print(f"   - Cambios: {changes}/{len(original_dna)} nucleótidos")
        print(f"   - Codones raros: {original_metrics['rare_codons_pct']:.1f}% → {optimized_metrics['rare_codons_pct']:.1f}%")
        print(f"   - GC3: {original_metrics['gc3']:.1f}% → {optimized_metrics['gc3']:.1f}%")
        print(f"   - Score de mejora: {optimization.get_improvement_score():.1f}/100")
        
        return optimization
    
    # ================================================================
    # RSCU (Relative Synonymous Codon Usage)
    # ================================================================
    
    def _get_genome_rscu(self, genome_id: str) -> Dict[str, float]:
        """
        Obtiene o calcula RSCU de un genoma.
        
        Args:
            genome_id: ID del genoma
        
        Returns:
            Dict {codon: RSCU}
        """
        # Intentar cargar del cache
        from services.cache_manager import get_cache_manager
        cache = get_cache_manager()
        
        cached = cache.get_analysis(genome_id, 'rscu')
        if cached:
            return cached
        
        # Calcular RSCU
        print(f"   Calculando RSCU de {genome_id}...")
        
        from services.ncbi_service import get_ncbi_service
        from services.genome_analysis import get_analysis_service
        
        ncbi = get_ncbi_service()
        analysis = get_analysis_service()
        
        # Descargar genoma
        record = ncbi.fetch_genome(genome_id)
        if not record:
            print(f"   ⚠️ No se pudo descargar genoma, usando referencia")
            return self._load_reference_rscu()
        
        # Analizar codones
        codon_analysis = analysis.analyze_codons_in_cds(record, genome_id)
        codons = codon_analysis['codons']
        
        # Calcular RSCU
        rscu = analysis.calculate_rscu(codons)
        
        # Cachear
        cache.cache_analysis(genome_id, 'rscu', rscu)
        
        return rscu
    
    def _load_reference_rscu(self) -> Dict[str, float]:
        """
        Carga tabla de referencia RSCU de E. coli K-12 MG1655.
        
        Returns:
            Dict {codon: RSCU}
        """
        if self.reference_rscu:
            return self.reference_rscu
        
        # Buscar archivo de tabla
        table_file = config.CODON_TABLES_DIR / 'ecoli_k12_mg1655.json'
        
        if table_file.exists():
            with open(table_file, 'r') as f:
                self.reference_rscu = json.load(f)
                return self.reference_rscu
        
        # Si no existe, usar valores típicos de E. coli
        # Fuente: Nakamura et al. (2000) - valores aproximados
        self.reference_rscu = self._get_default_ecoli_rscu()
        
        # Guardar para próxima vez
        table_file.parent.mkdir(parents=True, exist_ok=True)
        with open(table_file, 'w') as f:
            json.dump(self.reference_rscu, f, indent=2)
        
        return self.reference_rscu
    
    def _get_default_ecoli_rscu(self) -> Dict[str, float]:
        """
        RSCU por defecto de E. coli K-12 (valores típicos).
        
        Returns:
            Dict {codon: RSCU}
        """
        # Valores aproximados basados en literatura
        # RSCU > 1.5 = muy usado, RSCU < 0.5 = raro
        return {
            # Ala (A)
            'GCG': 2.6, 'GCC': 1.3, 'GCA': 0.8, 'GCT': 0.3,
            # Arg (R)
            'CGT': 2.4, 'CGC': 2.2, 'CGA': 0.4, 'CGG': 0.1, 'AGA': 0.2, 'AGG': 0.1,
            # Asn (N)
            'AAC': 1.8, 'AAT': 0.2,
            # Asp (D)
            'GAT': 1.7, 'GAC': 0.3,
            # Cys (C)
            'TGC': 1.7, 'TGT': 0.3,
            # Gln (Q)
            'CAG': 1.8, 'CAA': 0.2,
            # Glu (E)
            'GAA': 1.7, 'GAG': 0.3,
            # Gly (G)
            'GGT': 2.2, 'GGC': 1.7, 'GGA': 0.2, 'GGG': 0.2,
            # His (H)
            'CAT': 1.6, 'CAC': 0.4,
            # Ile (I)
            'ATT': 1.8, 'ATC': 1.5, 'ATA': 0.1,
            # Leu (L)
            'CTG': 2.8, 'TTG': 0.8, 'CTT': 0.5, 'CTC': 0.3, 'CTA': 0.1, 'TTA': 0.1,
            # Lys (K)
            'AAA': 1.7, 'AAG': 0.3,
            # Met (M)
            'ATG': 1.0,
            # Phe (F)
            'TTT': 1.6, 'TTC': 0.4,
            # Pro (P)
            'CCG': 2.3, 'CCA': 0.9, 'CCT': 0.4, 'CCC': 0.2,
            # Ser (S)
            'AGC': 1.8, 'TCT': 1.0, 'TCC': 0.9, 'AGT': 0.6, 'TCA': 0.4, 'TCG': 0.3,
            # Thr (T)
            'ACC': 2.3, 'ACG': 1.0, 'ACA': 0.5, 'ACT': 0.3,
            # Trp (W)
            'TGG': 1.0,
            # Tyr (Y)
            'TAT': 1.6, 'TAC': 0.4,
            # Val (V)
            'GTT': 1.8, 'GTA': 1.0, 'GTG': 1.5, 'GTC': 0.3,
            # Stop
            'TAA': 1.9, 'TAG': 0.2, 'TGA': 0.9
        }
    
    # ================================================================
    # REVERSE TRANSLATION
    # ================================================================
    
    def _build_preferred_codon_table(self, rscu: Dict[str, float]) -> Dict[str, str]:
        """
        Construye tabla de codones preferidos basada en RSCU.
        
        Args:
            rscu: Dict {codon: RSCU}
        
        Returns:
            Dict {aminoacido: codon_preferido}
        """
        # Agrupar codones por aminoácido
        aa_codons = defaultdict(list)
        
        for codon, aa in self.codon_table.forward_table.items():
            aa_codons[aa].append(codon)
        
        # Para cada aminoácido, seleccionar codón con mayor RSCU
        preferred = {}
        
        for aa, codons in aa_codons.items():
            # Obtener RSCU de cada codón
            codon_rscu = [(codon, rscu.get(codon, 1.0)) for codon in codons]
            
            # Ordenar por RSCU descendente
            codon_rscu.sort(key=lambda x: x[1], reverse=True)
            
            # Seleccionar el más usado
            preferred[aa] = codon_rscu[0][0]
        
        # Añadir stop codon más común (TAA en E. coli)
        stop_codons = list(self.codon_table.stop_codons)
        stop_rscu = [(codon, rscu.get(codon, 1.0)) for codon in stop_codons]
        stop_rscu.sort(key=lambda x: x[1], reverse=True)
        preferred['*'] = stop_rscu[0][0]
        
        # Metionina (start)
        preferred['M'] = 'ATG'  # Único codón para Met
        
        return preferred
    
    def _reverse_translate_naive(self, protein_sequence: str) -> str:
        """
        Reverse translation naive (primer codón de cada aminoácido).
        
        Args:
            protein_sequence: Secuencia de proteína
        
        Returns:
            Secuencia de DNA
        """
        dna = ""
        
        # Tabla inversa simple (primer codón alfabéticamente)
        simple_table = {
            'A': 'GCA', 'R': 'AGA', 'N': 'AAT', 'D': 'GAT', 'C': 'TGT',
            'Q': 'CAA', 'E': 'GAA', 'G': 'GGA', 'H': 'CAT', 'I': 'ATA',
            'L': 'CTA', 'K': 'AAA', 'M': 'ATG', 'F': 'TTT', 'P': 'CCA',
            'S': 'AGT', 'T': 'ACA', 'W': 'TGG', 'Y': 'TAT', 'V': 'GTA',
            '*': 'TAA'
        }
        
        for aa in protein_sequence:
            dna += simple_table.get(aa.upper(), 'NNN')
        
        return dna
    
    def _reverse_translate_optimized(self,
                                     protein_sequence: str,
                                     preferred_codons: Dict[str, str]) -> str:
        """
        Reverse translation optimizada usando codones preferidos.
        
        Args:
            protein_sequence: Secuencia de proteína
            preferred_codons: Dict {aa: codon_preferido}
        
        Returns:
            Secuencia de DNA optimizada
        """
        dna = ""
        
        for aa in protein_sequence:
            codon = preferred_codons.get(aa.upper(), 'NNN')
            dna += codon
        
        return dna
    
    # ================================================================
    # MÉTRICAS DE CALIDAD
    # ================================================================
    
    def _calculate_sequence_metrics(self,
                                    dna_sequence: str,
                                    rscu: Dict[str, float]) -> Dict[str, float]:
        """
        Calcula métricas de calidad de una secuencia.
        
        Returns:
            Dict con métricas
        """
        # GC content
        gc = gc_content(dna_sequence)
        
        # GC3 (GC en tercera posición)
        third_positions = [dna_sequence[i+2] for i in range(0, len(dna_sequence)-2, 3)]
        gc3 = self._gc_of_bases(third_positions)
        
        # Codones
        codons = [dna_sequence[i:i+3] for i in range(0, len(dna_sequence)-2, 3)]
        
        # Codones raros (RSCU < 0.5)
        rare_count = sum(1 for codon in codons if rscu.get(codon, 1.0) < 0.5)
        rare_pct = (rare_count / len(codons) * 100) if len(codons) > 0 else 0.0
        
        # Distancia RSCU (promedio de diferencias)
        rscu_diffs = [abs(rscu.get(codon, 1.0) - 1.0) for codon in codons]
        rscu_distance = sum(rscu_diffs) / len(rscu_diffs) if rscu_diffs else 0.0
        
        # Similitud de uso de codones (1 - normalized distance)
        codon_similarity = max(0.0, 1.0 - (rscu_distance / 2.0))
        
        return {
            'gc': gc,
            'gc3': gc3,
            'rare_codons_pct': rare_pct,
            'rscu_distance': rscu_distance,
            'codon_similarity': codon_similarity
        }
    
    def _gc_of_bases(self, bases: List[str]) -> float:
        """Calcula GC de una lista de bases."""
        if not bases:
            return 0.0
        
        g = sum(1 for b in bases if b.upper() == 'G')
        c = sum(1 for b in bases if b.upper() == 'C')
        
        return (g + c) / len(bases) * 100
    
    # ================================================================
    # UTILIDADES
    # ================================================================
    
    def optimize_for_genome(self,
                           protein_sequence: str,
                           genome_id: str) -> CodonOptimization:
        """
        Método de conveniencia para optimizar para un genoma específico.
        
        Args:
            protein_sequence: Secuencia de proteína
            genome_id: ID del genoma
        
        Returns:
            CodonOptimization
        """
        return self.optimize_sequence(protein_sequence, genome_id=genome_id)


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_optimizer_service_instance = None

def get_optimizer_service() -> CodonOptimizerService:
    """
    Obtiene la instancia singleton del servicio de optimización.
    
    Returns:
        CodonOptimizerService instance
    """
    global _optimizer_service_instance
    
    if _optimizer_service_instance is None:
        _optimizer_service_instance = CodonOptimizerService()
    
    return _optimizer_service_instance


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    print("=== Test Codon Optimizer Service ===\n")
    
    optimizer = get_optimizer_service()
    
    # Secuencia de proteína de ejemplo (Insulina humana - fragmento)
    protein = "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
    
    print(f"Proteína: {len(protein)} aminoácidos")
    print(f"Secuencia: {protein[:50]}...\n")
    
    # Optimizar
    result = optimizer.optimize_sequence(protein)
    
    print(f"\n=== RESULTADOS ===")
    print(f"Secuencia original ({len(result.original_sequence)} bp):")
    print(f"  {result.original_sequence[:60]}...")
    print(f"\nSecuencia optimizada ({len(result.optimized_sequence)} bp):")
    print(f"  {result.optimized_sequence[:60]}...")
    
    print(f"\nMétricas:")
    print(f"  Cambios: {result.changes_count} nucleótidos")
    print(f"  GC: {result.original_gc:.1f}% → {result.optimized_gc:.1f}%")
    print(f"  GC3: {result.original_gc3:.1f}% → {result.optimized_gc3:.1f}%")
    print(f"  Codones raros: {result.rare_codons_original:.1f}% → {result.rare_codons_optimized:.1f}%")
    print(f"  Score de mejora: {result.get_improvement_score():.1f}/100")
    
    # Verificar que la proteína no cambió
    from utils.sequence_utils import translate_dna
    protein_check = translate_dna(result.optimized_sequence)
    print(f"\n✓ Proteína verificada: {'IDÉNTICA' if protein_check == protein else 'ERROR'}")