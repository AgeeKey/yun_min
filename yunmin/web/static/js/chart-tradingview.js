/**
 * TradingView-style Candlestick Chart
 * Uses Lightweight Charts library (same as Binance)
 */

export class TradingChart {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
        this.candleSeries = null;
        this.volumeSeries = null;
        this.emaFastSeries = null;
        this.emaSlowSeries = null;
        this.markers = [];
        this.indicatorsVisible = true;
        
        this.init();
    }
    
    init() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error('Chart container not found:', this.containerId);
            return;
        }
        
        // Create chart with Binance-style dark theme
        this.chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight,
            layout: {
                background: { color: '#1e222d' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: '#2b2b43' },
                horzLines: { color: '#2b2b43' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: '#485c7b',
            },
            timeScale: {
                borderColor: '#485c7b',
                timeVisible: true,
                secondsVisible: false,
            },
        });
        
        // Add candlestick series (main chart)
        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        
        // Add volume histogram series
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: 'volume',
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });
        
        // Add EMA lines (Fast - 9 period)
        this.emaFastSeries = this.chart.addLineSeries({
            color: '#2196F3',
            lineWidth: 2,
            title: 'EMA 9',
            lastValueVisible: false,
            priceLineVisible: false,
        });
        
        // Add EMA lines (Slow - 21 period)
        this.emaSlowSeries = this.chart.addLineSeries({
            color: '#FF9800',
            lineWidth: 2,
            title: 'EMA 21',
            lastValueVisible: false,
            priceLineVisible: false,
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.chart.applyOptions({
                width: container.clientWidth,
            });
        });
    }
    
    /**
     * Update chart with new candlestick data
     * @param {Array} candles - Array of {time, open, high, low, close, volume}
     */
    setData(candles) {
        if (!this.candleSeries || !candles || candles.length === 0) {
            return;
        }
        
        // Set candlestick data
        this.candleSeries.setData(candles);
        
        // Set volume data
        const volumeData = candles.map(candle => ({
            time: candle.time,
            value: candle.volume || 0,
            color: candle.close >= candle.open ? '#26a69a80' : '#ef535080'
        }));
        this.volumeSeries.setData(volumeData);
        
        // Calculate and set EMA data
        const emaFastData = this.calculateEMA(candles, 9);
        const emaSlowData = this.calculateEMA(candles, 21);
        
        if (emaFastData.length > 0) {
            this.emaFastSeries.setData(emaFastData);
        }
        
        if (emaSlowData.length > 0) {
            this.emaSlowSeries.setData(emaSlowData);
        }
    }
    
    /**
     * Update the last candle in real-time
     * @param {Object} candle - {time, open, high, low, close, volume}
     */
    updateRealtime(candle) {
        if (!this.candleSeries) {
            return;
        }
        
        this.candleSeries.update(candle);
        
        // Update volume
        if (candle.volume) {
            this.volumeSeries.update({
                time: candle.time,
                value: candle.volume,
                color: candle.close >= candle.open ? '#26a69a80' : '#ef535080'
            });
        }
    }
    
    /**
     * Add a trade marker on the chart
     * @param {Object} trade - {time, price, side, text}
     */
    addTradeMarker(trade) {
        if (!this.candleSeries) {
            return;
        }
        
        const marker = {
            time: trade.time,
            position: trade.side === 'BUY' ? 'belowBar' : 'aboveBar',
            color: trade.side === 'BUY' ? '#26a69a' : '#ef5350',
            shape: trade.side === 'BUY' ? 'arrowUp' : 'arrowDown',
            text: trade.text || `${trade.side} @${trade.price}`,
        };
        
        this.markers.push(marker);
        this.candleSeries.setMarkers(this.markers);
    }
    
    /**
     * Clear all trade markers
     */
    clearMarkers() {
        this.markers = [];
        if (this.candleSeries) {
            this.candleSeries.setMarkers([]);
        }
    }
    
    /**
     * Toggle visibility of indicators (EMA lines)
     */
    toggleIndicators() {
        this.indicatorsVisible = !this.indicatorsVisible;
        
        if (this.emaFastSeries) {
            this.emaFastSeries.applyOptions({
                visible: this.indicatorsVisible
            });
        }
        
        if (this.emaSlowSeries) {
            this.emaSlowSeries.applyOptions({
                visible: this.indicatorsVisible
            });
        }
    }
    
    /**
     * Calculate Exponential Moving Average
     * @param {Array} candles - Array of candle data
     * @param {number} period - EMA period
     * @returns {Array} EMA data points
     */
    calculateEMA(candles, period) {
        if (candles.length < period) {
            return [];
        }
        
        const k = 2 / (period + 1);
        const emaData = [];
        
        // Calculate initial SMA
        let sum = 0;
        for (let i = 0; i < period; i++) {
            sum += candles[i].close;
        }
        let ema = sum / period;
        
        emaData.push({
            time: candles[period - 1].time,
            value: ema
        });
        
        // Calculate EMA for remaining candles
        for (let i = period; i < candles.length; i++) {
            ema = candles[i].close * k + ema * (1 - k);
            emaData.push({
                time: candles[i].time,
                value: ema
            });
        }
        
        return emaData;
    }
    
    /**
     * Fit chart content to visible range
     */
    fitContent() {
        if (this.chart) {
            this.chart.timeScale().fitContent();
        }
    }
    
    /**
     * Cleanup and destroy chart
     */
    destroy() {
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
        }
    }
}
