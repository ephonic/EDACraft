"""
Execution API — Flow execution management and status tracking

Endpoints:
- GET  /api/execution/status      — Get current execution status
- POST /api/execution/start       — Start execution flow
- POST /api/execution/pause       — Pause execution
- POST /api/execution/resume      — Resume execution
- POST /api/execution/stop        — Stop execution
- GET  /api/execution/history     — Get execution history
- GET  /api/execution/stage/{name} — Get stage execution details
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import asyncio
import threading
import time

router = APIRouter()

# Execution state
_execution_state = {
    "status": "idle",  # idle, running, paused, completed, failed, stopped
    "current_stage": None,
    "started_at": None,
    "paused_at": None,
    "completed_at": None,
    "stages": {},
    "logs": [],
    "thread": None
}

# Stage definitions with metadata
STAGE_DEFINITIONS = {
    "synthesis": {
        "name": "Synthesis",
        "description": "RTL synthesis and optimization",
        "tool": "Design Compiler",
        "dependencies": [],
        "estimated_time": 1800  # seconds
    },
    "floorplan": {
        "name": "Floorplan",
        "description": "Floorplan definition and macro placement",
        "tool": "ICC2",
        "dependencies": ["synthesis"],
        "estimated_time": 1200
    },
    "placement": {
        "name": "Placement",
        "description": "Standard cell placement",
        "tool": "ICC2",
        "dependencies": ["floorplan"],
        "estimated_time": 3600
    },
    "cts": {
        "name": "CTS",
        "description": "Clock tree synthesis",
        "tool": "ICC2",
        "dependencies": ["placement"],
        "estimated_time": 1800
    },
    "routing": {
        "name": "Routing",
        "description": "Global and detail routing",
        "tool": "ICC2",
        "dependencies": ["cts"],
        "estimated_time": 7200
    },
    "drc": {
        "name": "DRC",
        "description": "Design rule checking",
        "tool": "Calibre",
        "dependencies": ["routing"],
        "estimated_time": 1800
    },
    "lvs": {
        "name": "LVS",
        "description": "Layout vs schematic verification",
        "tool": "Calibre",
        "dependencies": ["routing"],
        "estimated_time": 1800
    },
    "eco_fix": {
        "name": "ECO Fix",
        "description": "Engineering change order fixes",
        "tool": "ICC2",
        "dependencies": ["drc", "lvs"],
        "estimated_time": 3600
    }
}


def _reset_execution_state():
    """Reset execution state to initial"""
    global _execution_state
    _execution_state = {
        "status": "idle",
        "current_stage": None,
        "started_at": None,
        "paused_at": None,
        "completed_at": None,
        "stages": {},
        "logs": [],
        "thread": None
    }
    
    # Initialize stage states
    for stage_name, stage_def in STAGE_DEFINITIONS.items():
        _execution_state["stages"][stage_name] = {
            "name": stage_def["name"],
            "description": stage_def["description"],
            "tool": stage_def["tool"],
            "status": "pending",  # pending, running, completed, failed, skipped
            "started_at": None,
            "completed_at": None,
            "duration": None,
            "logs": [],
            "metrics": {},
            "dependencies": stage_def["dependencies"]
        }


_reset_execution_state()


def _execute_flow_thread(stage_order):
    """Thread function to execute flow stages"""
    global _execution_state
    
    _execution_state["status"] = "running"
    _execution_state["started_at"] = datetime.now().isoformat()
    
    for stage_name in stage_order:
        if _execution_state["status"] == "stopped":
            break
        
        if _execution_state["status"] == "paused":
            while _execution_state["status"] == "paused":
                time.sleep(1)
                if _execution_state["status"] == "stopped":
                    break
        
        if _execution_state["status"] == "stopped":
            break
        
        # Check dependencies
        stage = _execution_state["stages"][stage_name]
        deps_met = all(
            _execution_state["stages"][dep]["status"] == "completed"
            for dep in stage["dependencies"]
        )
        
        if not deps_met:
            stage["status"] = "skipped"
            stage["logs"].append(f"Skipped: dependencies not met")
            continue
        
        # Run stage
        _execution_state["current_stage"] = stage_name
        stage["status"] = "running"
        stage["started_at"] = datetime.now().isoformat()
        
        # Simulate execution (replace with actual tool execution)
        estimated_time = STAGE_DEFINITIONS[stage_name]["estimated_time"]
        for i in range(10):
            if _execution_state["status"] == "stopped":
                break
            if _execution_state["status"] == "paused":
                while _execution_state["status"] == "paused":
                    time.sleep(1)
                    if _execution_state["status"] == "stopped":
                        break
                if _execution_state["status"] == "stopped":
                    break
            
            time.sleep(estimated_time / 100)  # 1/10 of estimated time
            
            # Add progress log
            progress = (i + 1) * 10
            stage["logs"].append(f"Progress: {progress}%")
        
        if _execution_state["status"] == "stopped":
            stage["status"] = "failed"
            stage["completed_at"] = datetime.now().isoformat()
            break
        
        # Complete stage
        stage["status"] = "completed"
        stage["completed_at"] = datetime.now().isoformat()
        start_time = datetime.fromisoformat(stage["started_at"])
        end_time = datetime.fromisoformat(stage["completed_at"])
        stage["duration"] = (end_time - start_time).total_seconds()
        
        # Add completion log
        stage["logs"].append(f"Completed in {stage['duration']:.1f}s")
    
    # Finalize
    if _execution_state["status"] == "running":
        _execution_state["status"] = "completed"
    _execution_state["completed_at"] = datetime.now().isoformat()
    _execution_state["current_stage"] = None


class ExecutionStartRequest(BaseModel):
    stage_order: Optional[list[str]] = None
    design_config: Optional[str] = None


@router.get("/execution/status")
def get_execution_status():
    """Get current execution status"""
    # Exclude thread object from response
    response = {k: v for k, v in _execution_state.items() if k != 'thread'}
    return response


@router.post("/execution/start")
def start_execution(request: ExecutionStartRequest):
    """Start flow execution"""
    global _execution_state
    
    if _execution_state["status"] == "running":
        raise HTTPException(400, "Execution already running")
    
    # Reset state
    _reset_execution_state()
    
    # Use provided stage order or default
    stage_order = request.stage_order or list(STAGE_DEFINITIONS.keys())
    
    # Start execution in background thread
    thread = threading.Thread(target=_execute_flow_thread, args=(stage_order,))
    thread.daemon = True
    thread.start()
    _execution_state["thread"] = thread
    
    return {"status": "started", "message": "Flow execution started"}


@router.post("/execution/pause")
def pause_execution():
    """Pause flow execution"""
    if _execution_state["status"] != "running":
        raise HTTPException(400, "Execution not running")
    
    _execution_state["status"] = "paused"
    _execution_state["paused_at"] = datetime.now().isoformat()
    
    return {"status": "paused", "message": "Execution paused"}


@router.post("/execution/resume")
def resume_execution():
    """Resume flow execution"""
    if _execution_state["status"] != "paused":
        raise HTTPException(400, "Execution not paused")
    
    _execution_state["status"] = "running"
    _execution_state["paused_at"] = None
    
    return {"status": "resumed", "message": "Execution resumed"}


@router.post("/execution/stop")
def stop_execution():
    """Stop flow execution"""
    if _execution_state["status"] not in ["running", "paused"]:
        raise HTTPException(400, "Execution not active")
    
    _execution_state["status"] = "stopped"
    _execution_state["completed_at"] = datetime.now().isoformat()
    
    return {"status": "stopped", "message": "Execution stopped"}


@router.get("/execution/history")
def get_execution_history():
    """Get execution history (placeholder)"""
    return {
        "executions": [
            {
                "id": 1,
                "started_at": "2024-01-01T10:00:00",
                "completed_at": "2024-01-01T12:30:00",
                "status": "completed",
                "stages_completed": 7
            }
        ]
    }


@router.get("/execution/stage/{name}")
def get_stage_details(name: str):
    """Get stage execution details"""
    if name not in _execution_state["stages"]:
        raise HTTPException(404, f"Stage '{name}' not found")
    
    return _execution_state["stages"][name]


@router.get("/execution/stages")
def get_all_stages():
    """Get all stage definitions and statuses"""
    return {
        "definitions": STAGE_DEFINITIONS,
        "statuses": _execution_state["stages"]
    }
