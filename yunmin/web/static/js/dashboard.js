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
        this.startTime = Date.now();
        
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
        
        // Start uptime counter
        this.startUptimeCounter();
        
        console.log('Dashboard initialized');
    }
    
    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Load all data in parallel
            await Promise.all([
                this.loadPortfolio(),
                this.loadPositions(),
                this.loadTrades(),
                this.loadEquityCurve(),
                this.loadCandles(),
                this.loadAIStatus(),
                this.loadTokenUsage(),
                this.loadSystemStatus(),
                this.loadAIDecisions(),
                this.loadPerformance()
            ]);
            
            console.log('Initial data loaded');
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Error loading data', 'error');
        }
    }
    
    async loadPortfolio() {
        try {
            const response = await fetch('/api/portfolio');
            const portfolio = await response.json();
            this.updatePortfolioDisplay(portfolio);
        } catch (error) {
            console.error('Error loading portfolio:', error);
        }
    }
    
    async loadPositions() {
        try {
            const response = await fetch('/api/positions');
            const positions = await response.json();
            this.updatePositionsDisplay(positions);
        } catch (error) {
            console.error('Error loading positions:', error);
        }
    }
    
    async loadTrades() {
        try {
            const response = await fetch('/api/trades?limit=10');
            const trades = await response.json();
            this.updateTradesDisplay(trades);
        } catch (error) {
            console.error('Error loading trades:', error);
        }
    }
    
    async loadEquityCurve() {
        try {
            const response = await fetch('/api/equity-curve?days=7');
            const data = await response.json();
            this.equityChart.setData(data);
        } catch (error) {
            console.error('Error loading equity curve:', error);
        }
    }
    
    async loadAIStatus() {
        try {
            const response = await fetch('/api/ai-status');
            const status = await response.json();
            this.updateAIStatusDisplay(status);
        } catch (error) {
            console.error('Error loading AI status:', error);
        }
    }
    
    async loadTokenUsage() {
        try {
            const response = await fetch('/api/token-usage');
            const usage = await response.json();
            this.updateTokenUsageDisplay(usage);
        } catch (error) {
            console.error('Error loading token usage:', error);
        }
    }
    
    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            this.updateSystemStatusDisplay(status);
        } catch (error) {
            console.error('Error loading system status:', error);
        }
    }
    
    async loadAIDecisions() {
        try {
            const response = await fetch('/api/ai-decisions?limit=10');
            const decisions = await response.json();
            this.updateAIDecisionTimeline(decisions);
        } catch (error) {
            console.error('Error loading AI decisions:', error);
        }
    }
    
    async loadPerformance() {
        try {
            const response = await fetch('/api/performance');
            const perf = await response.json();
            this.updatePerformanceDisplay(perf);
        } catch (error) {
            console.error('Error loading performance:', error);
        }
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
                
                // Update high/low
                const high = Math.max(...candles.slice(-24).map(c => c.high));
                const low = Math.min(...candles.slice(-24).map(c => c.low));
                this.updatePriceHighLow(high, low);
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
        
        const high = Math.max(...candles.slice(-24).map(c => c.high));
        const low = Math.min(...candles.slice(-24).map(c => c.low));
        this.updatePriceHighLow(high, low);
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
        
        this.ws.on('ai_update', (data) => {
            this.loadAIStatus();
            this.loadAIDecisions();
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
        
        const winRateTop = document.getElementById('win-rate-top');
        if (winRateTop && portfolio.win_rate !== undefined) {
            winRateTop.textContent = `${portfolio.win_rate.toFixed(1)}%`;
        }
        
        const tradeCount = document.getElementById('trade-count');
        if (tradeCount && portfolio.total_trades !== undefined) {
            tradeCount.textContent = portfolio.total_trades;
        }
        
        // Calculate ROI
        const roi = document.getElementById('roi');
        if (roi && portfolio.total_pnl_pct !== undefined) {
            const roiValue = portfolio.total_pnl_pct;
            roi.textContent = `${roiValue >= 0 ? '+' : ''}${roiValue.toFixed(2)}%`;
            roi.className = `font-mono ${roiValue >= 0 ? 'text-green-400' : 'text-red-400'}`;
        }
    }
    
    updatePerformanceDisplay(perf) {
        const dailyPnl = document.getElementById('daily-pnl');
        if (dailyPnl && perf.daily_pnl !== undefined) {
            dailyPnl.textContent = `${perf.daily_pnl >= 0 ? '+' : ''}$${perf.daily_pnl.toFixed(2)}`;
            dailyPnl.className = `text-lg font-bold font-mono ${perf.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`;
        }
        
        const maxDrawdown = document.getElementById('max-drawdown');
        if (maxDrawdown && perf.max_drawdown !== undefined) {
            maxDrawdown.textContent = `${perf.max_drawdown.toFixed(2)}%`;
        }
    }
    
    updateAIStatusDisplay(status) {
        // Strategic Brain
        if (status.strategic) {
            const s = status.strategic;
            this.updateElement('strategic-regime', s.regime?.toUpperCase() || 'N/A');
            this.updateElement('strategic-scenario', s.scenario || 'N/A');
            this.updateElement('strategic-decision', s.decision || 'HOLD');
            this.updateElement('strategic-confidence', `${(s.confidence || 0).toFixed(0)}%`);
            
            const confBar = document.getElementById('strategic-confidence-bar');
            if (confBar) {
                confBar.style.width = `${s.confidence || 0}%`;
            }
            
            const updateTime = s.last_update ? new Date(s.last_update).toLocaleTimeString() : '--';
            this.updateElement('strategic-update', updateTime);
            
            // Update decision color
            const decisionEl = document.getElementById('strategic-decision');
            if (decisionEl) {
                decisionEl.className = this.getDecisionClass(s.decision);
            }
            
            // Update regime badge
            const regimeEl = document.getElementById('strategic-regime');
            if (regimeEl) {
                regimeEl.className = this.getRegimeBadgeClass(s.regime);
            }
        }
        
        // Tactical Brain
        if (status.tactical) {
            const t = status.tactical;
            this.updateElement('tactical-regime', t.regime?.toUpperCase() || 'N/A');
            this.updateElement('tactical-scenario', t.scenario || 'N/A');
            this.updateElement('tactical-decision', t.decision || 'HOLD');
            this.updateElement('tactical-confidence', `${(t.confidence || 0).toFixed(0)}%`);
            
            const confBar = document.getElementById('tactical-confidence-bar');
            if (confBar) {
                confBar.style.width = `${t.confidence || 0}%`;
                confBar.className = `h-2 rounded-full ${this.getConfidenceBarColor(t.decision)}`;
            }
            
            const updateTime = t.last_update ? new Date(t.last_update).toLocaleTimeString() : '--';
            this.updateElement('tactical-update', updateTime);
            
            // Update decision color
            const decisionEl = document.getElementById('tactical-decision');
            if (decisionEl) {
                decisionEl.className = this.getDecisionClass(t.decision);
            }
            
            // Update regime badge
            const regimeEl = document.getElementById('tactical-regime');
            if (regimeEl) {
                regimeEl.className = this.getRegimeBadgeClass(t.regime);
            }
        }
    }
    
    updateTokenUsageDisplay(usage) {
        this.updateElement('tokens-today', usage.total_tokens_today?.toLocaleString() || '0');
        this.updateElement('tokens-week', usage.total_tokens_week?.toLocaleString() || '0');
        this.updateElement('tokens-month', usage.total_tokens_month?.toLocaleString() || '0');
        
        this.updateElement('cost-today', `$${(usage.cost_today || 0).toFixed(2)}`);
        this.updateElement('cost-week', `$${(usage.cost_week || 0).toFixed(2)}`);
        this.updateElement('cost-month', `$${(usage.cost_month || 0).toFixed(2)}`);
        
        this.updateElement('last-request-tokens', usage.last_request_tokens || '0');
        
        const lastReqTime = usage.last_request_time ? 
            new Date(usage.last_request_time).toLocaleTimeString() : '--';
        this.updateElement('last-request-time', lastReqTime);
        
        // Update model breakdown
        const breakdownEl = document.getElementById('model-breakdown');
        if (breakdownEl && usage.model_breakdown) {
            let html = '';
            for (const [model, tokens] of Object.entries(usage.model_breakdown)) {
                const colorClass = model.includes('o3') ? 'text-purple-400' : 'text-blue-400';
                html += `
                    <div class="flex justify-between text-xs">
                        <span class="${colorClass}">${model}:</span>
                        <span class="font-mono">${tokens.toLocaleString()} tokens</span>
                    </div>
                `;
            }
            breakdownEl.innerHTML = html;
        }
    }
    
    updateSystemStatusDisplay(status) {
        // Bot state
        const botState = document.getElementById('bot-state');
        const statusIndicator = document.getElementById('status-indicator');
        if (botState && status.bot_state) {
            botState.textContent = status.bot_state;
            if (statusIndicator) {
                statusIndicator.className = `w-3 h-3 rounded-full mr-2 ${
                    status.bot_state === 'RUNNING' ? 'bg-green-500 animate-pulse' :
                    status.bot_state === 'PAUSED' ? 'bg-yellow-500' : 'bg-red-500'
                }`;
            }
        }
        
        // Connection statuses
        this.updateConnectionStatus('binance-status', status.binance_connected);
        this.updateConnectionStatus('openai-status', status.openai_connected);
        
        // Version
        this.updateElement('version', status.version || '1.0.0');
        this.updateElement('footer-version', status.version || '1.0.0');
        
        // Last heartbeat
        const heartbeat = status.last_heartbeat ? 
            new Date(status.last_heartbeat).toLocaleTimeString() : '--';
        this.updateElement('last-heartbeat', heartbeat);
    }
    
    updateAIDecisionTimeline(decisions) {
        const container = document.getElementById('decision-timeline-items');
        if (!container) return;
        
        if (!decisions || decisions.length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-center w-full">No recent decisions</p>';
            return;
        }
        
        container.innerHTML = decisions.map(d => {
            const time = new Date(d.timestamp).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
            const decisionColor = this.getDecisionColor(d.decision);
            const brainIcon = d.brain_type === 'strategic' ? '🧠' : '⚡';
            const executed = d.executed ? '✓' : '✗';
            const executedColor = d.executed ? 'text-green-400' : 'text-red-400';
            
            return `
                <div class="flex-shrink-0 bg-gray-700 rounded-lg p-3 min-w-[140px]">
                    <div class="text-xs text-gray-400 mb-1">${time}</div>
                    <div class="flex items-center gap-1 mb-1">
                        <span>${brainIcon}</span>
                        <span class="font-bold ${decisionColor}">${d.decision}</span>
                    </div>
                    <div class="text-xs text-gray-400">
                        ${d.regime?.toUpperCase() || 'N/A'} | ${d.confidence?.toFixed(0) || 0}%
                    </div>
                    <div class="text-xs ${executedColor} mt-1">
                        ${executed} Executed
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updateConnectionStatus(elementId, connected) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        if (connected) {
            el.innerHTML = `
                <span class="w-2 h-2 bg-green-500 rounded-full mr-1"></span>
                <span class="text-green-400 text-xs">Connected</span>
            `;
        } else {
            el.innerHTML = `
                <span class="w-2 h-2 bg-red-500 rounded-full mr-1"></span>
                <span class="text-red-400 text-xs">Disconnected</span>
            `;
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
    
    updatePriceHighLow(high, low) {
        const highEl = document.getElementById('price-high');
        const lowEl = document.getElementById('price-low');
        
        if (highEl) highEl.textContent = `$${high.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
        if (lowEl) lowEl.textContent = `$${low.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
    }
    
    // Helper methods
    updateElement(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
    
    getDecisionClass(decision) {
        switch (decision?.toUpperCase()) {
            case 'BUY': return 'text-lg font-bold text-green-400';
            case 'SELL': return 'text-lg font-bold text-red-400';
            default: return 'text-lg font-bold text-yellow-400';
        }
    }
    
    getDecisionColor(decision) {
        switch (decision?.toUpperCase()) {
            case 'BUY': return 'text-green-400';
            case 'SELL': return 'text-red-400';
            default: return 'text-yellow-400';
        }
    }
    
    getRegimeBadgeClass(regime) {
        switch (regime?.toLowerCase()) {
            case 'bull': return 'badge badge-success';
            case 'bear': return 'badge badge-danger';
            default: return 'badge badge-warning';
        }
    }
    
    getConfidenceBarColor(decision) {
        switch (decision?.toUpperCase()) {
            case 'BUY': return 'bg-green-500';
            case 'SELL': return 'bg-red-500';
            default: return 'bg-blue-500';
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
                this.loadAIStatus();
                this.loadTokenUsage();
                this.loadSystemStatus();
            }
        }, 10000);
    }
    
    startUptimeCounter() {
        setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor((elapsed % 3600) / 60);
            this.updateElement('uptime', `${hours}h ${minutes}m`);
        }, 60000); // Update every minute
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
