// =====================================================================
// mom/mesh/trimesh.hpp —— 三角网格 + RWG 基函数（3D 任意结构支持）
//
// M1 阶段：建立三角网格基础设施，支持任意平面/三维导体表面。
// 与现有 RectMesh/RooftopBasis 并行存在，不修改旧代码。
//
// RWG（Rao-Wilton-Glisson）基函数：
//   定义在两个相邻三角形共享的内边上。
//   f(r) = +(l/(2A⁺))(r - ρ_c⁺)  on T⁺（正三角形）
//   f(r) = -(l/(2A⁻))(r - ρ_c⁻)  on T⁻（负三角形）
//   其中 l=边长，A=三角形面积，ρ_c=三角形上的自由顶点（不在共享边上的顶点）。
//   散度：∇·f = +l/A⁺ on T⁺，-l/A⁻ on T⁻（每三角形常数）。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include <vector>
#include <array>
#include <map>
#include <algorithm>

namespace mom::mesh {

// 三角网格顶点（带层索引，为后续多层格林函数准备）
struct TriVertex {
    Real  x = 0, y = 0, z = 0;
    Index layer = 0;   // 所在介质层索引

    Vec3 pos() const { return Vec3(x, y, z); }
};

// 三角形单元（预计算面积、法向、中心）
struct Triangle {
    Index v[3];          // 顶点索引（逆时针为正法向）
    Real  area = 0;      // 三角形面积
    Vec3  normal;        // 单位法向
    Vec3  centroid;      // 重心

    // 三条边（顶点对），用于内边检测
    std::array<std::pair<Index, Index>, 3> edges() const {
        return {{{v[0], v[1]}, {v[1], v[2]}, {v[2], v[0]}}};
    }
};

// RWG 基函数（定义在内边上）
struct RwgBasis {
    Index t_plus   = -1;   // 正三角形索引
    Index t_minus  = -1;   // 负三角形索引（-1=边界边，无 RWG）
    Index v_free_plus  = -1;   // 正三角形上的自由顶点（不在共享边上）
    Index v_free_minus = -1;   // 负三角形上的自由顶点
    Index v_edge[2]   = {-1, -1};  // 共享边的两个顶点
    Real  edge_length  = 0;     // 共享边长
    bool  is_vertical  = false; // 是否为垂直边（z 方向）

    bool is_interior() const { return t_minus >= 0; }
};

// 三角网格
struct TriMesh {
    std::vector<TriVertex> vertices;
    std::vector<Triangle>  triangles;
    std::vector<RwgBasis>  bases;     // RWG 基函数（从内边生成）

    // —— 工厂方法 —— //

    // 矩形带网格（兼容旧 RectMesh 用法，每矩形单元 2 个三角形）
    //   nx, ny: x/y 方向分段数
    //   z: 导体所在 z 平面
    //   layer: 介质层索引
    static TriMesh rectangle_strip(Real x0, Real x1, Real y0, Real y1,
                                    Real z, int nx, int ny,
                                    Index layer = 0);

    // 从顶点+三角形列表构造（外部网格导入，如 gmsh）
    static TriMesh from_triangle_list(const std::vector<Vec3>& verts,
                                      const std::vector<std::array<Index, 3>>& tris,
                                      Index layer = 0,
                                      bool include_boundary = false);

    // 获取三角形顶点坐标
    Vec3 tri_vertex(Index ti, Index vi) const {
        return vertices[triangles[ti].v[vi]].pos();
    }

    // 三角形面积计算（静态工具）
    static Real compute_area(const Vec3& v0, const Vec3& v1, const Vec3& v2);

    // 从三角形列表构建 RWG 基函数（内边检测）
    // include_boundary: 若 true，则边界边也生成半 RWG 基（t_minus=-1）
    void build_rwg_bases(bool include_boundary = false);

    // 诊断信息
    Index num_interior_edges() const;
    Real total_area() const;
};

// —— RWG 形函数与散度 —— //

// RWG 矢量形函数：在三角形 tri 上的点 r 处求值
//   tri = t_plus 或 t_minus
//   返回 Vec3（电流方向）
Vec3 rwg_shape(const RwgBasis& b, const TriMesh& mesh, const Vec3& r, Index tri);

// RWG 散度（每三角形常数）
//   t_plus: +edge_length / (2 * area_plus)
//   t_minus: -edge_length / (2 * area_minus)
Real rwg_div(const RwgBasis& b, const TriMesh& mesh, Index tri);

} // namespace mom::mesh
