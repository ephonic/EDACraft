"""ThorCluster module package (cluster top).

Public API:
    - cluster_functional: L1 functional cluster model.
    - NSM: number of SMs in the cluster.
"""

from __future__ import annotations

from thor_gpu.modules.gpu_cluster.layer_L1_behavior.src.behavior import (
    NSM, cluster_functional,
)

__all__ = ["NSM", "cluster_functional"]
