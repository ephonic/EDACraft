// =====================================================================
// bindings/mom_bindings.cpp —— pybind11 绑定（_mom 扩展）
//
// 阶段 0 目标：验证 Python ↔ C++ ↔ NumPy 零拷贝通路，并暴露
//             FrequencySweep（与 Python 侧 mom.FreqSweep 同源）。
// 重活（格林函数 / MoM / pFFT）由后续阶段逐步绑定。
// =====================================================================

// 包含 pybind11 核心头文件（但不包含 stl.h）
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

// 包含 TriMesh 定义
#include "mom/mesh/trimesh.hpp"

// 必须在包含 pybind11/stl.h 之前声明 PYBIND11_MAKE_OPAQUE
// 否则 std::vector 等 STL 容器的自动转换规则会先注册，导致 TriMesh 被转换为 tuple
PYBIND11_MAKE_OPAQUE(mom::mesh::TriMesh);

// 现在可以安全地包含 stl.h
#include <pybind11/stl.h>

#include "mom/sweep/frequency_sweep.hpp"
#include "mom/microstrip.hpp"
#include "mom/mesh/mesh.hpp"
#include "mom/mom/rwg_assembly.hpp"
#include "mom/mom/efie.hpp"
#include "mom/solver/dense.hpp"
#include "mom/solver/pfft.hpp"
#include "mom/tl_extract.hpp"
#include "mom/green/green.hpp"
#include "mom/green/spectral.hpp"
#include "mom/green/poles.hpp"
#include "mom/green/branch.hpp"
#include "mom/green/medium.hpp"
#include "mom/green/layered_spatial.hpp"
#include "mom/green/qwe.hpp"
#include "mom/green/dyadic.hpp"
#include "mom/lc_extract.hpp"
#include "mom/common/vec3.hpp"
#include "mom/common/types.hpp"

namespace py = pybind11;
using mom::Real;
using mom::Complex;
using mom::Size;
using mom::Index;
using mom::SweepScale;
using mom::FrequencySweep;
using mom::MicrostripConfig;
using mom::solve_microstrip_sparam;
using mom::Vec3;
using mom::Iunit;
namespace gphys = mom::phys;

// ---- 最小冒烟测试：证明 C++↔NumPy 零拷贝通路 ----
// 接收一个 NumPy float64 数组，就地平方（非拥有视图，零拷贝）。
static void square_inplace(py::array_t<double, py::array::c_style> arr) {
    auto buf = arr.mutable_unchecked<1>();
    for (py::ssize_t i = 0; i < buf.shape(0); ++i)
        buf(i) *= buf(i);
}

PYBIND11_MODULE(_mom, m) {
    m.doc() = "mom C++ core bindings (MoM + multilayer Green's function)";

    m.def("square_inplace", &square_inplace,
          py::arg("arr").noconvert(),
          "就地平方一个 float64 NumPy 数组（零拷贝通路冒烟测试）");

    // ---- SweepScale 枚举 ----
    py::enum_<SweepScale>(m, "SweepScale")
        .value("Linear", SweepScale::Linear)
        .value("Log",    SweepScale::Log);

    // ---- FrequencySweep ----
    py::class_<FrequencySweep>(m, "FrequencySweep")
        .def(py::init<>())
        .def(py::init<Real, Real, Size, SweepScale>(),
             py::arg("start"), py::arg("stop"),
             py::arg("count"), py::arg("scale"))
        .def_readwrite("start", &FrequencySweep::start)
        .def_readwrite("stop",  &FrequencySweep::stop)
        .def_readwrite("count", &FrequencySweep::count)
        .def_readwrite("scale", &FrequencySweep::scale)
        .def("frequencies", [](const FrequencySweep& self) {
            auto freqs = self.frequencies();
            // 返回 NumPy 视图（拷贝一次，但为连续 double 数组，下游高效）
            py::array_t<double> result(freqs.size());
            auto buf = result.mutable_unchecked<1>();
            for (Size i = 0; i < freqs.size(); ++i)
                buf(i) = freqs[i];
            return result;
        }, "生成本次扫频的全部频点（Hz），返回 NumPy float64 数组");

    m.attr("__version__") = "0.0.1";

    // ---- MicrostripConfig ----
    py::class_<MicrostripConfig>(m, "MicrostripConfig")
        .def(py::init<>())
        .def_readwrite("length",     &MicrostripConfig::length)
        .def_readwrite("width",      &MicrostripConfig::width)
        .def_readwrite("height",     &MicrostripConfig::height)
        .def_readwrite("eps_eff",    &MicrostripConfig::eps_eff)
        .def_readwrite("nx",         &MicrostripConfig::nx)
        .def_readwrite("gauss",      &MicrostripConfig::gauss)
        .def_readwrite("z0_ref",     &MicrostripConfig::z0_ref)
        .def_readwrite("has_ground", &MicrostripConfig::has_ground);

    // ---- 单频点求解：返回 2x2 S 参数（NumPy complex128） ----
    m.def("solve_microstrip", [](Real freq, const MicrostripConfig& cfg) {
        auto s = solve_microstrip_sparam(freq, cfg);
        std::vector<py::ssize_t> shape{2, 2};
        py::array_t<std::complex<double>> arr(shape);
        auto buf = arr.mutable_unchecked<2>();
        for (int i = 0; i < 2; ++i)
            for (int j = 0; j < 2; ++j)
                buf(i, j) = s[i * 2 + j];
        return arr;
    }, py::arg("freq"), py::arg("cfg"),
       "求解微带线 2 端口 S 参数（单频点）。返回 (2,2) complex128 数组。");

    // ---- TriMesh（三角网格 + RWG 基函数）----
    py::class_<mom::mesh::TriMesh>(m, "TriMesh")
        .def(py::init<>())
        .def("n_vertices", [](const mom::mesh::TriMesh& m) { return m.vertices.size(); })
        .def("n_triangles", [](const mom::mesh::TriMesh& m) { return m.triangles.size(); })
        .def("n_rwg", [](const mom::mesh::TriMesh& m) { return m.bases.size(); })
        .def("n_interior_edges", [](const mom::mesh::TriMesh& m) { return m.num_interior_edges(); })
        .def("total_area", [](const mom::mesh::TriMesh& m) { return m.total_area(); })
        .def("build_rwg_bases", &mom::mesh::TriMesh::build_rwg_bases,
             "从三角形列表构建 RWG 基函数（内边检测）")
        .def("get_rwg_info", [](const mom::mesh::TriMesh& m, Index i) {
            if (static_cast<size_t>(i) >= m.bases.size()) throw std::out_of_range("RWG index out of range");
            const auto& b = m.bases[i];
            return py::dict(
                py::arg("t_plus") = b.t_plus,
                py::arg("t_minus") = b.t_minus,
                py::arg("edge_length") = b.edge_length,
                py::arg("is_vertical") = b.is_vertical,
                py::arg("is_interior") = b.is_interior()
            );
        }, py::arg("i"), "获取第 i 个 RWG 基函数的信息")
        .def("get_vertex", [](const mom::mesh::TriMesh& m, Index i) {
            if (static_cast<size_t>(i) >= m.vertices.size()) throw std::out_of_range("Vertex index out of range");
            const auto& v = m.vertices[i];
            return py::make_tuple(v.x, v.y, v.z);
        }, py::arg("i"), "获取第 i 个顶点的坐标 (x, y, z)")
        .def("get_triangle", [](const mom::mesh::TriMesh& m, Index i) {
            if (static_cast<size_t>(i) >= m.triangles.size()) throw std::out_of_range("Triangle index out of range");
            const auto& t = m.triangles[i];
            return py::make_tuple(t.v[0], t.v[1], t.v[2]);
        }, py::arg("i"), "获取第 i 个三角形的顶点索引 (v0, v1, v2)")
        .def("get_triangle_centroid", [](const mom::mesh::TriMesh& m, Index i) {
            if (static_cast<size_t>(i) >= m.triangles.size()) throw std::out_of_range("Triangle index out of range");
            const auto& t = m.triangles[i];
            return py::make_tuple(t.centroid.x, t.centroid.y, t.centroid.z);
        }, py::arg("i"), "获取第 i 个三角形的重心坐标 (x, y, z)");

    m.def("trimesh_rectangle_strip", [](double x0, double x1, double y0, double y1,
                                         double z, int nx, int ny, int layer) -> std::unique_ptr<mom::mesh::TriMesh> {
        return std::make_unique<mom::mesh::TriMesh>(
            mom::mesh::TriMesh::rectangle_strip(x0, x1, y0, y1, z, nx, ny, layer));
    }, py::arg("x0"), py::arg("x1"), py::arg("y0"), py::arg("y1"),
       py::arg("z"), py::arg("nx"), py::arg("ny"), py::arg("layer") = 0,
       "[M1] 矩形带三角网格 + RWG 基函数。");

    // 从顶点和三角形列表创建 TriMesh（用于测试垂直结构）
    m.def("trimesh_from_list", [](py::array_t<double> verts, py::array_t<int> tris, int layer) -> std::unique_ptr<mom::mesh::TriMesh> {
        auto v_buf = verts.unchecked<2>();
        auto t_buf = tris.unchecked<2>();
        
        if (v_buf.shape(1) != 3) throw std::runtime_error("verts must have shape (N, 3)");
        if (t_buf.shape(1) != 3) throw std::runtime_error("tris must have shape (M, 3)");
        
        std::vector<mom::Vec3> vertices(v_buf.shape(0));
        for (py::ssize_t i = 0; i < v_buf.shape(0); ++i) {
            vertices[i] = mom::Vec3(v_buf(i, 0), v_buf(i, 1), v_buf(i, 2));
        }
        
        std::vector<std::array<Index, 3>> triangles(t_buf.shape(0));
        for (py::ssize_t i = 0; i < t_buf.shape(0); ++i) {
            triangles[i] = {{static_cast<Index>(t_buf(i, 0)), 
                            static_cast<Index>(t_buf(i, 1)), 
                            static_cast<Index>(t_buf(i, 2))}};
        }
        
        return std::make_unique<mom::mesh::TriMesh>(
            mom::mesh::TriMesh::from_triangle_list(vertices, triangles, static_cast<Index>(layer)));
    }, py::arg("verts"), py::arg("tris"), py::arg("layer") = 0,
       "从顶点数组 (N,3) 和三角形数组 (M,3) 创建 TriMesh。");

    // ---- 并矢格林函数（M2）----
    py::class_<mom::green::dyadic::SpatialDyadic>(m, "SpatialDyadic")
        .def("vector_dot", &mom::green::dyadic::SpatialDyadic::vector_dot,
             py::arg("rho"), py::arg("fx"), py::arg("fy"), py::arg("fz"),
             py::arg("fxp"), py::arg("fyp"), py::arg("fzp"),
             "矢量位点积：G_A(ρ) · (fx·fx' + fy·fy') + G_Azz(ρ) · fz·fz'")
        .def("scalar_dot", &mom::green::dyadic::SpatialDyadic::scalar_dot,
             py::arg("rho"), py::arg("div_f"), py::arg("div_fp"),
             "标量势乘积：G_phi(ρ) · div_f · div_fp");

    m.def("build_dyadic_green", [](double freq, double eps_r, double tand, double h,
                                    double z_src, double z_obs, int n_intervals, int gauss_order) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_obs);
        std::vector<mom::green::poles::Pole> pole_list;  // 空极点列表
        return mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, n_intervals, gauss_order);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"),
       py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[M2] 构建空域并矢格林函数（水平电流版本）。");

    m.def("trimesh_from_list", [](py::array_t<double> verts_xyz,
                                   py::array_t<int> tris_v, int layer) {
        auto v = verts_xyz.unchecked<2>();
        auto t = tris_v.unchecked<2>();
        std::vector<mom::Vec3> verts(v.shape(0));
        for (int i = 0; i < v.shape(0); ++i)
            verts[i] = mom::Vec3(v(i,0), v(i,1), v(i,2));
        std::vector<std::array<mom::Index,3>> tris(t.shape(0));
        for (int i = 0; i < t.shape(0); ++i)
            tris[i] = {mom::Index(t(i,0)), mom::Index(t(i,1)), mom::Index(t(i,2))};
        auto mesh = mom::mesh::TriMesh::from_triangle_list(verts, tris, layer);
        return py::make_tuple(int(mesh.vertices.size()), int(mesh.triangles.size()), int(mesh.bases.size()));
    }, py::arg("verts"), py::arg("tris"), py::arg("layer") = 0,
       "[M1] 从顶点+三角形列表构造三角网格。");

    // ---- M3: RWG MPIE 装配 ----
    m.def("assemble_rwg_test", [](double freq, double eps_r, double tand, double h,
                                   double x0, double x1, double y0, double y1,
                                   int nx, int ny, int gauss_order) {
        // 构建三角网格
        auto mesh = mom::mesh::TriMesh::rectangle_strip(x0, x1, y0, y1, h, nx, ny);
        // 构建格林函数
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, 40, 5);
        // 装配
        auto blk = mom::mom::assemble_rwg(mesh, dyad, gauss_order);
        const Index nb = Index(mesh.bases.size());
        py::dict d;
        d["nb"] = int(nb);
        d["n_triangles"] = int(mesh.triangles.size());
        // 导出完整 ZA 矩阵
        py::array_t<std::complex<double>> za_array({nb, nb});
        auto za_buf = za_array.mutable_unchecked<2>();
        for (Index i = 0; i < nb; ++i)
            for (Index j = 0; j < nb; ++j)
                za_buf(i, j) = blk.ZA[i * nb + j];
        d["ZA"] = za_array;
        // 导出完整 ZPhi 矩阵
        py::array_t<std::complex<double>> zphi_array({nb, nb});
        auto zphi_buf = zphi_array.mutable_unchecked<2>();
        for (Index i = 0; i < nb; ++i)
            for (Index j = 0; j < nb; ++j)
                zphi_buf(i, j) = blk.ZPhi[i * nb + j];
        d["ZPhi"] = zphi_array;
        // ZA 最大/最小
        Real zmax = 0, zmin = 1e300;
        for (auto& v : blk.ZA) { zmax = std::max(zmax, std::abs(v)); zmin = std::min(zmin, std::abs(v)); }
        d["ZA_max"] = zmax;
        d["ZA_min"] = zmin;
        // 检查 NaN
        int nan_cnt = 0;
        for (auto& v : blk.ZA) if (!std::isfinite(v.real()) || !std::isfinite(v.imag())) nan_cnt++;
        d["ZA_nan"] = nan_cnt;
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("x0"), py::arg("x1"), py::arg("y0"), py::arg("y1"),
       py::arg("nx"), py::arg("ny"), py::arg("gauss_order") = 5,
       "[M3] RWG MPIE 装配测试（三角网格 + 并矢格林）。");

    // ---- M4: RWG 端到端 S 参数（三角网格 + QWE 并矢 + Schur N-端口）----
    m.def("solve_rwg_sparam", [](double freq, double eps_r, double tand, double h,
                                  double x0, double x1, double y0, double y1,
                                  int nx, int ny, int gauss_order,
                                  int n_intervals, int gauss_order_qwe,
                                  py::list ports_py, double z0_ref) {
        // 1. 三角网格
        auto mesh = mom::mesh::TriMesh::rectangle_strip(x0, x1, y0, y1, h, nx, ny);
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG 基函数过少");

        // 2. 并矢格林函数
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, n_intervals, gauss_order_qwe);

        // 3. RWG 装配
        auto rwg_blk = mom::mom::assemble_rwg(mesh, dyad, gauss_order);
        auto blk = mom::mom::to_mpie_blocks(rwg_blk);

        // 4. build_impedance + Schur N-端口
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);

        // 解析端口索引
        std::vector<Index> ports;
        for (auto p : ports_py) ports.push_back(Index(p.cast<int>()));
        const Index np = Index(ports.size());

        auto Zport = mom::schur_nport_export(Z, nb, ports);
        auto S = mom::zport_n_to_sparam(Zport, np, z0_ref);

        py::array_t<std::complex<double>> out({int(np), int(np)});
        auto ob = out.mutable_unchecked<2>();
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                ob(q, r) = S[q*np + r];
        return out;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("x0"), py::arg("x1"), py::arg("y0"), py::arg("y1"),
       py::arg("nx"), py::arg("ny"), py::arg("gauss_order") = 5,
       py::arg("n_intervals") = 40, py::arg("gauss_order_qwe") = 5,
       py::arg("ports"), py::arg("z0_ref") = 50.0,
       "[M4] RWG 端到端 S 参数（三角网格 + QWE 并矢 + Schur N-端口）。");

    // ---- 从预构建 TriMesh 求解 S 参数 ----
    m.def("solve_rwg_sparam_from_mesh", [](const mom::mesh::TriMesh& mesh,
                                             double freq, double eps_r, double tand, double h,
                                             int gauss_order,
                                             int n_intervals, int gauss_order_qwe,
                                             py::list ports_py, double z0_ref) {
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG bases too few");

        // 1. 并矢格林函数
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, n_intervals, gauss_order_qwe);

        // 2. RWG 装配
        auto rwg_blk = mom::mom::assemble_rwg(mesh, dyad, gauss_order);

        // 3. build_rwg_impedance（专用 RWG 阻抗构建）+ Schur N-端口
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_rwg_impedance(rwg_blk, mesh, omega);

        // 解析端口索引
        std::vector<Index> ports;
        for (auto p : ports_py) ports.push_back(Index(p.cast<int>()));
        const Index np = Index(ports.size());

        auto Zport = mom::schur_nport_export(Z, nb, ports);
        auto S = mom::zport_n_to_sparam(Zport, np, z0_ref);

        py::array_t<std::complex<double>> out({int(np), int(np)});
        auto ob = out.mutable_unchecked<2>();
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                ob(q, r) = S[q*np + r];
        return out;
    }, py::arg("mesh"), py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("gauss_order") = 5,
       py::arg("n_intervals") = 40, py::arg("gauss_order_qwe") = 5,
       py::arg("ports"), py::arg("z0_ref") = 50.0,
       "[M4] 从预构建 TriMesh 求解 RWG S 参数。");

    // ---- 构建 RWG 阻抗矩阵（专用量纲归一化）----
    m.def("build_rwg_impedance", [](py::dict rwg_blk_dict,
                                     const mom::mesh::TriMesh& mesh,
                                     double omega) {
        // Convert Python dict to RwgMPIEBlocks
        mom::mom::RwgMPIEBlocks rwg_blk;
        
        py::array_t<std::complex<double>> ZA_arr = rwg_blk_dict["ZA"].cast<py::array_t<std::complex<double>>>();
        py::array_t<std::complex<double>> ZPhi_arr = rwg_blk_dict["ZPhi"].cast<py::array_t<std::complex<double>>>();
        
        auto ZA_unchecked = ZA_arr.unchecked<1>();
        auto ZPhi_unchecked = ZPhi_arr.unchecked<1>();
        
        py::ssize_t size = ZA_arr.size();
        rwg_blk.ZA.resize(size);
        rwg_blk.ZPhi.resize(size);
        
        for (py::ssize_t i = 0; i < size; ++i) {
            rwg_blk.ZA[i] = ZA_unchecked(i);
            rwg_blk.ZPhi[i] = ZPhi_unchecked(i);
        }
        
        auto Z = mom::mom::build_rwg_impedance(rwg_blk, mesh, omega);
        const Index nb = Index(mesh.bases.size());
        py::array_t<std::complex<double>> out({int(nb), int(nb)});
        auto ob = out.mutable_unchecked<2>();
        for (Index m = 0; m < nb; ++m)
            for (Index n = 0; n < nb; ++n)
                ob(m, n) = Z[m * nb + n];
        return out;
    }, py::arg("rwg_blk"), py::arg("mesh"), py::arg("omega"),
       "构建 RWG 阻抗矩阵（专用量纲归一化）。");

    // ---- 从预构建 TriMesh 求解 S 参数（快速版本，使用查找表）----
    m.def("solve_rwg_sparam_from_mesh_fast", [](const mom::mesh::TriMesh& mesh,
                                             double freq, double eps_r, double tand, double h,
                                             int gauss_order, int n_lookup,
                                             py::list ports_py, double z0_ref) {
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG bases too few");

        // 1. 并矢格林函数
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, 40, 5);

        // 2. RWG 快速装配（使用查找表）
        auto rwg_blk = mom::mom::assemble_rwg_fast(mesh, dyad, gauss_order, n_lookup);

        // 3. build_rwg_impedance（专用 RWG 阻抗构建，正确处理量纲归一化）
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_rwg_impedance(rwg_blk, mesh, omega);

        // 解析端口索引
        std::vector<Index> ports;
        for (auto p : ports_py) ports.push_back(Index(p.cast<int>()));
        const Index np = Index(ports.size());

        // 使用 Schur 降阶获取正确的 N 端口阻抗矩阵
        // 注意：build_rwg_impedance 已经应用了 inv_lmln 归一化，
        // 所以 Z 矩阵已经是正确的 Ohm 量纲，不需要再次归一化
        auto Zport = mom::schur_nport_export(Z, nb, ports);
        
        auto S = mom::zport_n_to_sparam(Zport, np, z0_ref);

        py::array_t<std::complex<double>> out({int(np), int(np)});
        auto ob = out.mutable_unchecked<2>();
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                ob(q, r) = S[q*np + r];
        return out;
    }, py::arg("mesh"), py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("gauss_order") = 3, py::arg("n_lookup") = 200,
       py::arg("ports"), py::arg("z0_ref") = 50.0,
       "[M4] 从预构建 TriMesh 求解 RWG S 参数（快速版本）。");

    // ---- 从预构建 TriMesh 扫频求解 S 参数（pFFT + GMRES，支持 0-60 GHz）----
    m.def("solve_rwg_sparam_pfft_sweep", [](const mom::mesh::TriMesh& mesh,
                                             py::array_t<double> freqs,
                                             double eps_r, double tand, double h,
                                             py::list ports_py, double z0_ref,
                                             int grid_resolution, double near_threshold,
                                             double gmres_tol, int gmres_max_iter) {
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG bases too few");

        // 解析频率列表
        auto freq_buf = freqs.unchecked<1>();
        const Index nfreq = Index(freq_buf.shape(0));
        
        // 解析端口索引
        std::vector<Index> ports;
        for (auto p : ports_py) ports.push_back(Index(p.cast<int>()));
        const Index np = Index(ports.size());

        // 输出数组：(nfreq, nport, nport)
        py::array_t<std::complex<double>> out({int(nfreq), int(np), int(np)});
        auto ob = out.mutable_unchecked<3>();

        // 对每个频率点求解
        #ifdef MOM_HAS_OPENMP
        #pragma omp parallel for schedule(dynamic, 1)
        #endif
        for (Index fi = 0; fi < nfreq; ++fi) {
            double freq = freq_buf(fi);
            
            try {
                // 1. 并矢格林函数
                mom::green::spectral::LayeredMedium med;
                mom::green::DielectricLayer L;
                L.thickness = h; L.eps_r = eps_r; L.tand = tand;
                med.layers.push_back(L); med.ground_z = 0.0;
                mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
                const Real k0v = sg.k0();
                const Real k_med = k0v * std::sqrt(eps_r);
                auto pole_list = mom::green::poles::find_surface_wave_poles(
                    sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
                auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, 40, 5);

                // 2. 构建 pFFT 矩阵向量乘法器
                mom::solver::PFFTConfig config;
                config.grid_resolution = grid_resolution > 0 ? grid_resolution : 0;
                config.near_threshold = near_threshold;
                mom::solver::PFFTMatrixVector pfft_mat(mesh, dyad, config);

                // 3. 对每个端口求解
                std::vector<std::vector<Complex>> currents(np);

                for (Index p = 0; p < np; ++p) {
                    // 构建右端向量（端口激励）
                    std::vector<Complex> b(nb, Complex(0, 0));
                    b[ports[p]] = Complex(1, 0);

                    // GMRES 求解
                    auto x = mom::solver::solve_gmres(pfft_mat, b, gmres_tol, gmres_max_iter, 50);
                    currents[p] = x;
                }

                // 4. 提取端口阻抗
                std::vector<Complex> Zport(np * np, Complex(0, 0));
                for (Index q = 0; q < np; ++q) {
                    for (Index r = 0; r < np; ++r) {
                        Zport[q * np + r] = Complex(1, 0) / currents[r][ports[q]];
                    }
                }

                // 5. 转换为 S 参数
                auto S = mom::zport_n_to_sparam(Zport, np, z0_ref);

                // 6. 存储结果
                for (Index q = 0; q < np; ++q)
                    for (Index r = 0; r < np; ++r)
                        ob(fi, q, r) = S[q*np + r];
                        
            } catch (const std::exception& e) {
                // 如果某个频率点失败，填充 NaN
                for (Index q = 0; q < np; ++q)
                    for (Index r = 0; r < np; ++r)
                        ob(fi, q, r) = std::complex<double>(std::nan(""), std::nan(""));
            }
        }

        return out;
    }, py::arg("mesh"), py::arg("freqs"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("ports"), py::arg("z0_ref") = 50.0,
       py::arg("grid_resolution") = 0, py::arg("near_threshold") = 0.0,
       py::arg("gmres_tol") = 1e-6, py::arg("gmres_max_iter") = 1000,
       "[M4] 从预构建 TriMesh 扫频求解 RWG S 参数（pFFT + GMRES，支持 0-60 GHz）。");

    // ---- 正确的 S 参数提取：使用 pFFT 加速 + Schur complement ----
    m.def("solve_rwg_sparam_port_edges", [](const mom::mesh::TriMesh& mesh,
                                             py::array_t<double> freqs,
                                             double eps_r, double tand, double h,
                                             py::list port_edges_py,  // 每个端口是一个边缘基函数索引
                                             double z0_ref,
                                             int grid_resolution, double near_threshold,
                                             double gmres_tol, int gmres_max_iter) {
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG bases too few");

        // 解析频率列表
        auto freq_buf = freqs.unchecked<1>();
        const Index nfreq = Index(freq_buf.shape(0));
        
        // 解析端口边缘（每个端口一个基函数索引）
        std::vector<Index> port_edges;
        for (auto idx : port_edges_py) {
            port_edges.push_back(Index(idx.cast<int>()));
        }
        const Index np = Index(port_edges.size());
        
        if (np < 2) throw std::runtime_error("Need at least 2 ports");

        // 输出数组：(nfreq, nport, nport)
        py::array_t<std::complex<double>> out({int(nfreq), int(np), int(np)});
        auto ob = out.mutable_unchecked<3>();

        // 对每个频率点求解
        #ifdef MOM_HAS_OPENMP
        #pragma omp parallel for schedule(dynamic, 1)
        #endif
        for (Index fi = 0; fi < nfreq; ++fi) {
            double freq = freq_buf(fi);
            
            try {
                // 1. 并矢格林函数
                mom::green::spectral::LayeredMedium med;
                mom::green::DielectricLayer L;
                L.thickness = h; L.eps_r = eps_r; L.tand = tand;
                med.layers.push_back(L); med.ground_z = 0.0;
                mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
                const Real k0v = sg.k0();
                const Real k_med = k0v * std::sqrt(eps_r);
                auto pole_list = mom::green::poles::find_surface_wave_poles(
                    sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
                auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, 40, 5);

                // 2. 使用快速装配构建阻抗矩阵（而不是 pFFT）
                auto rwg_blk = mom::mom::assemble_rwg_fast(mesh, dyad, 3, 200);
                auto blk = mom::mom::to_mpie_blocks(rwg_blk);
                const Real omega = 2.0 * gphys::pi * freq;
                auto Z = mom::mom::build_impedance(blk, omega, eps_r);

                // 3. 使用 Schur complement 提取端口阻抗矩阵
                auto Zport = mom::schur_nport_export(Z, nb, port_edges);

                // 4. 转换为 S 参数
                auto S = mom::zport_n_to_sparam(Zport, np, z0_ref);

                // 5. 存储结果
                for (Index q = 0; q < np; ++q)
                    for (Index r = 0; r < np; ++r)
                        ob(fi, q, r) = S[q*np + r];
                        
            } catch (const std::exception& e) {
                // 如果某个频率点失败，填充 NaN
                for (Index q = 0; q < np; ++q)
                    for (Index r = 0; r < np; ++r)
                        ob(fi, q, r) = std::complex<double>(std::nan(""), std::nan(""));
            }
        }

        return out;
    }, py::arg("mesh"), py::arg("freqs"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("port_edges"), py::arg("z0_ref") = 50.0,
       py::arg("grid_resolution") = 0, py::arg("near_threshold") = 0.0,
       py::arg("gmres_tol") = 1e-6, py::arg("gmres_max_iter") = 1000,
       "[M4] 正确的 S 参数提取：使用快速装配 + Schur complement。");

    // ---- 集总端口激励：在信号和 GND 之间施加电压源 ----
    m.def("solve_rwg_lumped_port_sweep", [](const mom::mesh::TriMesh& mesh,
                                             py::array_t<double> freqs,
                                             double eps_r, double tand, double h,
                                             py::list signal_bases_py,  // 信号端 RWG 基函数索引
                                             py::list gnd_bases_py,     // GND 端 RWG 基函数索引
                                             double z0_ref,
                                             int grid_resolution, double near_threshold,
                                             double gmres_tol, int gmres_max_iter) {
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG bases too few");

        // 解析频率列表
        auto freq_buf = freqs.unchecked<1>();
        const Index nfreq = Index(freq_buf.shape(0));
        
        // 解析端口基函数索引
        std::vector<Index> signal_bases, gnd_bases;
        for (auto p : signal_bases_py) signal_bases.push_back(Index(p.cast<int>()));
        for (auto p : gnd_bases_py) gnd_bases.push_back(Index(p.cast<int>()));
        
        const Index n_signal = Index(signal_bases.size());
        const Index n_gnd = Index(gnd_bases.size());
        
        if (n_signal == 0 || n_gnd == 0) {
            throw std::runtime_error("Must provide at least one signal and one GND basis");
        }

        // 输出数组：(nfreq, 2, 2) - 2端口 S 参数
        py::array_t<std::complex<double>> out({int(nfreq), 2, 2});
        auto ob = out.mutable_unchecked<3>();

        // 对每个频率点求解
        #ifdef MOM_HAS_OPENMP
        #pragma omp parallel for schedule(dynamic, 1)
        #endif
        for (Index fi = 0; fi < nfreq; ++fi) {
            double freq = freq_buf(fi);
            
            try {
                // 1. 并矢格林函数
                mom::green::spectral::LayeredMedium med;
                mom::green::DielectricLayer L;
                L.thickness = h; L.eps_r = eps_r; L.tand = tand;
                med.layers.push_back(L); med.ground_z = 0.0;
                mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
                const Real k0v = sg.k0();
                const Real k_med = k0v * std::sqrt(eps_r);
                auto pole_list = mom::green::poles::find_surface_wave_poles(
                    sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
                auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, 40, 5);

                // 2. 构建 pFFT 矩阵向量乘法器
                mom::solver::PFFTConfig config;
                config.grid_resolution = grid_resolution > 0 ? grid_resolution : 0;
                config.near_threshold = near_threshold;
                mom::solver::PFFTMatrixVector pfft_mat(mesh, dyad, config);

                // 3. 构建集总端口激励向量
                // 端口 1：在信号端施加 +1，GND 端施加 -1
                std::vector<Complex> b1(nb, Complex(0, 0));
                Real signal_weight = 1.0 / Real(n_signal);
                Real gnd_weight = 1.0 / Real(n_gnd);
                
                for (Index idx : signal_bases) {
                    b1[idx] += Complex(signal_weight, 0);
                }
                for (Index idx : gnd_bases) {
                    b1[idx] -= Complex(gnd_weight, 0);
                }

                // 4. GMRES 求解
                auto x1 = mom::solver::solve_gmres(pfft_mat, b1, gmres_tol, gmres_max_iter, 50);

                // 5. 提取端口阻抗
                // V = 1V（施加的电压）
                // I = 从电流分布中提取
                // 简化：使用信号端电流的平均值
                Complex I_signal(0, 0);
                for (Index idx : signal_bases) {
                    I_signal += x1[idx];
                }
                I_signal /= Real(n_signal);
                
                // Z = V / I
                Complex Z11 = Complex(1, 0) / I_signal;
                
                // 转换为 S 参数（单端口简化）
                Complex S11 = (Z11 - z0_ref) / (Z11 + z0_ref);
                Complex S21 = Complex(2, 0) * std::sqrt(z0_ref) / (Z11 + z0_ref);
                
                // 存储结果（简化为 2x2，假设对称）
                ob(fi, 0, 0) = S11;
                ob(fi, 0, 1) = S21;
                ob(fi, 1, 0) = S21;
                ob(fi, 1, 1) = S11;
                        
            } catch (const std::exception& e) {
                // 如果某个频率点失败，填充 NaN
                for (int q = 0; q < 2; ++q)
                    for (int r = 0; r < 2; ++r)
                        ob(fi, q, r) = std::complex<double>(std::nan(""), std::nan(""));
            }
        }

        return out;
    }, py::arg("mesh"), py::arg("freqs"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("signal_bases"), py::arg("gnd_bases"),
       py::arg("z0_ref") = 50.0,
       py::arg("grid_resolution") = 0, py::arg("near_threshold") = 0.0,
       py::arg("gmres_tol") = 1e-5, py::arg("gmres_max_iter") = 200,
       "[M4] 集总端口激励求解 S 参数（信号-GND 端口）。");

    // ---- 从预构建 TriMesh 求解 S 参数（pFFT + GMRES 版本，适合大规模问题）----
    m.def("solve_rwg_sparam_pfft", [](const mom::mesh::TriMesh& mesh,
                                       double freq, double eps_r, double tand, double h,
                                       py::list ports_py, double z0_ref,
                                       int grid_resolution, double near_threshold,
                                       double gmres_tol, int gmres_max_iter) {
        const Index nb = Index(mesh.bases.size());
        if (nb < 8) throw std::runtime_error("RWG bases too few");

        // 1. 并矢格林函数
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        auto dyad = mom::green::dyadic::build_horizontal_dyadic(sg, eps_r, pole_list, 40, 5);

        // 2. 构建 pFFT 矩阵向量乘法器
        mom::solver::PFFTConfig config;
        config.grid_resolution = grid_resolution > 0 ? grid_resolution : 0;  // 0 = 自动
        config.near_threshold = near_threshold;
        mom::solver::PFFTMatrixVector pfft_mat(mesh, dyad, config);

        // 3. 解析端口索引
        std::vector<Index> ports;
        for (auto p : ports_py) ports.push_back(Index(p.cast<int>()));
        const Index np = Index(ports.size());

        // 4. 对每个端口求解
        const Real omega = 2.0 * gphys::pi * freq;
        std::vector<std::vector<Complex>> currents(np);

        for (Index p = 0; p < np; ++p) {
            // 构建右端向量（端口激励）
            std::vector<Complex> b(nb, Complex(0, 0));
            b[ports[p]] = Complex(1, 0);  // 简化：单位激励

            // GMRES 求解
            auto x = mom::solver::solve_gmres(pfft_mat, b, gmres_tol, gmres_max_iter, 50);
            currents[p] = x;
        }

        // 5. 提取端口阻抗（简化：使用电流比）
        std::vector<Complex> Zport(np * np, Complex(0, 0));
        for (Index q = 0; q < np; ++q) {
            for (Index r = 0; r < np; ++r) {
                // 简化：Z[q,r] = V[q] / I[r]（假设 V = 1）
                Zport[q * np + r] = Complex(1, 0) / currents[r][ports[q]];
            }
        }

        // 6. 转换为 S 参数
        auto S = mom::zport_n_to_sparam(Zport, np, z0_ref);

        py::array_t<std::complex<double>> out({int(np), int(np)});
        auto ob = out.mutable_unchecked<2>();
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                ob(q, r) = S[q*np + r];
        return out;
    }, py::arg("mesh"), py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("ports"), py::arg("z0_ref") = 50.0,
       py::arg("grid_resolution") = 0, py::arg("near_threshold") = 0.0,
       py::arg("gmres_tol") = 1e-6, py::arg("gmres_max_iter") = 1000,
       "[M4] 从预构建 TriMesh 求解 RWG S 参数（pFFT + GMRES，适合大规模问题）。");

    // ---- 扫频求解：逐点精确求解，返回 (nfreq, 2, 2) complex128 ----
    m.def("solve_microstrip_sweep",
          [](py::array_t<double> freqs, const MicrostripConfig& cfg) {
        auto fbuf = freqs.unchecked<1>();
        const Size nf = fbuf.shape(0);
        std::vector<py::ssize_t> shape{(py::ssize_t)nf, 2, 2};
        py::array_t<std::complex<double>> arr(shape);
        auto sbuf = arr.mutable_unchecked<3>();
        for (Size k = 0; k < nf; ++k) {
            auto s = solve_microstrip_sparam(fbuf(k), cfg);
            for (int i = 0; i < 2; ++i)
                for (int j = 0; j < 2; ++j)
                    sbuf((py::ssize_t)k, i, j) = s[i * 2 + j];
        }
        return arr;
    }, py::arg("freqs").noconvert(), py::arg("cfg"),
       "逐点扫频求解微带线 2 端口 S 参数。freqs 为 float64 频率数组 (Hz)，"
       "返回 (nfreq,2,2) complex128。");

    // ---- 调试：导出 MPIE 装配的矢量位块 ZA（行主序 nb×nb） ----
    m.def("debug_microstrip_ZA", [](const MicrostripConfig& cfg, double freq) {
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = cfg.length;
        mesh.y_min = -0.5 * cfg.width; mesh.y_max = 0.5 * cfg.width;
        mesh.z0 = cfg.height; mesh.nx = cfg.nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        const Real omega = 2.0 * gphys::pi * freq;
        const Real kk = mom::green::k0(omega) * std::sqrt(cfg.eps_eff);
        struct GCtx { Real k; Real ground_z; };
        GCtx gctx{kk, cfg.has_ground ? 0.0 :
                  std::numeric_limits<Real>::quiet_NaN()};
        auto cb_direct = [](double* ro, double* rs, void* ctx) -> Complex {
            auto* g = static_cast<GCtx*>(ctx);
            return mom::green::green_direct(Vec3(ro[0],ro[1],ro[2]),
                                       Vec3(rs[0],rs[1],rs[2]), g->k);
        };
        auto cb_imgA = [](double* ro, double* rs, void* ctx) -> Complex {
            auto* g = static_cast<GCtx*>(ctx);
            return mom::green::vector_green_image(Vec3(ro[0],ro[1],ro[2]),
                                       Vec3(rs[0],rs[1],rs[2]), g->k, g->ground_z);
        };
        auto cb_imgP = [](double* ro, double* rs, void* ctx) -> Complex {
            auto* g = static_cast<GCtx*>(ctx);
            return mom::green::scalar_green_image(Vec3(ro[0],ro[1],ro[2]),
                                       Vec3(rs[0],rs[1],rs[2]), g->k, g->ground_z);
        };
        auto blk = mom::mom::assemble_mpie(mesh, bases,
                                           cb_direct, cb_imgA,
                                           cb_direct, cb_imgP,
                                           &gctx, cfg.gauss);
        constexpr Real cf = gphys::inv_4pi * gphys::inv_4pi;
        std::vector<py::ssize_t> sh{nb, nb};
        py::array_t<std::complex<double>> A(sh), P(sh);
        auto ab = A.mutable_unchecked<2>();
        auto pb = P.mutable_unchecked<2>();
        for (Index i = 0; i < nb; ++i)
            for (Index j = 0; j < nb; ++j) {
                ab(i, j) = blk.ZA[i * nb + j] * cf;
                pb(i, j) = blk.ZPhi[i * nb + j] * cf;
            }
        return py::make_tuple(A, P, py::cast(nb));
    }, py::arg("cfg"), py::arg("freq"),
       "[调试] 返回 (ZA, ZPhi, nb)：装配后的矢量位/标量势块（已含 1/4π²）。");

    // ---- 调试：assemble_mpie_single 的 ZA/ZPhi 导出（归一化诊断）----
    m.def("debug_single_ZA", [](Real freq, Real eps_r, Real h, Real length,
                                Real width, int nx, int gauss) {
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        const Real k = mom::green::k0(2.0 * gphys::pi * freq) * std::sqrt(eps_r);
        auto GA_rho = [&](Real rho) -> Complex {
            return (mom::green::green_direct(Vec3(rho, 0, h), Vec3(0, 0, h), k)
                    + mom::green::vector_green_image(Vec3(rho, 0, h), Vec3(0, 0, h), k, 0.0))
                   / Complex(4.0 * gphys::pi, 0.0);
        };
        auto GP_rho = [&](Real rho) -> Complex {
            return (mom::green::green_direct(Vec3(rho, 0, h), Vec3(0, 0, h), k)
                    + mom::green::scalar_green_image(Vec3(rho, 0, h), Vec3(0, 0, h), k, 0.0))
                   / Complex(4.0 * gphys::pi, 0.0);
        };
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        std::vector<py::ssize_t> sh{nb, nb};
        py::array_t<std::complex<double>> A(sh), P(sh);
        auto ab = A.mutable_unchecked<2>(); auto pb = P.mutable_unchecked<2>();
        for (Index i = 0; i < nb; ++i)
            for (Index j = 0; j < nb; ++j) {
                ab(i, j) = blk.ZA[i * nb + j];
                pb(i, j) = blk.ZPhi[i * nb + j];
            }
        return py::make_tuple(A, P, py::cast(nb));
    }, py::arg("freq"), py::arg("eps_r"), py::arg("h"), py::arg("length"),
       py::arg("width"), py::arg("nx"), py::arg("gauss"),
       "[调试] assemble_mpie_single 的 ZA/ZPhi（诊断归一化）。");

    // ---- 传输线开路-短路法 Z0 提取 ----
    m.def("extract_tl_z0", [](Real freq, const MicrostripConfig& cfg) {
        // 复用 microstrip 求解器内部装配流程得到 Z，再调开路-短路法。
        // 这里直接重新装配以保证一致（与 solve_microstrip_sparam 同源）。
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = cfg.length;
        mesh.y_min = -0.5 * cfg.width; mesh.y_max = 0.5 * cfg.width;
        mesh.z0 = cfg.height; mesh.nx = cfg.nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 2) throw std::runtime_error("nx 过小");

        const Real omega = 2.0 * gphys::pi * freq;
        const Real k = mom::green::k0(omega) * std::sqrt(cfg.eps_eff);
        struct GCtx { Real k; Real ground_z; };
        GCtx gctx{k, cfg.has_ground ? 0.0 :
                  std::numeric_limits<Real>::quiet_NaN()};
        auto cb_dir = [](double* ro, double* rs, void* c) -> Complex {
            auto* g = static_cast<GCtx*>(c);
            return mom::green::green_direct(Vec3(ro[0],ro[1],ro[2]),
                                       Vec3(rs[0],rs[1],rs[2]), g->k);
        };
        auto cb_iA = [](double* ro, double* rs, void* c) -> Complex {
            auto* g = static_cast<GCtx*>(c);
            return mom::green::vector_green_image(Vec3(ro[0],ro[1],ro[2]),
                                       Vec3(rs[0],rs[1],rs[2]), g->k, g->ground_z);
        };
        auto cb_iP = [](double* ro, double* rs, void* c) -> Complex {
            auto* g = static_cast<GCtx*>(c);
            return mom::green::scalar_green_image(Vec3(ro[0],ro[1],ro[2]),
                                       Vec3(rs[0],rs[1],rs[2]), g->k, g->ground_z);
        };
        auto blk = mom::mom::assemble_mpie(mesh, bases, cb_dir, cb_iA,
                                           cb_dir, cb_iP, &gctx, cfg.gauss);
        constexpr Real cf = gphys::inv_4pi * gphys::inv_4pi;
        for (auto& v : blk.ZA)   v *= cf;
        for (auto& v : blk.ZPhi) v *= cf;
        auto Z = mom::mom::build_impedance(blk, omega, cfg.eps_eff);

        auto tl = mom::extract_tl_open_short(Z, nb, /*port_in=*/0, /*port_out=*/nb - 1);
        py::dict d;
        d["z_oc"] = tl.z_oc;
        d["z_sc"] = tl.z_sc;
        d["z0"]   = tl.z0;
        d["beta_l"] = tl.beta_l;
        d["nb"] = nb;
        return d;
    }, py::arg("freq"), py::arg("cfg"),
       "开路-短路法提取微带线特征阻抗 Z0 = sqrt(Z_oc·Z_sc)，返回 dict。");

    // ---- 谱域格林函数 G_tilde(k_rho)（阶段 2.1 验证用） ----
    // 输入：频率、介质（eps_r, tand, 厚度 h）、源/场 z、k_rho 复数组。
    // 返回：G_A、G_phi 复数组。
    m.def("spectral_green", [](double freq, double eps_r, double tand, double h,
                               double z_src, double z_obs,
                               py::array_t<double> kr_re, py::array_t<double> kr_im) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand; L.is_half_space = false;
        med.layers.push_back(L);
        med.ground_z = 0.0;   // PEC 底
        SG sg(med, freq, z_src, z_obs);

        auto kr = kr_re.unchecked<1>();
        auto ki = kr_im.unchecked<1>();
        const Size n = kr.shape(0);
        std::vector<py::ssize_t> sh{(py::ssize_t)n};
        py::array_t<std::complex<double>> GA(sh), GP(sh);
        auto ga = GA.mutable_unchecked<1>();
        auto gp = GP.mutable_unchecked<1>();
        for (Size i = 0; i < n; ++i) {
            Complex krho(kr(i), ki(i));
            auto k = sg(krho);
            ga(i) = k.G_A;
            gp(i) = k.G_phi;
        }
        return py::make_tuple(GA, GP);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"),
       py::arg("kr_re").noconvert(), py::arg("kr_im").noconvert(),
       "[阶段2] 谱域格林函数 G_A、G_phi 在给定 k_rho 复数组上的求值。");

    // ---- 调试：广义反射系数 Rup_TM/Rdn_TM（核对极点） ----
    m.def("debug_R_TM", [](double freq, double eps_r, double tand, double h,
                           double z_src, double kr_re, double kr_im) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_src);
        auto r = sg.debug_R_TM(Complex(kr_re, kr_im));
        return py::make_tuple(r.first, r.second);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("kr_re"), py::arg("kr_im"),
       "[调试] 返回 (Rup_TM, Rdn_TM)。");

    // ---- 多段 DCIM 拟合（含项提取：准静态 + 极点） + 空域复镜像（阶段 2.5） ----
    m.def("dcim_fit", [](double freq, double eps_r, double tand, double h,
                         double z_src, double z_obs,
                         py::array_t<double> k0_re, py::array_t<double> k0_im,
                         py::array_t<double> k1_re, py::array_t<double> k1_im,
                         int n_seg_pts, int n_images,
                         double pole_k_min, double pole_k_max, double pole_im_max, int pole_grid_n) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_obs);
        // 先找极点（用于项提取）
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, pole_k_min, pole_k_max, pole_im_max, pole_grid_n);
        auto k0r = k0_re.unchecked<1>(); auto k0i = k0_im.unchecked<1>();
        auto k1r = k1_re.unchecked<1>(); auto k1i = k1_im.unchecked<1>();
        const Size ns = k0r.shape(0);
        std::vector<std::pair<Complex, Complex>> paths;
        for (Size s = 0; s < ns; ++s)
            paths.emplace_back(Complex(k0r(s), k0i(s)), Complex(k1r(s), k1i(s)));
        auto fit = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, n_seg_pts, n_images);
        py::list result;
        for (auto& seg : fit.segments) {
            py::list seglist;
            for (auto& ci : seg) {
                py::dict d;
                d["amplitude"] = ci.amplitude;
                d["alpha"] = ci.alpha;
                seglist.append(d);
            }
            result.append(seglist);
        }
        // 同时返回极点（供空域重构用）
        py::list pole_py;
        for (auto& p : pole_list) {
            py::dict d;
            d["k_rho"] = p.k_rho; d["residue"] = p.residue;
            pole_py.append(d);
        }
        return py::make_tuple(result, pole_py);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"),
       py::arg("k0_re").noconvert(), py::arg("k0_im").noconvert(),
       py::arg("k1_re").noconvert(), py::arg("k1_im").noconvert(),
       py::arg("n_seg_pts"), py::arg("n_images"),
       py::arg("pole_k_min"), py::arg("pole_k_max"), py::arg("pole_im_max"), py::arg("pole_grid_n"),
       "[阶段2.5] 多段 DCIM（含项提取）+ 极点，返回 (segments, poles)。");

    // 由复镜像项计算空域格林函数
    m.def("dcim_spatial", [](py::list segments, double rho) {
        std::vector<mom::green::branch::ComplexImage> all;
        for (auto seg : segments)
            for (auto item : seg) {
                mom::green::branch::ComplexImage ci;
                ci.amplitude = item.cast<py::dict>()["amplitude"].cast<Complex>();
                ci.alpha = item.cast<py::dict>()["alpha"].cast<Complex>();
                all.push_back(ci);
            }
        return mom::green::branch::spatial_from_images(all, rho);
    }, py::arg("segments"), py::arg("rho"),
       "[阶段2.5] 由复镜像项计算空域支线格林函数贡献。");

    // ---- 空域格林函数重构（准静态 + 极点留数 + DCIM 复镜像）（阶段 2.7） ----
    m.def("spatial_GA", [](double freq, double eps_r, double tand, double h,
                           double z_src, double z_obs, double rho,
                           py::list segments, py::list poles_py) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_obs);
        std::vector<mom::green::poles::Pole> pole_list;
        for (auto p : poles_py) {
            auto d = p.cast<py::dict>();
            mom::green::poles::Pole pl;
            pl.k_rho = d["k_rho"].cast<Complex>();
            pl.residue = d["residue"].cast<Complex>();
            pole_list.push_back(pl);
        }
        std::vector<mom::green::branch::ComplexImage> images;
        for (auto seg : segments)
            for (auto item : seg) {
                mom::green::branch::ComplexImage ci;
                ci.amplitude = item.cast<py::dict>()["amplitude"].cast<Complex>();
                ci.alpha = item.cast<py::dict>()["alpha"].cast<Complex>();
                images.push_back(ci);
            }
        return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, images, rho, /*include_qs=*/true, /*phi_sign=*/false);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"), py::arg("rho"),
       py::arg("segments"), py::arg("poles"),
       "[阶段2.7] 空域格林函数重构（准静态+极点+DCIM）。");

    // 调试用：带 include_qs/phi_sign 显式参数的空域重构（no-QS 验证）
    m.def("spatial_GA2", [](double freq, double eps_r, double tand, double h,
                            double z_src, double z_obs, double rho,
                            py::list segments, py::list poles_py,
                            bool include_qs, bool phi_sign) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_obs);
        std::vector<mom::green::poles::Pole> pole_list;
        for (auto p : poles_py) {
            auto d = p.cast<py::dict>();
            mom::green::poles::Pole pl;
            pl.k_rho = d["k_rho"].cast<Complex>(); pl.residue = d["residue"].cast<Complex>();
            pole_list.push_back(pl);
        }
        std::vector<mom::green::branch::ComplexImage> images;
        for (auto seg : segments) for (auto item : seg) {
            mom::green::branch::ComplexImage ci;
            ci.amplitude = item.cast<py::dict>()["amplitude"].cast<Complex>();
            ci.alpha = item.cast<py::dict>()["alpha"].cast<Complex>();
            images.push_back(ci);
        }
        return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, images, rho, include_qs, phi_sign);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"), py::arg("rho"),
       py::arg("segments"), py::arg("poles"), py::arg("include_qs"), py::arg("phi_sign"),
       "[调试] 空域重构（显式 include_qs/phi_sign）。");

    // 调试用：带 extract_qs 参数的 DCIM 拟合（no-QS 验证）
    m.def("dcim_fit2", [](double freq, double eps_r, double tand, double h,
                          double z_src, double z_obs,
                          py::array_t<double> k0_re, py::array_t<double> k0_im,
                          py::array_t<double> k1_re, py::array_t<double> k1_im,
                          int n_seg_pts, int n_images,
                          double pole_k_min, double pole_k_max,
                          double pole_im_max, int pole_grid_n,
                          bool use_phi, bool extract_qs) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_obs);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, pole_k_min, pole_k_max, pole_im_max, pole_grid_n);
        auto k0r = k0_re.unchecked<1>(); auto k0i = k0_im.unchecked<1>();
        auto k1r = k1_re.unchecked<1>(); auto k1i = k1_im.unchecked<1>();
        const Size ns = k0r.shape(0);
        std::vector<std::pair<Complex, Complex>> paths;
        for (Size s = 0; s < ns; ++s)
            paths.emplace_back(Complex(k0r(s), k0i(s)), Complex(k1r(s), k1i(s)));
        auto fit = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, n_seg_pts, n_images, use_phi, extract_qs);
        py::tuple result = py::make_tuple();
        py::list segs; py::list poles_out;
        for (auto& seg : fit.segments) {
            py::list sl;
            for (auto& ci : seg) {
                py::dict d; d["amplitude"] = ci.amplitude; d["alpha"] = ci.alpha;
                sl.append(d);
            }
            segs.append(sl);
        }
        for (auto& p : pole_list) {
            py::dict d; d["k_rho"] = p.k_rho; d["residue"] = p.residue;
            poles_out.append(d);
        }
        return py::make_tuple(segs, poles_out);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"),
       py::arg("k0_re"), py::arg("k0_im"), py::arg("k1_re"), py::arg("k1_im"),
       py::arg("n_seg_pts"), py::arg("n_images"),
       py::arg("pole_k_min"), py::arg("pole_k_max"),
       py::arg("pole_im_max"), py::arg("pole_grid_n"),
       py::arg("use_phi"), py::arg("extract_qs"),
       "[调试] DCIM 拟合（显式 extract_qs）。");

    // ---- 阶段 3：多层格林函数 + MoM 装配，开路-短路 Z0 ----
    m.def("solve_layered_z0", [](double freq, double eps_r, double tand, double h,
                                 double length, double width, int nx, int gauss) {
        // 多层介质（单层 eps_r + PEC 底）
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        mom::green::LayeredSpatialGreen lg(sg, /*kmax_factor=*/30.0, /*n_pts=*/300);
        // 网格
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 2) throw std::runtime_error("nx 过小");
        // 单核装配
        auto blk = mom::mom::assemble_mpie_single(
            mesh, bases,
            [&](Real rho){ return lg.G_A(rho); },
            [&](Real rho){ return lg.G_phi(rho); },
            gauss, width);
        // 阻抗合成（eps_eff=eps_r；阶段 3 介质由格林函数吸收，此处 eps_eff 仅作系数占位）
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        // 开路-短路 Z0
        auto tl = mom::extract_tl_open_short(Z, nb, 0, nb - 1);
        py::dict d;
        d["z_oc"] = tl.z_oc; d["z_sc"] = tl.z_sc;
        d["z0"] = tl.z0; d["Re_zoc"] = tl.z_oc.real();
        d["nb"] = nb;
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       "[阶段3] 多层格林函数 + MoM 装配，开路-短路法 Z0。返回 dict。");

    // ---- 调试：导出空域格林函数 G_A(ρ)、G_phi(ρ)（阶段 3 验证用）----
    m.def("layered_green", [](double freq, double eps_r, double tand, double h,
                              py::array_t<double> rho_arr) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        mom::green::LayeredSpatialGreen lg(sg, 30.0, 300);
        auto rh = rho_arr.unchecked<1>();
        const Size n = rh.shape(0);
        py::array_t<std::complex<double>> GA(n), GP(n);
        auto ga = GA.mutable_unchecked<1>(); auto gp = GP.mutable_unchecked<1>();
        for (Size i = 0; i < n; ++i) {
            ga(i) = lg.G_A(rh(i));
            gp(i) = lg.G_phi(rh(i));
        }
        return py::make_tuple(GA, GP);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("rho_arr").noconvert(),
       "[调试] 空域格林函数 G_A(ρ)、G_phi(ρ)。");

    // ---- 阶段 3 验证：自由空间+镜像单核格林 + 单核装配，开路-短路 Z0 ----
    //   用阶段 1 已验证的自由空间+镜像格林（封装为单核 G(ρ)），验证单核装配路径正确。
    //   ε=1 + PEC 接地时，应复现阶段 1 的 Re(Z_oc)≈90Ω。
    m.def("solve_freespace_single_z0", [](double freq, double eps_r, double tand, double h,
                                          double length, double width, int nx, int gauss) {
        const Real omega = 2.0 * gphys::pi * freq;
        const Real k = mom::green::k0(omega) * std::sqrt(eps_r);
        // 自由空间+PEC 镜像格林（同阶段 1）封装为单核 G(ρ)。
        // G_A(ρ) = (1/(4π))(e^{-jkR1}/R1 + e^{-jkR2}/R2)，R1=ρ, R2=√(ρ²+(2h)²)
        auto GA_rho = [&](Real rho) -> Complex {
            Real r1 = rho;
            Vec3 obs(rho, 0, h), src(0, 0, h);
            return (mom::green::green_direct(obs, src, k)
                    + mom::green::vector_green_image(obs, src, k, 0.0)) / Complex(4.0 * gphys::pi, 0.0);
        };
        auto GP_rho = [&](Real rho) -> Complex {
            Vec3 obs(rho, 0, h), src(0, 0, h);
            return (mom::green::green_direct(obs, src, k)
                    + mom::green::scalar_green_image(obs, src, k, 0.0)) / Complex(4.0 * gphys::pi, 0.0);
        };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 2) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto tl = mom::extract_tl_open_short(Z, nb, 0, nb - 1);
        py::dict d;
        d["z_oc"] = tl.z_oc; d["z_sc"] = tl.z_sc;
        d["Re_zoc"] = tl.z_oc.real(); d["nb"] = nb;
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       "[阶段3验证] 自由空间+镜像单核装配 Z0（验证装配路径，应≈90Ω for eps=1）。");

    // ---- 阶段 3.5/3.6：DCIM 空域格林 + 单核装配，多层 Z0 ----
    m.def("solve_dcim_z0", [](double freq, double eps_r, double tand, double h,
                              double length, double width, int nx, int gauss) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real Ks = 5.0 * k0v;
        std::vector<std::pair<Complex, Complex>> paths;
        // DCIM 路径：起点必须避开实轴支点 k0（t=0 处 k_z=0 奇异会污染 GPOF）。
        // 从支点上方小偏置 k0·(1 + j·0.05) 起，斜向上至 (k0+Ks, Ks)。
        paths.emplace_back(Complex(k0v, 0.05 * k0v), Complex(k0v + Ks, Ks));
        // 表面波极点位于 k0 < Re(kρ) < k0·√ε_r 的第四象限（实轴下方）。
        // 搜索范围必须覆盖到介质波数 k0·√ε_r，否则漏极点 → DCIM 拟合污染。
        const Real k_med = k0v * std::sqrt(eps_r);
        const Real pole_im = 0.3 * k0v;   // 第四象限虚部搜索深度
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, pole_im, 200);
        // G_A 与 G_phi 分别 DCIM 拟合。多层（ε≠1）必须 extract_qs=false：
        //   完整 G̃ 沿上半平面路径指数衰减，GPOF 直接拟合（含界面反射结构），
        //   不再提取发散的"直接+PEC镜像"自由空间尾部。
        //   对应 spatial_GA_reconstruct 须 include_qs=false（仅复镜像 + 极点）。
        const bool use_no_qs = (eps_r != 1.0);
        auto fitA = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, 80, 10, /*use_phi=*/false, /*extract_qs=*/!use_no_qs);
        auto fitP = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, 80, 10, /*use_phi=*/true, /*extract_qs=*/!use_no_qs);
        std::vector<mom::green::branch::ComplexImage> imagesA, imagesPhi;
        for (auto& seg : fitA.segments)
            for (auto& ci : seg) imagesA.push_back(ci);
        for (auto& seg : fitP.segments)
            for (auto& ci : seg) imagesPhi.push_back(ci);

        auto GA_rho = [&](Real rho) {
            return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, imagesA, rho, /*include_qs=*/!use_no_qs, /*phi_sign=*/false);
        };
        auto GP_rho = [&](Real rho) {
            return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, imagesPhi, rho, /*include_qs=*/!use_no_qs, /*phi_sign=*/true);
        };

        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 2) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto tl = mom::extract_tl_open_short(Z, nb, 0, nb - 1);
        py::dict d;
        d["z_oc"] = tl.z_oc; d["z_sc"] = tl.z_sc;
        d["Re_zoc"] = tl.z_oc.real(); d["nb"] = nb;
        d["n_poles"] = int(pole_list.size());
        d["n_images"] = int(imagesA.size());
        d["Z_diag0_re"] = Z[0].real();
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       "[阶段3.6] DCIM 空域格林（G_A + G_phi 分离）+ 单核装配，多层 Z0（open-short）。");

    // ---- 本征模法 Z0 提取（对准静态电抗病态鲁棒）----
    m.def("solve_dcim_z0_eigen", [](double freq, double eps_r, double tand, double h,
                                    double length, double width, int nx, int gauss) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real Ks = 5.0 * k0v;
        std::vector<std::pair<Complex, Complex>> paths;
        paths.emplace_back(Complex(k0v, 0.05 * k0v), Complex(k0v + Ks, Ks));
        const Real k_med_e = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med_e, 0.3 * k0v, 200);
        const bool use_no_qs_e = (eps_r != 1.0);
        auto fitA = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, 80, 10, /*use_phi=*/false, /*extract_qs=*/!use_no_qs_e);
        auto fitP = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, 80, 10, /*use_phi=*/true, /*extract_qs=*/!use_no_qs_e);
        std::vector<mom::green::branch::ComplexImage> imagesA, imagesPhi;
        for (auto& seg : fitA.segments) for (auto& ci : seg) imagesA.push_back(ci);
        for (auto& seg : fitP.segments) for (auto& ci : seg) imagesPhi.push_back(ci);
        auto GA_rho = [&](Real rho){ return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, imagesA, rho, /*include_qs=*/!use_no_qs_e, /*phi_sign=*/false); };
        auto GP_rho = [&](Real rho){ return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, imagesPhi, rho, /*include_qs=*/!use_no_qs_e, /*phi_sign=*/true); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小（本征模法需 nb>=8）");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        const Real dx = length / Real(nx);
        auto tl = mom::extract_tl_eigenmode(Z, nb, dx);
        py::dict d;
        d["z0"] = tl.z0;
        d["beta_l"] = tl.beta_l;
        d["Re_z0"] = tl.z0.real();
        d["nb"] = nb;
        d["n_poles"] = int(pole_list.size());
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       "[阶段3.6] DCIM + 本征模法 Z0 提取（准静态鲁棒）。");

    // ---- QWE 空域格林（empymod 风格，尾部提取 + J1 零点分段 Shanks 外推）----
    // 单点空域格林诊断（验证用）
    m.def("qwe_spatial_GA", [](double freq, double eps_r, double tand, double h,
                               double rho, int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        return mom::green::qwe::spatial_GA_qwe(sg, rho, eps_r, n_intervals, gauss_order);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("rho"), py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE] 空域 G_A(ρ)（尾部提取 + QWE 残差）。");

    m.def("qwe_spatial_Gphi", [](double freq, double eps_r, double tand, double h,
                                 double rho, int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        return mom::green::qwe::spatial_Gphi_qwe(sg, rho, eps_r, n_intervals, gauss_order);
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("rho"), py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE] 空域 G_phi(ρ)。");

    // QWE 空域格林 + 单核装配 + Schur Z0 提取（端到端）
    m.def("solve_qwe_z0", [](double freq, double eps_r, double tand, double h,
                             double length, double width, int nx, int gauss,
                             int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        auto GA_rho = [&](Real rho){ return mom::green::qwe::spatial_GA_qwe(sg, rho, eps_r, n_intervals, gauss_order); };
        auto GP_rho = [&](Real rho){ return mom::green::qwe::spatial_Gphi_qwe(sg, rho, eps_r, n_intervals, gauss_order); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        // 诊断：Z 矩阵统计
        int nan_cnt = 0, inf_cnt = 0;
        double zmax_re = 0, zmin_re = 1e300;
        for (auto& v : Z) {
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag())) {
                if (std::isnan(v.real())) ++nan_cnt; else ++inf_cnt;
            }
            zmax_re = std::max(zmax_re, std::abs(v.real()));
            zmin_re = std::min(zmin_re, std::abs(v.real()));
        }
        auto tl = mom::extract_tl_open_short(Z, nb, 0, nb - 1);
        py::dict d;
        d["z_oc"] = tl.z_oc; d["z_sc"] = tl.z_sc;
        d["Re_zoc"] = tl.z_oc.real(); d["nb"] = nb;
        d["Z_nan"] = nan_cnt; d["Z_inf"] = inf_cnt;
        d["Z_maxre"] = zmax_re; d["Z_minre"] = zmin_re;
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE] QWE 空域格林 + 装配 + Schur Z0（多层鲁棒）。");

    // QWE + 装配 + L/C 提取（避免 open-short 病态）
    m.def("solve_qwe_z0_lc", [](double freq, double eps_r, double tand, double h,
                                double length, double width, int nx, int gauss,
                                int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        auto GA_rho = [&](Real rho){ return mom::green::qwe::spatial_GA_qwe(sg, rho, eps_r, n_intervals, gauss_order); };
        auto GP_rho = [&](Real rho){ return mom::green::qwe::spatial_Gphi_qwe(sg, rho, eps_r, n_intervals, gauss_order); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto lc = mom::lc::extract_lc(blk.ZA, blk.ZPhi, omega, eps_r, length, width, nb);
        py::dict d;
        d["z0"] = lc.z0; d["Re_z0"] = lc.z0.real(); d["beta"] = lc.beta;
        d["L"] = lc.L_per_len; d["C"] = lc.C_per_len; d["nb"] = nb;
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE+L/C] QWE 空域格林 + 装配 + L/C 提取 Z0（准静态鲁棒）。");

    // QWE 加速版（谱核缓存 + 插值，适合高 nx）
    m.def("solve_qwe_z0_fast", [](double freq, double eps_r, double tand, double h,
                                  double length, double width, int nx, int gauss,
                                  int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        // 谱核缓存：λ 范围覆盖装配中所有 ρ 的断点（ρ 最大 ~length，断点 j1z/ρ_min）
        const Real k0v = sg.k0();
        const Real lam_max = 200.0 * k0v;          // 远场截断
        const Real lam_min = 1e-3 * k0v;           // 近场
        mom::green::qwe::CachedQWE cqwe(sg, eps_r, lam_min, lam_max, 3000, n_intervals, gauss_order);
        auto GA_rho = [&](Real rho){ return cqwe.GA(rho); };
        auto GP_rho = [&](Real rho){ return cqwe.Gphi(rho); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto tl = mom::extract_tl_open_short(Z, nb, 0, nb - 1);
        py::dict d;
        d["z_oc"] = tl.z_oc; d["z_sc"] = tl.z_sc;
        d["z0"] = tl.z0; d["Re_zoc"] = tl.z_oc.real(); d["nb"] = nb;
        return d;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE-fast] 谱核缓存加速 + 装配 + Z0（高 nx 可行）。");

    // QWE 空域格林 + 装配 + Schur 2-端口 → S 参数（多层 ε≠1 可用）
    m.def("solve_qwe_sparam", [](double freq, double eps_r, double tand, double h,
                                 double length, double width, int nx, int gauss,
                                 double z0_ref, int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        auto GA_rho = [&](Real rho){ return mom::green::qwe::spatial_GA_qwe(sg, rho, eps_r, n_intervals, gauss_order); };
        auto GP_rho = [&](Real rho){ return mom::green::qwe::spatial_Gphi_qwe(sg, rho, eps_r, n_intervals, gauss_order); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        // Schur 2-端口 → S 参数
        auto Zport = mom::schur_2port_export(Z, nb, 0, nb - 1);
        auto S = mom::solver::zport_to_sparam(Zport, z0_ref, 2);
        py::array_t<std::complex<double>> out({2, 2});
        auto ob = out.mutable_unchecked<2>();
        for (int i = 0; i < 2; ++i)
            for (int j = 0; j < 2; ++j)
                ob(i, j) = S[i*2 + j];
        return out;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("z0_ref"), py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE S-param] QWE 空域格林 + 装配 + Schur 2-端口 → S 参数（多层 ε≠1）。");

    // QWE 加速版（CachedQWE 谱核缓存 + 插值）→ S 参数，带自适应 nx
    m.def("solve_qwe_sparam_auto", [](double freq, double eps_r, double tand, double h,
                                      double length, double width, double z0_ref,
                                      int gauss, int n_intervals, int gauss_order) {
        // 自适应 nx：dx = length/nx ≤ λ_eff / 15（每波长 15 点，工程精度）
        //   λ_eff = c / (f · √ε_eff)，ε_eff ≈ (ε_r+1)/2（初估）
        Real eps_eff_est = 0.5 * (eps_r + 1.0);
        Real lam_eff = 3e8 / (freq * std::sqrt(eps_eff_est));
        int nx = int(std::ceil(15.0 * length / lam_eff));
        nx = std::max(nx, 40);    // 最小 40（低频也保精度）
        nx = std::min(nx, 200);   // 最大 200（速度限制）

        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        const Real lam_min = 1e-3 * k0v;
        const Real lam_max = 200.0 * k0v;
        mom::green::qwe::CachedQWE cqwe(sg, eps_r, lam_min, lam_max, 3000, n_intervals, gauss_order);
        auto GA_rho = [&](Real rho){
            if (pole_list.empty()) return cqwe.GA(rho);
            return mom::green::qwe::spatial_GA_qwe_poles(sg, rho, eps_r, pole_list, n_intervals, gauss_order);
        };
        auto GP_rho = [&](Real rho){ return cqwe.Gphi(rho); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto Zport = mom::schur_2port_export(Z, nb, 0, nb - 1);
        auto S = mom::solver::zport_to_sparam(Zport, z0_ref, 2);
        py::array_t<std::complex<double>> out({2, 2});
        auto ob = out.mutable_unchecked<2>();
        for (int i = 0; i < 2; ++i)
            for (int j = 0; j < 2; ++j)
                ob(i, j) = S[i*2 + j];
        py::dict result;
        result["S"] = out;
        result["nx"] = nx;
        result["n_poles"] = int(pole_list.size());
        return result;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("z0_ref"),
       py::arg("gauss") = 3, py::arg("n_intervals") = 50, py::arg("gauss_order") = 6,
       "[QWE S-param auto] 自适应 nx（λ_eff/10）+ 极点提取 + Schur 2-端口 → S 参数。");

    // A-EFIE 求解（低频稳定）→ S 参数
    m.def("solve_aefie_sparam", [](double freq, double eps_r, double tand, double h,
                                   double length, double width, int nx, int gauss,
                                   double z0_ref, int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        const Real lam_min = 1e-3 * k0v;
        const Real lam_max = 200.0 * k0v;
        mom::green::qwe::CachedQWE cqwe(sg, eps_r, lam_min, lam_max, 3000, n_intervals, gauss_order);
        auto GA_rho = [&](Real rho){
            if (pole_list.empty()) return cqwe.GA(rho);
            return mom::green::qwe::spatial_GA_qwe_poles(sg, rho, eps_r, pole_list, n_intervals, gauss_order);
        };
        auto GP_rho = [&](Real rho){ return cqwe.Gphi(rho); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        const Real dx = length / Real(nx);

        // A-EFIE 求解 → 标准 Z 端口 → S 参数
        auto Zport = mom::mom::solve_aefie_zport(blk, omega, eps_r, dx, nb, 0, nb - 1);
        auto S = mom::solver::zport_to_sparam(Zport, z0_ref, 2);
        py::array_t<std::complex<double>> out({2, 2});
        auto ob = out.mutable_unchecked<2>();
        for (int i = 0; i < 2; ++i)
            for (int j = 0; j < 2; ++j)
                ob(i, j) = S[i*2 + j];
        return out;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("z0_ref"), py::arg("n_intervals") = 50, py::arg("gauss_order") = 6,
       "[A-EFIE] A-EFIE 低频稳定 + Schur 2-端口 → S 参数。");

    // QWE 加速版（CachedQWE 谱核缓存 + 插值）→ S 参数
    m.def("solve_qwe_sparam_fast", [](double freq, double eps_r, double tand, double h,
                                      double length, double width, int nx, int gauss,
                                      double z0_ref, int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        // 表面波极点搜索（高频厚介质必需）
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        const Real lam_min = 1e-3 * k0v;
        const Real lam_max = 200.0 * k0v;
        mom::green::qwe::CachedQWE cqwe(sg, eps_r, lam_min, lam_max, 3000, n_intervals, gauss_order);
        // 有极点时用 spatial_GA_qwe_poles，否则用缓存加速
        auto GA_rho = [&](Real rho){
            if (pole_list.empty()) return cqwe.GA(rho);
            return mom::green::qwe::spatial_GA_qwe_poles(sg, rho, eps_r, pole_list, n_intervals, gauss_order);
        };
        auto GP_rho = [&](Real rho){ return cqwe.Gphi(rho); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto Zport = mom::schur_2port_export(Z, nb, 0, nb - 1);
        auto S = mom::solver::zport_to_sparam(Zport, z0_ref, 2);
        py::array_t<std::complex<double>> out({2, 2});
        auto ob = out.mutable_unchecked<2>();
        for (int i = 0; i < 2; ++i)
            for (int j = 0; j < 2; ++j)
                ob(i, j) = S[i*2 + j];
        return out;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("z0_ref"), py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE S-param fast] 谱核缓存加速 + Schur 2-端口 → S 参数（多层快速）。");

    // N-端口 S 参数（QWE + Schur N-port）。ports 为端口基函数索引列表。
    m.def("solve_qwe_sparam_nport", [](double freq, double eps_r, double tand, double h,
                                       double length, double width, int nx, int gauss,
                                       py::object z0_ref_obj, py::list ports_py,
                                       int n_intervals, int gauss_order) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        mom::green::qwe::CachedQWE cqwe(sg, eps_r, 1e-3*k0v, 200.0*k0v, 3000, n_intervals, gauss_order);
        auto GA_rho = [&](Real rho){ return cqwe.GA(rho); };
        auto GP_rho = [&](Real rho){ return cqwe.Gphi(rho); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        // 解析端口索引
        std::vector<Index> ports;
        for (auto p : ports_py) ports.push_back(Index(p.cast<int>()));
        const Index np = Index(ports.size());
        if (np < 1) throw std::runtime_error("至少 1 个端口");
        for (Index p : ports) if (p >= nb) throw std::runtime_error("端口索引越界");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto Zport = mom::schur_nport_export(Z, nb, ports);
        // z0_ref: 标量（等参考）
        double z0 = 50.0;
        if (py::isinstance<py::float_>(z0_ref_obj) || py::isinstance<py::int_>(z0_ref_obj)) {
            z0 = z0_ref_obj.cast<double>();
        } else {
            z0 = z0_ref_obj.cast<py::list>()[0].cast<double>();
        }
        // N-port S = (Z - z0·I)(Z + z0·I)⁻¹（核心函数用 Eigen）
        auto S = mom::zport_n_to_sparam(Zport, np, z0);
        py::array_t<std::complex<double>> out({int(np), int(np)});
        auto ob = out.mutable_unchecked<2>();
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                ob(q, r) = S[q*np + r];
        return out;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("z0_ref"), py::arg("ports"),
       py::arg("n_intervals") = 60, py::arg("gauss_order") = 7,
       "[QWE N-port S-param] N-端口 S 参数（Schur N-port 降阶，多层快速）。");

    // DCIM 空域格林 + 装配 + Schur 2-端口 → S 参数（快速多层）
    m.def("solve_dcim_sparam", [](double freq, double eps_r, double tand, double h,
                                  double length, double width, int nx, int gauss,
                                  double z0_ref) {
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L); med.ground_z = 0.0;
        mom::green::spectral::SpectralGreensFunction sg(med, freq, h, h);
        const Real k0v = sg.k0();
        const Real Ks = 5.0 * k0v;
        std::vector<std::pair<Complex, Complex>> paths;
        paths.emplace_back(Complex(k0v, 0.05 * k0v), Complex(k0v + Ks, Ks));
        const Real k_med = k0v * std::sqrt(eps_r);
        auto pole_list = mom::green::poles::find_surface_wave_poles(
            sg, 0.95 * k0v, 1.05 * k_med, 0.3 * k0v, 200);
        const bool use_no_qs = (eps_r != 1.0);
        auto fitA = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, 80, 10, /*use_phi=*/false, /*extract_qs=*/!use_no_qs);
        auto fitP = mom::green::branch::fit_branch_cut_dcim(sg, pole_list, paths, 80, 10, /*use_phi=*/true,  /*extract_qs=*/!use_no_qs);
        std::vector<mom::green::branch::ComplexImage> imagesA, imagesPhi;
        for (auto& seg : fitA.segments) for (auto& ci : seg) imagesA.push_back(ci);
        for (auto& seg : fitP.segments) for (auto& ci : seg) imagesPhi.push_back(ci);
        auto GA_rho = [&](Real rho){ return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, imagesA, rho, /*include_qs=*/!use_no_qs, /*phi_sign=*/false); };
        auto GP_rho = [&](Real rho){ return mom::green::branch::spatial_GA_reconstruct(sg, pole_list, imagesPhi, rho, /*include_qs=*/!use_no_qs, /*phi_sign=*/true); };
        mom::mesh::RectMesh mesh;
        mesh.x_min = 0.0; mesh.x_max = length;
        mesh.y_min = -0.5 * width; mesh.y_max = 0.5 * width;
        mesh.z0 = h; mesh.nx = nx; mesh.ny = 1;
        auto bases = mesh.bases();
        const Index nb = Index(bases.size());
        if (nb < 8) throw std::runtime_error("nx 过小");
        auto blk = mom::mom::assemble_mpie_single(mesh, bases, GA_rho, GP_rho, gauss, width);
        const Real omega = 2.0 * gphys::pi * freq;
        auto Z = mom::mom::build_impedance(blk, omega, eps_r);
        auto Zport = mom::schur_2port_export(Z, nb, 0, nb - 1);
        auto S = mom::solver::zport_to_sparam(Zport, z0_ref, 2);
        py::array_t<std::complex<double>> out({2, 2});
        auto ob = out.mutable_unchecked<2>();
        for (int i = 0; i < 2; ++i)
            for (int j = 0; j < 2; ++j)
                ob(i, j) = S[i*2 + j];
        return out;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("length"), py::arg("width"), py::arg("nx"), py::arg("gauss"),
       py::arg("z0_ref"),
       "[DCIM S-param] DCIM 空域格林 + 装配 + Schur 2-端口 → S 参数（快速多层）。");


    m.def("find_poles", [](double freq, double eps_r, double tand, double h,
                           double z_src, double z_obs,
                           double k_min, double k_max, double im_max, int grid_n) {
        using SG = mom::green::spectral::SpectralGreensFunction;
        mom::green::spectral::LayeredMedium med;
        mom::green::DielectricLayer L;
        L.thickness = h; L.eps_r = eps_r; L.tand = tand;
        med.layers.push_back(L);
        med.ground_z = 0.0;
        SG sg(med, freq, z_src, z_obs);
        auto poles = mom::green::poles::find_surface_wave_poles(sg, k_min, k_max, im_max, grid_n);
        py::list result;
        for (auto& p : poles) {
            py::dict d;
            d["k_rho"] = p.k_rho;
            d["residue"] = p.residue;
            result.append(d);
        }
        return result;
    }, py::arg("freq"), py::arg("eps_r"), py::arg("tand"), py::arg("h"),
       py::arg("z_src"), py::arg("z_obs"),
       py::arg("k_min"), py::arg("k_max"), py::arg("im_max"), py::arg("grid_n"),
       "[阶段2.4] Chew 极点搜索：返回第四象限 surface-wave 极点列表（k_rho, residue）。");

    // ---- pFFT 加速（阶段 6）----
    py::class_<mom::solver::PFFTConfig>(m, "PFFTConfig")
        .def(py::init<>())
        .def_readwrite("near_threshold", &mom::solver::PFFTConfig::near_threshold)
        .def_readwrite("grid_resolution", &mom::solver::PFFTConfig::grid_resolution)
        .def_readwrite("use_double_precision_far", &mom::solver::PFFTConfig::use_double_precision_far);

    py::class_<mom::solver::PFFTMatrixVector>(m, "PFFTMatrixVector")
        .def(py::init<const mom::mesh::TriMesh&, const mom::green::dyadic::SpatialDyadic&, const mom::solver::PFFTConfig&>(),
             py::arg("mesh"), py::arg("green"), py::arg("config") = mom::solver::PFFTConfig())
        .def("multiply", &mom::solver::PFFTMatrixVector::multiply, py::arg("x"),
             "pFFT 矩阵向量乘法：y = Z·x")
        .def("size", &mom::solver::PFFTMatrixVector::size, "返回基函数数");

    m.def("solve_gmres", &mom::solver::solve_gmres,
          py::arg("A"), py::arg("b"), py::arg("tol") = 1e-6,
          py::arg("max_iter") = 1000, py::arg("restart") = 50,
          "GMRES 迭代求解器（使用 pFFT 矩阵向量乘法）");

    m.def("assemble_rwg_pfft", [](const mom::mesh::TriMesh& mesh,
                                   const mom::green::dyadic::SpatialDyadic& green,
                                   int gauss_order, size_t n_lookup) {
        auto blocks = mom::mom::assemble_rwg_fast(mesh, green, gauss_order, n_lookup);
        py::dict result;
        result["ZA"] = blocks.ZA;
        result["ZPhi"] = blocks.ZPhi;
        return result;
    }, py::arg("mesh"), py::arg("green"),
       py::arg("gauss_order") = 5, py::arg("n_lookup") = 2000,
       "RWG 装配（格林函数查找表加速版）");
}
