/**
 * Equity Curve Chart using Chart.js
 * Shows portfolio value over time
 */

export class EquityChart {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chart = null;
        this.init();
    }
    
    init() {
        const ctx = document.getElementById(this.canvasId);
        if (!ctx) {
            console.error('Canvas element not found:', this.canvasId);
            return;
        }
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Value ($)',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#e0e0e0',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#667eea',
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += '$' + context.parsed.y.toLocaleString('en-US', {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    });
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: '#888',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: {
                            color: '#2a2a3e',
                            drawBorder: false
                        }
                    },
                    x: {
                        ticks: {
                            color: '#888',
                            maxRotation: 45,
                            minRotation: 0
                        },
                        grid: {
                            color: '#2a2a3e',
                            drawBorder: false
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Update chart with new equity data
     * @param {Array} data - Array of {timestamp, equity}
     */
    setData(data) {
        if (!this.chart || !data || data.length === 0) {
            return;
        }
        
        // Format timestamps to readable labels
        const labels = data.map(d => {
            const date = new Date(d.timestamp);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        });
        
        const values = data.map(d => d.equity);
        
        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = values;
        
        // Update line color based on trend
        const firstValue = values[0];
        const lastValue = values[values.length - 1];
        const isProfit = lastValue >= firstValue;
        
        this.chart.data.datasets[0].borderColor = isProfit ? '#26a69a' : '#ef5350';
        this.chart.data.datasets[0].backgroundColor = isProfit 
            ? 'rgba(38, 166, 154, 0.1)' 
            : 'rgba(239, 83, 80, 0.1)';
        
        this.chart.update('none');
    }
    
    /**
     * Add a new data point to the chart
     * @param {Object} dataPoint - {timestamp, equity}
     */
    addDataPoint(dataPoint) {
        if (!this.chart) {
            return;
        }
        
        const date = new Date(dataPoint.timestamp);
        const label = date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        this.chart.data.labels.push(label);
        this.chart.data.datasets[0].data.push(dataPoint.equity);
        
        // Keep only last 100 points for performance
        if (this.chart.data.labels.length > 100) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        
        this.chart.update('none');
    }
    
    /**
     * Destroy chart instance
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
}
