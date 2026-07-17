#!/usr/bin/env python3
"""
ImplCraft Web Server Launcher

Usage:
    python run_web.py                        # Default: port 8000
    python run_web.py --port 9000            # Custom port
    python run_web.py --host 0.0.0.0         # Bind to all interfaces
    python run_web.py --db data/my_design.db # Custom database path
    python run_web.py --reload               # Auto-reload on code changes

Environment variables:
    IMPLCRAFT_DB     - SQLite database path (default: data/implcraft.db)
    IMPLCRAFT_PORT   - Server port (default: 8000)
    IMPLCRAFT_HOST   - Bind address (default: 127.0.0.1)
    IMPLCRAFT_GIT_REPO - Git repository path (default: current directory)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="ImplCraft Web Server")
    parser.add_argument("--host", default=os.environ.get("IMPLCRAFT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("IMPLCRAFT_PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--db", default=os.environ.get("IMPLCRAFT_DB", "data/implcraft.db"))
    parser.add_argument("--git-repo", default=os.environ.get("IMPLCRAFT_GIT_REPO", "."))
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    os.environ["IMPLCRAFT_DB"] = args.db
    os.environ["IMPLCRAFT_GIT_REPO"] = args.git_repo

    # Initialize database
    from web.backend.db.engine import init_db
    init_db(args.db)
    print(f"Database initialized: {args.db}")

    # Launch server
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install -r web/backend/requirements.txt")
        sys.exit(1)

    print(f"Starting ImplCraft Web Server on {args.host}:{args.port}")
    print(f"API docs: http://{args.host}:{args.port}/api/docs")
    print(f"Dashboard: http://{args.host}:{args.port}/")

    uvicorn.run(
        "web.backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
