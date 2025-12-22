"""
Script to run the Meeting MCP Server.

Usage:
    python scripts/run_meeting_mcp_server.py --transport sse --port 8082
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Run Meeting MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="sse",
        help="Transport type"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8082,
        help="Port to listen on"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create config
    from mcp_meeting_server.config import MeetingServerConfig
    
    config = MeetingServerConfig(
        transport=args.transport,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    
    # Run server
    from mcp_meeting_server.server import run_server
    run_server(config)


if __name__ == "__main__":
    main()
