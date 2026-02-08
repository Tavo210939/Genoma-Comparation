"""
Design Proposal Model - Propuesta de diseño genético
Representa la propuesta final del sistema de diseño genético in-silico.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Alert:
    """
    Representa una alerta de compatibilidad.
    
    Attributes:
        type: Tipo de alerta (glycosylation, signal_peptide, etc)
        level: RED o YELLOW
        message: Mensaje descriptivo
        evidence: Evidencia de UniProt
    """
    
    type: str
    level: str  # RED o YELLOW
    message: str
    evidence: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'type': self.type,
            'level': self.level,
            'message': self.message,
            'evidence': self.evidence
        }


@dataclass
class CodonOptimization:
    """
    Representa una optimización de codones.
    
    Attributes:
        original_sequence: Secuencia de DNA original
        optimized_sequence: Secuencia de DNA optimizada
        original_gc: GC content original
        optimized_gc: GC content optimizado
        original_gc3: GC3 original
        optimized_gc3: GC3 optimizado
        rare_codons_original: % codones raros original
        rare_codons_optimized: % codones raros optimizado
        changes_count: Número de cambios realizados
        rscu_distance: Distancia RSCU con el genoma
        codon_usage_similarity: Similitud de uso de codones (0-1)
    """
    
    original_sequence: str
    optimized_sequence: str
    
    # Métricas originales
    original_gc: float = 0.0
    original_gc3: float = 0.0
    rare_codons_original: float = 0.0
    
    # Métricas optimizadas
    optimized_gc: float = 0.0
    optimized_gc3: float = 0.0
    rare_codons_optimized: float = 0.0
    
    # Cambios
    changes_count: int = 0
    
    # Similitud con hospedero
    rscu_distance: float = 0.0
    codon_usage_similarity: float = 0.0
    
    def get_improvement_score(self) -> float:
        """
        Calcula un score de mejora (0-100).
        
        Returns:
            Score donde 100 = mejor
        """
        score = 0.0
        
        # Reducción de codones raros (40 puntos)
        if self.rare_codons_original > 0:
            reduction = (self.rare_codons_original - self.rare_codons_optimized) / self.rare_codons_original
            score += min(reduction * 40, 40)
        
        # Similitud de uso de codones (30 puntos)
        score += self.codon_usage_similarity * 30
        
        # GC3 match (30 puntos)
        # Asumiendo que GC3 ideal para E. coli es ~53%
        gc3_diff = abs(self.optimized_gc3 - 53.0)
        gc3_score = max(0, 30 - gc3_diff)
        score += gc3_score
        
        return min(score, 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'original': {
                'sequence': self.original_sequence[:100] + '...' if len(self.original_sequence) > 100 else self.original_sequence,
                'length': len(self.original_sequence),
                'gc': round(self.original_gc, 2),
                'gc3': round(self.original_gc3, 2),
                'rare_codons_pct': round(self.rare_codons_original, 2)
            },
            'optimized': {
                'sequence': self.optimized_sequence[:100] + '...' if len(self.optimized_sequence) > 100 else self.optimized_sequence,
                'length': len(self.optimized_sequence),
                'gc': round(self.optimized_gc, 2),
                'gc3': round(self.optimized_gc3, 2),
                'rare_codons_pct': round(self.rare_codons_optimized, 2)
            },
            'changes': self.changes_count,
            'metrics': {
                'rscu_distance': round(self.rscu_distance, 4),
                'codon_usage_similarity': round(self.codon_usage_similarity, 4),
                'improvement_score': round(self.get_improvement_score(), 2)
            }
        }


@dataclass
class DesignProposal:
    """
    Propuesta completa de diseño genético in-silico.
    
    Attributes:
        # Proteína objetivo
        target_protein_id: Accession de la proteína
        target_protein_name: Nombre de la proteína
        target_organism: Organismo de origen
        
        # Genoma hospedero
        genome_id: ID del genoma hospedero
        
        # Decisión
        base_case: "homolog_exists" | "requires_external_gene"
        compatibility: "ok" | "conditions" | "high_risk"
        confidence: "high" | "medium" | "borderline"
        
        # Explicación
        reasoning: Explicación de la decisión
        
        # Alertas
        alerts_red: Lista de alertas críticas (RED)
        alerts_yellow: Lista de alertas de advertencia (YELLOW)
        
        # Comparación con genoma
        best_local_candidate: Información del mejor candidato local
        
        # Propuesta de optimización
        codon_optimization: CodonOptimization object (si aplica)
        
        # Recomendaciones
        strategy: "use_local" | "modify_local" | "introduce_external"
        recommendations: Lista de recomendaciones
        
        # Metadata
        analysis_date: Timestamp del análisis
        pipeline_version: Versión del pipeline usada
    """
    
    # Proteína objetivo
    target_protein_id: str
    target_protein_name: str
    target_organism: str
    
    # Genoma
    genome_id: str
    
    # Decisión (modelo corregido)
    base_case: str  # "homolog_exists" o "requires_external_gene"
    compatibility: str  # "ok", "conditions", "high_risk"
    confidence: str = "high"  # "high", "medium", "borderline"
    
    # Explicación
    reasoning: str = ""
    
    # Alertas
    alerts_red: List[Alert] = field(default_factory=list)
    alerts_yellow: List[Alert] = field(default_factory=list)
    
    # Mejor candidato local
    best_local_candidate: Optional[Dict[str, Any]] = None
    
    # Optimización de codones
    codon_optimization: Optional[CodonOptimization] = None
    
    # Estrategia y recomendaciones
    strategy: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    analysis_date: str = ""
    pipeline_version: str = ""
    
    def has_critical_issues(self) -> bool:
        """
        Determina si hay problemas críticos.
        
        Returns:
            True si hay alertas RED
        """
        return len(self.alerts_red) > 0
    
    def is_recommended(self) -> bool:
        """
        Determina si la propuesta es recomendada.
        
        Returns:
            True si compatibility != "high_risk"
        """
        return self.compatibility != "high_risk"
    
    def get_alert_summary(self) -> str:
        """
        Genera un resumen de alertas.
        
        Returns:
            String con resumen
        """
        total_red = len(self.alerts_red)
        total_yellow = len(self.alerts_yellow)
        
        if total_red == 0 and total_yellow == 0:
            return "Sin alertas - Compatible"
        elif total_red > 0:
            return f"{total_red} alertas críticas, {total_yellow} advertencias"
        else:
            return f"{total_yellow} advertencias"
    
    def to_dict(self, include_optimization_details: bool = True) -> Dict[str, Any]:
        """
        Convierte a diccionario.
        
        Args:
            include_optimization_details: Si incluir detalles de optimización
        
        Returns:
            Dict completo de la propuesta
        """
        data = {
            'target_protein': {
                'accession': self.target_protein_id,
                'name': self.target_protein_name,
                'organism': self.target_organism
            },
            'genome': {
                'id': self.genome_id
            },
            'decision': {
                'base_case': self.base_case,
                'compatibility': self.compatibility,
                'confidence': self.confidence,
                'reasoning': self.reasoning,
                'is_recommended': self.is_recommended()
            },
            'alerts': {
                'red': [a.to_dict() for a in self.alerts_red],
                'yellow': [a.to_dict() for a in self.alerts_yellow],
                'summary': self.get_alert_summary(),
                'has_critical': self.has_critical_issues()
            },
            'strategy': self.strategy,
            'recommendations': self.recommendations,
            'metadata': {
                'analysis_date': self.analysis_date,
                'pipeline_version': self.pipeline_version
            }
        }
        
        if self.best_local_candidate:
            data['best_local_candidate'] = self.best_local_candidate
        
        if self.codon_optimization and include_optimization_details:
            data['codon_optimization'] = self.codon_optimization.to_dict()
        
        return data


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    from datetime import datetime
    
    # Crear alertas de ejemplo
    alert1 = Alert(
        type="signal_peptide",
        level="YELLOW",
        message="Proteína secretada - requiere verificación del sistema Sec de E. coli",
        evidence="UniProt annotation: Signal peptide 1-24"
    )
    
    alert2 = Alert(
        type="disulfide_bonds",
        level="YELLOW",
        message="Requiere 3 puentes disulfuro",
        evidence="UniProt annotation: Disulfide bonds"
    )
    
    # Crear propuesta de ejemplo
    proposal = DesignProposal(
        target_protein_id="P01308",
        target_protein_name="Insulin",
        target_organism="Homo sapiens",
        genome_id="NC_000913.3",
        base_case="requires_external_gene",
        compatibility="conditions",
        confidence="high",
        reasoning="No se encontró homólogo con similitud suficiente (mejor hit: 45% identidad, 78% cobertura). Se requiere introducción de gen externo. Sin embargo, la proteína presenta características que requieren atención.",
        alerts_yellow=[alert1, alert2],
        strategy="introduce_external",
        recommendations=[
            "Expresar en periplasma para formación de puentes disulfuro",
            "Usar vector con péptido señal compatible con E. coli",
            "Considerar optimización de codones para mejorar expresión"
        ],
        analysis_date=datetime.now().isoformat(),
        pipeline_version="2.0.0"
    )
    
    print("=== Design Proposal Example ===")
    print(f"Target: {proposal.target_protein_name}")
    print(f"Base case: {proposal.base_case}")
    print(f"Compatibility: {proposal.compatibility}")
    print(f"Alert summary: {proposal.get_alert_summary()}")
    print(f"Is recommended: {proposal.is_recommended()}")
    print(f"\nReasoning:\n{proposal.reasoning}")
    print(f"\nRecommendations:")
    for i, rec in enumerate(proposal.recommendations, 1):
        print(f"  {i}. {rec}")