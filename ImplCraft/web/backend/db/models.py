"""
SQLAlchemy ORM models for the design management database.

Tables:
- designs: Design projects (one per top-level chip design)
- stages: Flow stage executions (synthesis, placement, routing, etc.)
- metrics: Time-series QoR metrics (timing, area, power, DRC)
- scripts: Generated Tcl/shell scripts with preview content
- git_commits: Git version control history for design files
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Float, String, Text, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, JSON, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


class DesignRecord(Base):
    """A design project — top-level entity."""
    __tablename__ = "designs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True)
    top_module = Column(String(256), default="top")
    description = Column(Text, default="")
    config_path = Column(String(1024), default="")
    work_root = Column(String(1024), default="")
    pdk_name = Column(String(128), default="")
    target_utilization = Column(Float, default=0.7)
    clock_period_ns = Column(Float, default=10.0)
    status = Column(String(32), default="created")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    stages = relationship("StageRecord", back_populates="design", cascade="all, delete-orphan")
    metrics = relationship("MetricRecord", back_populates="design", cascade="all, delete-orphan")
    scripts = relationship("ScriptRecord", back_populates="design", cascade="all, delete-orphan")
    git_commits = relationship("GitCommitRecord", back_populates="design", cascade="all, delete-orphan")
    modules = relationship("ModuleRecord", back_populates="design", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_designs_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "top_module": self.top_module,
            "description": self.description,
            "config_path": self.config_path,
            "work_root": self.work_root,
            "pdk_name": self.pdk_name,
            "target_utilization": self.target_utilization,
            "clock_period_ns": self.clock_period_ns,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "stage_count": len(self.stages) if self.stages else 0,
            "module_count": len(self.modules) if self.modules else 0,
        }


class StageRecord(Base):
    """A flow stage execution record."""
    __tablename__ = "stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(Integer, ForeignKey("designs.id"), nullable=False)
    stage_name = Column(String(64), nullable=False)
    tool = Column(String(64), default="")
    flow_stage = Column(String(32), default="")
    status = Column(String(32), default="pending")
    work_dir = Column(String(1024), default="")
    log_file = Column(String(1024), default="")

    elapsed_seconds = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    timing_wns = Column(Float, nullable=True)
    timing_tns = Column(Float, nullable=True)
    timing_violating_paths = Column(Integer, nullable=True)
    timing_endpoints = Column(Integer, nullable=True)

    area_total = Column(Float, nullable=True)
    area_utilization = Column(Float, nullable=True)
    area_std_cells = Column(Integer, nullable=True)

    power_total_mw = Column(Float, nullable=True)
    power_dynamic_mw = Column(Float, nullable=True)
    power_leakage_mw = Column(Float, nullable=True)

    route_drc_errors = Column(Integer, nullable=True)
    route_wirelength = Column(Float, nullable=True)

    messages = Column(JSON, default=list)
    output_files = Column(JSON, default=dict)

    created_at = Column(DateTime, default=_utcnow)

    design = relationship("DesignRecord", back_populates="stages")

    __table_args__ = (
        Index("ix_stages_design", "design_id"),
        Index("ix_stages_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "design_id": self.design_id,
            "stage_name": self.stage_name,
            "tool": self.tool,
            "flow_stage": self.flow_stage,
            "status": self.status,
            "work_dir": self.work_dir,
            "log_file": self.log_file,
            "elapsed_seconds": self.elapsed_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "timing": {
                "wns": self.timing_wns,
                "tns": self.timing_tns,
                "violating_paths": self.timing_violating_paths,
                "endpoints": self.timing_endpoints,
            },
            "area": {
                "total": self.area_total,
                "utilization": self.area_utilization,
                "std_cells": self.area_std_cells,
            },
            "power": {
                "total_mw": self.power_total_mw,
                "dynamic_mw": self.power_dynamic_mw,
                "leakage_mw": self.power_leakage_mw,
            },
            "route": {
                "drc_errors": self.route_drc_errors,
                "wirelength": self.route_wirelength,
            },
            "messages": self.messages or [],
            "output_files": self.output_files or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MetricRecord(Base):
    """Time-series QoR metrics snapshot for trend tracking."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(Integer, ForeignKey("designs.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=True)
    iteration = Column(Integer, default=1)
    snapshot_at = Column(DateTime, default=_utcnow)

    wns = Column(Float, nullable=True)
    tns = Column(Float, nullable=True)
    utilization = Column(Float, nullable=True)
    total_power_mw = Column(Float, nullable=True)
    leakage_power_mw = Column(Float, nullable=True)
    drc_errors = Column(Integer, nullable=True)
    num_violating_paths = Column(Integer, nullable=True)
    num_endpoints = Column(Integer, nullable=True)
    max_transition_violations = Column(Integer, nullable=True)
    max_capacitance_violations = Column(Integer, nullable=True)

    extra = Column(JSON, default=dict)

    design = relationship("DesignRecord", back_populates="metrics")

    __table_args__ = (
        Index("ix_metrics_design_iter", "design_id", "iteration"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "design_id": self.design_id,
            "stage_id": self.stage_id,
            "iteration": self.iteration,
            "snapshot_at": self.snapshot_at.isoformat() if self.snapshot_at else None,
            "wns": self.wns,
            "tns": self.tns,
            "utilization": self.utilization,
            "total_power_mw": self.total_power_mw,
            "leakage_power_mw": self.leakage_power_mw,
            "drc_errors": self.drc_errors,
            "num_violating_paths": self.num_violating_paths,
            "num_endpoints": self.num_endpoints,
            "extra": self.extra or {},
        }


class ScriptRecord(Base):
    """Generated script with preview content for confirmation workflow."""
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(Integer, ForeignKey("designs.id"), nullable=False)
    stage_name = Column(String(64), default="")
    script_type = Column(String(32), default="tcl")
    filename = Column(String(256), default="")
    content = Column(Text, default="")
    preview_content = Column(Text, default="")

    status = Column(String(32), default="generated")
    exit_code = Column(Integer, nullable=True)
    execution_log = Column(Text, default="")

    generated_at = Column(DateTime, default=_utcnow)
    executed_at = Column(DateTime, nullable=True)

    design = relationship("DesignRecord", back_populates="scripts")

    __table_args__ = (
        Index("ix_scripts_design", "design_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "design_id": self.design_id,
            "stage_name": self.stage_name,
            "script_type": self.script_type,
            "filename": self.filename,
            "content": self.content,
            "preview_content": self.preview_content,
            "status": self.status,
            "exit_code": self.exit_code,
            "execution_log": self.execution_log,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }



class ModuleRecord(Base):
    """A partitioned module within a design — tracks per-module execution progress."""
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(Integer, ForeignKey("designs.id"), nullable=False)
    name = Column(String(256), nullable=False)
    hierarchy = Column(String(1024), default="")
    parent_name = Column(String(256), nullable=True)
    level = Column(Integer, default=0)  # 0=top-level, 1=submodule, etc.

    synthesis_status = Column(String(32), default="pending")
    floorplan_status = Column(String(32), default="pending")
    placement_status = Column(String(32), default="pending")
    cts_status = Column(String(32), default="pending")
    routing_status = Column(String(32), default="pending")
    drc_status = Column(String(32), default="pending")
    lvs_status = Column(String(32), default="pending")

    synthesis_elapsed = Column(Float, default=0.0)
    floorplan_elapsed = Column(Float, default=0.0)
    placement_elapsed = Column(Float, default=0.0)
    cts_elapsed = Column(Float, default=0.0)
    routing_elapsed = Column(Float, default=0.0)
    drc_elapsed = Column(Float, default=0.0)
    lvs_elapsed = Column(Float, default=0.0)

    area_um = Column(Float, nullable=True)
    cell_count = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    design = relationship("DesignRecord", back_populates="modules")

    __table_args__ = (
        Index("ix_modules_design", "design_id"),
        Index("ix_modules_name", "design_id", "name"),
    )

    STAGE_NAMES = ["synthesis", "floorplan", "placement", "cts", "routing", "drc", "lvs"]

    def get_stage_status(self, stage_name):
        return getattr(self, f"{stage_name}_status", "pending")

    def set_stage_status(self, stage_name, status):
        attr = f"{stage_name}_status"
        if hasattr(self, attr):
            setattr(self, attr, status)

    def get_stage_elapsed(self, stage_name):
        return getattr(self, f"{stage_name}_elapsed", 0.0)

    def set_stage_elapsed(self, stage_name, elapsed):
        attr = f"{stage_name}_elapsed"
        if hasattr(self, attr):
            setattr(self, attr, elapsed)

    def to_dict(self) -> dict:
        stages = {}
        for sn in self.STAGE_NAMES:
            stages[sn] = {
                "status": self.get_stage_status(sn),
                "elapsed": self.get_stage_elapsed(sn),
            }
        return {
            "id": self.id,
            "design_id": self.design_id,
            "name": self.name,
            "hierarchy": self.hierarchy,
            "parent_name": self.parent_name,
            "level": self.level,
            "stages": stages,
            "area_um": self.area_um,
            "cell_count": self.cell_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GitCommitRecord(Base):
    """Git commit history for design file version control."""
    __tablename__ = "git_commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(Integer, ForeignKey("designs.id"), nullable=True)
    commit_hash = Column(String(40), nullable=False)
    short_hash = Column(String(10), default="")
    author = Column(String(256), default="")
    email = Column(String(256), default="")
    message = Column(Text, default="")
    branch = Column(String(256), default="main")

    files_changed = Column(Integer, default=0)
    insertions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    changed_files = Column(JSON, default=list)

    committed_at = Column(DateTime, nullable=True)
    recorded_at = Column(DateTime, default=_utcnow)

    design = relationship("DesignRecord", back_populates="git_commits")

    __table_args__ = (
        Index("ix_git_hash", "commit_hash"),
        Index("ix_git_design", "design_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "design_id": self.design_id,
            "commit_hash": self.commit_hash,
            "short_hash": self.short_hash,
            "author": self.author,
            "email": self.email,
            "message": self.message,
            "branch": self.branch,
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "changed_files": self.changed_files or [],
            "committed_at": self.committed_at.isoformat() if self.committed_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
