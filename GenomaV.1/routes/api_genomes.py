"""
API Genomes Blueprint - Endpoints para manejo de genomas
Rutas refactorizadas usando los servicios modulares.
"""

from flask import Blueprint, jsonify, request
from services.ncbi_service import get_ncbi_service
from services.genome_analysis import get_analysis_service
from models.genome import create_genome_from_seqrecord

bp = Blueprint('genomes', __name__)

# Servicios
ncbi_service = get_ncbi_service()
analysis_service = get_analysis_service()


@bp.route('/genomes', methods=['GET'])
def list_genomes():
    """
    Lista todos los genomas disponibles de E. coli.
    
    Query params:
        - refresh: true/false - Forzar búsqueda en NCBI
    
    Returns:
        {
            "genomes": [
                {"name": "K-12 MG1655", "id": "NC_000913.3"},
                ...
            ],
            "total": 10
        }
    """
    try:
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Obtener genomas
        if force_refresh:
            genomes_dict = ncbi_service.search_ecoli_genomes()
        else:
            genomes_dict = ncbi_service.get_available_genomes()
        
        # Formatear respuesta
        genomes_list = [
            {"name": name, "id": acc_id}
            for name, acc_id in genomes_dict.items()
        ]
        
        return jsonify({
            "genomes": genomes_list,
            "total": len(genomes_list)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/genomes/<genome_id>', methods=['GET'])
def get_genome_info(genome_id):
    """
    Obtiene información básica de un genoma.
    
    Args:
        genome_id: GenBank accession (ej: NC_000913.3)
    
    Returns:
        {
            "accession": "NC_000913.3",
            "title": "...",
            "organism": "Escherichia coli...",
            "length": 4641652,
            ...
        }
    """
    try:
        info = ncbi_service.get_genome_info(genome_id)
        
        if not info:
            return jsonify({"error": "Genome not found"}), 404
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/genomes/<genome_id>/stats', methods=['GET'])
def get_genome_stats(genome_id):
    """
    Obtiene estadísticas completas de un genoma.
    
    Args:
        genome_id: GenBank accession
    
    Query params:
        - refresh: true/false - Forzar recálculo (ignora cache)
    
    Returns:
        {
            "genome": {...},
            "genes": {...},
            "compactness": {...},
            "codon_analysis": {...},
            "validation": {...}
        }
    """
    try:
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Descargar genoma
        record = ncbi_service.fetch_genome(genome_id, force_refresh)
        if not record:
            return jsonify({"error": "Failed to download genome"}), 500
        
        # Crear objeto Genome
        genome = create_genome_from_seqrecord(record, genome_id)
        
        # Extraer genes (con cache)
        genes = analysis_service.extract_genes_from_record(record, genome_id)
        genome.genes = genes
        genome.gene_count = len(genes)
        genome._calculate_compactness()
        
        # Análisis de codones
        codon_analysis = analysis_service.analyze_codon_usage(record, genome_id)
        
        # Análisis de genoma completo
        triplets_genome = analysis_service.analyze_triplets_genome_wide(
            str(record.seq).upper(), 
            genome_id
        )
        
        # Validación con literatura
        validation = analysis_service.validate_with_literature(genome, codon_analysis)
        
        # Espacios intergénicos
        intergenic_spaces = analysis_service.analyze_intergenic_spaces(genome, top_n=10)
        
        # Respuesta completa
        return jsonify({
            "genome": {
                "accession": genome.accession,
                "organism": genome.organism,
                "length": genome.length,
                "gc_content": round(genome.gc_content, 2),
                "gene_count": genome.gene_count
            },
            "genes": {
                "total": genome.gene_count,
                "valid": codon_analysis['statistics']['valid_cds'],
                "problematic": codon_analysis['statistics']['problematic_cds'],
                "largest": genes[0].to_dict() if genes else None,
                "smallest": genes[-1].to_dict() if genes else None
            },
            "compactness": {
                "coding_length": genome.coding_length,
                "coding_percentage": round(genome.coding_percentage, 2),
                "non_coding_length": genome.length - genome.coding_length,
                "gene_density": round(genome.gene_density, 1)
            },
            "codon_analysis": {
                "cds": {
                    "start_codons": codon_analysis['start_codons'],
                    "stop_codons": codon_analysis['stop_codons'],
                    "gc_position": codon_analysis['gc_position'],
                    "total_codons": codon_analysis['total_count']
                },
                "genome_wide": {
                    "ATG": triplets_genome['total'].get('ATG', 0),
                    "GTG": triplets_genome['total'].get('GTG', 0),
                    "TTG": triplets_genome['total'].get('TTG', 0),
                    "TAA": triplets_genome['total'].get('TAA', 0),
                    "TAG": triplets_genome['total'].get('TAG', 0),
                    "TGA": triplets_genome['total'].get('TGA', 0)
                }
            },
            "validation": validation,
            "intergenic_spaces": intergenic_spaces
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/genomes/compare', methods=['POST'])
def compare_genomes():
    """
    Compara dos genomas de E. coli.
    
    Body:
        {
            "genome1": "NC_000913.3",
            "genome2": "NC_007779.1"
        }
    
    Returns:
        {
            "genome1": {...},
            "genome2": {...},
            "differences": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'genome1' not in data or 'genome2' not in data:
            return jsonify({
                "error": "Missing parameters",
                "required": ["genome1", "genome2"]
            }), 400
        
        genome1_id = data['genome1']
        genome2_id = data['genome2']
        
        # Descargar ambos genomas
        record1 = ncbi_service.fetch_genome(genome1_id)
        record2 = ncbi_service.fetch_genome(genome2_id)
        
        if not record1 or not record2:
            return jsonify({"error": "Failed to download one or both genomes"}), 500
        
        # Crear objetos Genome
        genome1 = create_genome_from_seqrecord(record1, genome1_id)
        genome2 = create_genome_from_seqrecord(record2, genome2_id)
        
        # Análisis de ambos
        analysis1 = analysis_service.analyze_codon_usage(record1, genome1_id)
        analysis2 = analysis_service.analyze_codon_usage(record2, genome2_id)
        
        # Comparar start codons
        start_diff = {}
        for codon in ["ATG", "GTG", "TTG", "OTROS"]:
            count1 = analysis1['start_codons'].get(codon, 0)
            count2 = analysis2['start_codons'].get(codon, 0)
            start_diff[codon] = {
                "genome1": count1,
                "genome2": count2,
                "difference": count2 - count1
            }
        
        # Comparar stop codons
        stop_diff = {}
        for codon in ["TAA", "TAG", "TGA"]:
            count1 = analysis1['stop_codons'].get(codon, 0)
            count2 = analysis2['stop_codons'].get(codon, 0)
            stop_diff[codon] = {
                "genome1": count1,
                "genome2": count2,
                "difference": count2 - count1
            }
        
        # Comparar GC por posición
        gc_diff = {}
        for pos in ["GC1", "GC2", "GC3"]:
            gc1 = analysis1['gc_position'][pos]
            gc2 = analysis2['gc_position'][pos]
            gc_diff[pos] = {
                "genome1": round(gc1, 2),
                "genome2": round(gc2, 2),
                "difference": round(gc2 - gc1, 2)
            }
        
        # Respuesta
        return jsonify({
            "genome1": {
                "id": genome1_id,
                "organism": genome1.organism,
                "length": genome1.length,
                "gene_count": genome1.gene_count,
                "gc_content": round(genome1.gc_content, 2),
                "coding_percentage": round(genome1.coding_percentage, 2)
            },
            "genome2": {
                "id": genome2_id,
                "organism": genome2.organism,
                "length": genome2.length,
                "gene_count": genome2.gene_count,
                "gc_content": round(genome2.gc_content, 2),
                "coding_percentage": round(genome2.coding_percentage, 2)
            },
            "differences": {
                "length": abs(genome2.length - genome1.length),
                "gene_count": abs(genome2.gene_count - genome1.gene_count),
                "gc_content": abs(genome2.gc_content - genome1.gc_content),
                "start_codons": start_diff,
                "stop_codons": stop_diff,
                "gc_position": gc_diff
            },
            "summary": {
                "similar": abs(genome2.gc_content - genome1.gc_content) < 2.0,
                "gene_difference_pct": abs(genome2.gene_count - genome1.gene_count) / genome1.gene_count * 100
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/genomes/<genome_id>/download', methods=['GET'])
def download_genome(genome_id):
    """
    Descarga un genoma (fuerza refresh del cache).
    
    Args:
        genome_id: GenBank accession
    
    Returns:
        {"message": "Genome downloaded", "accession": "..."}
    """
    try:
        record = ncbi_service.fetch_genome(genome_id, force_refresh=True)
        
        if not record:
            return jsonify({"error": "Failed to download genome"}), 500
        
        return jsonify({
            "message": "Genome downloaded successfully",
            "accession": genome_id,
            "length": len(record.seq),
            "features": len(record.features)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500