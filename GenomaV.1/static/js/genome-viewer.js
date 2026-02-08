// ============================================
// GENOME-VIEWER.JS - Visualización Genómica
// ============================================

// ============================================
// VISUALIZADOR CIRCULAR (D3.js)
// ============================================

class GenomeViewer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    this.width = this.container.clientWidth || 800;
    this.height = 600;
    this.radius = Math.min(this.width, this.height) / 2 - 100;
    
    this.data = null;
    this.svg = null;
    this.inspector = null;
  }

  render(genomeData) {
    this.data = genomeData;
    this.clear();
    this.createSVG();
    this.drawGenome();
    this.setupInteractions();
  }

  clear() {
    this.container.innerHTML = '';
  }

  createSVG() {
    this.svg = d3.select(this.container)
      .append('svg')
      .attr('width', this.width)
      .attr('height', this.height)
      .append('g')
      .attr('transform', `translate(${this.width / 2}, ${this.height / 2})`);

    // Grupo para los elementos del genoma
    this.genomeGroup = this.svg.append('g').attr('class', 'genome-group');
    
    // Grupo para las etiquetas
    this.labelsGroup = this.svg.append('g').attr('class', 'labels-group');
  }

  drawGenome() {
    if (!this.data || !this.data.genome) return;

    const genome = this.data.genome;
    const genes = this.data.genes?.genes || [];

    // Círculo base del genoma
    this.drawGenomeCircle(genome.length);

    // Marcadores de posición
    this.drawPositionMarkers(genome.length);

    // Genes como arcos
    this.drawGenes(genes, genome.length);

    // Información central
    this.drawCentralInfo(genome);
  }

  drawGenomeCircle(length) {
    // Círculo exterior
    this.genomeGroup.append('circle')
      .attr('r', this.radius)
      .attr('fill', 'none')
      .attr('stroke', '#E5E7EB')
      .attr('stroke-width', 2);

    // Círculo interior
    this.genomeGroup.append('circle')
      .attr('r', this.radius - 40)
      .attr('fill', 'none')
      .attr('stroke', '#E5E7EB')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2');
  }

  drawPositionMarkers(length) {
    const markers = 12; // 12 marcadores (como reloj)
    const step = length / markers;

    for (let i = 0; i < markers; i++) {
      const angle = (i * 360 / markers) - 90;
      const rad = (angle * Math.PI) / 180;
      
      const x1 = Math.cos(rad) * (this.radius - 5);
      const y1 = Math.sin(rad) * (this.radius - 5);
      const x2 = Math.cos(rad) * (this.radius + 10);
      const y2 = Math.sin(rad) * (this.radius + 10);

      // Línea del marcador
      this.labelsGroup.append('line')
        .attr('x1', x1)
        .attr('y1', y1)
        .attr('x2', x2)
        .attr('y2', y2)
        .attr('stroke', '#9CA3AF')
        .attr('stroke-width', 2);

      // Etiqueta de posición
      const position = Math.round(i * step);
      const labelX = Math.cos(rad) * (this.radius + 30);
      const labelY = Math.sin(rad) * (this.radius + 30);

      this.labelsGroup.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('fill', '#6B7280')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .text(`${(position / 1000).toFixed(0)}kb`);
    }
  }

  drawGenes(genes, genomeLength) {
    if (!genes || genes.length === 0) return;

    // Limitar genes para rendimiento
    const maxGenes = 500;
    const sampledGenes = genes.length > maxGenes 
      ? this.sampleGenes(genes, maxGenes) 
      : genes;

    const arc = d3.arc()
      .innerRadius(this.radius - 35)
      .outerRadius(this.radius - 5);

    sampledGenes.forEach((gene, i) => {
      const startAngle = (gene.start / genomeLength) * 2 * Math.PI - Math.PI / 2;
      const endAngle = (gene.end / genomeLength) * 2 * Math.PI - Math.PI / 2;

      // Color según strand
      const color = gene.strand === 1 ? '#7C3AED' : '#A78BFA';

      this.genomeGroup.append('path')
        .datum({
          startAngle: startAngle,
          endAngle: endAngle
        })
        .attr('d', arc)
        .attr('fill', color)
        .attr('opacity', 0.7)
        .attr('stroke', 'white')
        .attr('stroke-width', 0.5)
        .style('cursor', 'pointer')
        .attr('data-gene-id', gene.id)
        .on('mouseover', (event) => {
          d3.select(event.target)
            .attr('opacity', 1)
            .attr('stroke-width', 2)
            .attr('stroke', '#F59E0B');
          
          this.showGeneTooltip(event, gene);
        })
        .on('mouseout', (event) => {
          d3.select(event.target)
            .attr('opacity', 0.7)
            .attr('stroke-width', 0.5)
            .attr('stroke', 'white');
          
          this.hideGeneTooltip();
        })
        .on('click', (event) => {
          this.selectGene(gene);
        });
    });
  }

  sampleGenes(genes, maxSamples) {
    const step = Math.floor(genes.length / maxSamples);
    return genes.filter((_, i) => i % step === 0);
  }

  drawCentralInfo(genome) {
    const centerGroup = this.svg.append('g').attr('class', 'center-info');

    // Nombre del organismo
    centerGroup.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', -20)
      .attr('fill', '#7C3AED')
      .attr('font-size', '16px')
      .attr('font-weight', 'bold')
      .text(this.truncateText(genome.organism, 30));

    // Longitud
    centerGroup.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 5)
      .attr('fill', '#6B7280')
      .attr('font-size', '14px')
      .text(`${(genome.length / 1000000).toFixed(2)} Mb`);

    // Genes
    centerGroup.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 25)
      .attr('fill', '#6B7280')
      .attr('font-size', '14px')
      .text(`${genome.gene_count.toLocaleString()} genes`);

    // GC content
    centerGroup.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 45)
      .attr('fill', '#6B7280')
      .attr('font-size', '14px')
      .text(`GC: ${genome.gc_content}%`);
  }

  setupInteractions() {
    // Zoom y pan
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        this.svg.attr('transform', event.transform);
      });

    d3.select(this.container).select('svg').call(zoom);
  }

  showGeneTooltip(event, gene) {
    // Remover tooltip anterior si existe
    d3.select('.gene-tooltip').remove();

    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'gene-tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.9)')
      .style('color', 'white')
      .style('padding', '12px')
      .style('border-radius', '8px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('z-index', '10000')
      .style('max-width', '300px')
      .html(`
        <strong>${gene.gene || gene.locus_tag}</strong><br>
        <em>${gene.product}</em><br>
        <span style="color: #A78BFA;">Posición:</span> ${gene.start.toLocaleString()} - ${gene.end.toLocaleString()}<br>
        <span style="color: #A78BFA;">Longitud:</span> ${gene.length.toLocaleString()} bp<br>
        <span style="color: #A78BFA;">Strand:</span> ${gene.strand === 1 ? '+' : '-'}<br>
        <span style="color: #A78BFA;">GC:</span> ${gene.gc_content}%
      `);

    const tooltipNode = tooltip.node();
    const rect = tooltipNode.getBoundingClientRect();

    tooltip
      .style('left', `${event.pageX - rect.width / 2}px`)
      .style('top', `${event.pageY - rect.height - 10}px`);
  }

  hideGeneTooltip() {
    d3.select('.gene-tooltip').remove();
  }

  selectGene(gene) {
    console.log('Gene selected:', gene);
    
    // Abrir inspector de secuencias
    if (!this.inspector) {
      this.inspector = new SequenceInspector('sequence-inspector');
    }

    this.inspector.show(gene);
  }

  truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
  }
}

// ============================================
// INSPECTOR DE SECUENCIAS (Canvas)
// ============================================

class SequenceInspector {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    this.canvas = null;
    this.ctx = null;
    this.data = null;
    
    // Configuración visual
    this.nucleotideHeight = 20;
    this.nucleotideWidth = 12;
    this.trackHeight = 30;
    this.padding = 20;

    // Colores
    this.colors = {
      A: '#10B981',
      T: '#3B82F6',
      G: '#F59E0B',
      C: '#EF4444',
      background: '#FAFAF9',
      text: '#1F2937',
      gridLine: '#E5E7EB'
    };

    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div style="background: white; border-radius: 12px; padding: 20px; border: 1px solid #E5E7EB;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
          <h3 style="margin: 0; color: #1F2937; font-size: 1.125rem;">Inspector de Secuencias</h3>
          <button onclick="document.getElementById('sequence-inspector').style.display='none'" 
                  style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6B7280;">
            ×
          </button>
        </div>
        <div id="inspector-info" style="margin-bottom: 15px; padding: 12px; background: #F3F0FF; border-radius: 8px;">
          <!-- Gene info -->
        </div>
        <div style="overflow-x: auto; background: #FAFAF9; border-radius: 8px; padding: 10px;">
          <canvas id="sequence-canvas"></canvas>
        </div>
      </div>
    `;

    this.canvas = document.getElementById('sequence-canvas');
    this.ctx = this.canvas.getContext('2d');
  }

  show(gene) {
    this.container.style.display = 'block';
    this.data = gene;

    // Actualizar info del gen
    document.getElementById('inspector-info').innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
        <div><strong>Gen:</strong> ${gene.gene || gene.locus_tag}</div>
        <div><strong>Producto:</strong> ${gene.product}</div>
        <div><strong>Posición:</strong> ${gene.start} - ${gene.end}</div>
        <div><strong>Longitud:</strong> ${gene.length} bp</div>
        <div><strong>Strand:</strong> ${gene.strand === 1 ? '+ (forward)' : '- (reverse)'}</div>
        <div><strong>GC%:</strong> ${gene.gc_content}%</div>
      </div>
    `;

    this.render();
  }

  render() {
    if (!this.data || !this.data.sequence) {
      this.renderPlaceholder();
      return;
    }

    const sequence = this.data.sequence;
    const maxNucleotides = 100; // Limitar para rendimiento
    const displaySeq = sequence.length > maxNucleotides 
      ? sequence.substring(0, maxNucleotides) 
      : sequence;

    // Dimensiones del canvas
    const width = displaySeq.length * this.nucleotideWidth + this.padding * 2;
    const height = this.trackHeight * 3 + this.padding * 2;

    this.canvas.width = width;
    this.canvas.height = height;

    // Fondo
    this.ctx.fillStyle = this.colors.background;
    this.ctx.fillRect(0, 0, width, height);

    // Dibujar tracks
    this.drawNucleotideTrack(displaySeq, this.padding, this.padding);
    this.drawCodonTrack(displaySeq, this.padding, this.padding + this.trackHeight + 10);
    this.drawAminoAcidTrack(displaySeq, this.padding, this.padding + this.trackHeight * 2 + 20);

    // Mensaje si fue truncado
    if (sequence.length > maxNucleotides) {
      this.ctx.fillStyle = this.colors.text;
      this.ctx.font = '12px sans-serif';
      this.ctx.fillText(
        `Mostrando primeros ${maxNucleotides} de ${sequence.length} nucleótidos`,
        this.padding,
        height - 10
      );
    }
  }

  drawNucleotideTrack(sequence, x, y) {
    this.ctx.font = 'bold 11px monospace';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i < sequence.length; i++) {
      const nt = sequence[i].toUpperCase();
      const posX = x + i * this.nucleotideWidth;

      // Fondo
      this.ctx.fillStyle = this.colors[nt] || '#9CA3AF';
      this.ctx.fillRect(posX, y, this.nucleotideWidth - 2, this.nucleotideHeight);

      // Letra
      this.ctx.fillStyle = 'white';
      this.ctx.fillText(nt, posX + this.nucleotideWidth / 2, y + this.nucleotideHeight / 2);
    }
  }

  drawCodonTrack(sequence, x, y) {
    this.ctx.font = '10px monospace';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i < sequence.length - 2; i += 3) {
      const codon = sequence.substring(i, i + 3).toUpperCase();
      const posX = x + i * this.nucleotideWidth;

      // Fondo del codón
      this.ctx.fillStyle = '#E9D5FF';
      this.ctx.fillRect(posX, y, this.nucleotideWidth * 3 - 2, this.nucleotideHeight);

      // Borde
      this.ctx.strokeStyle = '#7C3AED';
      this.ctx.lineWidth = 1;
      this.ctx.strokeRect(posX, y, this.nucleotideWidth * 3 - 2, this.nucleotideHeight);

      // Texto del codón
      this.ctx.fillStyle = '#5B21B6';
      this.ctx.fillText(codon, posX + (this.nucleotideWidth * 3) / 2, y + this.nucleotideHeight / 2);
    }
  }

  drawAminoAcidTrack(sequence, x, y) {
    this.ctx.font = 'bold 11px monospace';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';

    const codonTable = this.getCodonTable();

    for (let i = 0; i < sequence.length - 2; i += 3) {
      const codon = sequence.substring(i, i + 3).toUpperCase();
      const aa = codonTable[codon] || 'X';
      const posX = x + i * this.nucleotideWidth;

      // Fondo
      this.ctx.fillStyle = aa === '*' ? '#FEE2E2' : '#DBEAFE';
      this.ctx.fillRect(posX, y, this.nucleotideWidth * 3 - 2, this.nucleotideHeight);

      // Aminoácido
      this.ctx.fillStyle = aa === '*' ? '#DC2626' : '#1E40AF';
      this.ctx.fillText(aa, posX + (this.nucleotideWidth * 3) / 2, y + this.nucleotideHeight / 2);
    }
  }

  getCodonTable() {
    return {
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
    };
  }

  renderPlaceholder() {
    this.canvas.width = 600;
    this.canvas.height = 100;

    this.ctx.fillStyle = this.colors.background;
    this.ctx.fillRect(0, 0, 600, 100);

    this.ctx.fillStyle = this.colors.text;
    this.ctx.font = '14px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('No hay secuencia disponible para este gen', 300, 50);
  }
}

// ============================================
// EXPORTAR
// ============================================

window.GenomeViewer = GenomeViewer;
window.SequenceInspector = SequenceInspector;