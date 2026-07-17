"""32-bit UCIe 互连示例（依赖 pip install gmsh）。

本例演示用 mom.gmsh_mesh 构建 UCIe 网格并查看其规模。UCIe 求解需要根据
信号凸点（signal bump）位置确定端口边缘索引，流程较长；本例先聚焦"建网 +
检查"，并在末尾给出可选的求解入口。

注意：完整 UCIe 几何规模较大（数千三角形），求解较慢；首次运行请确保已
  pip install gmsh
并已  pip install -e .  编译好 _mom 扩展。

运行：python examples/run_ucie_demo.py
"""
import numpy as np

import mom
import mom.gmsh_mesh
from mom.gmsh_mesh import build_ucie_32bit_mesh


def build_and_inspect():
    """1) 构建 UCIe 网格并检查规模。"""
    print("=== 构建 32-bit UCIe 网格（需 pip install gmsh）===")
    # 减小 n_bits 可显著缩短建网时间，便于快速验证
    mesh, structure = build_ucie_32bit_mesh(n_bits=8, verbose=False)

    print(f"信号位数 n_bits      : {structure.n_bits}")
    print(f"信号凸点 port_bumps  : {len(structure.port_bumps)}")
    print(f"接地凸点 gnd_bumps   : {len(structure.gnd_bumps)}")
    print(f"顶点数 n_vertices    : {mesh.n_vertices()}")
    print(f"三角形数 n_triangles : {mesh.n_triangles()}")
    print(f"RWG 基函数 n_rwg     : {mesh.n_rwg()}")
    print(f"总面积 total_area    : {mesh.total_area()*1e6:.3f} mm^2")
    return mesh, structure


def optional_solve_demo(mesh):
    """2) 可选：在 UCIe 网格上做一次单频求解（演示入口）。

    solve_rwg_sparam_port_edges 需要每个端口指定一个边缘基函数索引。完整 UCIe
    的端口选择取决于凸点几何，本例用首尾两个基函数作为占位端口，仅作 API 演示；
    生产用例请按信号凸点位置精确选取 port_edges。
    """
    nb = mesh.n_rwg()
    if nb < 8:
        print("RWG 基函数太少，跳过求解演示。")
        return

    port_edges = [0, nb - 1]   # 占位：首尾基函数
    freqs = np.array([1e9, 5e9])
    print(f"\n=== 可选求解演示（port_edges={port_edges} 占位）===")
    try:
        S = mom._mom.solve_rwg_sparam_port_edges(
            mesh, freqs, eps_r=4.3, tand=0.01, h=100e-6,
            port_edges=port_edges, z0_ref=50.0,
            grid_resolution=16, near_threshold=0.3, gmres_tol=1e-3, gmres_max_iter=200,
        )
        S = np.asarray(S)
        print(f"S shape: {S.shape}")
        for i, f in enumerate(freqs):
            print(f"  {f/1e9:.0f} GHz: |S11|={abs(S[i,0,0]):.4f} |S21|={abs(S[i,1,0]):.4f}")
    except Exception as e:
        # 占位端口可能不对应真实物理凸点，求解失败属正常；不影响建网演示。
        print(f"占位端口求解未成功（预期情况，端口需按凸点几何精确选取）: {e}")


def main():
    mesh, structure = build_and_inspect()
    optional_solve_demo(mesh)


if __name__ == "__main__":
    main()
