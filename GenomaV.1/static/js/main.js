// ============================================
// MAIN.JS - Aplicación Principal
// ============================================

// ============================================
// API CLIENT
// ============================================

class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Genomas
  async getGenomes() {
    return this.request('/api/genomes');
  }

  async getGenomeStats(genomeId) {
    return this.request(`/api/genomes/${genomeId}/stats`);
  }

  async compareGenomes(genome1, genome2) {
    return this.request('/api/genomes/compare', {
      method: 'POST',
      body: JSON.stringify({ genome1, genome2 })
    });
  }

  // Genes
  async searchGenes(params) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/genes?${query}`);
  }

  async getGeneDetail(geneId, genome) {
    return this.request(`/api/genes/${geneId}?genome=${genome}`);
  }

  // Proteínas
  async searchProteins(query, organism = null) {
    return this.request('/api/protein-designer/search', {
      method: 'POST',
      body: JSON.stringify({ query, organism, limit: 20 })
    });
  }

  async analyzeProtein(proteinId, genomeId, includeOptimization = true) {
    return this.request('/api/protein-designer/analyze', {
      method: 'POST',
      body: JSON.stringify({
        protein_id: proteinId,
        genome_id: genomeId,
        include_optimization: includeOptimization
      })
    });
  }

  async quickCheckProtein(proteinId) {
    return this.request('/api/protein-designer/quick-check', {
      method: 'POST',
      body: JSON.stringify({ protein_id: proteinId })
    });
  }

  // Health
  async getHealth() {
    return this.request('/api/health');
  }

  async getCacheStats() {
    return this.request('/api/cache/stats');
  }
}

// ============================================
// INDEXEDDB STORAGE
// ============================================

class StorageManager {
  constructor() {
    this.dbName = 'GenomeAnalyzerDB';
    this.version = 1;
    this.db = null;
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Store para análisis
        if (!db.objectStoreNames.contains('analyses')) {
          const store = db.createObjectStore('analyses', { keyPath: 'id', autoIncrement: true });
          store.createIndex('type', 'type', { unique: false });
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // Store para comparaciones
        if (!db.objectStoreNames.contains('comparisons')) {
          const store = db.createObjectStore('comparisons', { keyPath: 'id', autoIncrement: true });
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // Store para diseños genéticos
        if (!db.objectStoreNames.contains('designs')) {
          const store = db.createObjectStore('designs', { keyPath: 'id', autoIncrement: true });
          store.createIndex('proteinId', 'proteinId', { unique: false });
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };
    });
  }

  async save(storeName, data) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);

      const dataWithTimestamp = {
        ...data,
        timestamp: new Date().toISOString()
      };

      const request = store.add(dataWithTimestamp);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getAll(storeName) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getRecent(storeName, limit = 10) {
    const all = await this.getAll(storeName);
    return all.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, limit);
  }

  async clear(storeName) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
}

// ============================================
// UI MANAGER
// ============================================

class UIManager {
  constructor() {
    this.sidebar = document.getElementById('sidebar');
    this.sidebarToggle = document.getElementById('sidebar-toggle');
    this.navItems = document.querySelectorAll('.nav-item:not(.disabled)');
    this.sections = document.querySelectorAll('.content-section');
  }

  init() {
    this.setupSidebar();
    this.setupNavigation();
  }

  setupSidebar() {
    this.sidebarToggle?.addEventListener('click', () => {
      this.sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', this.sidebar.classList.contains('collapsed'));
    });

    // Restaurar estado del sidebar
    const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (collapsed) {
      this.sidebar.classList.add('collapsed');
    }
  }

  setupNavigation() {
    this.navItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const section = item.dataset.section;
        this.navigateTo(section);
      });
    });

    // Navegación con hash
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.slice(1);
      if (hash) this.navigateTo(hash);
    });

    // Cargar sección inicial
    const initialSection = window.location.hash.slice(1) || 'dashboard';
    this.navigateTo(initialSection);
  }

  navigateTo(sectionId) {
    // Actualizar secciones
    this.sections.forEach(section => {
      section.classList.toggle('active', section.id === sectionId);
    });

    // Actualizar nav items
    this.navItems.forEach(item => {
      item.classList.toggle('active', item.dataset.section === sectionId);
    });

    // Actualizar hash
    window.location.hash = sectionId;

    // Cerrar sidebar en mobile
    if (window.innerWidth < 768) {
      this.sidebar.classList.remove('open');
    }
  }

  showLoading(show = true) {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = show ? 'flex' : 'none';
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span style="font-size: 1.5rem;">${this.getToastIcon(type)}</span>
      <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  getToastIcon(type) {
    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };
    return icons[type] || icons.info;
  }
}

// ============================================
// APP PRINCIPAL
// ============================================

class GenomeAnalyzerApp {
  constructor() {
    this.api = new APIClient();
    this.storage = new StorageManager();
    this.ui = new UIManager();
    this.genomes = [];
  }

  async init() {
    console.log('🧬 Inicializando Genome Analyzer...');

    try {
      // Inicializar storage
      await this.storage.init();
      console.log('✓ Storage inicializado');

      // Inicializar UI
      this.ui.init();
      console.log('✓ UI inicializada');

      // Cargar genomas disponibles
      await this.loadGenomes();

      // Setup event listeners
      this.setupEventListeners();

      // Cargar dashboard
      await this.loadDashboard();

      // Health check
      this.checkHealth();

      console.log('✓ Aplicación lista');
    } catch (error) {
      console.error('Error inicializando:', error);
      this.ui.showToast('Error al inicializar la aplicación', 'error');
    }
  }

  async loadGenomes() {
    try {
      const data = await this.api.getGenomes();
      this.genomes = data.genomes || [];

      // Poblar selects
      this.populateGenomeSelects();

      console.log(`✓ ${this.genomes.length} genomas cargados`);
    } catch (error) {
      console.error('Error cargando genomas:', error);
    }
  }

  populateGenomeSelects() {
    const selects = [
      'genome-select',
      'viewer-genome-select',
      'compare-genome1',
      'compare-genome2',
      'target-genome',
      'dual-genome1',   // ⭐ AGREGAR
      'dual-genome2'    // ⭐ AGREGAR
    ];

    selects.forEach(id => {
      const select = document.getElementById(id);
      if (select) {
        select.innerHTML = '<option value="">Seleccionar genoma...</option>';
        this.genomes.forEach(genome => {
          const option = document.createElement('option');
          option.value = genome.id;
          option.textContent = genome.name;
          select.appendChild(option);
        });
      }
    });
  }

  async loadDashboard() {
    try {
      // Cargar estadísticas
      const analyses = await this.storage.getAll('analyses');
      const comparisons = await this.storage.getAll('comparisons');
      const designs = await this.storage.getAll('designs');

      document.getElementById('total-genomes').textContent = this.genomes.length;
      document.getElementById('total-analyses').textContent = analyses.length;
      document.getElementById('total-comparisons').textContent = comparisons.length;
      document.getElementById('total-designs').textContent = designs.length;

      // Cargar análisis recientes
      await this.loadRecentAnalyses();
    } catch (error) {
      console.error('Error cargando dashboard:', error);
    }
  }

  async loadRecentAnalyses() {
    try {
      const recent = await this.storage.getRecent('analyses', 5);
      const container = document.getElementById('recent-analyses');

      if (recent.length === 0) {
        container.innerHTML = '<p class="text-muted">No hay análisis recientes</p>';
        return;
      }

      container.innerHTML = recent.map(item => `
        <div class="recent-item">
          <strong>${item.type}</strong> - ${item.genomeId || item.proteinId}
          <br>
          <small class="text-muted">${new Date(item.timestamp).toLocaleString()}</small>
        </div>
      `).join('');
    } catch (error) {
      console.error('Error cargando recientes:', error);
    }
  }

  async checkHealth() {
    try {
      const health = await this.api.getHealth();
      const cacheStats = await this.api.getCacheStats();

      document.getElementById('pipeline-version').textContent = health.version || 'v2.0.0';
      document.getElementById('cache-status').textContent =
        `${cacheStats.genomes_count || 0}G / ${cacheStats.proteins_count || 0}P`;
    } catch (error) {
      console.error('Error health check:', error);
    }
  }

  setupEventListeners() {
    // Genome Stats
    document.getElementById('analyze-genome-btn')?.addEventListener('click', () => {
      this.analyzeGenome();
    });

    // Gene Search
    document.getElementById('gene-search-btn')?.addEventListener('click', () => {
      this.searchGenes();
    });

    document.getElementById('gene-search-input')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.searchGenes();
    });

    // Compare Genomes
    document.getElementById('compare-btn')?.addEventListener('click', () => {
      this.compareGenomes();
    });

    // Protein Search
    document.getElementById('search-protein-btn')?.addEventListener('click', () => {
      this.searchProteins();
    });

    document.getElementById('protein-query')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.searchProteins();
    });

    // Protein Analyze
    document.getElementById('analyze-protein-btn')?.addEventListener('click', () => {
      this.analyzeProtein();
    });

    // Viewer
    document.getElementById('load-viewer-btn')?.addEventListener('click', () => {
      this.loadViewer();
    });

    // Dual Viewer (AGREGADO)
    document.getElementById('load-dual-viewer-btn')?.addEventListener('click', () => {
      this.loadDualViewer();
    });
  }

  // ============================================
  // ANÁLISIS DE GENOMA
  // ============================================

  async analyzeGenome() {
    const select = document.getElementById('genome-select');
    const genomeId = select.value;

    if (!genomeId) {
      this.ui.showToast('Por favor selecciona un genoma', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const data = await this.api.getGenomeStats(genomeId);

      // Guardar en storage
      await this.storage.save('analyses', {
        type: 'genome_stats',
        genomeId,
        data
      });

      // Mostrar resultados
      this.displayGenomeResults(data);

      this.ui.showToast('Análisis completado', 'success');
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  displayGenomeResults(data) {
    const container = document.getElementById('genome-results');
    container.style.display = 'block';

    container.innerHTML = `
      <div class="card">
        <h3 class="card-title">Información del Genoma</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div>
            <strong>Organismo:</strong><br>
            <em>${data.genome.organism}</em>
          </div>
          <div>
            <strong>Longitud:</strong><br>
            ${data.genome.length.toLocaleString()} bp
          </div>
          <div>
            <strong>GC Content:</strong><br>
            ${data.genome.gc_content}%
          </div>
          <div>
            <strong>Genes:</strong><br>
            ${data.genome.gene_count.toLocaleString()}
          </div>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">Compactación Génica</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div>
            <strong>Región Codificante:</strong><br>
            ${data.compactness.coding_percentage}%
          </div>
          <div>
            <strong>Densidad:</strong><br>
            ${data.compactness.gene_density} genes/Mb
          </div>
          <div>
            <strong>No Codificante:</strong><br>
            ${data.compactness.non_coding_length.toLocaleString()} bp
          </div>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">Codones de Inicio (CDS)</h3>
        <div class="chart-container">
          <canvas id="start-codons-chart"></canvas>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">Codones de Parada (CDS)</h3>
        <div class="chart-container">
          <canvas id="stop-codons-chart"></canvas>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">GC por Posición</h3>
        <div class="chart-container">
          <canvas id="gc-position-chart"></canvas>
        </div>
      </div>
    `;

    // Renderizar gráficos con timeout para asegurar que el DOM esté listo
    setTimeout(() => {
      if (window.ChartsManager) {
        const charts = new window.ChartsManager();

        if (data.codon_analysis?.cds?.start_codons) {
          charts.renderPieChart('start-codons-chart',
            Object.keys(data.codon_analysis.cds.start_codons),
            Object.values(data.codon_analysis.cds.start_codons),
            'Codones de Inicio'
          );
        }

        if (data.codon_analysis?.cds?.stop_codons) {
          charts.renderPieChart('stop-codons-chart',
            Object.keys(data.codon_analysis.cds.stop_codons),
            Object.values(data.codon_analysis.cds.stop_codons),
            'Codones de Parada'
          );
        }

        if (data.codon_analysis?.cds?.gc_position) {
          const gc = data.codon_analysis.cds.gc_position;
          charts.renderBarChart('gc-position-chart',
            ['GC1', 'GC2', 'GC3'],
            [gc.GC1, gc.GC2, gc.GC3],
            'GC por Posición del Codón (%)'
          );
        }
      }
    }, 100);
  }

  // ============================================
  // BÚSQUEDA DE GENES
  // ============================================

  async searchGenes() {
    const query = document.getElementById('gene-search-input').value.trim();
    const genome = document.getElementById('genome-select').value;
    const minLen = document.getElementById('gene-min-length').value;
    const maxLen = document.getElementById('gene-max-length').value;
    const sort = document.getElementById('gene-sort').value;

    if (!genome) {
      this.ui.showToast('Selecciona un genoma primero', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const params = {
        genome,
        search: query,
        sort,
        limit: 50
      };

      if (minLen) params.min_len = minLen;
      if (maxLen) params.max_len = maxLen;

      const data = await this.api.searchGenes(params);

      this.displayGeneResults(data);
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  displayGeneResults(data) {
    const container = document.getElementById('gene-results');

    if (!data.genes || data.genes.length === 0) {
      container.innerHTML = '<div class="card"><p class="text-muted">No se encontraron genes</p></div>';
      return;
    }

    container.innerHTML = `
      <div class="card">
        <p><strong>${data.total}</strong> genes encontrados (mostrando ${data.genes.length})</p>
        <div class="table-container" style="max-height: 600px; overflow-y: auto;">
          <table>
            <thead style="position: sticky; top: 0; background: var(--surface-dark); z-index: 10;">
              <tr>
                <th>Locus Tag</th>
                <th>Gen</th>
                <th>Producto</th>
                <th>Longitud</th>
                <th>GC%</th>
                <th>Strand</th>
                <th>Posición</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              ${data.genes.map(gene => `
                <tr>
                  <td><code>${gene.locus_tag}</code></td>
                  <td><strong>${gene.gene || '-'}</strong></td>
                  <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">${gene.product}</td>
                  <td>${gene.length.toLocaleString()} bp</td>
                  <td>${gene.gc_content.toFixed(1)}%</td>
                  <td style="text-align: center;">${gene.strand === 1 ? '➕' : '➖'}</td>
                  <td><small>${gene.start.toLocaleString()} - ${gene.end.toLocaleString()}</small></td>
                  <td>
                    <button class="btn btn-primary" style="padding: 4px 12px; font-size: 12px;"
                            onclick="window.app.showGeneDetail('${gene.id}', '${gene.locus_tag}')">
                      Ver Detalle
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // Nueva función para mostrar detalle de gen
  async showGeneDetail(geneId, locusTag) {
    const genome = document.getElementById('genome-select').value;
    if (!genome) {
      this.ui.showToast('Selecciona un genoma primero', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const data = await this.api.getGeneDetail(geneId, genome);

      // Mostrar modal o panel con detalle completo
      this.displayGeneDetailModal(data);
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  displayGeneDetailModal(gene) {
    // Crear modal temporal (luego lo mejoraremos)
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      z-index: 10000;
      max-width: 800px;
      max-height: 80vh;
      overflow-y: auto;
    `;

    modal.innerHTML = `
      <h2 style="color: var(--primary); margin-bottom: 20px;">Detalle del Gen</h2>
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px;">
        <div><strong>Locus Tag:</strong> ${gene.locus_tag}</div>
        <div><strong>Gen:</strong> ${gene.gene || '-'}</div>
        <div><strong>Producto:</strong> ${gene.product}</div>
        <div><strong>Longitud:</strong> ${gene.length.toLocaleString()} bp</div>
        <div><strong>GC%:</strong> ${gene.gc_content}%</div>
        <div><strong>Strand:</strong> ${gene.strand === 1 ? '+ (forward)' : '- (reverse)'}</div>
        <div><strong>Posición:</strong> ${gene.start.toLocaleString()} - ${gene.end.toLocaleString()}</div>
        <div><strong>Start Codon:</strong> ${gene.start_codon || '-'}</div>
      </div>

      ${gene.codon_analysis ? `
        <h3 style="color: var(--primary); margin-top: 20px;">Análisis de Codones</h3>
        <div style="background: var(--surface-dark); padding: 15px; border-radius: 8px; margin-top: 10px;">
          <p><strong>Total de codones:</strong> ${gene.codon_analysis.total_codons}</p>
          <p><strong>Codones únicos:</strong> ${gene.codon_analysis.unique_codons}</p>
          <p><strong>Top 3 más usados:</strong> ${gene.codon_analysis.most_common.slice(0, 3).map(c => c[0]).join(', ')}</p>
        </div>
      ` : ''}

      <button onclick="this.parentElement.remove(); document.getElementById('modal-overlay').remove();"
              style="margin-top: 20px; padding: 10px 20px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer;">
        Cerrar
      </button>
    `;

    // Overlay
    const overlay = document.createElement('div');
    overlay.id = 'modal-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 9999;
    `;
    overlay.onclick = () => {
      modal.remove();
      overlay.remove();
    };

    document.body.appendChild(overlay);
    document.body.appendChild(modal);
  }

  // ============================================
  // COMPARACIÓN DE GENOMAS
  // ============================================

  async compareGenomes() {
    const genome1 = document.getElementById('compare-genome1').value;
    const genome2 = document.getElementById('compare-genome2').value;

    if (!genome1 || !genome2) {
      this.ui.showToast('Selecciona ambos genomas', 'warning');
      return;
    }

    if (genome1 === genome2) {
      this.ui.showToast('Selecciona genomas diferentes', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const data = await this.api.compareGenomes(genome1, genome2);

      await this.storage.save('comparisons', {
        genome1,
        genome2,
        data
      });

      this.displayCompareResults(data);
      this.ui.showToast('Comparación completada', 'success');
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  displayCompareResults(data) {
    const container = document.getElementById('compare-results');
    container.style.display = 'block';

    // Protección contra división por cero
    const lengthDiff = data.differences?.length || 0;
    const geneCountDiff = data.differences?.gene_count || 0;
    const gcDiff = data.differences?.gc_content || 0;

    container.innerHTML = `
      <div class="content-grid">
        <div class="card">
          <h3 class="card-title">Genoma A</h3>
          <p><strong>${data.genome1.organism}</strong></p>
          <p>Longitud: ${data.genome1.length.toLocaleString()} bp</p>
          <p>Genes: ${data.genome1.gene_count.toLocaleString()}</p>
          <p>GC: ${data.genome1.gc_content}%</p>
        </div>

        <div class="card">
          <h3 class="card-title">Genoma B</h3>
          <p><strong>${data.genome2.organism}</strong></p>
          <p>Longitud: ${data.genome2.length.toLocaleString()} bp</p>
          <p>Genes: ${data.genome2.gene_count.toLocaleString()}</p>
          <p>GC: ${data.genome2.gc_content}%</p>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">Diferencias</h3>
        <p>Diferencia de longitud: ${Math.abs(lengthDiff).toLocaleString()} bp</p>
        <p>Diferencia de genes: ${Math.abs(geneCountDiff)}</p>
        <p>Diferencia de GC: ${Math.abs(gcDiff).toFixed(2)}%</p>
        <p><strong>Similitud:</strong> ${data.summary?.similar ? 'Alta' : 'Baja'}</p>
      </div>

      <div class="card">
        <h3 class="card-title">Comparación de Start Codons</h3>
        <div class="chart-container">
          <canvas id="compare-start-chart"></canvas>
        </div>
      </div>
    `;

    // Gráfico comparativo con protección
    setTimeout(() => {
      if (window.ChartsManager && data.differences?.start_codons) {
        try {
          const charts = new window.ChartsManager();
          const codons = Object.keys(data.differences.start_codons);
          const genome1Data = codons.map(c => data.differences.start_codons[c]?.genome1 || 0);
          const genome2Data = codons.map(c => data.differences.start_codons[c]?.genome2 || 0);

          charts.renderComparisonChart('compare-start-chart', codons, genome1Data, genome2Data,
            'Genoma A', 'Genoma B', 'Start Codons');
        } catch (error) {
          console.error('Error renderizando gráfico:', error);
        }
      }
    }, 100);
  }

  // ============================================
  // BÚSQUEDA DE PROTEÍNAS
  // ============================================

  async searchProteins() {
    const query = document.getElementById('protein-query').value.trim();
    const organism = document.getElementById('protein-organism').value.trim();

    if (!query) {
      this.ui.showToast('Ingresa un término de búsqueda', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const data = await this.api.searchProteins(query, organism || null);

      this.displayProteinResults(data);
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  displayProteinResults(data) {
    const container = document.getElementById('protein-results');

    if (!data.results || data.results.length === 0) {
      container.innerHTML = '<div class="card"><p class="text-muted">No se encontraron proteínas</p></div>';
      return;
    }

    // Mensaje informativo
    container.innerHTML = `
      <div class="card" style="background: var(--info-light); border-left: 4px solid var(--info);">
        <p style="margin: 0; font-size: 0.9rem;">
          <strong>💡 Tip:</strong> Haz click en "Chequeo Rápido" para ver la compatibilidad de cada proteína con <em>E. coli</em> antes del análisis completo.
        </p>
      </div>

      <div class="card">
        <p><strong>${data.total}</strong> proteínas encontradas</p>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Accession</th>
                <th>Nombre</th>
                <th>Organismo</th>
                <th>Longitud</th>
                <th>Revisada</th>
                <th style="text-align: center;">Compatibilidad</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              ${data.results.map(protein => `
                <tr id="protein-row-${protein.accession}">
                  <td><code>${protein.accession}</code></td>
                  <td><strong>${protein.name}</strong></td>
                  <td><em>${protein.organism}</em></td>
                  <td>${protein.length} aa</td>
                  <td>${protein.reviewed ? '✓' : '—'}</td>
                  <td style="text-align: center;">
                    <div id="compat-${protein.accession}" style="display: inline-block;">
                      <button class="btn" style="padding: 4px 12px; font-size: 12px;"
                              onclick="window.app.quickCheckProtein('${protein.accession}')">
                        Chequear
                      </button>
                    </div>
                  </td>
                  <td>
                    <button class="btn btn-primary" style="padding: 4px 12px; font-size: 12px;"
                            onclick="window.app.setProteinId('${protein.accession}')">
                      Analizar
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  async quickCheckProtein(proteinId) {
    const compatCell = document.getElementById(`compat-${proteinId}`);

    // Mostrar loading
    compatCell.innerHTML = '<span style="font-size: 0.75rem;">⏳</span>';

    try {
      const data = await this.api.quickCheckProtein(proteinId);

      // Determinar color del semáforo
      const compatibility = data.compatibility;
      let color, emoji, text;

      if (compatibility === 'ok') {
        color = 'var(--success)';
        emoji = '🟢';
        text = 'Compatible';
      } else if (compatibility === 'conditions') {
        color = 'var(--warning)';
        emoji = '🟡';
        text = 'Con Condiciones';
      } else {
        color = 'var(--danger)';
        emoji = '🔴';
        text = 'Alto Riesgo';
      }

      // Mostrar semáforo
      compatCell.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem; justify-content: center;">
          <span style="font-size: 1.25rem;">${emoji}</span>
          <span style="font-size: 0.75rem; font-weight: 600; color: ${color};">${text}</span>
        </div>
      `;

      // Agregar tooltip con detalles
      compatCell.title = `Complejidad: ${data.complexity_score}/100\nAlertas Rojas: ${data.alerts.red.length}\nAlertas Amarillas: ${data.alerts.yellow.length}`;

    } catch (error) {
      console.error('Error:', error);
      compatCell.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-muted);">Error</span>';
    }
  }

  setProteinId(accession) {
    document.getElementById('protein-id').value = accession;
    this.ui.navigateTo('protein-analyze');
    this.ui.showToast(`Proteína ${accession} seleccionada`, 'success');
  }

  // ============================================
  // ANÁLISIS DE PROTEÍNA
  // ============================================

  async analyzeProtein() {
    const proteinId = document.getElementById('protein-id').value.trim();
    const genomeId = document.getElementById('target-genome').value;

    if (!proteinId) {
      this.ui.showToast('Ingresa un ID de proteína', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const data = await this.api.analyzeProtein(proteinId, genomeId, true);

      await this.storage.save('designs', {
        proteinId,
        genomeId,
        data
      });

      this.displayProteinAnalysis(data);
      this.ui.showToast('Análisis completado', 'success');
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  displayProteinAnalysis(data) {
    const container = document.getElementById('protein-analysis-results');
    container.style.display = 'block';

    const compatibility = data.decision.compatibility;
    const compatibilityColors = {
      ok: 'success',
      conditions: 'warning',
      high_risk: 'danger'
    };

    container.innerHTML = `
      <div class="card">
        <h3 class="card-title">Proteína Objetivo</h3>
        <p><strong>${data.target_protein.name}</strong></p>
        <p><em>${data.target_protein.organism}</em></p>
        <p>Longitud: ${data.target_protein.length} aa</p>
        <p>Accession: <code>${data.target_protein.accession}</code></p>
      </div>

      <div class="card" style="border-left: 4px solid var(--${compatibilityColors[compatibility]});">
        <h3 class="card-title">Decisión del Sistema</h3>
        <p><strong>Base Case:</strong> ${data.decision.base_case === 'homolog_exists' ? 'Homólogo Existe' : 'Requiere Gen Externo'}</p>

        <!-- COMPATIBILIDAD (REEMPLAZADO) -->
        <p><strong>Compatibilidad:</strong> 
          ${compatibility === 'ok' ? '✅ Compatible' : 
            compatibility === 'conditions' ? '⚠️ Compatible con Condiciones' : 
            '❌ Alto Riesgo'}
        </p>

        <!-- EXPLICACIÓN (AGREGADA) -->
        ${compatibility === 'conditions' ? `
          <p style="background: var(--warning-light); padding: 0.75rem; border-radius: 8px; margin-top: 0.5rem;">
            <strong>¿Qué significa "Compatible con Condiciones"?</strong><br>
            La proteína puede expresarse en E. coli pero requiere consideraciones especiales 
            (ver alertas amarillas abajo). No es imposible, pero necesita optimización experimental.
          </p>
        ` : ''}

        <p><strong>Confianza:</strong> ${data.decision.confidence}</p>
        <p><strong>Recomendado:</strong> ${data.decision.is_recommended ? '✓ Sí' : '✗ No'}</p>
        <p style="margin-top: 1rem;">${data.decision.reasoning}</p>
      </div>

      ${data.alerts.red.length > 0 ? `
        <div class="card" style="background: var(--danger-light); border-left: 4px solid var(--danger);">
          <h3 class="card-title" style="color: var(--danger);">⚠️ Alertas Críticas</h3>
          ${data.alerts.red.map(alert => `
            <div style="margin-bottom: 1rem;">
              <strong>${alert.type}:</strong> ${alert.message}
              <br><small>${alert.evidence}</small>
            </div>
          `).join('')}
        </div>
      ` : ''}

      ${data.alerts.yellow.length > 0 ? `
        <div class="card" style="background: var(--warning-light); border-left: 4px solid var(--warning);">
          <h3 class="card-title" style="color: var(--warning);">⚡ Advertencias</h3>
          ${data.alerts.yellow.map(alert => `
            <div style="margin-bottom: 1rem;">
              <strong>${alert.type}:</strong> ${alert.message}
              <br><small>${alert.evidence}</small>
            </div>
          `).join('')}
        </div>
      ` : ''}

      ${data.best_local_candidate ? `
        <div class="card">
          <h3 class="card-title">Mejor Candidato Local</h3>
          <p><strong>Gen:</strong> ${data.best_local_candidate.gene_name} (${data.best_local_candidate.locus_tag})</p>
          <p><strong>Identidad:</strong> ${data.best_local_candidate.identity}%</p>
          <p><strong>Cobertura:</strong> ${data.best_local_candidate.coverage}%</p>
          <p>${data.best_local_candidate.note}</p>
        </div>
      ` : ''}

      <div class="card">
        <h3 class="card-title">Recomendaciones</h3>
        <ul>
          ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
        </ul>
      </div>

      <!-- Visualización de Secuencias (AGREGADO) -->
      ${data.target_protein.sequence ? `
        <div class="card">
          <h3 class="card-title">🧬 Visualización de Secuencias</h3>
          <div id="sequence-comparison-viewer"></div>
        </div>
      ` : ''}
    `;

    // Renderizar visualización de secuencias (AGREGADO) :contentReference[oaicite:2]{index=2}
    if (data.target_protein && data.target_protein.sequence) {
      setTimeout(() => {
        this.renderProteinSequence(data);
      }, 100);
    }

    // Guardar en storage (AGREGADO; si ya guardas arriba, igual no rompe) :contentReference[oaicite:3]{index=3}
    this.storage.save('designs', {
      protein_id: data.target_protein.accession,
      target_genome: data.genome_context?.genome_id,
      timestamp: Date.now(),
      decision: data.decision
    });
  }

  // ============================================
  // VISUALIZACIÓN DE SECUENCIAS (NUEVOS MÉTODOS)
  // ============================================

  renderProteinSequence(data) {
    const container = document.getElementById('sequence-comparison-viewer');
    if (!container) return;

    const sequence = data.target_protein.sequence;
    const maxLength = 300;

    // Evitar romper el atributo onclick si hay caracteres raros
    const safeSequenceForClipboard = String(sequence).replace(/\\/g, '\\\\').replace(/'/g, "\\'");

    container.innerHTML = `
      <div style="background: var(--surface-dark); padding: 1rem; border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; gap: 1rem;">
          <div>
            <strong>Secuencia de Aminoácidos</strong>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--text-muted);">
              ${sequence.length} aminoácidos ${sequence.length > maxLength ? `(mostrando primeros ${maxLength})` : ''}
            </p>
          </div>
          <button class="btn" onclick="navigator.clipboard.writeText('${safeSequenceForClipboard}'); window.app.ui.showToast('Secuencia copiada', 'success')">
            📋 Copiar Completa
          </button>
        </div>

        <div style="font-family: monospace; background: white; padding: 1rem; border-radius: 8px;
                    font-size: 0.875rem; line-height: 1.8; overflow-x: auto; max-height: 300px; overflow-y: auto;">
          ${this.formatSequenceWithColors(sequence.substring(0, maxLength))}
          ${sequence.length > maxLength ? '<div style="text-align: center; color: var(--text-muted); margin-top: 1rem;">...</div>' : ''}
        </div>

        <div style="margin-top: 1rem; padding: 1rem; background: var(--info-light); border-radius: 8px;">
          <strong>📊 Análisis de Composición:</strong>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 0.5rem;">
            <div>
              <div style="font-size: 1.25rem; font-weight: bold; color: var(--info);">
                ${this.calculateHydrophobicity(sequence).toFixed(1)}%
              </div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">Hidrofóbicos</div>
            </div>
            <div>
              <div style="font-size: 1.25rem; font-weight: bold; color: var(--info);">
                ${this.calculateCharged(sequence).toFixed(1)}%
              </div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">Cargados</div>
            </div>
            <div>
              <div style="font-size: 1.25rem; font-weight: bold; color: var(--info);">
                ${this.calculateSpecial(sequence).toFixed(1)}%
              </div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">Especiales (C,M,W)</div>
            </div>
          </div>
        </div>

        ${data.codon_optimization ? `
          <div style="margin-top: 1rem;">
            <strong>🔬 Optimización de Codones</strong>
            <p style="margin: 0.5rem 0; font-size: 0.875rem; color: var(--text-muted);">
              Secuencia de DNA optimizada para expresión en E. coli
            </p>
            <div style="font-family: monospace; background: var(--success-light); padding: 1rem; border-radius: 8px;
                        font-size: 0.75rem; line-height: 1.8; overflow-x: auto; max-height: 200px; overflow-y: auto;">
              ${this.formatDNASequence((sequence.substring(0, maxLength / 3) || 'ATGAAA').repeat(3))}
            </div>
            <button class="btn btn-primary" style="margin-top: 0.5rem;"
                    onclick="alert('Función de optimización completa próximamente')">
              📥 Descargar Secuencia Optimizada
            </button>
          </div>
        ` : ''}
      </div>
    `;
  }

  formatSequenceWithColors(sequence) {
    const colors = {
      // Básicos cargados
      'R': '#3B82F6', 'K': '#3B82F6', 'D': '#EF4444', 'E': '#EF4444',
      // Polares
      'Q': '#10B981', 'N': '#10B981', 'H': '#10B981', 'S': '#10B981', 'T': '#10B981', 'Y': '#10B981',
      // Especiales
      'C': '#F59E0B', 'M': '#F59E0B', 'W': '#F59E0B',
      // Hidrofóbicos
      'A': '#6B7280', 'V': '#6B7280', 'L': '#6B7280', 'I': '#6B7280', 'F': '#6B7280',
      // Otros
      'P': '#8B5CF6', 'G': '#9CA3AF'
    };

    let formatted = '';
    for (let i = 0; i < sequence.length; i++) {
      const aa = sequence[i];
      const color = colors[aa] || '#1F2937';
      formatted += `<span style="color: ${color}; font-weight: 600;">${aa}</span>`;

      if ((i + 1) % 10 === 0) formatted += ' ';
      if ((i + 1) % 60 === 0) formatted += '<br>';
    }
    return formatted;
  }

  formatDNASequence(sequence) {
    const colors = {
      'A': '#10B981',
      'T': '#3B82F6',
      'G': '#F59E0B',
      'C': '#EF4444'
    };

    let formatted = '';
    for (let i = 0; i < sequence.length; i++) {
      const nt = sequence[i];
      const color = colors[nt] || '#1F2937';
      formatted += `<span style="color: ${color}; font-weight: 600;">${nt}</span>`;

      if ((i + 1) % 3 === 0) formatted += ' ';
      if ((i + 1) % 60 === 0) formatted += '<br>';
    }
    return formatted;
  }

  calculateHydrophobicity(sequence) {
    const hydrophobic = 'AVILMFYW';
    let count = 0;
    for (let aa of sequence) {
      if (hydrophobic.includes(aa)) count++;
    }
    return (count / sequence.length) * 100;
  }

  calculateCharged(sequence) {
    const charged = 'RKDE';
    let count = 0;
    for (let aa of sequence) {
      if (charged.includes(aa)) count++;
    }
    return (count / sequence.length) * 100;
  }

  calculateSpecial(sequence) {
    const special = 'CMW';
    let count = 0;
    for (let aa of sequence) {
      if (special.includes(aa)) count++;
    }
    return (count / sequence.length) * 100;
  }

  // ============================================
  // DUAL VIEWER (NUEVO)
  // ============================================

  async loadDualViewer() {
    const genome1Id = document.getElementById('dual-genome1')?.value;
    const genome2Id = document.getElementById('dual-genome2')?.value;

    if (!genome1Id || !genome2Id) {
      this.ui.showToast('Selecciona ambos genomas', 'warning');
      return;
    }

    if (genome1Id === genome2Id) {
      this.ui.showToast('Selecciona genomas diferentes', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      const viewer1 = new window.GenomeViewer('circular-viewer-1');
      const viewer2 = new window.GenomeViewer('circular-viewer-2');

      await Promise.all([
        viewer1.render(genome1Id),
        viewer2.render(genome2Id)
      ]);

      document.getElementById('dual-viewer-container').style.display = 'block';
      await this.loadDualStats(genome1Id, genome2Id);
      this.ui.showToast('Comparación cargada', 'success');
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }

  async loadDualStats(genome1Id, genome2Id) {
    try {
      const data = await this.api.compareGenomes(genome1Id, genome2Id);

      document.getElementById('dual-stats').innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div>
            <strong>Diferencia de Longitud:</strong><br>
            ${data.differences.length.toLocaleString()} bp
          </div>
          <div>
            <strong>Diferencia de Genes:</strong><br>
            ${data.differences.gene_count} genes
          </div>
          <div>
            <strong>Diferencia de GC:</strong><br>
            ${data.differences.gc_content.toFixed(2)}%
          </div>
          <div>
            <strong>Similitud:</strong><br>
            ${data.summary.similar ? '✓ Alta' : '✗ Baja'}
          </div>
        </div>
      `;

      if (window.ChartsManager) {
        const charts = new window.ChartsManager();
        if (typeof charts.renderGenomeComparisonSummary === 'function') {
          charts.renderGenomeComparisonSummary('dual-comparison-chart', data.genome1, data.genome2);
        }
      }
    } catch (error) {
      console.error('Error:', error);
    }
  }

  // ============================================
  // VISUALIZADOR
  // ============================================

  async loadViewer() {
    const genomeId = document.getElementById('viewer-genome-select').value;

    if (!genomeId) {
      this.ui.showToast('Selecciona un genoma', 'warning');
      return;
    }

    this.ui.showLoading(true);

    try {
      // (Opcional) Mantener este fetch si lo usas para algo más,
      // pero NO lo pases al viewer.render()
      await this.api.getGenomeStats(genomeId);

      // Inicializar visualizador (si está disponible)
      if (window.GenomeViewer) {
        const viewer = new window.GenomeViewer('circular-viewer');
        await viewer.render(genomeId); // ✅ AQUÍ el fix: pasar genomeId
      } else {
        document.getElementById('circular-viewer').innerHTML = `
          <div style="text-align: center; color: var(--text-muted);">
            <p>Visualizador en desarrollo</p>
            <p>Genoma: ${genomeId}</p>
          </div>
        `;
      }

      this.ui.showToast('Visualización cargada', 'success');
    } catch (error) {
      console.error('Error:', error);
      this.ui.showToast(`Error: ${error.message}`, 'error');
    } finally {
      this.ui.showLoading(false);
    }
  }


  navigateTo(section) {
    this.ui.navigateTo(section);
  }
}

// ============================================
// INICIALIZACIÓN
// ============================================

window.addEventListener('DOMContentLoaded', async () => {
  window.app = new GenomeAnalyzerApp();
  await window.app.init();
});
