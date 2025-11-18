#!/usr/bin/env python3
"""
PM MCP Server Startup Script

Starts the PM MCP Server with the specified transport.

Usage:
    # Run with stdio transport (for Claude Desktop)
    python scripts/run_pm_mcp_server.py --transport stdio
    
    # Run with SSE transport (for web agents)
    python scripts/run_pm_mcp_server.py --transport sse --port 8080
    
    # Run with HTTP transport
    python scripts/run_pm_mcp_server.py --transport http --port 8080
    
    # With custom database
    DATABASE_URL=postgresql://user:pass@host:port/db python scripts/run_pm_mcp_server.py
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp_servers.pm_server import PMMCPServer, PMServerConfig


def setup_logging(log_level: str) -> None:
    """Configure logging for the server."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("logs/pm_mcp_server.log")
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PM MCP Server - Expose PM operations as MCP tools"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (for sse/http transports, default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (for sse/http transports, default: 8080)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--enable-auth",
        action="store_true",
        help="Enable authentication"
    )
    
    parser.add_argument(
        "--enable-rbac",
        action="store_true",
        help="Enable role-based access control"
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("PM MCP Server Starting")
    logger.info("=" * 60)
    logger.info(f"Transport: {args.transport}")
    if args.transport in ["sse", "http"]:
        logger.info(f"Address: {args.host}:{args.port}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info(f"Authentication: {'Enabled' if args.enable_auth else 'Disabled'}")
    logger.info(f"RBAC: {'Enabled' if args.enable_rbac else 'Disabled'}")
    logger.info("=" * 60)
    
    # Create server configuration
    config = PMServerConfig(
        transport=args.transport,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        enable_auth=args.enable_auth,
        enable_rbac=args.enable_rbac
    )
    
    try:
        # Initialize and run server
        server = PMMCPServer(config)
        await server.run()
    except KeyboardInterrupt:
        logger.info("\nShutting down PM MCP Server...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

