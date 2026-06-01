"""
Functional models for skills.mem
"""
from __future__ import annotations
from typing import Any, Callable, Dict


def priorityencoder_functional(**kwargs) -> Callable:
    """Functional PriorityEncoder model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def ramdp_functional(**kwargs) -> Callable:
    """Functional RamDP model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def camsrl_functional(**kwargs) -> Callable:
    """Functional CamSRL model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def cambram_functional(**kwargs) -> Callable:
    """Functional CamBRAM model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def cam_functional(**kwargs) -> Callable:
    """Functional CAM model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def ddr3fifo_functional(**kwargs) -> Callable:
    """Functional DDR3FIFO model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def ddr3dfiseq_functional(**kwargs) -> Callable:
    """Functional DDR3DFISeq model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def ddr3core_functional(**kwargs) -> Callable:
    """Functional DDR3Core model."""
    def func(**inputs) -> Dict:
        return {}
    return func

def ddr3controller_functional(**kwargs) -> Callable:
    """Functional DDR3Controller model."""
    def func(**inputs) -> Dict:
        return {}
    return func
