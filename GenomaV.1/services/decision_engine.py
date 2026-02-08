"""
Decision Engine - Motor de decisiones para diseño genético in-silico
Implementa la lógica de decisión basada en:
- Similitud con genes del genoma (base_case)
- Anotaciones de compatibilidad (compatibility)
- Generación de alertas (RED/YELLOW)
- Razonamiento explicativo

Modelo de decisión:
    base_case: "homolog_exists" | "requires_external_gene"
    compatibility: "ok" | "conditions" | "high_risk"
    confidence: "high" | "medium" | "borderline"
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

import config
from models.protein import Protein
from models.comparison_result import ComparisonResult, AlignmentCandidate
from models.design_proposal import DesignProposal, Alert


class DecisionEngine:
    """
    Motor de decisiones para el sistema de diseño genético.
    
    Toma como entrada:
    - Proteína objetivo (de UniProt)
    - Resultado de comparación (vs genoma)
    
    Genera como salida:
    - DesignProposal completo con decisión, alertas y recomendaciones
    """
    
    def __init__(self):
        self.alerts_config = config.ALERTS_CONFIG
    
    # ================================================================
    # DECISIÓN PRINCIPAL
    # ================================================================
    
    def make_decision(self,
                     target_protein: Protein,
                     comparison_result: ComparisonResult,
                     genome_id: str) -> DesignProposal:
        """
        Toma la decisión completa sobre el diseño genético.
        
        Args:
            target_protein: Proteína objetivo
            comparison_result: Resultado de la comparación
            genome_id: ID del genoma hospedero
        
        Returns:
            DesignProposal completo
        """
        print(f"\n🧠 Analizando compatibilidad de {target_protein.accession}...")
        
        # PASO 1: Determinar base_case
        base_case, confidence = self._determine_base_case(comparison_result)
        print(f"   ✓ Base case: {base_case} (confianza: {confidence})")
        
        # PASO 2: Evaluar compatibilidad (alertas)
        alerts_red, alerts_yellow = self._assess_compatibility(target_protein)
        print(f"   ✓ Alertas: {len(alerts_red)} RED, {len(alerts_yellow)} YELLOW")
        
        # PASO 3: Determinar nivel de compatibilidad
        compatibility = self._determine_compatibility_level(alerts_red, alerts_yellow)
        print(f"   ✓ Compatibility: {compatibility}")
        
        # PASO 4: Generar razonamiento
        reasoning = self._generate_reasoning(
            target_protein,
            comparison_result,
            base_case,
            compatibility,
            confidence
        )
        
        # PASO 5: Determinar estrategia
        strategy = self._determine_strategy(base_case, compatibility)
        
        # PASO 6: Generar recomendaciones
        recommendations = self._generate_recommendations(
            target_protein,
            base_case,
            compatibility,
            alerts_red,
            alerts_yellow
        )
        
        # PASO 7: Extraer mejor candidato local
        best_local = self._format_best_candidate(comparison_result.best_candidate)
        
        # Crear propuesta
        proposal = DesignProposal(
            target_protein_id=target_protein.accession,
            target_protein_name=target_protein.name,
            target_organism=target_protein.organism,
            genome_id=genome_id,
            base_case=base_case,
            compatibility=compatibility,
            confidence=confidence,
            reasoning=reasoning,
            alerts_red=alerts_red,
            alerts_yellow=alerts_yellow,
            best_local_candidate=best_local,
            strategy=strategy,
            recommendations=recommendations,
            analysis_date=datetime.now().isoformat(),
            pipeline_version=config.PIPELINE_VERSION
        )
        
        print(f"✓ Decisión completada: {base_case} + {compatibility}")
        
        return proposal
    
    # ================================================================
    # PASO 1: DETERMINAR BASE_CASE
    # ================================================================
    
    def _determine_base_case(self, 
                            comparison_result: ComparisonResult) -> tuple:
        """
        Determina el base_case basado en similitud.
        
        Returns:
            (base_case, confidence)
        """
        best = comparison_result.best_candidate
        
        if not best:
            return "requires_external_gene", "high"
        
        # Umbrales
        identity = best.identity
        coverage = best.coverage
        
        # Decisión con 3 niveles de confianza
        if (identity >= config.HOMOLOG_IDENTITY_THRESHOLD and 
            coverage >= config.HOMOLOG_COVERAGE_THRESHOLD):
            # Homólogo claro
            return "homolog_exists", "high"
        
        elif (identity >= config.BORDERLINE_IDENTITY_THRESHOLD and 
              coverage >= config.BORDERLINE_COVERAGE_THRESHOLD):
            # Zona borderline - existe algo parecido pero no muy cercano
            # En este caso, seguimos diciendo que existe homólogo pero con menos confianza
            return "homolog_exists", "borderline"
        
        else:
            # No hay homólogo útil
            return "requires_external_gene", "high"
    
    # ================================================================
    # PASO 2: EVALUAR COMPATIBILIDAD (ALERTAS)
    # ================================================================
    
    def _assess_compatibility(self, 
                             protein: Protein) -> tuple:
        """
        Evalúa compatibilidad de la proteína con E. coli.
        Genera alertas RED y YELLOW basadas en anotaciones.
        
        Returns:
            (alerts_red, alerts_yellow)
        """
        alerts_red = []
        alerts_yellow = []
        
        # 1. Glicosilación (RED - crítico)
        if protein.has_glycosylation:
            alert = self._create_alert(
                'glycosylation',
                f"Se detectaron {len(protein.glycosylation_sites)} sitios de glicosilación"
            )
            if alert:
                alerts_red.append(alert)
        
        # 2. Péptido señal (YELLOW - advertencia)
        if protein.has_signal_peptide:
            alert = self._create_alert(
                'signal_peptide',
                f"Péptido señal: {protein.signal_peptide_range}"
            )
            if alert:
                alerts_yellow.append(alert)
        
        # 3. Dominios transmembrana (RED si >3)
        if protein.transmembrane_count > 0:
            threshold = self.alerts_config['transmembrane'].get('threshold', 3)
            if protein.transmembrane_count >= threshold:
                alert = self._create_alert(
                    'transmembrane',
                    f"{protein.transmembrane_count} dominios transmembrana detectados"
                )
                if alert:
                    alerts_red.append(alert)
            else:
                # Menos de 3 dominios - solo advertencia
                alert = Alert(
                    type='transmembrane',
                    level='YELLOW',
                    message=f"{protein.transmembrane_count} dominio(s) transmembrana",
                    evidence=f"UniProt: {protein.transmembrane_count} región(es) TM"
                )
                alerts_yellow.append(alert)
        
        # 4. Puentes disulfuro (YELLOW)
        if protein.has_disulfide_bonds:
            alert = self._create_alert(
                'disulfide_bonds',
                f"{protein.disulfide_bond_count} puentes disulfuro"
            )
            if alert:
                alerts_yellow.append(alert)
        
        # 5. Metales (YELLOW)
        if protein.metal_binding:
            metals_str = ', '.join(protein.metal_binding)
            alert = self._create_alert(
                'metal_binding',
                f"Requiere: {metals_str}"
            )
            if alert:
                alerts_yellow.append(alert)
        
        # 6. Cofactores (YELLOW)
        if protein.cofactors:
            cofactors_str = ', '.join(protein.cofactors[:3])
            if len(protein.cofactors) > 3:
                cofactors_str += f" (+{len(protein.cofactors)-3} más)"
            alert = self._create_alert(
                'cofactor_required',
                f"Cofactores: {cofactors_str}"
            )
            if alert:
                alerts_yellow.append(alert)
        
        # 7. Proteasas (RED - toxicidad)
        if self._is_protease(protein):
            alert = self._create_alert(
                'protease',
                "Actividad proteolítica detectada"
            )
            if alert:
                alerts_red.append(alert)
        
        # 8. Toxinas (RED - toxicidad)
        if self._is_toxin(protein):
            alert = self._create_alert(
                'toxin',
                "Proteína tóxica identificada"
            )
            if alert:
                alerts_red.append(alert)
        
        return alerts_red, alerts_yellow
    
    def _create_alert(self, alert_type: str, evidence: str) -> Optional[Alert]:
        """
        Crea una alerta basada en configuración.
        
        Args:
            alert_type: Tipo de alerta
            evidence: Evidencia específica
        
        Returns:
            Alert object o None
        """
        if alert_type not in self.alerts_config:
            return None
        
        config_alert = self.alerts_config[alert_type]
        
        return Alert(
            type=alert_type,
            level=config_alert['level'],
            message=config_alert['message'],
            evidence=f"UniProt annotation: {evidence}"
        )
    
    def _is_protease(self, protein: Protein) -> bool:
        """Detecta si es una proteasa."""
        keywords_lower = [kw.lower() for kw in protein.keywords]
        
        # Buscar keywords de proteasas
        protease_keywords = ['protease', 'peptidase', 'endopeptidase', 'proteinase']
        
        return any(pk in ' '.join(keywords_lower) for pk in protease_keywords)
    
    def _is_toxin(self, protein: Protein) -> bool:
        """Detecta si es una toxina."""
        keywords_lower = [kw.lower() for kw in protein.keywords]
        name_lower = protein.name.lower()
        
        toxin_keywords = ['toxin', 'toxic', 'venom', 'lethal']
        
        return any(tk in ' '.join(keywords_lower) or tk in name_lower 
                  for tk in toxin_keywords)
    
    # ================================================================
    # PASO 3: DETERMINAR NIVEL DE COMPATIBILIDAD
    # ================================================================
    
    def _determine_compatibility_level(self,
                                      alerts_red: List[Alert],
                                      alerts_yellow: List[Alert]) -> str:
        """
        Determina el nivel de compatibilidad basado en alertas.
        
        Reglas:
        - high_risk: ≥1 alerta RED
        - conditions: ≥1 alerta YELLOW (sin RED)
        - ok: sin alertas
        
        Returns:
            "ok" | "conditions" | "high_risk"
        """
        if len(alerts_red) > 0:
            return "high_risk"
        elif len(alerts_yellow) > 0:
            return "conditions"
        else:
            return "ok"
    
    # ================================================================
    # PASO 4: GENERAR RAZONAMIENTO
    # ================================================================
    
    def _generate_reasoning(self,
                           protein: Protein,
                           comparison: ComparisonResult,
                           base_case: str,
                           compatibility: str,
                           confidence: str) -> str:
        """
        Genera explicación del razonamiento.
        
        Returns:
            String con explicación completa
        """
        reasoning_parts = []
        
        # Parte 1: Similitud
        best = comparison.best_candidate
        
        if base_case == "homolog_exists":
            if best:
                reasoning_parts.append(
                    f"Se encontró un gen homólogo en el genoma: {best.gene_name} "
                    f"({best.locus_tag}) con {best.identity:.1f}% de identidad y "
                    f"{best.coverage:.1f}% de cobertura."
                )
                
                if confidence == "borderline":
                    reasoning_parts.append(
                        f"Nota: La similitud está en zona borderline "
                        f"({config.BORDERLINE_IDENTITY_THRESHOLD}-{config.HOMOLOG_IDENTITY_THRESHOLD}% identidad). "
                        f"Se recomienda validación experimental."
                    )
            else:
                reasoning_parts.append(
                    "Se identificó similitud con genes del genoma."
                )
        else:
            if best:
                reasoning_parts.append(
                    f"El mejor candidato local ({best.gene_name}, {best.locus_tag}) "
                    f"muestra solo {best.identity:.1f}% de identidad y {best.coverage:.1f}% de cobertura, "
                    f"por debajo del umbral de homología ({config.HOMOLOG_IDENTITY_THRESHOLD}%/{config.HOMOLOG_COVERAGE_THRESHOLD}%). "
                    f"Se requiere introducción de gen externo."
                )
            else:
                reasoning_parts.append(
                    "No se encontraron genes homólogos en el genoma. "
                    "Se requiere introducción de gen externo."
                )
        
        # Parte 2: Compatibilidad
        if compatibility == "ok":
            reasoning_parts.append(
                "La proteína no presenta incompatibilidades conocidas con E. coli."
            )
        elif compatibility == "conditions":
            reasoning_parts.append(
                "La proteína presenta características que requieren atención especial "
                "para expresión funcional en E. coli."
            )
        else:  # high_risk
            reasoning_parts.append(
                "La proteína presenta incompatibilidades críticas con el sistema de expresión "
                "de E. coli. La expresión funcional puede no ser posible sin modificaciones significativas."
            )
        
        return " ".join(reasoning_parts)
    
    # ================================================================
    # PASO 5: DETERMINAR ESTRATEGIA
    # ================================================================
    
    def _determine_strategy(self, base_case: str, compatibility: str) -> str:
        """
        Determina la estrategia recomendada.
        
        Returns:
            "use_local" | "modify_local" | "introduce_external"
        """
        if base_case == "homolog_exists":
            if compatibility == "ok":
                return "use_local"
            else:
                return "modify_local"
        else:
            return "introduce_external"
    
    # ================================================================
    # PASO 6: GENERAR RECOMENDACIONES
    # ================================================================
    
    def _generate_recommendations(self,
                                 protein: Protein,
                                 base_case: str,
                                 compatibility: str,
                                 alerts_red: List[Alert],
                                 alerts_yellow: List[Alert]) -> List[str]:
        """
        Genera recomendaciones específicas.
        
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        # Recomendaciones basadas en base_case
        if base_case == "homolog_exists":
            recommendations.append(
                "Validar experimentalmente la función del gen homólogo local"
            )
            recommendations.append(
                "Considerar optimización de expresión mediante ingeniería de promotores"
            )
        else:
            recommendations.append(
                "Diseñar casete de expresión con gen externo optimizado"
            )
            recommendations.append(
                "Considerar optimización de codones para E. coli"
            )
        
        # Recomendaciones basadas en alertas RED
        for alert in alerts_red:
            if alert.type == 'glycosylation':
                recommendations.append(
                    "Crítico: Expresar en sistema eucariota (levadura, células de mamífero) "
                    "o considerar producción en E. coli de forma inactiva seguida de plegamiento in vitro"
                )
            
            elif alert.type == 'transmembrane':
                recommendations.append(
                    "Crítico: Evaluar expresión en cuerpos de inclusión y replegamiento, "
                    "o usar sistemas especializados para proteínas de membrana"
                )
            
            elif alert.type == 'protease':
                recommendations.append(
                    "Crítico: Usar cepas deficientes en proteasas y expresión regulada (inducible)"
                )
            
            elif alert.type == 'toxin':
                recommendations.append(
                    "Crítico: Evaluar riesgos de toxicidad. Considerar expresión condicional "
                    "o producción de variantes inactivadas"
                )
        
        # Recomendaciones basadas en alertas YELLOW
        for alert in alerts_yellow:
            if alert.type == 'signal_peptide':
                recommendations.append(
                    "Expresar con péptido señal compatible (pelB, ompA) para secreción al periplasma"
                )
            
            elif alert.type == 'disulfide_bonds':
                recommendations.append(
                    "Expresar en periplasma (ambiente oxidante) o usar cepas con citoplasma oxidante (Origami, SHuffle)"
                )
            
            elif alert.type == 'metal_binding':
                metals_str = ', '.join(protein.metal_binding)
                recommendations.append(
                    f"Suplementar medio de cultivo con: {metals_str}"
                )
            
            elif alert.type == 'cofactor_required':
                recommendations.append(
                    "Verificar capacidad de biosíntesis de cofactores en E. coli "
                    "o suplementar medio de cultivo"
                )
        
        # Recomendación general de validación
        if compatibility != "ok":
            recommendations.append(
                "Realizar pruebas de expresión a pequeña escala antes de escalar producción"
            )
        
        return recommendations
    
    # ================================================================
    # PASO 7: FORMATEAR MEJOR CANDIDATO
    # ================================================================
    
    def _format_best_candidate(self, 
                              candidate: Optional[AlignmentCandidate]) -> Optional[Dict[str, Any]]:
        """
        Formatea el mejor candidato para la propuesta.
        
        Returns:
            Dict con info del candidato o None
        """
        if not candidate:
            return None
        
        return {
            'gene_id': candidate.gene_id,
            'locus_tag': candidate.locus_tag,
            'gene_name': candidate.gene_name,
            'product': candidate.product,
            'identity': round(candidate.identity, 2),
            'coverage': round(candidate.coverage, 2),
            'score': round(candidate.score, 2),
            'note': self._get_candidate_note(candidate)
        }
    
    def _get_candidate_note(self, candidate: AlignmentCandidate) -> str:
        """Genera nota explicativa sobre el candidato."""
        if candidate.identity >= config.HOMOLOG_IDENTITY_THRESHOLD:
            return "Homólogo cercano - alta similitud"
        elif candidate.identity >= config.BORDERLINE_IDENTITY_THRESHOLD:
            return "Similitud moderada - zona borderline"
        else:
            return "Baja similitud - no es homólogo útil"


# ================================================================
# INSTANCIA GLOBAL (Singleton)
# ================================================================

_decision_engine_instance = None

def get_decision_engine() -> DecisionEngine:
    """
    Obtiene la instancia singleton del motor de decisiones.
    
    Returns:
        DecisionEngine instance
    """
    global _decision_engine_instance
    
    if _decision_engine_instance is None:
        _decision_engine_instance = DecisionEngine()
    
    return _decision_engine_instance


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    print("=== Test Decision Engine ===\n")
    
    # Este test requiere proteína y comparación reales
    # Ver protein_comparison.py para ejemplo completo
    
    print("Para probar el decision engine, ejecutar:")
    print("  python services/protein_comparison.py")
    print("\nEl motor de decisiones se usa automáticamente en ese flujo.")