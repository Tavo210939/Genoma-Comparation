"""
Gene Model - Estructura de datos para genes
Representa un gen (CDS) extraído de un genoma con todas sus propiedades.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Gene:
    """
    Representa un gen (CDS) con sus propiedades bioinformáticas.
    
    Attributes:
        id: Identificador estable (locus_tag, protein_id, o gene)
        locus_tag: Locus tag del gen (ej: b0001)
        gene: Nombre del gen (ej: thrL)
        product: Descripción del producto proteico
        protein_id: ID de la proteína (ej: NP_414542.1)
        sequence: Secuencia nucleotídica del CDS
        protein_sequence: Secuencia de aminoácidos traducida
        length: Longitud en pares de bases
        start: Posición de inicio en el genoma
        end: Posición de fin en el genoma
        strand: Cadena (+1 forward, -1 reverse)
        gc_content: Contenido GC del gen (%)
        codon_start: Frame de lectura (1, 2, o 3)
        transl_table: Tabla genética usada (11 para bacterias)
        start_codon: Codón de inicio (ATG, GTG, TTG)
        stop_codon: Codón de terminación (TAA, TAG, TGA)
        is_partial: Si es un CDS parcial/fragmentado
        has_issues: Si tiene problemas de validación
        issues: Lista de problemas detectados
        note: Notas adicionales del GenBank
    """
    
    # Identificadores
    id: str
    locus_tag: str = "-"
    gene: str = "-"
    product: str = "Unknown"
    protein_id: str = "-"
    
    # Secuencias
    sequence: str = ""
    protein_sequence: str = ""
    
    # Ubicación
    length: int = 0
    start: int = 0
    end: int = 0
    strand: int = 1  # 1 o -1
    
    # Propiedades bioinformáticas
    gc_content: float = 0.0
    codon_start: int = 1
    transl_table: int = 11
    start_codon: str = "ATG"
    stop_codon: str = "TAA"
    
    # Validación
    is_partial: bool = False
    has_issues: bool = False
    issues: list = field(default_factory=list)
    
    # Adicional
    note: str = "-"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validación y cálculos automáticos después de inicialización."""
        # Calcular longitud si no está definida
        if self.length == 0 and self.sequence:
            self.length = len(self.sequence)
        
        # Calcular GC si no está definido
        if self.gc_content == 0.0 and self.sequence:
            self.gc_content = self._calculate_gc()
    
    def _calculate_gc(self) -> float:
        """Calcula el contenido GC de la secuencia."""
        if not self.sequence:
            return 0.0
        
        g = self.sequence.upper().count('G')
        c = self.sequence.upper().count('C')
        total = len(self.sequence)
        
        return (g + c) / total * 100 if total > 0 else 0.0
    
    def validate(self) -> bool:
        """
        Valida el gen y detecta problemas.
        
        Returns:
            True si el gen es válido, False si tiene problemas críticos
        """
        self.issues = []
        self.has_issues = False
        
        # Validar longitud múltiplo de 3
        if self.length % 3 != 0:
            self.issues.append("Longitud no es múltiplo de 3")
            self.has_issues = True
        
        # Validar presencia de nucleótidos ambiguos
        if 'N' in self.sequence.upper():
            self.issues.append("Contiene nucleótidos ambiguos (N)")
            self.has_issues = True
        
        # Validar start codon
        if len(self.sequence) >= 3:
            actual_start = self.sequence[:3].upper()
            if actual_start not in ['ATG', 'GTG', 'TTG']:
                self.issues.append(f"Start codon inusual: {actual_start}")
                self.has_issues = True
        
        # Validar stop codon (solo si no es parcial)
        if not self.is_partial and len(self.sequence) >= 3:
            actual_stop = self.sequence[-3:].upper()
            if actual_stop not in ['TAA', 'TAG', 'TGA']:
                self.issues.append(f"Stop codon ausente o inusual: {actual_stop}")
                self.has_issues = True
        
        return not self.has_issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el gen a diccionario (para JSON)."""
        return {
            'id': self.id,
            'locus_tag': self.locus_tag,
            'gene': self.gene,
            'product': self.product,
            'protein_id': self.protein_id,
            'length': self.length,
            'start': self.start,
            'end': self.end,
            'strand': self.strand,
            'gc_content': round(self.gc_content, 2),
            'codon_start': self.codon_start,
            'transl_table': self.transl_table,
            'start_codon': self.start_codon,
            'stop_codon': self.stop_codon,
            'is_partial': self.is_partial,
            'has_issues': self.has_issues,
            'issues': self.issues,
            'note': self.note,
            'sequence_preview': self.sequence[:100] if self.sequence else ""
        }
    
    def to_fasta(self) -> str:
        """
        Genera formato FASTA del gen.
        
        Returns:
            String en formato FASTA
        """
        header = f">{self.id}|{self.locus_tag}|{self.gene} {self.product}"
        return f"{header}\n{self.sequence}"
    
    def to_protein_fasta(self) -> str:
        """
        Genera formato FASTA de la proteína traducida.
        
        Returns:
            String en formato FASTA
        """
        if not self.protein_sequence:
            return ""
        
        header = f">{self.protein_id}|{self.gene} {self.product}"
        return f"{header}\n{self.protein_sequence}"


# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def create_gene_from_feature(feature, genome_sequence: str, feature_index: int = 0) -> Gene:
    """
    Crea un objeto Gene desde un feature de BioPython.
    
    Args:
        feature: Feature de tipo CDS de BioPython
        genome_sequence: Secuencia completa del genoma
        feature_index: Índice del feature (fallback si no hay IDs)
    
    Returns:
        Gene object
    """
    q = feature.qualifiers
    
    # Extraer identificadores
    locus_tag = q.get("locus_tag", [None])[0]
    protein_id = q.get("protein_id", [None])[0]
    gene_name = q.get("gene", [None])[0]
    
    # ID estable (prioridad: locus_tag > protein_id > gene > índice)
    stable_id = locus_tag or protein_id or gene_name or f"gene_{feature_index}"
    
    # Extraer secuencia
    try:
        seq = str(feature.extract(genome_sequence))
    except:
        seq = ""
    
    # Codon start
    codon_start = int(q.get("codon_start", [1])[0])
    
    # Ajustar por codon_start
    if codon_start > 1 and seq:
        seq = seq[codon_start - 1:]
    
    # Start y stop codons
    start_codon = seq[:3].upper() if len(seq) >= 3 else "---"
    stop_codon = seq[-3:].upper() if len(seq) >= 3 else "---"
    
    # Detectar si es parcial
    is_partial = "partial" in str(feature.location)
    
    # Crear gene
    gene = Gene(
        id=stable_id,
        locus_tag=locus_tag or "-",
        gene=gene_name or "-",
        product=q.get("product", ["Unknown"])[0],
        protein_id=protein_id or "-",
        sequence=seq,
        length=len(seq),
        start=int(feature.location.start),
        end=int(feature.location.end),
        strand=feature.location.strand if hasattr(feature.location, 'strand') else 1,
        codon_start=codon_start,
        transl_table=int(q.get("transl_table", [11])[0]),
        start_codon=start_codon,
        stop_codon=stop_codon,
        is_partial=is_partial,
        note=q.get("note", ["-"])[0] if "note" in q else "-"
    )
    
    # Validar
    gene.validate()
    
    return gene


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    # Crear un gen de ejemplo
    gene = Gene(
        id="b0001",
        locus_tag="b0001",
        gene="thrL",
        product="thr operon leader peptide",
        protein_id="NP_414542.1",
        sequence="ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA",
        start=190,
        end=255,
        strand=1
    )
    
    # Validar
    is_valid = gene.validate()
    print(f"Gen válido: {is_valid}")
    print(f"GC content: {gene.gc_content:.2f}%")
    print(f"Issues: {gene.issues}")
    
    # Convertir a dict
    gene_dict = gene.to_dict()
    print(f"\nDict: {gene_dict}")
    
    # FASTA
    fasta = gene.to_fasta()
    print(f"\nFASTA:\n{fasta}")