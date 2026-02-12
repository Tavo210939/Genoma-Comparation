// ============================================
// GENOME-VIEWER.JS - Visualización Interactiva
// Basado en prototipo pero conectado al backend real
// ============================================

class GenomeViewer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Dimensiones
    this.width = Math.min(this.container.clientWidth || 800, 900);
    this.height = 580;
    this.radius = Math.min(this.width, this.height) / 2 - 100;

    // Estado
    this.state = {
      rotation: 0,
      showGenes: true,
      selectedGene: null,
      genomeData: null,
      genes: []
    };

    this.svg = null;
    this.inspector = null;
  }

  async render(genomeId) {
    try {
      // Cargar datos del genoma
      const response = await fetch(`/api/genomes/${genomeId}/stats`);
      if (!response.ok) throw new Error('Failed to load genome');
      
      const data = await response.json();
      this.state.genomeData = data;

      // Cargar genes
      const genesResponse = await fetch(`/api/genes?genome=${genomeId}&limit=500`);
      const genesData = await genesResponse.json();
      this.state.genes = genesData.genes || [];

      // Limpiar y crear SVG
      this.clear();
      this.createSVG();
      this.drawGenome();
      this.setupInteractions();

      // Inicializar inspector
      if (!this.inspector) {
        this.inspector = new SequenceInspector('sequence-inspector');
      }

    } catch (error) {
      console.error('Error rendering genome:', error);
      this.showError(error.message);
    }
  }

  clear() {
    this.container.innerHTML = '';
  }

  showError(message) {
    this.container.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
        <div style="text-align: center;">
          <p style="font-size: 1.5rem; margin-bottom: 1rem;">⚠️</p>
          <p>Error: ${message}</p>
        </div>
      </div>
    `;
  }

  createSVG() {
    this.svg = d3.select(this.container)
      .append('svg')
      .attr('viewBox', `0 0 ${this.width} ${this.height}`)
      .attr('width', '100%')
      .attr('height', '100%')
      .style('background', 'var(--surface)');

    // Filtros
    const defs = this.svg.append('defs');
    defs.html(`
      <filter id="glow">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    `);

    // Grupo principal
    this.viewport = this.svg.append('g').attr('class', 'viewport');
    this.scene = this.viewport.append('g')
      .attr('class', 'scene')
      .attr('transform', `translate(${this.width / 2}, ${this.height / 2})`);
    
    this.disk = this.scene.append('g').attr('class', 'disk');
  }

  drawGenome() {
    const data = this.state.genomeData;
    if (!data) return;

    // Círculo base
    this.disk.append('circle')
      .attr('r', this.radius)
      .attr('fill', 'none')
      .attr('stroke', 'var(--border)')
      .attr('stroke-width', 2);

    // Información central
    this.drawCenterInfo();

    // Marcadores de posición
    this.drawPositionMarkers();

    // Genes como arcos
    this.drawGenes();
  }

  drawCenterInfo() {
    const data = this.state.genomeData.genome;
    const center = this.disk.append('g').attr('class', 'center-info');

    // Círculo interno
    center.append('circle')
      .attr('r', 90)
      .attr('fill', 'var(--surface-dark)')
      .attr('stroke', 'var(--border)')
      .attr('stroke-width', 1);

    // Organismo
    center.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', -30)
      .attr('fill', 'var(--primary)')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text(this.truncate(data.organism, 25));

    // Longitud
    center.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', -5)
      .attr('fill', 'var(--text-secondary)')
      .attr('font-size', '13px')
      .text(`${(data.length / 1000000).toFixed(2)} Mb`);

    // Genes
    center.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 15)
      .attr('fill', 'var(--text-secondary)')
      .attr('font-size', '13px')
      .text(`${data.gene_count.toLocaleString()} genes`);

    // GC
    center.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 35)
      .attr('fill', 'var(--text-secondary)')
      .attr('font-size', '13px')
      .text(`GC: ${data.gc_content}%`);
  }

  drawPositionMarkers() {
    const genomeLength = this.state.genomeData.genome.length;
    const markers = 12;
    const step = genomeLength / markers;

    for (let i = 0; i < markers; i++) {
      const angle = (i * 360 / markers) - 90;
      const rad = (angle * Math.PI) / 180;

      const x1 = Math.cos(rad) * (this.radius - 5);
      const y1 = Math.sin(rad) * (this.radius - 5);
      const x2 = Math.cos(rad) * (this.radius + 10);
      const y2 = Math.sin(rad) * (this.radius + 10);

      // Línea
      this.disk.append('line')
        .attr('x1', x1).attr('y1', y1)
        .attr('x2', x2).attr('y2', y2)
        .attr('stroke', 'var(--text-muted)')
        .attr('stroke-width', 2);

      // Label
      const position = Math.round(i * step);
      const labelX = Math.cos(rad) * (this.radius + 30);
      const labelY = Math.sin(rad) * (this.radius + 30);

      this.disk.append('text')
        .attr('x', labelX)
        .attr('y', labelY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('fill', 'var(--text-muted)')
        .attr('font-size', '10px')
        .text(`${(position / 1000).toFixed(0)}kb`);
    }
  }

  drawGenes() {
    const genes = this.state.genes;
    const genomeLength = this.state.genomeData.genome.length;

    if (!genes || genes.length === 0) return;

    // Limitar para rendimiento
    const maxGenes = 500;
    const displayGenes = genes.length > maxGenes ? this.sampleGenes(genes, maxGenes) : genes;

    const arc = d3.arc()
      .innerRadius(this.radius - 35)
      .outerRadius(this.radius - 5);

    const genesGroup = this.disk.append('g').attr('class', 'genes-group');

    displayGenes.forEach(gene => {
      const startAngle = (gene.start / genomeLength) * 2 * Math.PI - Math.PI / 2;
      const endAngle = (gene.end / genomeLength) * 2 * Math.PI - Math.PI / 2;

      // Color según strand
      const color = gene.strand === 1 ? 'var(--primary)' : 'var(--primary-light)';

      const path = genesGroup.append('path')
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
        .attr('data-gene-id', gene.id);

      // Interacciones
      path.on('mouseover', (event) => {
        d3.select(event.target)
          .attr('opacity', 1)
          .attr('stroke-width', 2)
          .attr('stroke', 'var(--warning)');

        this.showTooltip(event, gene);
      });

      path.on('mouseout', (event) => {
        d3.select(event.target)
          .attr('opacity', 0.7)
          .attr('stroke-width', 0.5)
          .attr('stroke', 'white');

        this.hideTooltip();
      });

      path.on('click', (event) => {
        this.selectGene(gene);
      });
    });
  }

  sampleGenes(genes, maxSamples) {
    const step = Math.floor(genes.length / maxSamples);
    return genes.filter((_, i) => i % step === 0);
  }

  setupInteractions() {
    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        this.viewport.attr('transform', event.transform);
      });

    this.svg.call(zoom);

    // Rotación con SHIFT
    const dragRotate = d3.drag()
      .filter((event) => event.shiftKey)
      .on('drag', (event) => {
        this.state.rotation += event.dx * 0.35;
        this.disk.attr('transform', `rotate(${this.state.rotation})`);
      });

    this.svg.call(dragRotate);
  }

  showTooltip(event, gene) {
    const tooltip = d3.select('body').select('.gene-tooltip');
    
    if (tooltip.empty()) {
      d3.select('body')
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
        .style('max-width', '300px');
    }

    d3.select('.gene-tooltip')
      .html(`
        <strong>${gene.gene || gene.locus_tag}</strong><br>
        <em>${gene.product}</em><br>
        <span style="color: #A78BFA;">Posición:</span> ${gene.start.toLocaleString()} - ${gene.end.toLocaleString()}<br>
        <span style="color: #A78BFA;">Longitud:</span> ${gene.length.toLocaleString()} bp<br>
        <span style="color: #A78BFA;">Strand:</span> ${gene.strand === 1 ? '+' : '-'}<br>
        <span style="color: #A78BFA;">GC:</span> ${gene.gc_content}%
      `)
      .style('left', `${event.pageX + 10}px`)
      .style('top', `${event.pageY - 50}px`)
      .style('opacity', 1);
  }

  hideTooltip() {
    d3.select('.gene-tooltip').style('opacity', 0);
  }

  selectGene(gene) {
    console.log('Gene selected:', gene);
    this.state.selectedGene = gene;

    // Mostrar inspector
    if (this.inspector) {
      this.inspector.show(gene);
    }
  }

  truncate(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
  }
}

// ============================================
// SEQUENCE INSPECTOR - Canvas
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
    this.gene = null;

    // Config visual
    this.nucleotideWidth = 12;
    this.trackHeight = 70;
    this.padding = 14;

    // Colores
    this.colors = {
      A: '#10B981',
      T: '#3B82F6',
      G: '#F59E0B',
      C: '#EF4444',
      background: '#FAFAF9',
      text: '#1F2937'
    };

    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div style="background: white; border-radius: 12px; padding: 20px; border: 1px solid var(--border);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
          <h3 style="margin: 0; color: var(--primary); font-size: 1.125rem;">Inspector de Secuencias</h3>
          <button onclick="document.getElementById('sequence-inspector').style.display='none'" 
                  style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-muted);">
            ×
          </button>
        </div>
        <div id="inspector-info" style="margin-bottom: 15px; padding: 12px; background: var(--surface-dark); border-radius: 8px; font-size: 14px;">
          <p class="text-muted">Selecciona un gen para inspeccionar</p>
        </div>
        <div style="overflow-x: auto; background: var(--background); border-radius: 8px; padding: 10px;">
          <canvas id="sequence-canvas"></canvas>
        </div>
      </div>
    `;

    this.canvas = document.getElementById('sequence-canvas');
    this.ctx = this.canvas.getContext('2d');
  }

  show(gene) {
    this.container.style.display = 'block';
    this.gene = gene;

    // Actualizar info
    document.getElementById('inspector-info').innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
        <div><strong>Gen:</strong> ${gene.gene || gene.locus_tag}</div>
        <div><strong>Producto:</strong> ${gene.product}</div>
        <div><strong>Posición:</strong> ${gene.start.toLocaleString()} - ${gene.end.toLocaleString()}</div>
        <div><strong>Longitud:</strong> ${gene.length.toLocaleString()} bp</div>
        <div><strong>Strand:</strong> ${gene.strand === 1 ? '+ (forward)' : '- (reverse)'}</div>
        <div><strong>GC%:</strong> ${gene.gc_content}%</div>
      </div>
    `;

    this.render();
  }

  render() {
    if (!this.gene || !this.gene.sequence) {
      this.renderPlaceholder();
      return;
    }

    const sequence = this.gene.sequence;
    const maxNucleotides = 100;
    const displaySeq = sequence.length > maxNucleotides ? sequence.substring(0, maxNucleotides) : sequence;

    // Dimensiones
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(800, displaySeq.length * this.nucleotideWidth + this.padding * 2);
    const height = this.trackHeight * 3 + this.padding * 4;

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;

    this.ctx.scale(dpr, dpr);

    // Fondo
    this.ctx.fillStyle = this.colors.background;
    this.ctx.fillRect(0, 0, width, height);

    // Tracks
    this.drawNucleotideTrack(displaySeq, this.padding, this.padding);
    this.drawCodonTrack(displaySeq, this.padding, this.padding + this.trackHeight + 10);
    this.drawAminoAcidTrack(displaySeq, this.padding, this.padding + (this.trackHeight + 10) * 2);

    // Mensaje si truncado
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
      this.ctx.fillRect(posX, y, this.nucleotideWidth - 2, 20);

      // Letra
      this.ctx.fillStyle = 'white';
      this.ctx.fillText(nt, posX + this.nucleotideWidth / 2, y + 10);
    }

    // Label
    this.ctx.fillStyle = this.colors.text;
    this.ctx.font = '12px sans-serif';
    this.ctx.textAlign = 'left';
    this.ctx.fillText('Nucleótidos:', x, y - 5);
  }

  drawCodonTrack(sequence, x, y) {
    this.ctx.font = '10px monospace';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i < sequence.length - 2; i += 3) {
      const codon = sequence.substring(i, i + 3).toUpperCase();
      const posX = x + i * this.nucleotideWidth;

      // Fondo
      this.ctx.fillStyle = 'rgba(124, 58, 237, 0.1)';
      this.ctx.fillRect(posX, y, this.nucleotideWidth * 3 - 2, 20);

      // Borde
      this.ctx.strokeStyle = 'var(--primary)';
      this.ctx.lineWidth = 1;
      this.ctx.strokeRect(posX, y, this.nucleotideWidth * 3 - 2, 20);

      // Texto
      this.ctx.fillStyle = 'var(--primary)';
      this.ctx.fillText(codon, posX + (this.nucleotideWidth * 3) / 2, y + 10);
    }

    // Label
    this.ctx.fillStyle = this.colors.text;
    this.ctx.font = '12px sans-serif';
    this.ctx.textAlign = 'left';
    this.ctx.fillText('Codones:', x, y - 5);
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
      this.ctx.fillRect(posX, y, this.nucleotideWidth * 3 - 2, 20);

      // AA
      this.ctx.fillStyle = aa === '*' ? '#DC2626' : '#1E40AF';
      this.ctx.fillText(aa, posX + (this.nucleotideWidth * 3) / 2, y + 10);
    }

    // Label
    this.ctx.fillStyle = this.colors.text;
    this.ctx.font = '12px sans-serif';
    this.ctx.textAlign = 'left';
    this.ctx.fillText('Aminoácidos:', x, y - 5);
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
    const width = 800;
    const height = 100;
    
    this.canvas.width = width;
    this.canvas.height = height;
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;

    this.ctx.fillStyle = this.colors.background;
    this.ctx.fillRect(0, 0, width, height);

    this.ctx.fillStyle = this.colors.text;
    this.ctx.font = '14px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('No hay secuencia disponible para este gen', width / 2, height / 2);
  }
}

// Exportar
window.GenomeViewer = GenomeViewer;
window.SequenceInspector = SequenceInspector;
