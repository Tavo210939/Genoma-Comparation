// ============================================
// CHARTS.JS - Wrapper de Chart.js
// ============================================

class ChartsManager {
  constructor() {
    this.charts = {};
    this.defaultColors = {
      primary: '#7C3AED',
      primaryLight: '#A78BFA',
      success: '#10B981',
      warning: '#F59E0B',
      danger: '#EF4444',
      info: '#3B82F6',
      purple: ['#7C3AED', '#A78BFA', '#DDD6FE', '#E9D5FF'],
      gradient: ['#7C3AED', '#9333EA', '#A855F7', '#C084FC', '#D8B4FE']
    };
  }

  // ============================================
  // UTILIDADES
  // ============================================

  destroyChart(canvasId) {
    if (this.charts[canvasId]) {
      this.charts[canvasId].destroy();
      delete this.charts[canvasId];
    }
  }

  getCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      console.error(`Canvas ${canvasId} not found`);
      return null;
    }
    return canvas;
  }

  // ============================================
  // GRÁFICOS DE TORTA (PIE)
  // ============================================

  renderPieChart(canvasId, labels, data, title = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: this.defaultColors.gradient,
          borderColor: '#FFFFFF',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 15,
              font: {
                size: 12,
                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
              },
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold',
              family: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
            },
            color: '#1F2937',
            padding: 20
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS DE DONA (DOUGHNUT)
  // ============================================

  renderDoughnutChart(canvasId, labels, data, title = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: this.defaultColors.gradient,
          borderColor: '#FFFFFF',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 15,
              font: {
                size: 12,
                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
              },
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS DE BARRAS
  // ============================================

  renderBarChart(canvasId, labels, data, title = '', horizontal = false) {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: horizontal ? 'bar' : 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: title,
          data: data,
          backgroundColor: this.defaultColors.primary,
          borderColor: this.defaultColors.primary,
          borderWidth: 0,
          borderRadius: 6,
          barThickness: 'flex',
          maxBarThickness: 60
        }]
      },
      options: {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            cornerRadius: 8,
            titleFont: {
              size: 14
            },
            bodyFont: {
              size: 13
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: !horizontal,
              color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              font: {
                size: 12
              }
            }
          },
          y: {
            grid: {
              display: horizontal,
              color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              font: {
                size: 12
              }
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS DE LÍNEAS
  // ============================================

  renderLineChart(canvasId, labels, datasets, title = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    // Formatear datasets si es array simple
    if (!Array.isArray(datasets[0])) {
      datasets = [{
        label: title,
        data: datasets,
        borderColor: this.defaultColors.primary,
        backgroundColor: 'rgba(124, 58, 237, 0.1)',
        tension: 0.4
      }];
    }

    this.charts[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: datasets.map((dataset, i) => ({
          ...dataset,
          borderColor: dataset.borderColor || this.defaultColors.gradient[i % this.defaultColors.gradient.length],
          backgroundColor: dataset.backgroundColor || `rgba(124, 58, 237, ${0.1 + (i * 0.1)})`,
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: 'top',
            labels: {
              padding: 15,
              usePointStyle: true
            }
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            }
          },
          y: {
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS DE COMPARACIÓN (BARRAS AGRUPADAS)
  // ============================================

  renderComparisonChart(canvasId, labels, data1, data2, label1, label2, title = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: label1,
            data: data1,
            backgroundColor: this.defaultColors.primary,
            borderColor: this.defaultColors.primary,
            borderWidth: 0,
            borderRadius: 6
          },
          {
            label: label2,
            data: data2,
            backgroundColor: this.defaultColors.primaryLight,
            borderColor: this.defaultColors.primaryLight,
            borderWidth: 0,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              padding: 15,
              usePointStyle: true
            }
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            }
          },
          y: {
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS DE ÁREA APILADA
  // ============================================

  renderStackedAreaChart(canvasId, labels, datasets, title = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: datasets.map((dataset, i) => ({
          label: dataset.label,
          data: dataset.data,
          borderColor: this.defaultColors.gradient[i % this.defaultColors.gradient.length],
          backgroundColor: `rgba(124, 58, 237, ${0.3 - (i * 0.05)})`,
          borderWidth: 2,
          fill: true,
          tension: 0.4
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top'
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: {
              display: false
            }
          },
          y: {
            stacked: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS RADIALES (RADAR)
  // ============================================

  renderRadarChart(canvasId, labels, datasets, title = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    // Formatear datasets
    if (!Array.isArray(datasets[0])) {
      datasets = [{
        label: title,
        data: datasets,
        borderColor: this.defaultColors.primary,
        backgroundColor: 'rgba(124, 58, 237, 0.2)'
      }];
    }

    this.charts[canvasId] = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: datasets.map((dataset, i) => ({
          ...dataset,
          borderColor: dataset.borderColor || this.defaultColors.gradient[i],
          backgroundColor: dataset.backgroundColor || `rgba(124, 58, 237, ${0.2 + (i * 0.1)})`,
          borderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }))
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: 'top'
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        },
        scales: {
          r: {
            beginAtZero: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            },
            angleLines: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICO DE DISPERSIÓN
  // ============================================

  renderScatterPlot(canvasId, data, title = '', xLabel = '', yLabel = '') {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: title,
          data: data,
          backgroundColor: this.defaultColors.primary,
          borderColor: this.defaultColors.primary,
          pointRadius: 6,
          pointHoverRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          title: {
            display: !!title,
            text: title,
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        },
        scales: {
          x: {
            title: {
              display: !!xLabel,
              text: xLabel
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            }
          },
          y: {
            title: {
              display: !!yLabel,
              text: yLabel
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            }
          }
        }
      }
    });
  }

  // ============================================
  // GRÁFICOS ESPECIALIZADOS PARA GENÓMICA
  // ============================================

  renderGCContentChart(canvasId, gc1, gc2, gc3) {
    this.renderBarChart(canvasId, 
      ['Primera Posición', 'Segunda Posición', 'Tercera Posición'],
      [gc1, gc2, gc3],
      'Contenido GC por Posición del Codón (%)'
    );
  }

  renderCodonUsageComparison(canvasId, codons, genome1Data, genome2Data, genome1Name, genome2Name) {
    this.renderComparisonChart(canvasId, codons, genome1Data, genome2Data, 
      genome1Name, genome2Name, 'Comparación de Uso de Codones');
  }

  renderGeneDistribution(canvasId, lengths, frequencies) {
    const canvas = this.getCanvas(canvasId);
    if (!canvas) return;

    this.destroyChart(canvasId);

    const ctx = canvas.getContext('2d');

    this.charts[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: lengths,
        datasets: [{
          label: 'Número de Genes',
          data: frequencies,
          backgroundColor: this.defaultColors.primary,
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          title: {
            display: true,
            text: 'Distribución de Longitudes de Genes',
            font: {
              size: 16,
              weight: 'bold'
            },
            color: '#1F2937',
            padding: 20
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Longitud (bp)'
            },
            grid: {
              display: false
            }
          },
          y: {
            title: {
              display: true,
              text: 'Frecuencia'
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            beginAtZero: true
          }
        }
      }
    });
  }

  // ============================================
  // DESTRUIR TODOS LOS GRÁFICOS
  // ============================================

  destroyAll() {
    Object.keys(this.charts).forEach(id => {
      this.destroyChart(id);
    });
  }
}

// ============================================
// EXPORTAR
// ============================================

window.ChartsManager = ChartsManager;

// ============================================
// EJEMPLO DE USO
// ============================================

/*
const charts = new ChartsManager();

// Gráfico de torta
charts.renderPieChart('my-canvas', 
  ['ATG', 'GTG', 'TTG', 'Otros'],
  [850, 120, 45, 10],
  'Codones de Inicio'
);

// Gráfico de barras
charts.renderBarChart('my-canvas',
  ['GC1', 'GC2', 'GC3'],
  [52.3, 55.1, 53.7],
  'GC por Posición'
);

// Comparación
charts.renderComparisonChart('my-canvas',
  ['ATG', 'GTG', 'TTG'],
  [850, 120, 45],  // Genoma 1
  [920, 95, 38],   // Genoma 2
  'K-12 MG1655',
  'W3110',
  'Codones de Inicio'
);
*/