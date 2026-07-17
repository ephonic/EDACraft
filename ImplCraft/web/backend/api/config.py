"""
Config API — Project configuration management

Endpoints:
- GET  /api/config/project     — Get project configuration
- PUT  /api/config/project     — Update project configuration
- GET  /api/config/flow        — Get flow configuration
- PUT  /api/config/flow        — Update flow configuration
- GET  /api/config/designs     — List design configurations
- POST /api/config/designs     — Create design configuration
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
import yaml

router = APIRouter()

# In-memory config store (replace with DB in production)
_project_config = {
    "name": "ImplCraft Project",
    "design_files": [],
    "design_libraries": [],
    "working_directory": "/share/home/yangfan/backend_scripts/ImplCraft",
    "eda_tools": {
        "icc2_path": "/usr/local/synopsys/icc2",
        "pt_path": "/usr/local/synopsys/pt",
        "calibre_path": "/usr/local/mentor/calibre",
        "starrc_path": "/usr/local/synopsys/starrc"
    }
}

_flow_config = {
    "enabled_stages": [
        "synthesis", "floorplan", "placement", "cts", 
        "routing", "drc", "lvs"
    ],
    "stage_order": [
        "synthesis", "floorplan", "placement", "cts",
        "routing", "drc", "lvs", "eco_fix"
    ],
    "parallel_execution": False,
    "auto_continue": True,
    "checkpoint_enabled": True
}

_design_configs = []


class ProjectConfig(BaseModel):
    name: str
    design_files: list[str]
    design_libraries: list[str]
    working_directory: str
    eda_tools: dict


class FlowConfig(BaseModel):
    enabled_stages: list[str]
    stage_order: list[str]
    parallel_execution: bool
    auto_continue: bool
    checkpoint_enabled: bool


class DesignConfig(BaseModel):
    name: str
    top_module: str
    clock_period_ns: float
    target_utilization: float
    pdk_name: str
    config_path: Optional[str] = None
    work_root: Optional[str] = None


@router.get("/config/project")
def get_project_config():
    """Get project configuration"""
    return _project_config


@router.put("/config/project")
def update_project_config(config: ProjectConfig):
    """Update project configuration"""
    global _project_config
    _project_config = config.dict()
    
    # Save to file
    try:
        work_dir = Path(_project_config["working_directory"])
        work_dir.mkdir(parents=True, exist_ok=True)
        config_file = work_dir / ".implcraft_project.json"
        config_file.write_text(json.dumps(_project_config, indent=2))
    except Exception:
        pass  # Silently fail if can't write
    
    return {"status": "updated", "config": _project_config}


@router.get("/config/flow")
def get_flow_config():
    """Get flow configuration"""
    return _flow_config


@router.put("/config/flow")
def update_flow_config(config: FlowConfig):
    """Update flow configuration"""
    global _flow_config
    _flow_config = config.dict()
    
    # Save to file
    try:
        work_dir = Path(_project_config["working_directory"])
        work_dir.mkdir(parents=True, exist_ok=True)
        config_file = work_dir / ".implcraft_flow.json"
        config_file.write_text(json.dumps(_flow_config, indent=2))
    except Exception:
        pass  # Silently fail if can't write
    
    return {"status": "updated", "config": _flow_config}


@router.get("/config/designs")
def list_design_configs():
    """List all design configurations"""
    return _design_configs


@router.post("/config/designs")
def create_design_config(config: DesignConfig):
    """Create new design configuration"""
    global _design_configs
    
    # Check for duplicates
    for existing in _design_configs:
        if existing["name"] == config.name:
            raise HTTPException(400, f"Design config '{config.name}' already exists")
    
    config_dict = config.dict()
    _design_configs.append(config_dict)
    
    # Save to file
    try:
        work_dir = Path(_project_config["working_directory"])
        config_dir = work_dir / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / f"{config.name}.yaml"
        config_file.write_text(yaml.dump(config_dict))
    except Exception:
        pass  # Silently fail if can't write
    
    return {"status": "created", "config": config_dict}


@router.delete("/config/designs/{name}")
def delete_design_config(name: str):
    """Delete design configuration"""
    global _design_configs
    
    _design_configs = [d for d in _design_configs if d["name"] != name]
    
    # Delete file
    try:
        config_file = Path(_project_config["working_directory"]) / "configs" / f"{name}.yaml"
        if config_file.exists():
            config_file.unlink()
    except Exception:
        pass  # Silently fail if can't delete
    
    return {"status": "deleted", "name": name}
