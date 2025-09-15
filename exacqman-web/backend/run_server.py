#!/usr/bin/env python3
"""
ExacqMan Web Server Startup Script

Simple script to start the FastAPI server with proper configuration.
"""

import uvicorn
import sys
import os
import argparse
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start ExacqMan Web Server')
    parser.add_argument('--port', '-p', type=int, default=8000, 
                       help='Port number to run the server on (default: 8000)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind the server to (default: 0.0.0.0)')
    parser.add_argument('--no-reload', action='store_true',
                       help='Disable auto-reload for production')
    
    args = parser.parse_args()
    
    # Change to the backend directory
    os.chdir(backend_dir)
    
    print(f"Starting ExacqMan Web Server on {args.host}:{args.port}")
    
    # Start the server
    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level="info",
        access_log=True
    )
