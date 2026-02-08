"""
Genome Model - Estructura de datos para genomas
Representa un genoma completo con sus propiedades y genes.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from models.gene import Gene


@dataclass
class Genome:
    """
    Representa un genoma completo con sus propiedades.
    
    Attributes:
        accession: GenBank accession (ej: NC_000913.3)
        organism: Nombre del organismo
        strain: Cepa específica
        sequence: Secuencia completa del genoma
        length: Longitud en pares de bases
        gc_content: Contenido GC global (%)
        genes: Lista de genes (CDS) del genoma
        gene_count: Número total de genes
        coding_length: Longitud total de regiones codificantes
        coding_percentage: Porcentaje del genoma que codifica
        gene_density: Genes por megabase
        description: Descripción del genoma
        fetched_at: Timestamp de descarga
        metadata: Metadatos adicionales
    """
    
    # Identificación
    accession: str
    organism: str = "Unknown"
    strain: str = "Unknown"
    
    # Secuencia
    sequence: str = ""
    length: int = 0
    
    # Propiedades globales
    gc_content: float = 0.0
    
    # Genes
    genes: List[Gene] = field(default_factory=list)
    gene_count: int = 0
    
    # Compactación
    coding_length: int = 0
    coding_percentage: float = 0.0
    gene_density: float = 0.0  # genes/Mb
    
    # Adicional
    description: str = ""
    fetched_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Cálculos automáticos después de inicialización."""
        # Calcular longitud si no está definida
        if self.length == 0 and self.sequence:
            self.length = len(self.sequence)
        
        # Calcular GC global si no está definido
        if self.gc_content == 0.0 and self.sequence:
            self.gc_content = self._calculate_gc()
        
        # Contar genes si hay lista
        if self.gene_count == 0 and self.genes:
            self.gene_count = len(self.genes)
        
        # Calcular métricas de compactación
        if self.genes and self.length > 0:
            self._calculate_compactness()
    
    def _calculate_gc(self) -> float:
        """Calcula el contenido GC del genoma completo."""
        if not self.sequence:
            return 0.0
        
        seq_upper = self.sequence.upper()
        g = seq_upper.count('G')
        c = seq_upper.count('C')
        
        return (g + c) / len(self.sequence) * 100 if len(self.sequence) > 0 else 0.0
    
    def _calculate_compactness(self):
        """Calcula métricas de compactación génica."""
        if not self.genes or self.length == 0:
            return
        
        # Longitud codificante total
        self.coding_length = sum(gene.length for gene in self.genes)
        
        # Porcentaje codificante
        self.coding_percentage = (self.coding_length / self.length) * 100
        
        # Densidad génica (genes por megabase)
        self.gene_density = self.gene_count / (self.length / 1_000_000)
    
    def add_gene(self, gene: Gene):
        """
        Añade un gen al genoma.
        
        Args:
            gene: Gene object
        """
        self.genes.append(gene)
        self.gene_count = len(self.genes)
        self._calculate_compactness()
    
    def get_gene_by_id(self, gene_id: str) -> Optional[Gene]:
        """
        Busca un gen por su ID.
        
        Args:
            gene_id: ID del gen (locus_tag, protein_id, o gene)
        
        Returns:
            Gene object o None
        """
        for gene in self.genes:
            if gene.id == gene_id or gene.locus_tag == gene_id or gene.protein_id == gene_id:
                return gene
        return None
    
    def get_genes_by_name(self, name: str) -> List[Gene]:
        """
        Busca genes por nombre (parcial).
        
        Args:
            name: Nombre del gen o parte del producto
        
        Returns:
            Lista de genes que coinciden
        """
        name_lower = name.lower()
        matches = []
        
        for gene in self.genes:
            if (name_lower in gene.gene.lower() or 
                name_lower in gene.product.lower() or
                name_lower in gene.locus_tag.lower()):
                matches.append(gene)
        
        return matches
    
    def get_largest_genes(self, n: int = 10) -> List[Gene]:
        """
        Obtiene los N genes más largos.
        
        Args:
            n: Número de genes a retornar
        
        Returns:
            Lista de genes ordenados por longitud descendente
        """
        return sorted(self.genes, key=lambda g: g.length, reverse=True)[:n]
    
    def get_smallest_genes(self, n: int = 10) -> List[Gene]:
        """
        Obtiene los N genes más pequeños.
        
        Args:
            n: Número de genes a retornar
        
        Returns:
            Lista de genes ordenados por longitud ascendente
        """
        return sorted(self.genes, key=lambda g: g.length)[:n]
    
    def get_genes_with_issues(self) -> List[Gene]:
        """
        Obtiene todos los genes con problemas de validación.
        
        Returns:
            Lista de genes problemáticos
        """
        return [gene for gene in self.genes if gene.has_issues]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Genera estadísticas completas del genoma.
        
        Returns:
            Dict con estadísticas
        """
        valid_genes = [g for g in self.genes if not g.has_issues]
        problematic_genes = [g for g in self.genes if g.has_issues]
        
        # GC promedio de genes
        avg_gene_gc = sum(g.gc_content for g in valid_genes) / len(valid_genes) if valid_genes else 0.0
        
        # Longitudes
        gene_lengths = [g.length for g in valid_genes]
        avg_length = sum(gene_lengths) / len(gene_lengths) if gene_lengths else 0
        
        return {
            'genome': {
                'accession': self.accession,
                'organism': self.organism,
                'length': self.length,
                'gc_content': round(self.gc_content, 2)
            },
            'genes': {
                'total': self.gene_count,
                'valid': len(valid_genes),
                'problematic': len(problematic_genes),
                'avg_length': int(avg_length),
                'avg_gc': round(avg_gene_gc, 2)
            },
            'compactness': {
                'coding_length': self.coding_length,
                'coding_percentage': round(self.coding_percentage, 2),
                'non_coding_length': self.length - self.coding_length,
                'gene_density': round(self.gene_density, 1)
            }
        }
    
    def to_dict(self, include_genes: bool = False) -> Dict[str, Any]:
        """
        Convierte el genoma a diccionario (para JSON).
        
        Args:
            include_genes: Si incluir la lista completa de genes
        
        Returns:
            Dict con datos del genoma
        """
        data = {
            'accession': self.accession,
            'organism': self.organism,
            'strain': self.strain,
            'length': self.length,
            'gc_content': round(self.gc_content, 2),
            'gene_count': self.gene_count,
            'coding_length': self.coding_length,
            'coding_percentage': round(self.coding_percentage, 2),
            'gene_density': round(self.gene_density, 1),
            'description': self.description,
            'fetched_at': self.fetched_at
        }
        
        if include_genes:
            data['genes'] = [gene.to_dict() for gene in self.genes]
        
        return data
    
    def export_genes_fasta(self, filename: str):
        """
        Exporta todos los genes a un archivo FASTA.
        
        Args:
            filename: Ruta del archivo de salida
        """
        with open(filename, 'w') as f:
            for gene in self.genes:
                f.write(gene.to_fasta() + "\n\n")
    
    def export_proteome_fasta(self, filename: str):
        """
        Exporta el proteoma (proteínas traducidas) a un archivo FASTA.
        
        Args:
            filename: Ruta del archivo de salida
        """
        with open(filename, 'w') as f:
            for gene in self.genes:
                if gene.protein_sequence:
                    f.write(gene.to_protein_fasta() + "\n\n")


# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def create_genome_from_seqrecord(record, accession: str = None) -> Genome:
    """
    Crea un objeto Genome desde un SeqRecord de BioPython.
    
    Args:
        record: SeqRecord de BioPython
        accession: Accession opcional (si no está en el record)
    
    Returns:
        Genome object
    """
    from models.gene import create_gene_from_feature
    
    # Extraer información básica
    genome_accession = accession or record.id
    organism = record.annotations.get('organism', 'Unknown')
    
    # Extraer cepa (si está en las anotaciones)
    strain = "Unknown"
    if 'source' in record.annotations:
        source = record.annotations['source']
        if 'strain' in source:
            strain = source['strain']
    
    # Crear genoma
    genome = Genome(
        accession=genome_accession,
        organism=organism,
        strain=strain,
        sequence=str(record.seq),
        description=record.description
    )
    
    # Extraer genes (CDS)
    for idx, feature in enumerate(record.features):
        if feature.type == "CDS":
            gene = create_gene_from_feature(feature, record.seq, idx)
            genome.add_gene(gene)
    
    return genome


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    from models.gene import Gene
    
    # Crear genoma de ejemplo
    genome = Genome(
        accession="NC_000913.3",
        organism="Escherichia coli str. K-12 substr. MG1655",
        strain="K-12 MG1655",
        sequence="AGCTTTTCATTCTGACTGCAACGGGCAATATGTCTCTGTGTGGATTAAAAAAAGAGTGTCTGATAGCAGC" * 1000,
        description="E. coli K-12 MG1655 complete genome"
    )
    
    # Añadir genes de ejemplo
    gene1 = Gene(
        id="b0001",
        locus_tag="b0001",
        gene="thrL",
        sequence="ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA",
        length=66
    )
    
    gene2 = Gene(
        id="b0002",
        locus_tag="b0002",
        gene="thrA",
        sequence="ATGCGAGTGTTGAAGTTCGGCGGTACATCAGTGGCAAATGCAGAACGTTTTCTGCGTGTTGCCGATATTCTG" * 10,
        length=730
    )
    
    genome.add_gene(gene1)
    genome.add_gene(gene2)
    
    # Estadísticas
    stats = genome.get_statistics()
    print("=== Estadísticas del Genoma ===")
    print(f"Accession: {stats['genome']['accession']}")
    print(f"Longitud: {stats['genome']['length']:,} bp")
    print(f"GC: {stats['genome']['gc_content']}%")
    print(f"Genes: {stats['genes']['total']}")
    print(f"Compactación: {stats['compactness']['coding_percentage']}%")
    
    # Buscar genes
    print(f"\nGenes más grandes:")
    for gene in genome.get_largest_genes(5):
        print(f"  - {gene.gene} ({gene.locus_tag}): {gene.length} bp")