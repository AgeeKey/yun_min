#!/usr/bin/env python3
"""
YunMin Trading Dashboard Server
Standalone entry point for running the real-time trading dashboard.

Usage:
    python dashboard_server.py [--host HOST] [--port PORT]

Examples:
    python dashboard_server.py
    python dashboard_server.py --port 8080
    python dashboard_server.py --host 0.0.0.0 --port 5000
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import uvicorn
    from loguru import logger
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install required packages: pip install uvicorn loguru")
    sys.exit(1)


def main():
    """Main entry point for the dashboard server."""
    parser = argparse.ArgumentParser(
        description="YunMin Trading Dashboard Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dashboard_server.py                    # Start on localhost:5000
  python dashboard_server.py --port 8080        # Start on localhost:8080
  python dashboard_server.py --host 0.0.0.0     # Listen on all interfaces
        """
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Print startup banner
    print_banner(args.host, args.port)
    
    # Configure logging
    logger.info(f"Starting YunMin Trading Dashboard...")
    logger.info(f"Dashboard URL: http://{args.host}:{args.port}")
    
    # Run the server
    try:
        uvicorn.run(
            "yunmin.web.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Dashboard server stopped by user")
    except Exception as e:
        logger.error(f"Dashboard server error: {e}")
        sys.exit(1)


def print_banner(host: str, port: int):
    """Print startup banner."""
    banner = f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🤖 YunMin AI Trading Bot Dashboard                     ║
║                                                           ║
║   Real-time monitoring & analytics for your trading bot  ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║   📊 Dashboard: http://{host}:{port:<5}                      ║
║   📡 WebSocket: ws://{host}:{port:<5}/ws                     ║
║   🔧 API Docs:  http://{host}:{port:<5}/docs                 ║
║                                                           ║
║   Press Ctrl+C to stop the server                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


if __name__ == "__main__":
    main()
