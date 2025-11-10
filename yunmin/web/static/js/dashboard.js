/**
 * Main Dashboard Application
 * Coordinates charts, WebSocket, and UI updates
 */

import { TradingChart } from './chart-tradingview.js';
import { EquityChart } from './chart-equity.js';
import { DashboardWebSocket } from './websocket-client.js';

class Dashboard {
    constructor() {
        this.tradingChart = null;
        this.equityChart = null;
        this.ws = null;
        this.currentSymbol = 'BTC/USDT';
        this.currentInterval = '5m';
        this.updateInterval = null;
        
        this.init();
    }
    
    async init() {
        console.log('Initializing dashboard...');
        
        // Initialize charts
        this.tradingChart = new TradingChart('chart-container');
        this.equityChart = new EquityChart('equity-chart');
        
        // Load initial data
        await this.loadInitialData();
        
        // Connect WebSocket for real-time updates
        this.connectWebSocket();
        
        // Set up periodic updates as fallback
        this.startPeriodicUpdates();
        
        // Set up UI event listeners
        this.setupEventListeners();
        
        console.log('Dashboard initialized');
    }
    
    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Load portfolio metrics
            await this.loadPortfolio();
            
            // Load open positions
            await this.loadPositions();
            
            // Load recent trades
            await this.loadTrades();
            
            // Load equity curve
            await this.loadEquityCurve();
            
            // Load candlestick data
            await this.loadCandles();
            
            console.log('Initial data loaded');
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Error loading data', 'error');
        }
    }
    
    async loadPortfolio() {
        const response = await fetch('/api/portfolio');
        const portfolio = await response.json();
        this.updatePortfolioDisplay(portfolio);
    }
    
    async loadPositions() {
        const response = await fetch('/api/positions');
        const positions = await response.json();
        this.updatePositionsDisplay(positions);
    }
    
    async loadTrades() {
        const response = await fetch('/api/trades?limit=10');
        const trades = await response.json();
        this.updateTradesDisplay(trades);
    }
    
    async loadEquityCurve() {
        const response = await fetch('/api/equity-curve?days=7');
        const data = await response.json();
        this.equityChart.setData(data);
    }
    
    async loadCandles() {
        try {
            const response = await fetch(`/api/candles?symbol=${encodeURIComponent(this.currentSymbol)}&interval=${this.currentInterval}&limit=200`);
            const candles = await response.json();
            
            if (candles && candles.length > 0) {
                this.tradingChart.setData(candles);
                this.tradingChart.fitContent();
                
                // Update current price display
                const lastCandle = candles[candles.length - 1];
                this.updatePriceDisplay(lastCandle.close);
            }
        } catch (error) {
            console.error('Error loading candles:', error);
            // Generate mock data for demo
            this.loadMockCandles();
        }
    }
    
    loadMockCandles() {
        // Generate mock candlestick data for demo
        const now = Math.floor(Date.now() / 1000);
        const candles = [];
        let price = 50000;
        
        for (let i = 200; i > 0; i--) {
            const time = now - (i * 300); // 5-minute candles
            const open = price;
            const change = (Math.random() - 0.5) * 500;
            const close = open + change;
            const high = Math.max(open, close) + Math.random() * 200;
            const low = Math.min(open, close) - Math.random() * 200;
            const volume = Math.random() * 100 + 50;
            
            candles.push({ time, open, high, low, close, volume });
            price = close;
        }
        
        this.tradingChart.setData(candles);
        this.tradingChart.fitContent();
        this.updatePriceDisplay(price);
    }
    
    connectWebSocket() {
        this.ws = new DashboardWebSocket();
        
        this.ws.on('connected', () => {
            console.log('WebSocket connected');
            this.showNotification('Connected to live data', 'success');
        });
        
        this.ws.on('disconnected', () => {
            console.log('WebSocket disconnected');
            this.showNotification('Disconnected from live data', 'warning');
        });
        
        this.ws.on('update', (data) => {
            if (data.portfolio) {
                this.updatePortfolioDisplay(data.portfolio);
            }
            if (data.positions) {
                this.updatePositionsDisplay(data.positions);
            }
        });
        
        this.ws.on('price_update', (data) => {
            this.handlePriceUpdate(data);
        });
        
        this.ws.on('trade', (data) => {
            this.handleTradeUpdate(data);
        });
        
        this.ws.on('trade_executed', (trade) => {
            this.handleTradeUpdate(trade);
        });
        
        this.ws.on('position_update', (data) => {
            this.loadPositions();
        });
        
        this.ws.on('alert', (data) => {
            this.showNotification(data.message || data.title, data.level || 'info');
        });
    }
    
    handlePriceUpdate(data) {
        if (data.time && data.close) {
            this.tradingChart.updateRealtime(data);
            this.updatePriceDisplay(data.close);
        }
    }
    
    handleTradeUpdate(trade) {
        // Add trade marker to chart
        if (trade.time && trade.price) {
            this.tradingChart.addTradeMarker({
                time: trade.time,
                price: trade.price,
                side: trade.side,
                text: `${trade.side} @${trade.price.toFixed(2)}`
            });
        }
        
        // Reload trades list
        this.loadTrades();
        
        // Show notification
        const profitText = trade.pnl ? ` (${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)})` : '';
        this.showNotification(`Trade executed: ${trade.side} ${trade.symbol}${profitText}`, 'info');
    }
    
    updatePortfolioDisplay(portfolio) {
        // Update total value in header
        const totalValue = document.getElementById('total-value');
        if (totalValue && portfolio.current_equity !== undefined) {
            totalValue.textContent = `$${portfolio.current_equity.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}`;
        }
        
        // Update portfolio card
        const initialCapital = document.getElementById('initial-capital');
        if (initialCapital && portfolio.initial_capital !== undefined) {
            initialCapital.textContent = `$${portfolio.initial_capital.toLocaleString()}`;
        }
        
        const pnl = document.getElementById('pnl');
        if (pnl && portfolio.total_pnl !== undefined) {
            const pnlValue = portfolio.total_pnl;
            const pnlPct = portfolio.total_pnl_pct || 0;
            pnl.textContent = `${pnlValue >= 0 ? '+' : ''}$${pnlValue.toFixed(2)} (${pnlPct.toFixed(2)}%)`;
            pnl.className = `font-mono ${pnlValue >= 0 ? 'text-green-400' : 'text-red-400'}`;
        }
        
        const winRate = document.getElementById('win-rate');
        if (winRate && portfolio.win_rate !== undefined) {
            winRate.textContent = `${portfolio.win_rate.toFixed(1)}%`;
        }
        
        const tradeCount = document.getElementById('trade-count');
        if (tradeCount && portfolio.total_trades !== undefined) {
            tradeCount.textContent = portfolio.total_trades;
        }
    }
    
    updatePositionsDisplay(positions) {
        const container = document.getElementById('positions-list');
        if (!container) return;
        
        if (!positions || positions.length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-center">No open positions</p>';
            return;
        }
        
        container.innerHTML = positions.map(pos => {
            const pnlClass = pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400';
            const sideClass = pos.side === 'LONG' ? 'long' : 'short';
            
            return `
                <div class="position-card ${sideClass}">
                    <div class="flex justify-between mb-1">
                        <span class="font-bold">${pos.symbol}</span>
                        <span class="badge badge-${pos.side === 'LONG' ? 'success' : 'danger'}">${pos.side}</span>
                    </div>
                    <div class="text-xs text-gray-400">
                        Entry: $${pos.entry_price.toLocaleString()}<br>
                        Current: $${pos.current_price.toLocaleString()}<br>
                        Amount: ${pos.amount}
                    </div>
                    <div class="mt-2 ${pnlClass} font-bold">
                        ${pos.unrealized_pnl >= 0 ? '+' : ''}$${pos.unrealized_pnl.toFixed(2)} 
                        (${pos.unrealized_pnl_pct.toFixed(2)}%)
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updateTradesDisplay(trades) {
        const container = document.getElementById('trades-list');
        if (!container) return;
        
        if (!trades || trades.length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-center">No recent trades</p>';
            return;
        }
        
        container.innerHTML = trades.map(trade => {
            const pnlClass = trade.pnl >= 0 ? 'text-green-400' : 'text-red-400';
            const time = new Date(trade.exit_time).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            return `
                <div class="trade-item ${trade.side.toLowerCase()}">
                    <div>
                        <span class="font-bold">[${time}]</span>
                        <span class="badge badge-${trade.side === 'BUY' ? 'success' : 'danger'}">${trade.side}</span>
                        <span>${trade.symbol}</span>
                        <span class="text-gray-400">@$${trade.exit_price.toLocaleString()}</span>
                    </div>
                    <div class="${pnlClass} font-bold">
                        ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updatePriceDisplay(price) {
        const priceElement = document.getElementById('current-price');
        if (priceElement) {
            priceElement.textContent = `$${price.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}`;
        }
    }
    
    showNotification(message, level = 'info') {
        console.log(`[${level.toUpperCase()}] ${message}`);
        // Could implement toast notifications here
    }
    
    startPeriodicUpdates() {
        // Refresh data every 10 seconds as fallback
        this.updateInterval = setInterval(() => {
            if (!this.ws || !this.ws.isConnected()) {
                this.loadPortfolio();
                this.loadPositions();
            }
        }, 10000);
    }
    
    setupEventListeners() {
        // Symbol button
        const symbolBtn = document.getElementById('symbol-btn');
        if (symbolBtn) {
            symbolBtn.addEventListener('click', () => {
                // Could implement symbol selector
                console.log('Symbol selector not yet implemented');
            });
        }
        
        // Interval button
        const intervalBtn = document.getElementById('interval-btn');
        if (intervalBtn) {
            intervalBtn.addEventListener('click', () => {
                // Could implement interval selector
                console.log('Interval selector not yet implemented');
            });
        }
    }
    
    destroy() {
        if (this.ws) {
            this.ws.close();
        }
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.tradingChart) {
            this.tradingChart.destroy();
        }
        if (this.equityChart) {
            this.equityChart.destroy();
        }
    }
}

// Make toggleIndicators global for button onclick
window.toggleIndicators = function() {
    if (window.dashboardApp && window.dashboardApp.tradingChart) {
        window.dashboardApp.tradingChart.toggleIndicators();
    }
};

// Initialize dashboard when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.dashboardApp = new Dashboard();
    });
} else {
    window.dashboardApp = new Dashboard();
}
