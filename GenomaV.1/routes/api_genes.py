"""
API Genes Blueprint - Endpoints para consulta de genes
Incluye paginación, búsqueda y filtros.
"""

from flask import Blueprint, jsonify, request
from services.ncbi_service import get_ncbi_service
from services.genome_analysis import get_analysis_service
from models.genome import create_genome_from_seqrecord
from Bio.Data import CodonTable

bp = Blueprint('genes', __name__)

# Servicios
ncbi_service = get_ncbi_service()
analysis_service = get_analysis_service()


@bp.route('/genes', methods=['GET'])
def list_genes():
    """
    Lista genes de un genoma con paginación y filtros.
    
    Query params:
        - genome: ID del genoma (default: NC_000913.3)
        - page: Número de página (default: 1)
        - limit: Genes por página (default: 50, max: 1000)
        - search: Búsqueda por nombre/producto
        - min_len: Longitud mínima
        - max_len: Longitud máxima
        - sort: Campo de ordenamiento (length, gc, name)
        - order: asc/desc (default: desc)
    
    Returns:
        {
            "genes": [...],
            "total": 4321,
            "page": 1,
            "limit": 50,
            "total_pages": 87
        }
    """
    try:
        # Parámetros
        genome_id = request.args.get('genome', 'NC_000913.3')
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 1000)
        search = request.args.get('search', '').lower()
        min_len = request.args.get('min_len', type=int)
        max_len = request.args.get('max_len', type=int)
        sort_by = request.args.get('sort', 'length')
        order = request.args.get('order', 'desc')
        
        # Descargar genoma
        record = ncbi_service.fetch_genome(genome_id)
        if not record:
            return jsonify({"error": "Failed to download genome"}), 500
        
        # Extraer genes
        genes = analysis_service.extract_genes_from_record(record, genome_id)
        
        # Filtrar por búsqueda
        if search:
            genes = [
                g for g in genes
                if search in g.gene.lower() or search in g.product.lower() or search in g.locus_tag.lower()
            ]
        
        # Filtrar por longitud
        if min_len is not None:
            genes = [g for g in genes if g.length >= min_len]
        
        if max_len is not None:
            genes = [g for g in genes if g.length <= max_len]
        
        # Ordenar
        reverse = (order == 'desc')
        if sort_by == 'length':
            genes = sorted(genes, key=lambda g: g.length, reverse=reverse)
        elif sort_by == 'gc':
            genes = sorted(genes, key=lambda g: g.gc_content, reverse=reverse)
        elif sort_by == 'name':
            genes = sorted(genes, key=lambda g: g.gene.lower(), reverse=reverse)
        
        # Paginación
        total = len(genes)
        total_pages = (total + limit - 1) // limit
        start = (page - 1) * limit
        end = start + limit
        genes_page = genes[start:end]
        
        # Convertir a dict
        genes_data = [g.to_dict() for g in genes_page]
        
        return jsonify({
            "genes": genes_data,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/genes/<gene_id>', methods=['GET'])
def get_gene_detail(gene_id):
    """
    Obtiene detalles completos de un gen específico.
    
    Args:
        gene_id: ID estable (locus_tag, protein_id, o gene)
    
    Query params:
        - genome: ID del genoma (default: NC_000913.3)
    
    Returns:
        {
            "gene": {...},
            "sequence": "ATGCGA...",
            "protein_sequence": "MFKL...",
            "codon_analysis": {...},
            "rscu": {...}
        }
    """
    try:
        genome_id = request.args.get('genome', 'NC_000913.3')
        
        # Descargar genoma
        record = ncbi_service.fetch_genome(genome_id)
        if not record:
            return jsonify({"error": "Failed to download genome"}), 500
        
        # Buscar el feature específico
        gene_feature = None
        for feature in record.features:
            if feature.type == "CDS":
                locus_tag = feature.qualifiers.get("locus_tag", [None])[0]
                protein_id = feature.qualifiers.get("protein_id", [None])[0]
                gene_name = feature.qualifiers.get("gene", [None])[0]
                
                if gene_id in [locus_tag, protein_id, gene_name]:
                    gene_feature = feature
                    break
        
        if not gene_feature:
            return jsonify({"error": "Gene not found"}), 404
        
        # Extraer CDS correctamente
        cds_info = analysis_service._extract_cds_correctly(gene_feature, record)
        sequence = cds_info['sequence']
        
        # Dividir en codones
        codons = [sequence[i:i+3] for i in range(0, len(sequence), 3) 
                 if len(sequence[i:i+3]) == 3]
        
        from collections import Counter
        codon_counter = Counter(codons)
        
        # Traducir proteína usando tabla correcta
        transl_table = cds_info['transl_table']
        tabla = CodonTable.unambiguous_dna_by_id[transl_table]
        
        protein = ""
        for codon in codons:
            if codon in tabla.forward_table:
                protein += tabla.forward_table[codon]
            elif codon in tabla.stop_codons:
                protein += "*"
            else:
                protein += "X"
        
        # RSCU para este gen
        rscu = analysis_service.calculate_rscu(dict(codon_counter))
        
        # GC por posición
        gc_position = analysis_service.calculate_gc_by_position(codons)
        
        # Info del gen
        q = gene_feature.qualifiers
        gene_info = {
            "id": gene_id,
            "locus_tag": q.get("locus_tag", ["-"])[0],
            "gene": q.get("gene", ["-"])[0],
            "product": q.get("product", ["Unknown"])[0],
            "protein_id": q.get("protein_id", ["-"])[0],
            "length": len(sequence),
            "start": int(gene_feature.location.start),
            "end": int(gene_feature.location.end),
            "strand": gene_feature.location.strand,
            "codon_start": cds_info['codon_start'],
            "transl_table": cds_info['transl_table']
        }
        
        return jsonify({
            "gene": gene_info,
            "sequence": sequence,
            "protein_sequence": protein,
            "protein_length": len(protein),
            "codon_analysis": {
                "total_codons": len(codons),
                "unique_codons": len(codon_counter),
                "most_common": dict(codon_counter.most_common(10)),
                "gc_position": gc_position
            },
            "rscu": {
                "top_10": dict(sorted(rscu.items(), key=lambda x: x[1], reverse=True)[:10]),
                "bottom_10": dict(sorted(rscu.items(), key=lambda x: x[1])[:10])
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/genes/search', methods=['POST'])
def search_genes():
    """
    Búsqueda avanzada de genes.
    
    Body:
        {
            "genome": "NC_000913.3",
            "query": "lac",
            "filters": {
                "min_length": 1000,
                "max_length": 5000,
                "min_gc": 40,
                "max_gc": 60,
                "has_issues": false
            }
        }
    
    Returns:
        {
            "matches": [...],
            "total": 10
        }
    """
    try:
        data = request.get_json()
        
        genome_id = data.get('genome', 'NC_000913.3')
        query = data.get('query', '').lower()
        filters = data.get('filters', {})
        
        # Descargar genoma
        record = ncbi_service.fetch_genome(genome_id)
        if not record:
            return jsonify({"error": "Failed to download genome"}), 500
        
        # Extraer genes
        genes = analysis_service.extract_genes_from_record(record, genome_id)
        
        # Aplicar query
        if query:
            genes = [
                g for g in genes
                if query in g.gene.lower() or query in g.product.lower() or query in g.locus_tag.lower()
            ]
        
        # Aplicar filtros
        if 'min_length' in filters:
            genes = [g for g in genes if g.length >= filters['min_length']]
        
        if 'max_length' in filters:
            genes = [g for g in genes if g.length <= filters['max_length']]
        
        if 'min_gc' in filters:
            genes = [g for g in genes if g.gc_content >= filters['min_gc']]
        
        if 'max_gc' in filters:
            genes = [g for g in genes if g.gc_content <= filters['max_gc']]
        
        if 'has_issues' in filters:
            genes = [g for g in genes if g.has_issues == filters['has_issues']]
        
        return jsonify({
            "matches": [g.to_dict() for g in genes],
            "total": len(genes)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc() if request.args.get('debug') else None
        }), 500


@bp.route('/genes/<gene_id>/export', methods=['GET'])
def export_gene(gene_id):
    """
    Exporta un gen en formato FASTA.
    
    Args:
        gene_id: ID del gen
    
    Query params:
        - genome: ID del genoma
        - format: dna/protein (default: dna)
    
    Returns:
        Archivo FASTA
    """
    try:
        genome_id = request.args.get('genome', 'NC_000913.3')
        export_format = request.args.get('format', 'dna')
        
        # Descargar genoma
        record = ncbi_service.fetch_genome(genome_id)
        if not record:
            return jsonify({"error": "Failed to download genome"}), 500
        
        # Buscar gene
        from models.gene import create_gene_from_feature
        
        for idx, feature in enumerate(record.features):
            if feature.type == "CDS":
                gene = create_gene_from_feature(feature, record.seq, idx)
                
                if gene.id == gene_id or gene.locus_tag == gene_id:
                    if export_format == 'protein':
                        # Traducir si no está traducida
                        if not gene.protein_sequence:
                            # Traducir aquí
                            pass
                        fasta = gene.to_protein_fasta()
                    else:
                        fasta = gene.to_fasta()
                    
                    return fasta, 200, {'Content-Type': 'text/plain'}
        
        return jsonify({"error": "Gene not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500