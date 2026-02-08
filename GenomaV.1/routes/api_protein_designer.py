"""
API Protein Designer Blueprint - Endpoints del módulo de diseño genético
Expone el sistema completo de diseño genético in-silico.

Endpoints principales:
- POST /search: Buscar proteínas en UniProt
- POST /analyze: Análisis completo (comparación + decisión + optimización)
- POST /optimize-codons: Optimización de codones standalone
"""

from flask import Blueprint, jsonify, request
from services.uniprot_service import get_uniprot_service
from services.ncbi_service import get_ncbi_service
from services.genome_analysis import get_analysis_service
from services.protein_comparison import get_comparison_service
from services.decision_engine import get_decision_engine
from services.codon_optimizer import get_optimizer_service

bp = Blueprint('protein_designer', __name__)

# Servicios
uniprot_service = get_uniprot_service()
ncbi_service = get_ncbi_service()
analysis_service = get_analysis_service()
comparison_service = get_comparison_service()
decision_engine = get_decision_engine()
optimizer_service = get_optimizer_service()


@bp.route('/search', methods=['POST'])
def search_proteins():
    """
    Busca proteínas en UniProt.
    
    Body:
        {
            "query": "insulin",
            "organism": "Homo sapiens" (opcional),
            "reviewed": true (opcional),
            "limit": 10 (opcional)
        }
    
    Returns:
        {
            "results": [
                {
                    "accession": "P01308",
                    "name": "Insulin",
                    "organism": "Homo sapiens",
                    "length": 110,
                    "reviewed": true,
                    ...
                }
            ],
            "total": 10
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing required parameter: query"
            }), 400
        
        query = data['query']
        organism = data.get('organism', None)
        reviewed = data.get('reviewed', None)
        limit = data.get('limit', 10)
        
        # Buscar en UniProt
        results = uniprot_service.search_proteins(
            query=query,
            organism=organism,
            reviewed=reviewed,
            limit=limit
        )
        
        return jsonify({
            "results": results,
            "total": len(results)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/analyze', methods=['POST'])
def analyze_protein():
    """
    Análisis completo de diseño genético in-silico.
    
    Este es el endpoint PRINCIPAL del módulo. Realiza:
    1. Descarga de proteína desde UniProt
    2. Construcción del proteoma del genoma
    3. Comparación proteína vs proteoma
    4. Evaluación de compatibilidad (alertas)
    5. Generación de propuesta de diseño
    6. Optimización de codones (si aplica)
    
    Body:
        {
            "protein_id": "P01308",  // UniProt accession
            "genome_id": "NC_000913.3",  // GenBank accession (default: K-12)
            "include_optimization": true  // Si incluir optimización de codones
        }
    
    Returns:
        {
            "target_protein": {...},
            "genome_analysis": {...},
            "decision": {
                "base_case": "requires_external_gene",
                "compatibility": "conditions",
                "confidence": "high",
                "reasoning": "...",
                "is_recommended": true
            },
            "alerts": {
                "red": [...],
                "yellow": [...],
                "summary": "..."
            },
            "strategy": "introduce_external",
            "recommendations": [...],
            "best_local_candidate": {...},
            "codon_optimization": {...}  // Si include_optimization=true
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'protein_id' not in data:
            return jsonify({
                "error": "Missing required parameter: protein_id"
            }), 400
        
        protein_id = data['protein_id']
        genome_id = data.get('genome_id', 'NC_000913.3')
        include_optimization = data.get('include_optimization', True)
        
        print(f"\n{'='*60}")
        print(f"🔬 ANÁLISIS DE DISEÑO GENÉTICO IN-SILICO")
        print(f"{'='*60}")
        print(f"Proteína: {protein_id}")
        print(f"Genoma: {genome_id}")
        print(f"{'='*60}\n")
        
        # PASO 1: Descargar proteína objetivo
        print(f"📥 PASO 1: Descargando proteína {protein_id}...")
        target_protein = uniprot_service.fetch_protein(protein_id)
        
        if not target_protein:
            return jsonify({
                "error": f"Failed to fetch protein {protein_id} from UniProt"
            }), 404
        
        print(f"✓ Proteína: {target_protein.name}")
        print(f"  Organismo: {target_protein.organism}")
        print(f"  Longitud: {target_protein.length} aa")
        print(f"  Complejidad: {target_protein.get_complexity_score()}/100")
        
        # PASO 2: Descargar genoma y construir proteoma
        print(f"\n🧬 PASO 2: Preparando genoma {genome_id}...")
        record = ncbi_service.fetch_genome(genome_id)
        
        if not record:
            return jsonify({
                "error": f"Failed to fetch genome {genome_id}"
            }), 500
        
        print(f"✓ Genoma descargado: {len(record.seq):,} bp")
        
        # Extraer genes
        print(f"   Extrayendo genes...")
        genes = analysis_service.extract_genes_from_record(record, genome_id)
        print(f"✓ Proteoma construido: {len(genes)} genes")
        
        # PASO 3: Comparación proteína vs proteoma
        print(f"\n🔍 PASO 3: Comparando proteína contra proteoma...")
        comparison_result = comparison_service.compare_protein_vs_proteome(
            target_protein,
            genes,
            genome_id
        )
        
        # PASO 4: Tomar decisión
        print(f"\n🧠 PASO 4: Evaluando compatibilidad y generando propuesta...")
        proposal = decision_engine.make_decision(
            target_protein,
            comparison_result,
            genome_id
        )
        
        # PASO 5: Optimización de codones (si se requiere)
        optimization_result = None
        
        if include_optimization and proposal.base_case == "requires_external_gene":
            print(f"\n🧬 PASO 5: Optimizando codones para expresión...")
            
            try:
                optimization_result = optimizer_service.optimize_sequence(
                    target_protein.sequence,
                    genome_id=genome_id
                )
                
                # Agregar a la propuesta
                proposal.codon_optimization = optimization_result
                
            except Exception as e:
                print(f"⚠️ Error en optimización: {e}")
        
        # PASO 6: Preparar respuesta
        print(f"\n📊 PASO 6: Generando reporte final...")
        
        response = proposal.to_dict(include_optimization_details=True)
        
        # Agregar info de proteína objetivo
        response['target_protein'] = target_protein.to_dict(include_sequence=False)
        
        # Agregar resumen de comparación
        response['genome_analysis'] = {
            'genome_id': genome_id,
            'proteome_size': comparison_result.proteome_size,
            'candidates_found': comparison_result.total_matches,
            'computation_time': round(comparison_result.computation_time, 2)
        }
        
        # Agregar top candidatos
        if comparison_result.candidates:
            top_5 = [c.to_dict() for c in comparison_result.get_top_candidates(5)]
            response['top_candidates'] = top_5
        
        print(f"\n{'='*60}")
        print(f"✓ ANÁLISIS COMPLETADO")
        print(f"{'='*60}")
        print(f"Base case: {proposal.base_case}")
        print(f"Compatibility: {proposal.compatibility}")
        print(f"Recommended: {'✓ Sí' if proposal.is_recommended() else '✗ No'}")
        print(f"{'='*60}\n")
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}\n")
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/optimize-codons', methods=['POST'])
def optimize_codons():
    """
    Optimización de codones standalone.
    
    Body:
        {
            "protein_sequence": "MALK...",  // Secuencia de aminoácidos
            "genome_id": "NC_000913.3"  // Genoma de referencia (opcional)
        }
    
    Returns:
        {
            "original": {
                "sequence": "ATG...",
                "length": 330,
                "gc": 52.3,
                "gc3": 61.2,
                "rare_codons_pct": 15.4
            },
            "optimized": {
                "sequence": "ATG...",
                "length": 330,
                "gc": 50.8,
                "gc3": 53.1,
                "rare_codons_pct": 3.2
            },
            "changes": 45,
            "metrics": {
                "rscu_distance": 0.234,
                "codon_usage_similarity": 0.87,
                "improvement_score": 85.3
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'protein_sequence' not in data:
            return jsonify({
                "error": "Missing required parameter: protein_sequence"
            }), 400
        
        protein_sequence = data['protein_sequence'].strip()
        genome_id = data.get('genome_id', None)
        
        # Validar secuencia
        from utils.sequence_utils import is_valid_protein, clean_sequence
        
        protein_sequence = clean_sequence(protein_sequence, 'protein')
        
        if not is_valid_protein(protein_sequence):
            return jsonify({
                "error": "Invalid protein sequence. Only standard amino acids allowed."
            }), 400
        
        # Optimizar
        result = optimizer_service.optimize_sequence(
            protein_sequence,
            genome_id=genome_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/protein/<accession>', methods=['GET'])
def get_protein_details(accession):
    """
    Obtiene detalles completos de una proteína de UniProt.
    
    Args:
        accession: UniProt accession
    
    Returns:
        {
            "accession": "P01308",
            "name": "Insulin",
            "organism": "Homo sapiens",
            "sequence": "MALW...",
            "length": 110,
            "reviewed": true,
            "function": "...",
            "subcellular_location": [...],
            "has_signal_peptide": true,
            "transmembrane_count": 0,
            "complexity_score": 35,
            ...
        }
    """
    try:
        protein = uniprot_service.fetch_protein(accession)
        
        if not protein:
            return jsonify({
                "error": f"Protein {accession} not found"
            }), 404
        
        return jsonify(protein.to_dict(include_sequence=True))
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/quick-check', methods=['POST'])
def quick_compatibility_check():
    """
    Chequeo rápido de compatibilidad (sin comparación completa).
    
    Útil para evaluar rápidamente si una proteína es compatible
    con E. coli antes de hacer el análisis completo.
    
    Body:
        {
            "protein_id": "P01308"
        }
    
    Returns:
        {
            "protein": {...},
            "compatibility": "conditions",
            "alerts": {
                "red": [...],
                "yellow": [...]
            },
            "complexity_score": 35,
            "recommended": true
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'protein_id' not in data:
            return jsonify({
                "error": "Missing required parameter: protein_id"
            }), 400
        
        protein_id = data['protein_id']
        
        # Descargar proteína
        protein = uniprot_service.fetch_protein(protein_id)
        
        if not protein:
            return jsonify({
                "error": f"Protein {protein_id} not found"
            }), 404
        
        # Evaluar solo compatibilidad (sin comparación)
        alerts_red, alerts_yellow = decision_engine._assess_compatibility(protein)
        compatibility = decision_engine._determine_compatibility_level(alerts_red, alerts_yellow)
        
        return jsonify({
            "protein": protein.to_dict(include_sequence=False),
            "compatibility": compatibility,
            "alerts": {
                "red": [a.to_dict() for a in alerts_red],
                "yellow": [a.to_dict() for a in alerts_yellow],
                "summary": f"{len(alerts_red)} RED, {len(alerts_yellow)} YELLOW"
            },
            "complexity_score": protein.get_complexity_score(),
            "recommended": compatibility != "high_risk",
            "features": {
                "is_membrane_protein": protein.is_membrane_protein(),
                "is_secreted": protein.is_secreted(),
                "requires_ptms": protein.requires_ptms(),
                "requires_cofactors": protein.requires_cofactors()
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/batch-analyze', methods=['POST'])
def batch_analyze():
    """
    Análisis en batch de múltiples proteínas.
    
    Útil para evaluar varias proteínas candidatas a la vez.
    
    Body:
        {
            "protein_ids": ["P01308", "P12345", "P67890"],
            "genome_id": "NC_000913.3",
            "quick_mode": true  // Solo quick check, no comparación completa
        }
    
    Returns:
        {
            "results": [
                {
                    "protein_id": "P01308",
                    "status": "success",
                    "compatibility": "conditions",
                    "recommended": true,
                    ...
                },
                ...
            ],
            "total": 3,
            "successful": 2,
            "failed": 1
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'protein_ids' not in data:
            return jsonify({
                "error": "Missing required parameter: protein_ids"
            }), 400
        
        protein_ids = data['protein_ids']
        genome_id = data.get('genome_id', 'NC_000913.3')
        quick_mode = data.get('quick_mode', True)
        
        if not isinstance(protein_ids, list) or len(protein_ids) == 0:
            return jsonify({
                "error": "protein_ids must be a non-empty list"
            }), 400
        
        if len(protein_ids) > 20:
            return jsonify({
                "error": "Maximum 20 proteins per batch"
            }), 400
        
        results = []
        successful = 0
        failed = 0
        
        for protein_id in protein_ids:
            try:
                # Descargar proteína
                protein = uniprot_service.fetch_protein(protein_id)
                
                if not protein:
                    results.append({
                        "protein_id": protein_id,
                        "status": "not_found",
                        "error": "Protein not found in UniProt"
                    })
                    failed += 1
                    continue
                
                # Quick check
                alerts_red, alerts_yellow = decision_engine._assess_compatibility(protein)
                compatibility = decision_engine._determine_compatibility_level(alerts_red, alerts_yellow)
                
                result = {
                    "protein_id": protein_id,
                    "status": "success",
                    "name": protein.name,
                    "organism": protein.organism,
                    "length": protein.length,
                    "compatibility": compatibility,
                    "alerts_count": {
                        "red": len(alerts_red),
                        "yellow": len(alerts_yellow)
                    },
                    "complexity_score": protein.get_complexity_score(),
                    "recommended": compatibility != "high_risk"
                }
                
                results.append(result)
                successful += 1
                
            except Exception as e:
                results.append({
                    "protein_id": protein_id,
                    "status": "error",
                    "error": str(e)
                })
                failed += 1
        
        return jsonify({
            "results": results,
            "total": len(protein_ids),
            "successful": successful,
            "failed": failed
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500