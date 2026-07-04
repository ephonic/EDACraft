// =====================================================================
// mom/mesh/trimesh.cpp —— 三角网格 + RWG 基函数实现
// =====================================================================
#include "mom/mesh/trimesh.hpp"
#include "mom/common/vec3_ext.hpp"

#include <cmath>
#include <set>
#include <stdexcept>

namespace mom::mesh {

// =====================================================================
// 工具函数
// =====================================================================

Real TriMesh::compute_area(const Vec3& v0, const Vec3& v1, const Vec3& v2) {
    Vec3 e1 = v1 - v0;
    Vec3 e2 = v2 - v0;
    return 0.5 * norm(cross(e1, e2));
}

// 判断点是否在三角形内（重心坐标法）
static bool point_in_triangle(const Vec3& p, const Vec3& a, const Vec3& b, const Vec3& c) {
    Vec3 v0 = c - a, v1 = b - a, v2 = p - a;
    Real dot00 = dot(v0, v0), dot01 = dot(v0, v1), dot02 = dot(v0, v2);
    Real dot11 = dot(v1, v1), dot12 = dot(v1, v2);
    Real denom = dot00 * dot11 - dot01 * dot01;
    if (std::abs(denom) < 1e-30) return false;
    Real u = (dot11 * dot02 - dot01 * dot12) / denom;
    Real v = (dot00 * dot12 - dot01 * dot02) / denom;
    return (u >= -1e-10) && (v >= -1e-10) && (u + v <= 1 + 1e-10);
}

// 规范化边（小索引在前），用于边键
static std::pair<Index, Index> edge_key(Index a, Index b) {
    return (a < b) ? std::make_pair(a, b) : std::make_pair(b, a);
}

// =====================================================================
// 矩形带网格
// =====================================================================
TriMesh TriMesh::rectangle_strip(Real x0, Real x1, Real y0, Real y1,
                                  Real z, int nx, int ny, Index layer) {
    TriMesh mesh;
    if (nx < 1 || ny < 1)
        throw std::runtime_error("rectangle_strip: nx, ny >= 1 required");

    const Real dx = (x1 - x0) / nx;
    const Real dy = (y1 - y0) / ny;

    // 生成顶点 (nx+1) × (ny+1)
    mesh.vertices.resize((nx + 1) * (ny + 1));
    for (int j = 0; j <= ny; ++j)
        for (int i = 0; i <= nx; ++i) {
            Index idx = j * (nx + 1) + i;
            mesh.vertices[idx] = TriVertex{x0 + i * dx, y0 + j * dy, z, layer};
        }

    // 生成三角形：每矩形单元 2 个三角形
    // 对角线方向交替以避免偏差（保证网格对称性）
    mesh.triangles.reserve(nx * ny * 2);
    for (int j = 0; j < ny; ++j)
        for (int i = 0; i < nx; ++i) {
            Index v00 = j * (nx + 1) + i;
            Index v10 = j * (nx + 1) + (i + 1);
            Index v01 = (j + 1) * (nx + 1) + i;
            Index v11 = (j + 1) * (nx + 1) + (i + 1);

            // 交替对角线方向以保证网格对称性
            if ((i + j) % 2 == 0) {
                // 三角形 1: v00 → v10 → v11（逆时针，法向 +z）
                Triangle t1;
                t1.v[0] = v00; t1.v[1] = v10; t1.v[2] = v11;
                mesh.triangles.push_back(t1);

                // 三角形 2: v00 → v11 → v01
                Triangle t2;
                t2.v[0] = v00; t2.v[1] = v11; t2.v[2] = v01;
                mesh.triangles.push_back(t2);
            } else {
                // 三角形 1: v00 → v10 → v01（逆时针，法向 +z）
                Triangle t1;
                t1.v[0] = v00; t1.v[1] = v10; t1.v[2] = v01;
                mesh.triangles.push_back(t1);

                // 三角形 2: v10 → v11 → v01
                Triangle t2;
                t2.v[0] = v10; t2.v[1] = v11; t2.v[2] = v01;
                mesh.triangles.push_back(t2);
            }
        }

    // 预计算面积、法向、重心
    for (auto& tri : mesh.triangles) {
        Vec3 p0 = mesh.vertices[tri.v[0]].pos();
        Vec3 p1 = mesh.vertices[tri.v[1]].pos();
        Vec3 p2 = mesh.vertices[tri.v[2]].pos();
        tri.area = compute_area(p0, p1, p2);
        Vec3 n = cross(p1 - p0, p2 - p0);
        tri.normal = normalized(n);
        tri.centroid = (p0 + p1 + p2) * (1.0 / 3.0);
    }

    // 构建 RWG 基函数
    mesh.build_rwg_bases();
    return mesh;
}

// =====================================================================
// 从三角形列表构造
// =====================================================================
TriMesh TriMesh::from_triangle_list(const std::vector<Vec3>& verts,
                                    const std::vector<std::array<Index, 3>>& tris,
                                    Index layer) {
    TriMesh mesh;
    mesh.vertices.resize(verts.size());
    for (Index i = 0; i < Index(verts.size()); ++i)
        mesh.vertices[i] = {verts[i].x, verts[i].y, verts[i].z, layer};

    mesh.triangles.resize(tris.size());
    for (Index i = 0; i < Index(tris.size()); ++i) {
        mesh.triangles[i].v[0] = tris[i][0];
        mesh.triangles[i].v[1] = tris[i][1];
        mesh.triangles[i].v[2] = tris[i][2];
    }

    for (auto& tri : mesh.triangles) {
        Vec3 p0 = mesh.vertices[tri.v[0]].pos();
        Vec3 p1 = mesh.vertices[tri.v[1]].pos();
        Vec3 p2 = mesh.vertices[tri.v[2]].pos();
        tri.area = compute_area(p0, p1, p2);
        Vec3 n = cross(p1 - p0, p2 - p0);
        tri.normal = normalized(n);
        tri.centroid = (p0 + p1 + p2) * (1.0 / 3.0);
    }

    mesh.build_rwg_bases();
    return mesh;
}

// =====================================================================
// 内边检测 + RWG 基函数生成
// =====================================================================
void TriMesh::build_rwg_bases() {
    // 建立边 → 三角形对的映射
    // 每条边由规范化顶点对 (min, max) 标识
    struct EdgeInfo {
        Index tri1 = -1;       // 第一个三角形
        Index tri2 = -1;       // 第二个三角形（内边时有）
        Index v_shared[2];     // 共享边顶点（在 tri1 中的局部索引）
        Index v_shared_t2[2];  // 共享边顶点（在 tri2 中的局部索引）
    };

    std::map<std::pair<Index, Index>, EdgeInfo> edge_map;

    for (Index ti = 0; ti < Index(triangles.size()); ++ti) {
        const auto& tri = triangles[ti];
        for (int e = 0; e < 3; ++e) {
            Index va = tri.v[e];
            Index vb = tri.v[(e + 1) % 3];
            auto key = edge_key(va, vb);
            auto& info = edge_map[key];
            if (info.tri1 < 0) {
                info.tri1 = ti;
                info.v_shared[0] = e;
                info.v_shared[1] = (e + 1) % 3;
            } else {
                info.tri2 = ti;
                // 找到共享边在 tri2 中的局部索引
                for (int le = 0; le < 3; ++le) {
                    Index la = triangles[ti].v[le];
                    Index lb = triangles[ti].v[(le + 1) % 3];
                    auto k2 = edge_key(la, lb);
                    if (k2 == key) {
                        info.v_shared_t2[0] = le;
                        info.v_shared_t2[1] = (le + 1) % 3;
                        break;
                    }
                }
            }
        }
    }

    // 生成 RWG 基函数（仅内边，即 tri2 >= 0 的边）
    bases.clear();
    for (const auto& [key, info] : edge_map) {
        if (info.tri2 < 0) continue;   // 边界边，跳过

        RwgBasis basis;
        basis.t_plus = info.tri1;
        basis.t_minus = info.tri2;

        // 共享边的两个全局顶点
        const auto& t1 = triangles[info.tri1];
        basis.v_edge[0] = t1.v[info.v_shared[0]];
        basis.v_edge[1] = t1.v[info.v_shared[1]];

        // 边长
        Vec3 ep0 = vertices[basis.v_edge[0]].pos();
        Vec3 ep1 = vertices[basis.v_edge[1]].pos();
        basis.edge_length = dist(ep0, ep1);

        // 检测是否为垂直边（z 方向）
        // 如果边的 z 分量变化显著，则标记为垂直边
        Real dz = std::abs(ep1.z - ep0.z);
        Real dxy = std::sqrt((ep1.x - ep0.x)*(ep1.x - ep0.x) + 
                             (ep1.y - ep0.y)*(ep1.y - ep0.y));
        basis.is_vertical = (dz > 0.5 * basis.edge_length);  // z 分量占主导

        // 找各三角形的自由顶点（不在共享边上的那个）
        for (int vi = 0; vi < 3; ++vi) {
            Index gv = t1.v[vi];
            if (gv != basis.v_edge[0] && gv != basis.v_edge[1]) {
                basis.v_free_plus = gv;
                break;
            }
        }
        const auto& t2 = triangles[info.tri2];
        for (int vi = 0; vi < 3; ++vi) {
            Index gv = t2.v[vi];
            if (gv != basis.v_edge[0] && gv != basis.v_edge[1]) {
                basis.v_free_minus = gv;
                break;
            }
        }

        bases.push_back(basis);
    }
}

// =====================================================================
// RWG 形函数与散度
// =====================================================================

Vec3 rwg_shape(const RwgBasis& b, const TriMesh& mesh, const Vec3& r, Index tri) {
    if (tri == b.t_plus) {
        // f = +(l/(2A⁺))(r - ρ_free⁺)
        Vec3 rho_free = mesh.vertices[b.v_free_plus].pos();
        Real coef = b.edge_length / (2.0 * mesh.triangles[b.t_plus].area);
        return (r - rho_free) * coef;
    } else if (tri == b.t_minus) {
        // f = -(l/(2A⁻))(r - ρ_free⁻)
        Vec3 rho_free = mesh.vertices[b.v_free_minus].pos();
        Real coef = b.edge_length / (2.0 * mesh.triangles[b.t_minus].area);
        return (rho_free - r) * coef;
    }
    return Vec3(0, 0, 0);   // 不在此基函数的支撑域
}

Real rwg_div(const RwgBasis& b, const TriMesh& mesh, Index tri) {
    if (tri == b.t_plus)
        return b.edge_length / mesh.triangles[b.t_plus].area;     // +l/A⁺
    if (tri == b.t_minus)
        return -b.edge_length / mesh.triangles[b.t_minus].area;   // -l/A⁻
    return 0;
}

// =====================================================================
// 诊断
// =====================================================================
Index TriMesh::num_interior_edges() const {
    return Index(bases.size());
}

Real TriMesh::total_area() const {
    Real s = 0;
    for (const auto& t : triangles) s += t.area;
    return s;
}

} // namespace mom::mesh
