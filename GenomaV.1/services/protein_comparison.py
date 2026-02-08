"""
Protein Comparison Service - Comparación híbrida proteína vs genoma
Implementa estrategia de dos fases:
1. Filtrado rápido con k-mers (reduce candidatos)
2. Alineamiento preciso con BioPython (top candidatos)

Esto permite comparar una proteína contra miles de genes eficientemente.
"""

import time
from typing import List, Tuple, Dict, Any, Optional
from Bio import Align
from Bio.Align import PairwiseAligner
from collections import Counter

import config
from models.protein import Protein
from models.gene import Gene
from models.comparison_result import ComparisonResult, AlignmentCandidate
from utils.sequence_utils import (
    filter_by_kmer_similarity,
    quick_similarity,
    amino_acid_composition,
    composition_similarity
)


class ProteinComparisonService:
    """
    Servicio de comparación de proteínas contra genomas.
    
    Estrategia híbrida:
    1. Pre-filtrado rápido con k-mers (top 50-100)
    2. Alineamiento local preciso (top N final)
    """
    
    def __init__(self):
        # Configurar alineador de BioPython
        self.aligner = PairwiseAligner()
        self.aligner.mode = 'local'  # Alineamiento local (como BLAST)
        self.aligner.match_score = 2
        self.aligner.mismatch_score = -1
        self.aligner.open_gap_score = -2
        self.aligner.extend_gap_score = -0.5
    
    # ================================================================
    # COMPARACIÓN COMPLETA
    # ================================================================
    
    def compare_protein_vs_proteome(self,
                                    target_protein: Protein,
                                    genome_proteome: List[Gene],
                                    genome_id: str) -> ComparisonResult:
        """
        Compara una proteína objetivo contra el proteoma de un genoma.
        
        Args:
            target_protein: Proteína objetivo de UniProt
            genome_proteome: Lista de genes traducidos del genoma
            genome_id: ID del genoma
        
        Returns:
            ComparisonResult con candidatos ordenados
        """
        start_time = time.time()
        
        print(f"\n🔬 Comparando {target_protein.accession} contra {len(genome_proteome)} proteínas...")
        
        # FASE 1: Filtrado rápido con k-mers
        print(f"📊 Fase 1: Filtrado rápido con k-mers...")
        candidates_phase1 = self._quick_filter_phase(
            target_protein.sequence,
            genome_proteome
        )
        
        print(f"   ✓ Pre-seleccionados {len(candidates_phase1)} candidatos")
        
        # FASE 2: Alineamiento preciso
        print(f"🎯 Fase 2: Alineamiento preciso...")
        candidates_phase2 = self._precise_alignment_phase(
            target_protein.sequence,
            candidates_phase1
        )
        
        print(f"   ✓ Alineados {len(candidates_phase2)} candidatos")
        
        # Ordenar por score/identidad
        candidates_phase2.sort(key=lambda c: (c.identity, c.coverage), reverse=True)
        
        # Asignar ranks
        for i, candidate in enumerate(candidates_phase2, 1):
            candidate.rank = i
        
        # Crear resultado
        elapsed_time = time.time() - start_time
        
        result = ComparisonResult(
            target_protein_id=target_protein.accession,
            genome_id=genome_id,
            proteome_size=len(genome_proteome),
            candidates=candidates_phase2,
            comparison_method="hybrid_kmer_align",
            computation_time=elapsed_time
        )
        
        print(f"✓ Comparación completada en {elapsed_time:.2f}s")
        
        if result.best_candidate:
            print(f"   Mejor hit: {result.best_candidate.gene_name} "
                  f"({result.best_candidate.identity:.1f}% id, "
                  f"{result.best_candidate.coverage:.1f}% cov)")
        else:
            print(f"   No se encontraron hits significativos")
        
        return result
    
    # ================================================================
    # FASE 1: FILTRADO RÁPIDO CON K-MERS
    # ================================================================
    
    def _quick_filter_phase(self, 
                           target_seq: str,
                           genes: List[Gene]) -> List[Tuple[Gene, float]]:
        """
        Fase 1: Filtrado rápido usando k-mers.
        
        Args:
            target_seq: Secuencia objetivo (aminoácidos)
            genes: Lista de genes del genoma
        
        Returns:
            Lista de (Gene, similarity_score) top candidatos
        """
        # Preparar candidatos: (gene_id, protein_sequence)
        candidates = []
        for gene in genes:
            # Necesitamos la secuencia de proteína
            # Si no está traducida, traducir aquí
            if gene.protein_sequence:
                candidates.append((gene.id, gene.protein_sequence))
            else:
                # Traducir rápidamente (tabla estándar bacteria)
                protein_seq = self._translate_gene(gene)
                if protein_seq:
                    candidates.append((gene.id, protein_seq))
        
        # Filtrar con k-mers
        filtered = filter_by_kmer_similarity(
            target=target_seq,
            candidates=candidates,
            k=config.KMER_SIZE,
            method=config.KMER_SIMILARITY_METHOD,
            top_n=config.TOP_CANDIDATES_FOR_ALIGNMENT
        )
        
        # Mapear de vuelta a genes
        gene_dict = {g.id: g for g in genes}
        
        results = []
        for gene_id, protein_seq, similarity in filtered:
            gene = gene_dict.get(gene_id)
            if gene:
                # Guardar secuencia de proteína en el gen
                gene.protein_sequence = protein_seq
                results.append((gene, similarity))
        
        return results
    
    def _translate_gene(self, gene: Gene) -> str:
        """
        Traduce un gen a proteína usando tabla genética correcta.
        
        Args:
            gene: Gene object
        
        Returns:
            Secuencia de proteína
        """
        if not gene.sequence or len(gene.sequence) < 3:
            return ""
        
        try:
            from Bio.Data import CodonTable
            
            # Obtener tabla genética
            tabla = CodonTable.unambiguous_dna_by_id[gene.transl_table]
            
            # Traducir
            protein = ""
            for i in range(0, len(gene.sequence) - 2, 3):
                codon = gene.sequence[i:i+3]
                if codon in tabla.forward_table:
                    protein += tabla.forward_table[codon]
                elif codon in tabla.stop_codons:
                    protein += "*"
                else:
                    protein += "X"
            
            return protein
            
        except Exception as e:
            print(f"⚠️ Error traduciendo gen {gene.id}: {e}")
            return ""
    
    # ================================================================
    # FASE 2: ALINEAMIENTO PRECISO
    # ================================================================
    
    def _precise_alignment_phase(self,
                                 target_seq: str,
                                 candidates: List[Tuple[Gene, float]]) -> List[AlignmentCandidate]:
        """
        Fase 2: Alineamiento preciso con BioPython.
        
        Args:
            target_seq: Secuencia objetivo
            candidates: Lista de (Gene, kmer_similarity)
        
        Returns:
            Lista de AlignmentCandidate con métricas completas
        """
        results = []
        
        for gene, kmer_sim in candidates:
            if not gene.protein_sequence:
                continue
            
            # Alinear
            alignment_data = self._align_sequences(
                target_seq,
                gene.protein_sequence
            )
            
            if not alignment_data:
                continue
            
            # Crear candidato
            candidate = AlignmentCandidate(
                rank=0,  # Se asignará después
                gene_id=gene.id,
                locus_tag=gene.locus_tag,
                gene_name=gene.gene,
                product=gene.product,
                identity=alignment_data['identity'],
                coverage=alignment_data['coverage'],
                score=alignment_data['score'],
                aligned_length=alignment_data['aligned_length'],
                query_start=alignment_data['query_start'],
                query_end=alignment_data['query_end'],
                subject_start=alignment_data['subject_start'],
                subject_end=alignment_data['subject_end'],
                gaps=alignment_data['gaps'],
                mismatches=alignment_data['mismatches']
            )
            
            results.append(candidate)
        
        return results
    
    def _align_sequences(self, seq1: str, seq2: str) -> Optional[Dict[str, Any]]:
        """
        Alinea dos secuencias de proteínas.
        
        Args:
            seq1: Query (proteína objetivo)
            seq2: Subject (gen del genoma)
        
        Returns:
            Dict con métricas del alineamiento o None
        """
        try:
            # Realizar alineamiento
            alignments = self.aligner.align(seq1, seq2)
            
            if not alignments:
                return None
            
            # Tomar el mejor alineamiento
            best = alignments[0]
            
            # Extraer información
            aligned_query = str(best).split('\n')[0]
            aligned_subject = str(best).split('\n')[2] if len(str(best).split('\n')) > 2 else ""
            
            # Calcular métricas
            metrics = self._calculate_alignment_metrics(
                seq1, seq2, best, aligned_query, aligned_subject
            )
            
            return metrics
            
        except Exception as e:
            print(f"⚠️ Error en alineamiento: {e}")
            return None
    
    def _calculate_alignment_metrics(self,
                                     query: str,
                                     subject: str,
                                     alignment,
                                     aligned_query: str,
                                     aligned_subject: str) -> Dict[str, Any]:
        """
        Calcula métricas del alineamiento.
        
        Args:
            query: Secuencia query original
            subject: Secuencia subject original
            alignment: Objeto alignment de BioPython
            aligned_query: Query alineada (con gaps)
            aligned_subject: Subject alineada (con gaps)
        
        Returns:
            Dict con métricas
        """
        # Longitud del alineamiento
        aligned_length = len(aligned_query.replace('-', ''))
        
        # Contar identidades
        identities = sum(1 for q, s in zip(aligned_query, aligned_subject) 
                        if q == s and q != '-')
        
        # Contar gaps
        gaps = aligned_query.count('-') + aligned_subject.count('-')
        
        # Contar mismatches
        mismatches = sum(1 for q, s in zip(aligned_query, aligned_subject) 
                        if q != s and q != '-' and s != '-')
        
        # Porcentaje de identidad
        # Identidad = (identidades / longitud alineada) * 100
        identity = (identities / aligned_length * 100) if aligned_length > 0 else 0.0
        
        # Cobertura (coverage)
        # Coverage = (longitud alineada / longitud query) * 100
        coverage = (aligned_length / len(query) * 100) if len(query) > 0 else 0.0
        
        # Score del alineamiento
        score = alignment.score
        
        # Posiciones
        query_start = 0
        query_end = aligned_length
        subject_start = 0
        subject_end = aligned_length
        
        return {
            'identity': identity,
            'coverage': coverage,
            'score': score,
            'aligned_length': aligned_length,
            'query_start': query_start,
            'query_end': query_end,
            'subject_start': subject_start,
            'subject_end': subject_end,
            'gaps': gaps,
            'mismatches': mismatches
        }
    
    # ================================================================
    # UTILIDADES
    # ================================================================
    
    def find_best_match(self,
                       target_protein: Protein,
                       genome_proteome: List[Gene],
                       genome_id: str) -> Optional[AlignmentCandidate]:
        """
        Encuentra el mejor match (método simplificado).
        
        Args:
            target_protein: Proteína objetivo
            genome_proteome: Proteoma del genoma
            genome_id: ID del genoma
        
        Returns:
            Mejor candidato o None
        """
        result = self.compare_protein_vs_proteome(
            target_protein,
            genome_proteome,
            genome_id
        )
        
        return result.best_candidate
    
    def has_significant_homolog(self,
                               target_protein: Protein,
                               genome_proteome: List[Gene],
                               genome_id: str,
                               identity_threshold: float = None,
                               coverage_threshold: float = None) -> bool:
        """
        Determina si existe un homólogo significativo.
        
        Args:
            target_protein: Proteína objetivo
            genome_proteome: Proteoma del genoma
            genome_id: ID del genoma
            identity_threshold: Umbral de identidad (default: config)
            coverage_threshold: Umbral de cobertura (default: config)
        
        Returns:
            True si existe homólogo significativo
        """
        if identity_threshold is None:
            identity_threshold = config.HOMOLOG_IDENTITY_THRESHOLD
        
        if coverage_threshold is None:
            coverage_threshold = config.HOMOLOG_COVERAGE_THRESHOLD
        
        best = self.find_best_match(target_protein, genome_proteome, genome_id)
        
        if not best:
            return False
        
        return (best.identity >= identity_threshold and 
                best.coverage >= coverage_threshold)


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_comparison_service_instance = None

def get_comparison_service() -> ProteinComparisonService:
    """
    Obtiene la instancia singleton del servicio de comparación.
    
    Returns:
        ProteinComparisonService instance
    """
    global _comparison_service_instance
    
    if _comparison_service_instance is None:
        _comparison_service_instance = ProteinComparisonService()
    
    return _comparison_service_instance


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    from services.uniprot_service import get_uniprot_service
    from services.ncbi_service import get_ncbi_service
    from services.genome_analysis import get_analysis_service
    
    print("=== Test Protein Comparison Service ===\n")
    
    # Servicios
    uniprot = get_uniprot_service()
    ncbi = get_ncbi_service()
    analysis = get_analysis_service()
    comparison = get_comparison_service()
    
    # 1. Descargar proteína objetivo
    print("1. Descargando proteína de prueba (Insulin)...")
    target_protein = uniprot.fetch_protein("P01308")
    
    if not target_protein:
        print("❌ No se pudo descargar proteína")
        exit(1)
    
    print(f"   ✓ {target_protein.name} ({target_protein.length} aa)")
    
    # 2. Descargar genoma
    print("\n2. Descargando genoma E. coli K-12...")
    record = ncbi.fetch_genome("NC_000913.3")
    
    if not record:
        print("❌ No se pudo descargar genoma")
        exit(1)
    
    print(f"   ✓ Genoma descargado")
    
    # 3. Extraer genes
    print("\n3. Extrayendo genes del genoma...")
    genes = analysis.extract_genes_from_record(record, "NC_000913.3")
    print(f"   ✓ Extraídos {len(genes)} genes")
    
    # 4. Comparar
    print("\n4. Comparando proteína contra genoma...")
    result = comparison.compare_protein_vs_proteome(
        target_protein,
        genes,
        "NC_000913.3"
    )
    
    print(f"\n=== RESULTADOS ===")
    print(f"Total de matches: {result.total_matches}")
    print(f"Tiempo de cómputo: {result.computation_time:.2f}s")
    print(f"Tiene buen match: {result.has_good_match}")
    
    if result.best_candidate:
        print(f"\nMejor candidato:")
        print(f"  Gen: {result.best_candidate.gene_name} ({result.best_candidate.locus_tag})")
        print(f"  Producto: {result.best_candidate.product}")
        print(f"  Identidad: {result.best_candidate.identity:.2f}%")
        print(f"  Cobertura: {result.best_candidate.coverage:.2f}%")
        print(f"  Score: {result.best_candidate.score:.2f}")
    
    print(f"\nTop 5 candidatos:")
    for i, candidate in enumerate(result.get_top_candidates(5), 1):
        print(f"  {i}. {candidate.gene_name}: {candidate.identity:.1f}% id, {candidate.coverage:.1f}% cov")