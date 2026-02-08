"""
Sequence Utilities - Funciones auxiliares para análisis de secuencias
Incluye k-mers, similitud, hashing y otras operaciones comunes.
"""

import hashlib
from collections import Counter
from typing import List, Set, Dict, Tuple
import math


# ================================================================
# K-MERS
# ================================================================

def generate_kmers(sequence: str, k: int = 3) -> List[str]:
    """
    Genera k-mers de una secuencia.
    
    Args:
        sequence: Secuencia (DNA o proteína)
        k: Tamaño del k-mer
    
    Returns:
        Lista de k-mers
    
    Example:
        >>> generate_kmers("PROTEIN", k=3)
        ['PRO', 'ROT', 'OTE', 'TEI', 'EIN']
    """
    if len(sequence) < k:
        return []
    
    return [sequence[i:i+k] for i in range(len(sequence) - k + 1)]


def count_kmers(sequence: str, k: int = 3) -> Counter:
    """
    Cuenta k-mers en una secuencia.
    
    Args:
        sequence: Secuencia
        k: Tamaño del k-mer
    
    Returns:
        Counter con frecuencias de k-mers
    """
    kmers = generate_kmers(sequence, k)
    return Counter(kmers)


def kmer_profile(sequence: str, k: int = 3) -> Dict[str, int]:
    """
    Genera perfil de k-mers (diccionario ordenado).
    
    Args:
        sequence: Secuencia
        k: Tamaño del k-mer
    
    Returns:
        Dict {kmer: count}
    """
    return dict(count_kmers(sequence, k))


# ================================================================
# SIMILITUD ENTRE SECUENCIAS
# ================================================================

def jaccard_similarity(seq1: str, seq2: str, k: int = 3) -> float:
    """
    Calcula similitud de Jaccard entre dos secuencias usando k-mers.
    
    Jaccard = |A ∩ B| / |A ∪ B|
    
    Args:
        seq1: Primera secuencia
        seq2: Segunda secuencia
        k: Tamaño del k-mer
    
    Returns:
        Similitud entre 0.0 y 1.0
    
    Example:
        >>> jaccard_similarity("PROTEIN", "PROTEASE", k=3)
        0.4545...
    """
    kmers1 = set(generate_kmers(seq1, k))
    kmers2 = set(generate_kmers(seq2, k))
    
    if not kmers1 and not kmers2:
        return 1.0
    
    if not kmers1 or not kmers2:
        return 0.0
    
    intersection = len(kmers1 & kmers2)
    union = len(kmers1 | kmers2)
    
    return intersection / union if union > 0 else 0.0


def cosine_similarity(seq1: str, seq2: str, k: int = 3) -> float:
    """
    Calcula similitud de coseno entre dos secuencias usando k-mers.
    
    Cosine = (A · B) / (||A|| * ||B||)
    
    Args:
        seq1: Primera secuencia
        seq2: Segunda secuencia
        k: Tamaño del k-mer
    
    Returns:
        Similitud entre 0.0 y 1.0
    """
    counter1 = count_kmers(seq1, k)
    counter2 = count_kmers(seq2, k)
    
    # Todos los k-mers únicos
    all_kmers = set(counter1.keys()) | set(counter2.keys())
    
    if not all_kmers:
        return 0.0
    
    # Vectores de frecuencias
    vec1 = [counter1.get(kmer, 0) for kmer in all_kmers]
    vec2 = [counter2.get(kmer, 0) for kmer in all_kmers]
    
    # Producto punto
    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    
    # Magnitudes
    magnitude1 = math.sqrt(sum(v ** 2 for v in vec1))
    magnitude2 = math.sqrt(sum(v ** 2 for v in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def quick_similarity(seq1: str, seq2: str, k: int = 3, method: str = 'jaccard') -> float:
    """
    Calcula similitud rápida entre secuencias.
    
    Args:
        seq1: Primera secuencia
        seq2: Segunda secuencia
        k: Tamaño del k-mer
        method: 'jaccard' o 'cosine'
    
    Returns:
        Similitud entre 0.0 y 1.0
    """
    if method == 'cosine':
        return cosine_similarity(seq1, seq2, k)
    else:
        return jaccard_similarity(seq1, seq2, k)


# ================================================================
# FILTRADO RÁPIDO
# ================================================================

def filter_by_kmer_similarity(target: str, 
                              candidates: List[Tuple[str, str]], 
                              k: int = 3,
                              method: str = 'jaccard',
                              top_n: int = 50) -> List[Tuple[str, str, float]]:
    """
    Filtra candidatos por similitud de k-mers (rápido).
    
    Args:
        target: Secuencia objetivo
        candidates: Lista de (id, secuencia)
        k: Tamaño del k-mer
        method: 'jaccard' o 'cosine'
        top_n: Número de top candidatos a retornar
    
    Returns:
        Lista de (id, secuencia, similitud) ordenada por similitud descendente
    
    Example:
        >>> candidates = [("gene1", "MFKLPROTEINA"), ("gene2", "MFKLPROT")]
        >>> filter_by_kmer_similarity("MFKLPROTEIN", candidates, top_n=2)
        [('gene1', 'MFKLPROTEINA', 0.95), ('gene2', 'MFKLPROT', 0.85)]
    """
    results = []
    
    for candidate_id, candidate_seq in candidates:
        similarity = quick_similarity(target, candidate_seq, k, method)
        results.append((candidate_id, candidate_seq, similarity))
    
    # Ordenar por similitud descendente
    results.sort(key=lambda x: x[2], reverse=True)
    
    return results[:top_n]


# ================================================================
# HASHING Y CHECKSUMS
# ================================================================

def sequence_hash(sequence: str, algorithm: str = 'sha256') -> str:
    """
    Calcula hash de una secuencia.
    
    Args:
        sequence: Secuencia
        algorithm: Algoritmo de hash (md5, sha1, sha256)
    
    Returns:
        Hash hexadecimal
    
    Example:
        >>> sequence_hash("PROTEIN", "sha256")
        'a1b2c3d4...'
    """
    if algorithm == 'md5':
        hasher = hashlib.md5()
    elif algorithm == 'sha1':
        hasher = hashlib.sha1()
    else:  # sha256
        hasher = hashlib.sha256()
    
    hasher.update(sequence.encode())
    return hasher.hexdigest()


def sequences_are_identical(seq1: str, seq2: str) -> bool:
    """
    Verifica si dos secuencias son idénticas usando hash.
    
    Args:
        seq1: Primera secuencia
        seq2: Segunda secuencia
    
    Returns:
        True si son idénticas
    """
    return sequence_hash(seq1) == sequence_hash(seq2)


# ================================================================
# COMPOSICIÓN DE AMINOÁCIDOS
# ================================================================

def amino_acid_composition(sequence: str) -> Dict[str, float]:
    """
    Calcula composición de aminoácidos (%).
    
    Args:
        sequence: Secuencia de proteína
    
    Returns:
        Dict {aminoácido: porcentaje}
    """
    if not sequence:
        return {}
    
    counter = Counter(sequence.upper())
    total = len(sequence)
    
    return {aa: (count / total) * 100 for aa, count in counter.items()}


def composition_similarity(seq1: str, seq2: str) -> float:
    """
    Calcula similitud basada en composición de aminoácidos.
    
    Args:
        seq1: Primera secuencia
        seq2: Segunda secuencia
    
    Returns:
        Similitud entre 0.0 y 1.0
    """
    comp1 = amino_acid_composition(seq1)
    comp2 = amino_acid_composition(seq2)
    
    # Todos los aminoácidos presentes
    all_aa = set(comp1.keys()) | set(comp2.keys())
    
    if not all_aa:
        return 0.0
    
    # Diferencia absoluta promedio
    diff_sum = sum(abs(comp1.get(aa, 0) - comp2.get(aa, 0)) for aa in all_aa)
    avg_diff = diff_sum / len(all_aa)
    
    # Convertir a similitud (0 diff = 1.0 similarity)
    return max(0.0, 1.0 - (avg_diff / 100))


# ================================================================
# VALIDACIÓN DE SECUENCIAS
# ================================================================

def is_valid_dna(sequence: str) -> bool:
    """
    Valida si una secuencia es DNA válido.
    
    Args:
        sequence: Secuencia
    
    Returns:
        True si solo contiene A, T, G, C, N
    """
    valid_bases = set('ATGCN')
    return all(base.upper() in valid_bases for base in sequence)


def is_valid_protein(sequence: str) -> bool:
    """
    Valida si una secuencia es proteína válida.
    
    Args:
        sequence: Secuencia
    
    Returns:
        True si solo contiene aminoácidos estándar
    """
    valid_aa = set('ACDEFGHIKLMNPQRSTVWY*X')  # * = stop, X = desconocido
    return all(aa.upper() in valid_aa for aa in sequence)


def clean_sequence(sequence: str, seq_type: str = 'auto') -> str:
    """
    Limpia una secuencia (elimina espacios, números, etc).
    
    Args:
        sequence: Secuencia sucia
        seq_type: 'dna', 'protein', o 'auto'
    
    Returns:
        Secuencia limpia
    """
    # Eliminar espacios, números, y caracteres especiales
    cleaned = ''.join(c for c in sequence if c.isalpha() or c == '*')
    
    # Convertir a mayúsculas
    cleaned = cleaned.upper()
    
    return cleaned


# ================================================================
# TRADUCCIÓN DNA → PROTEÍNA
# ================================================================

CODON_TABLE_STANDARD = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G'
}


def translate_dna(dna_sequence: str, table: Dict[str, str] = None) -> str:
    """
    Traduce secuencia de DNA a proteína.
    
    Args:
        dna_sequence: Secuencia de DNA
        table: Tabla genética (default: estándar)
    
    Returns:
        Secuencia de proteína
    """
    if table is None:
        table = CODON_TABLE_STANDARD
    
    # Limpiar secuencia
    dna = clean_sequence(dna_sequence, 'dna')
    
    # Traducir
    protein = ""
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i+3]
        aa = table.get(codon, 'X')
        protein += aa
    
    return protein


def reverse_complement(dna_sequence: str) -> str:
    """
    Calcula el complemento reverso de una secuencia de DNA.
    
    Args:
        dna_sequence: Secuencia de DNA
    
    Returns:
        Complemento reverso
    """
    complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
    
    # Complemento
    comp = ''.join(complement.get(base.upper(), 'N') for base in dna_sequence)
    
    # Reverso
    return comp[::-1]


# ================================================================
# ESTADÍSTICAS DE SECUENCIAS
# ================================================================

def gc_content(sequence: str) -> float:
    """
    Calcula contenido GC de una secuencia.
    
    Args:
        sequence: Secuencia de DNA
    
    Returns:
        Porcentaje GC
    """
    seq_upper = sequence.upper()
    g = seq_upper.count('G')
    c = seq_upper.count('C')
    
    return (g + c) / len(sequence) * 100 if len(sequence) > 0 else 0.0


def calculate_molecular_weight(protein_sequence: str) -> float:
    """
    Calcula peso molecular aproximado de una proteína (kDa).
    
    Args:
        protein_sequence: Secuencia de proteína
    
    Returns:
        Peso molecular en kDa
    """
    # Pesos moleculares promedio de aminoácidos (Da)
    aa_weights = {
        'A': 89.1, 'R': 174.2, 'N': 132.1, 'D': 133.1, 'C': 121.2,
        'Q': 146.2, 'E': 147.1, 'G': 75.1, 'H': 155.2, 'I': 131.2,
        'L': 131.2, 'K': 146.2, 'M': 149.2, 'F': 165.2, 'P': 115.1,
        'S': 105.1, 'T': 119.1, 'W': 204.2, 'Y': 181.2, 'V': 117.1
    }
    
    weight = sum(aa_weights.get(aa.upper(), 110) for aa in protein_sequence)
    
    # Restar agua por enlace peptídico
    weight -= (len(protein_sequence) - 1) * 18.0
    
    return weight / 1000.0  # Convertir a kDa


# ================================================================
# EJEMPLO DE USO
# ================================================================

if __name__ == "__main__":
    print("=== Sequence Utils Examples ===\n")
    
    # Test 1: K-mers
    seq = "PROTEIN"
    kmers = generate_kmers(seq, k=3)
    print(f"1. K-mers de '{seq}':")
    print(f"   {kmers}\n")
    
    # Test 2: Similitud
    seq1 = "MFKLPROTEIN"
    seq2 = "MFKLPROT"
    jaccard = jaccard_similarity(seq1, seq2, k=3)
    cosine = cosine_similarity(seq1, seq2, k=3)
    print(f"2. Similitud entre '{seq1}' y '{seq2}':")
    print(f"   Jaccard: {jaccard:.4f}")
    print(f"   Cosine: {cosine:.4f}\n")
    
    # Test 3: Hash
    seq_hash = sequence_hash(seq1)
    print(f"3. Hash de '{seq1}':")
    print(f"   {seq_hash[:16]}...\n")
    
    # Test 4: Composición
    comp = amino_acid_composition(seq1)
    print(f"4. Composición de aminoácidos:")
    for aa, pct in sorted(comp.items()):
        print(f"   {aa}: {pct:.1f}%")
    
    # Test 5: Filtrado rápido
    candidates = [
        ("gene1", "MFKLPROTEINA"),
        ("gene2", "MFKLPROT"),
        ("gene3", "ABCDEFGH")
    ]
    filtered = filter_by_kmer_similarity(seq1, candidates, top_n=2)
    print(f"\n5. Top 2 candidatos similares a '{seq1}':")
    for gene_id, seq, sim in filtered:
        print(f"   {gene_id}: {sim:.4f}")