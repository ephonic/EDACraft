"""TCAD: 3D Quantum-Corrected Semiconductor Device Simulator with 128-bit Precision"""

__version__ = "0.2.0"

from .core import SolverType
from .geometry import Device, Material, Region, DopingProfile
from .mesh import StructuredGrid, generate_mesh
from .simulator import Simulator, simulate_device, simulate_sweep, UnstructuredSimulator

__all__ = [
    "Device", "Material", "Region", "DopingProfile",
    "StructuredGrid", "generate_mesh",
    "Simulator", "simulate_device", "simulate_sweep", "SolverType",
    "UnstructuredSimulator",
]
