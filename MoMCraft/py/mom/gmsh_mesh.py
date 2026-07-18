"""
gmsh 网格生成器 - 为 MoM 求解器生成 3D 三角网格

支持的结构：
- 矩形平面导体
- 圆柱形 TSV / 过孔
- 微凸点 (microbump)
- 组合结构
"""

import numpy as np
import gmsh
import sys
from typing import List, Tuple, Optional, Dict, Any


class GmshMesher:
    """gmsh 网格生成器，输出兼容 TriMesh 的格式"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.vertices: List[Tuple[float, float, float]] = []
        self.triangles: List[Tuple[int, int, int]] = []
        self.physical_groups: Dict[str, List[int]] = {}  # name -> triangle indices

    def _log(self, msg: str):
        if self.verbose:
            print(f"[GmshMesher] {msg}")

    def add_rectangle(self, x0: float, y0: float, z: float,
                      x1: float, y1: float,
                      mesh_size: float = 0.1,
                      name: str = "rect",
                      layer: int = 0) -> int:
        """添加矩形平面导体"""
        self._log(f"Adding rectangle {name}: ({x0},{y0},{z}) - ({x1},{y1},{z})")

        # 使用 gmsh API
        gmsh.model.add("temp_rect")

        # 创建矩形表面
        rect = gmsh.model.occ.addRectangle(x0, y0, z, x1-x0, y1-y0)
        gmsh.model.occ.synchronize()

        # 设置网格尺寸
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)

        # 生成 2D 网格
        gmsh.model.mesh.generate(2)

        # 提取网格数据
        node_tags, node_coords, _ = gmsh.model.mesh.getNodes()

        # 构建顶点映射
        coord_map = {}
        for i, tag in enumerate(node_tags):
            x = node_coords[3*i]
            y = node_coords[3*i + 1]
            z_coord = node_coords[3*i + 2]
            coord_map[tag] = (x, y, z_coord)

        # 提取三角形
        elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(2)

        tri_start = len(self.vertices)
        tag_to_idx = {}

        for tag, (x, y, z_coord) in coord_map.items():
            tag_to_idx[tag] = len(self.vertices)
            self.vertices.append((x, y, z_coord))

        for et, ent in zip(elem_types, elem_node_tags):
            if et == 2:  # 三角形
                for i in range(0, len(ent), 3):
                    t0 = tag_to_idx[ent[i]]
                    t1 = tag_to_idx[ent[i+1]]
                    t2 = tag_to_idx[ent[i+2]]
                    self.triangles.append((t0, t1, t2))

        # 记录物理组
        self.physical_groups[name] = list(range(tri_start, len(self.triangles)))

        # 清除临时模型
        gmsh.model.remove()

        return len(self.triangles) - tri_start

    def add_cylinder_surface(self, xc: float, yc: float, z0: float, z1: float,
                             radius: float, n_segments: int = 12,
                             name: str = "via", layer: int = 0) -> int:
        """添加圆柱面（TSV/过孔表面）"""
        self._log(f"Adding cylinder {name}: center=({xc},{yc}), z=[{z0},{z1}], r={radius}")

        gmsh.model.add("temp_cylinder")

        # 创建圆柱体
        cylinder = gmsh.model.occ.addCylinder(xc, yc, z0, 0, 0, z1-z0, radius)
        gmsh.model.occ.synchronize()

        # 设置网格尺寸
        circumference = 2 * np.pi * radius
        mesh_size = circumference / n_segments
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)

        # 生成 2D 表面网格
        gmsh.model.mesh.generate(2)

        # 提取网格
        node_tags, node_coords, _ = gmsh.model.mesh.getNodes()

        coord_map = {}
        for i, tag in enumerate(node_tags):
            x = node_coords[3*i]
            y = node_coords[3*i + 1]
            z = node_coords[3*i + 2]
            coord_map[tag] = (x, y, z)

        elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(2)

        tri_start = len(self.vertices)
        tag_to_idx = {}

        for tag, (x, y, z) in coord_map.items():
            tag_to_idx[tag] = len(self.vertices)
            self.vertices.append((x, y, z))

        for et, ent in zip(elem_types, elem_node_tags):
            if et == 2:  # 三角形
                for i in range(0, len(ent), 3):
                    t0 = tag_to_idx[ent[i]]
                    t1 = tag_to_idx[ent[i+1]]
                    t2 = tag_to_idx[ent[i+2]]
                    self.triangles.append((t0, t1, t2))

        self.physical_groups[name] = list(range(tri_start, len(self.triangles)))

        gmsh.model.remove()

        return len(self.triangles) - tri_start

    def add_via_with_pads(self, xc: float, yc: float, z_bottom: float, z_top: float,
                          via_radius: float, pad_radius: float,
                          n_segments: int = 12,
                          name: str = "via", layer: int = 0) -> int:
        """添加带焊盘的过孔结构"""
        self._log(f"Adding via {name} with pads")

        total_tris = 0

        # 底部焊盘
        total_tris += self.add_rectangle(
            xc - pad_radius, yc - pad_radius, z_bottom,
            xc + pad_radius, yc + pad_radius,
            mesh_size=2*np.pi*pad_radius/n_segments/2,
            name=f"{name}_pad_bottom", layer=layer
        )

        # 圆柱体
        total_tris += self.add_cylinder_surface(
            xc, yc, z_bottom, z_top,
            via_radius, n_segments,
            name=f"{name}_barrel", layer=layer
        )

        # 顶部焊盘
        total_tris += self.add_rectangle(
            xc - pad_radius, yc - pad_radius, z_top,
            xc + pad_radius, yc + pad_radius,
            mesh_size=2*np.pi*pad_radius/n_segments/2,
            name=f"{name}_pad_top", layer=layer
        )

        return total_tris

    def add_trace(self, x0: float, y0: float, x1: float, y1: float,
                  z: float, width: float,
                  mesh_size: float = 0.05,
                  name: str = "trace", layer: int = 0) -> int:
        """添加走线（矩形导体）"""
        # 计算走线方向
        dx = x1 - x0
        dy = y1 - y0
        length = np.sqrt(dx*dx + dy*dy)

        if length < 1e-10:
            raise ValueError("Trace length too small")

        # 法向（垂直于走线方向）
        nx = -dy / length * width / 2
        ny = dx / length * width / 2

        # 四个角点
        corners = [
            (x0 + nx, y0 + ny),
            (x0 - nx, y0 - ny),
            (x1 - nx, y1 - ny),
            (x1 + nx, y1 + ny),
        ]

        return self.add_rectangle(
            min(c[0] for c in corners), min(c[1] for c in corners), z,
            max(c[0] for c in corners), max(c[1] for c in corners),
            mesh_size=mesh_size, name=name, layer=layer
        )

    def get_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """返回顶点和三角形数组，兼容 trimesh_from_list"""
        verts = np.array(self.vertices, dtype=np.float64)
        tris = np.array(self.triangles, dtype=np.int32)
        return verts, tris

    def get_physical_group_triangles(self, name: str) -> List[int]:
        """获取指定物理组的三角形索引"""
        return self.physical_groups.get(name, [])

    def clear(self):
        """清除所有数据"""
        self.vertices.clear()
        self.triangles.clear()
        self.physical_groups.clear()


def create_gmsh_mesher(verbose: bool = False) -> GmshMesher:
    """创建 gmsh 网格生成器"""
    # 初始化 gmsh
    gmsh.initialize()
    if not verbose:
        gmsh.option.setNumber("General.Verbosity", 0)
    return GmshMesher(verbose=verbose)


def finalize_gmsh_mesher(mesher: GmshMesher):
    """结束 gmsh 会话"""
    gmsh.finalize()


class UCieStructure:
    """32-bit UCIe 互连结构建模

    结构层次（从上到下）：
    - Die 层：微凸点阵列
    - 中间层：RDL 走线 + TSV
    - 基板层：GND 平面

    参数：
    - n_bits: 信号位数 (默认 32)
    - pitch: 凸点间距 (默认 40um)
    - tsv_pitch: TSV 间距 (默认 100um)
    """

    def __init__(self, n_bits: int = 32, verbose: bool = False):
        self.n_bits = n_bits
        self.verbose = verbose

        # 默认尺寸 (单位: m)
        self.bump_pitch = 40e-6      # 40 um
        self.bump_radius = 10e-6     # 10 um
        self.bump_height = 20e-6     # 20 um

        self.tsv_pitch = 100e-6      # 100 um
        self.tsv_radius = 5e-6       # 5 um
        self.tsv_height = 100e-6     # 100 um

        self.rdl_width = 10e-6       # 10 um
        self.rdl_thickness = 1e-6    # 1 um

        self.substrate_height = 50e-6  # 50 um

        # 端口定义
        self.port_bumps: List[int] = []  # 信号凸点索引
        self.gnd_bumps: List[int] = []   # 接地凸点索引

    def build_mesh(self) -> Tuple[np.ndarray, np.ndarray]:
        """构建完整的 3D 网格"""
        mesher = create_gmsh_mesher(verbose=self.verbose)

        try:
            # 计算结构尺寸
            total_width = self.n_bits * self.bump_pitch * 2  # 信号+GND
            total_length = total_width  # 正方形区域

            # 1. 顶部 RDL 层 (z = tsv_height + bump_height)
            z_top = self.tsv_height + self.bump_height

            # 为每个信号位创建凸点
            for i in range(self.n_bits):
                x = i * self.bump_pitch * 2
                y = total_width / 2

                # 信号凸点（圆柱）
                mesher.add_cylinder_surface(
                    x, y, self.tsv_height, z_top,
                    self.bump_radius, n_segments=8,
                    name=f"bump_sig_{i}"
                )
                self.port_bumps.append(i)

                # 相邻 GND 凸点
                if i < self.n_bits - 1:
                    x_gnd = x + self.bump_pitch
                    mesher.add_cylinder_surface(
                        x_gnd, y, self.tsv_height, z_top,
                        self.bump_radius * 0.8, n_segments=8,
                        name=f"bump_gnd_{i}"
                    )
                    self.gnd_bumps.append(i)

            # 2. 中间 TSV 层 (z = 0 到 tsv_height)
            n_tsv = self.n_bits // 4 + 1  # 每 4 位一个 GND TSV

            for i in range(n_tsv):
                x = i * self.tsv_pitch * 4
                y = total_width / 2

                mesher.add_cylinder_surface(
                    x, y, 0, self.tsv_height,
                    self.tsv_radius, n_segments=8,
                    name=f"tsv_gnd_{i}"
                )

            # 3. 底部 GND 平面 (z = 0)
            mesher.add_rectangle(
                -self.bump_pitch, -self.bump_pitch, 0,
                total_length + self.bump_pitch, total_width + self.bump_pitch,
                mesh_size=self.bump_pitch / 2,
                name="gnd_plane"
            )

            verts, tris = mesher.get_arrays()

        finally:
            finalize_gmsh_mesher(mesher)

        return verts, tris


def build_ucie_32bit_mesh(n_bits: int = 32, verbose: bool = False):
    """构建 32-bit UCIe 网格并返回 TriMesh"""
    from . import _mom

    structure = UCieStructure(n_bits=n_bits, verbose=verbose)
    verts, tris = structure.build_mesh()

    print(f"UCie {n_bits}-bit mesh: {len(verts)} vertices, {len(tris)} triangles")

    # 创建 TriMesh
    mesh = _mom.trimesh_from_list(verts, tris, 0)

    return mesh, structure


if __name__ == "__main__":
    # 测试
    print("Testing gmsh mesh generation...")

    mesher = create_gmsh_mesher(verbose=True)

    # 添加简单矩形
    mesher.add_rectangle(0, 0, 0, 1e-3, 1e-3, mesh_size=0.2e-3, name="test_rect")

    verts, tris = mesher.get_arrays()
    print(f"Rectangle mesh: {len(verts)} vertices, {len(tris)} triangles")

    finalize_gmsh_mesher(mesher)
    print("Done!")
