"""
Protein Model - Estructura de datos para proteínas de UniProt
Representa una proteína con todas sus anotaciones relevantes.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import hashlib


@dataclass
class Protein:
    """
    Representa una proteína de UniProt con sus anotaciones.
    
    Attributes:
        accession: UniProt accession (ej: P01308)
        name: Nombre de la proteína
        organism: Organismo de origen
        sequence: Secuencia de aminoácidos
        length: Longitud de la proteína
        reviewed: Si está revisada (Swiss-Prot vs TrEMBL)
        protein_existence: Nivel de evidencia (1-5)
        gene_names: Nombres de genes asociados
        
        # Anotaciones funcionales
        function: Descripción de función
        ec_number: Número EC (si es enzima)
        
        # Localización
        subcellular_location: Localización celular
        has_signal_peptide: Si tiene péptido señal
        signal_peptide_range: Rango del péptido señal
        
        # Estructura
        transmembrane_regions: Lista de regiones transmembrana
        transmembrane_count: Número de dominios TM
        
        # Modificaciones post-traduccionales
        has_glycosylation: Si requiere glicosilación
        glycosylation_sites: Sitios de glicosilación
        has_disulfide_bonds: Si tiene puentes disulfuro
        disulfide_bond_count: Número de puentes disulfuro
        
        # Cofactores y metales
        cofactors: Lista de cofactores requeridos
        metal_binding: Lista de iones metálicos
        
        # Otros
        keywords: Lista de keywords
        go_terms: Gene Ontology terms
        metadata: Metadatos adicionales completos
    """
    
    # Identificación básica
    accession: str
    name: str = "Unknown"
    organism: str = "Unknown"
    
    # Secuencia
    sequence: str = ""
    length: int = 0
    
    # Calidad/evidencia
    reviewed: bool = False
    protein_existence: int = 5  # 1=experimental, 5=predicted
    
    # Genes
    gene_names: List[str] = field(default_factory=list)
    
    # Función
    function: str = ""
    ec_number: Optional[str] = None
    
    # Localización
    subcellular_location: List[str] = field(default_factory=list)
    has_signal_peptide: bool = False
    signal_peptide_range: Optional[str] = None
    
    # Estructura
    transmembrane_regions: List[Dict[str, int]] = field(default_factory=list)
    transmembrane_count: int = 0
    
    # PTMs (Post-Translational Modifications)
    has_glycosylation: bool = False
    glycosylation_sites: List[Dict[str, Any]] = field(default_factory=list)
    has_disulfide_bonds: bool = False
    disulfide_bond_count: int = 0
    
    # Cofactores
    cofactors: List[str] = field(default_factory=list)
    metal_binding: List[str] = field(default_factory=list)
    
    # Anotaciones generales
    keywords: List[str] = field(default_factory=list)
    go_terms: List[str] = field(default_factory=list)
    
    # Metadatos completos (JSON raw de UniProt)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Cálculos automáticos después de inicialización."""
        # Calcular longitud si no está definida
        if self.length == 0 and self.sequence:
            self.length = len(self.sequence)
        
        # Contar dominios transmembrana
        if self.transmembrane_count == 0 and self.transmembrane_regions:
            self.transmembrane_count = len(self.transmembrane_regions)
    
    def get_sequence_hash(self) -> str:
        """
        Calcula hash SHA256 de la secuencia.
        
        Returns:
            Hash hexadecimal
        """
        return hashlib.sha256(self.sequence.encode()).hexdigest()
    
    def is_membrane_protein(self) -> bool:
        """
        Determina si es una proteína de membrana.
        
        Returns:
            True si tiene dominios transmembrana
        """
        return self.transmembrane_count > 0
    
    def is_secreted(self) -> bool:
        """
        Determina si es una proteína secretada.
        
        Returns:
            True si tiene péptido señal o localización extracelular
        """
        if self.has_signal_peptide:
            return True
        
        secreted_locations = ['secreted', 'extracellular', 'cell surface']
        for location in self.subcellular_location:
            if any(loc in location.lower() for loc in secreted_locations):
                return True
        
        return False
    
    def requires_ptms(self) -> bool:
        """
        Determina si requiere modificaciones post-traduccionales.
        
        Returns:
            True si requiere PTMs complejas
        """
        return self.has_glycosylation or self.has_disulfide_bonds
    
    def requires_cofactors(self) -> bool:
        """
        Determina si requiere cofactores.
        
        Returns:
            True si requiere cofactores o metales
        """
        return len(self.cofactors) > 0 or len(self.metal_binding) > 0
    
    def get_complexity_score(self) -> int:
        """
        Calcula un score de complejidad (0-100).
        
        Factores:
        - Dominios transmembrana
        - PTMs
        - Cofactores
        - Péptido señal
        
        Returns:
            Score de 0 (simple) a 100 (muy complejo)
        """
        score = 0
        
        # Transmembrana (20 puntos por dominio, max 60)
        score += min(self.transmembrane_count * 20, 60)
        
        # Glicosilación (20 puntos)
        if self.has_glycosylation:
            score += 20
        
        # Puentes disulfuro (10 puntos)
        if self.has_disulfide_bonds:
            score += 10
        
        # Péptido señal (10 puntos)
        if self.has_signal_peptide:
            score += 10
        
        # Cofactores (5 puntos por cada uno, max 20)
        score += min(len(self.cofactors) * 5, 20)
        
        # Metales (5 puntos por cada uno, max 20)
        score += min(len(self.metal_binding) * 5, 20)
        
        return min(score, 100)
    
    def to_dict(self, include_sequence: bool = True) -> Dict[str, Any]:
        """
        Convierte la proteína a diccionario.
        
        Args:
            include_sequence: Si incluir la secuencia completa
        
        Returns:
            Dict con datos de la proteína
        """
        data = {
            'accession': self.accession,
            'name': self.name,
            'organism': self.organism,
            'length': self.length,
            'reviewed': self.reviewed,
            'protein_existence': self.protein_existence,
            'gene_names': self.gene_names,
            'function': self.function[:200] + '...' if len(self.function) > 200 else self.function,
            'ec_number': self.ec_number,
            'subcellular_location': self.subcellular_location,
            'has_signal_peptide': self.has_signal_peptide,
            'transmembrane_count': self.transmembrane_count,
            'has_glycosylation': self.has_glycosylation,
            'has_disulfide_bonds': self.has_disulfide_bonds,
            'disulfide_bond_count': self.disulfide_bond_count,
            'cofactors': self.cofactors,
            'metal_binding': self.metal_binding,
            'keywords': self.keywords[:10],  # Primeros 10
            'complexity_score': self.get_complexity_score()
        }
        
        if include_sequence:
            data['sequence'] = self.sequence
            data['sequence_hash'] = self.get_sequence_hash()
        
        return data
    
    def to_fasta(self) -> str:
        """
        Genera formato FASTA de la proteína.
        
        Returns:
            String en formato FASTA
        """
        header = f">{self.accession}|{self.name}|{self.organism}"
        
        # Dividir secuencia en líneas de 60 caracteres
        seq_lines = [self.sequence[i:i+60] for i in range(0, len(self.sequence), 60)]
        
        return header + "\n" + "\n".join(seq_lines)


# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def create_protein_from_uniprot_json(data: Dict[str, Any]) -> Protein:
    """
    Crea un objeto Protein desde JSON de UniProt API.
    
    Args:
        data: Datos JSON de UniProt
    
    Returns:
        Protein object
    """
    # Esta función se implementará en uniprot_service.py
    # Aquí solo definimos la estructura
    pass


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    # Crear proteína de ejemplo (Insulina humana)
    insulin = Protein(
        accession="P01308",
        name="Insulin",
        organism="Homo sapiens",
        sequence="MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
        reviewed=True,
        protein_existence=1,
        gene_names=["INS"],
        function="Insulin decreases blood glucose concentration",
        subcellular_location=["Secreted"],
        has_signal_peptide=True,
        signal_peptide_range="1-24",
        has_disulfide_bonds=True,
        disulfide_bond_count=3,
        keywords=["Diabetes mellitus", "Hormone", "Secreted"]
    )
    
    print("=== Protein Example ===")
    print(f"Accession: {insulin.accession}")
    print(f"Name: {insulin.name}")
    print(f"Length: {insulin.length} aa")
    print(f"Reviewed: {insulin.reviewed}")
    print(f"Is secreted: {insulin.is_secreted()}")
    print(f"Requires PTMs: {insulin.requires_ptms()}")
    print(f"Complexity score: {insulin.get_complexity_score()}/100")
    print(f"\nFASTA:\n{insulin.to_fasta()}")