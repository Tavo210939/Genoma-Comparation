"""
Comparison Result Model - Resultado de comparación proteína vs genoma
Representa el resultado de comparar una proteína objetivo contra un genoma.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AlignmentCandidate:
    """
    Representa un candidato de alineamiento (gen del genoma).
    
    Attributes:
        rank: Posición en el ranking (1 = mejor)
        gene_id: ID del gen
        locus_tag: Locus tag del gen
        gene_name: Nombre del gen
        product: Descripción del producto
        identity: Porcentaje de identidad
        coverage: Porcentaje de cobertura
        score: Score del alineamiento
        e_value: E-value (si aplica)
        aligned_length: Longitud del alineamiento
        query_start: Inicio en la query
        query_end: Fin en la query
        subject_start: Inicio en el sujeto
        subject_end: Fin en el sujeto
        gaps: Número de gaps
        mismatches: Número de mismatches
    """
    
    rank: int
    gene_id: str
    locus_tag: str = "-"
    gene_name: str = "-"
    product: str = "Unknown"
    
    # Métricas de similitud
    identity: float = 0.0  # Porcentaje
    coverage: float = 0.0  # Porcentaje
    score: float = 0.0
    e_value: Optional[float] = None
    
    # Detalles del alineamiento
    aligned_length: int = 0
    query_start: int = 0
    query_end: int = 0
    subject_start: int = 0
    subject_end: int = 0
    gaps: int = 0
    mismatches: int = 0
    
    def is_good_match(self, identity_threshold: float = 60.0, 
                     coverage_threshold: float = 80.0) -> bool:
        """
        Determina si es un buen match según umbrales.
        
        Args:
            identity_threshold: Umbral de identidad (%)
            coverage_threshold: Umbral de cobertura (%)
        
        Returns:
            True si supera ambos umbrales
        """
        return self.identity >= identity_threshold and self.coverage >= coverage_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'rank': self.rank,
            'gene_id': self.gene_id,
            'locus_tag': self.locus_tag,
            'gene_name': self.gene_name,
            'product': self.product,
            'identity': round(self.identity, 2),
            'coverage': round(self.coverage, 2),
            'score': round(self.score, 2),
            'e_value': self.e_value,
            'aligned_length': self.aligned_length,
            'alignment_region': f"{self.query_start}-{self.query_end}",
            'gaps': self.gaps,
            'mismatches': self.mismatches
        }


@dataclass
class ComparisonResult:
    """
    Resultado completo de comparar una proteína contra un genoma.
    
    Attributes:
        target_protein_id: Accession de la proteína objetivo
        genome_id: ID del genoma analizado
        proteome_size: Número de proteínas en el genoma
        candidates: Lista de candidatos ordenados por similitud
        best_candidate: Mejor candidato (o None)
        has_good_match: Si hay al menos un buen match
        total_matches: Total de matches encontrados
        comparison_method: Método usado (hybrid, blast, etc)
        computation_time: Tiempo de cómputo (segundos)
    """
    
    target_protein_id: str
    genome_id: str
    proteome_size: int
    
    # Resultados
    candidates: List[AlignmentCandidate] = field(default_factory=list)
    best_candidate: Optional[AlignmentCandidate] = None
    
    # Estadísticas
    has_good_match: bool = False
    total_matches: int = 0
    
    # Metadata
    comparison_method: str = "hybrid"
    computation_time: float = 0.0
    
    def __post_init__(self):
        """Cálculos automáticos."""
        # Asignar mejor candidato
        if self.candidates and not self.best_candidate:
            self.best_candidate = self.candidates[0]
        
        # Total de matches
        if self.total_matches == 0:
            self.total_matches = len(self.candidates)
        
        # Determinar si hay buen match
        if self.best_candidate:
            import config
            self.has_good_match = self.best_candidate.is_good_match(
                config.HOMOLOG_IDENTITY_THRESHOLD,
                config.HOMOLOG_COVERAGE_THRESHOLD
            )
    
    def get_top_candidates(self, n: int = 5) -> List[AlignmentCandidate]:
        """
        Obtiene los top N candidatos.
        
        Args:
            n: Número de candidatos
        
        Returns:
            Lista de candidatos
        """
        return self.candidates[:n]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Genera un resumen del resultado.
        
        Returns:
            Dict con resumen
        """
        summary = {
            'target_protein': self.target_protein_id,
            'genome': self.genome_id,
            'proteome_size': self.proteome_size,
            'total_matches': self.total_matches,
            'has_good_match': self.has_good_match,
            'computation_time': round(self.computation_time, 2)
        }
        
        if self.best_candidate:
            summary['best_match'] = {
                'gene': self.best_candidate.gene_name,
                'locus_tag': self.best_candidate.locus_tag,
                'identity': round(self.best_candidate.identity, 2),
                'coverage': round(self.best_candidate.coverage, 2)
            }
        else:
            summary['best_match'] = None
        
        return summary
    
    def to_dict(self, include_all_candidates: bool = False) -> Dict[str, Any]:
        """
        Convierte a diccionario.
        
        Args:
            include_all_candidates: Si incluir todos los candidatos
        
        Returns:
            Dict completo
        """
        data = {
            'target_protein_id': self.target_protein_id,
            'genome_id': self.genome_id,
            'proteome_size': self.proteome_size,
            'has_good_match': self.has_good_match,
            'total_matches': self.total_matches,
            'comparison_method': self.comparison_method,
            'computation_time': round(self.computation_time, 2)
        }
        
        if include_all_candidates:
            data['candidates'] = [c.to_dict() for c in self.candidates]
        else:
            # Solo top 10
            data['top_candidates'] = [c.to_dict() for c in self.candidates[:10]]
        
        if self.best_candidate:
            data['best_candidate'] = self.best_candidate.to_dict()
        
        return data


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    # Crear candidatos de ejemplo
    candidate1 = AlignmentCandidate(
        rank=1,
        gene_id="b1234",
        locus_tag="b1234",
        gene_name="insA",
        product="Hypothetical insulin-like protein",
        identity=45.2,
        coverage=78.5,
        score=234.5,
        aligned_length=85,
        query_start=1,
        query_end=85,
        subject_start=1,
        subject_end=85
    )
    
    candidate2 = AlignmentCandidate(
        rank=2,
        gene_id="b5678",
        locus_tag="b5678",
        gene_name="pepA",
        product="Peptidase A",
        identity=28.1,
        coverage=45.3,
        score=123.4,
        aligned_length=50
    )
    
    # Crear resultado de comparación
    result = ComparisonResult(
        target_protein_id="P01308",
        genome_id="NC_000913.3",
        proteome_size=4321,
        candidates=[candidate1, candidate2],
        comparison_method="hybrid",
        computation_time=2.5
    )
    
    print("=== Comparison Result Example ===")
    print(f"Target: {result.target_protein_id}")
    print(f"Genome: {result.genome_id}")
    print(f"Has good match: {result.has_good_match}")
    print(f"\nBest candidate:")
    print(f"  Gene: {result.best_candidate.gene_name}")
    print(f"  Identity: {result.best_candidate.identity}%")
    print(f"  Coverage: {result.best_candidate.coverage}%")
    print(f"\nSummary:")
    print(result.get_summary())