"""
ImplCraft Web Server — FastAPI application for design management.

Features:
- REST API for designs, stages, metrics, scripts, git
- WebSocket for real-time progress updates
- Static file serving for frontend
- CORS support for development

Usage:
    uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from .db.engine import init_db
from .api.designs import router as designs_router
from .api.stages import router as stages_router
from .api.metrics import router as metrics_router
from .api.scripts import router as scripts_router
from .api.git import router as git_router
from .api.dashboard import router as dashboard_router
from .api.config import router as config_router
from .api.execution import router as execution_router
from .api.modules import router as modules_router
from .api.risk import router as risk_router

logger = logging.getLogger("implcraft.server")

# Create FastAPI application
app = FastAPI(
    title="ImplCraft Design Manager",
    description="Professional IC backend design management platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(designs_router, prefix="/api", tags=["designs"])
app.include_router(stages_router, prefix="/api", tags=["stages"])
app.include_router(metrics_router, prefix="/api", tags=["metrics"])
app.include_router(scripts_router, prefix="/api", tags=["scripts"])
app.include_router(git_router, prefix="/api", tags=["git"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(config_router, prefix="/api", tags=["config"])
app.include_router(execution_router, prefix="/api", tags=["execution"])
app.include_router(modules_router, prefix="/api", tags=["modules"])
app.include_router(risk_router, prefix="/api", tags=["risk"])


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    db_path = os.environ.get("IMPLCRAFT_DB", "data/implcraft.db")
    init_db(db_path)
    logger.info(f"Database initialized: {db_path}")


# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time design progress updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now, can be extended for bidirectional
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Static file serving for frontend
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>ImplCraft Dashboard</h1><p>Frontend not found.</p>")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "implcraft"}
