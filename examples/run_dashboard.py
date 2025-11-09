#!/usr/bin/env python3
"""
Example: Running the YunMin Trading Dashboard

This script demonstrates how to start the web dashboard server.
The dashboard provides real-time monitoring with TradingView-style charts.

Usage:
    python examples/run_dashboard.py

    Or with custom port:
    python examples/run_dashboard.py --port 8080

Then open your browser to: http://localhost:5000
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description='Run YunMin Trading Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload on code changes')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 YunMin Trading Dashboard")
    print("=" * 60)
    print(f"\n📡 Starting server on http://{args.host}:{args.port}")
    print("\n📊 Features:")
    print("  • TradingView-style candlestick charts")
    print("  • Real-time portfolio monitoring")
    print("  • Live trade notifications")
    print("  • Binance-style dark theme")
    print("\n🌐 Open your browser to:")
    print(f"  http://localhost:{args.port}")
    print("\n⚡ Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    try:
        import uvicorn
        from yunmin.web.api import app
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )
    except ImportError as e:
        print(f"\n❌ Error: Missing dependency - {e}")
        print("\n💡 Install required packages:")
        print("   pip install fastapi uvicorn jinja2 python-multipart loguru")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
