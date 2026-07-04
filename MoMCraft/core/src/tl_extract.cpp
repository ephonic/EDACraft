// =====================================================================
// mom/tl_extract.cpp —— 开路-短路法传输线参数提取
//
// 正确的 2 端口阻抗矩阵通过【电流激励 + Schur 降阶】得到（修复旧实现的
// 数学退化：旧式 Vport(q,p)=V_q/I_p 中 V_q=(Z·I)[q]=δ(q,p) → Zport 恒对角）。
// =====================================================================
#include "mom/tl_extract.hpp"
#include "mom/solver/dense.hpp"

#ifdef MOM_USE_EIGEN
#include <Eigen/Dense>
#include <Eigen/LU>
#endif

#include <cmath>
#include <stdexcept>
#include <vector>

namespace mom {

// —— 2 端口阻抗矩阵：电流激励 + Schur 降阶 ——
//
// MPIE 系统 Z·I = V（I 为基函数电流，V 为外加切向场）。
// 物理边界：内部 PEC 导体上外加场为零 → V_int = 0；端口注入已知电流 I_port。
//
// 分块：[端口 (2) | 内部 (nb-2)]
//   V_port = Z_pp·I_port + Z_pi·I_int
//   0      = Z_ip·I_port + Z_ii·I_int   →  I_int = -Z_ii⁻¹·Z_ip·I_port
// 代入得 V_port = (Z_pp - Z_pi·Z_ii⁻¹·Z_ip)·I_port
//   2 端口阻抗矩阵 Zport_2x2 = Z_pp - Z_pi·Z_ii⁻¹·Z_ip   （Schur 补）
//
// 这个 2×2 矩阵才是真正的传输线 2 端口阻抗矩阵：
//   Z_oc = Zport2[0,0]                          （远端开路：I_out=0）
//   Z_sc = Zport2[0,0] - Zport2[0,1]²/Zport2[1,1]（远端短路：V_out=0）
//   Z0   = sqrt(Z_oc·Z_sc)
static bool schur_2port(const std::vector<Complex>& Z, Index nb,
                        Index p0, Index p1,
                        Complex Zport2[4]) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    const Index ni = nb - 2;
    if (ni <= 0) {
        // 退化为纯 2×2：直接取 Z 子矩阵
        Zport2[0] = Z[p0*nb+p0]; Zport2[1] = Z[p0*nb+p1];
        Zport2[2] = Z[p1*nb+p0]; Zport2[3] = Z[p1*nb+p1];
        return true;
    }
    // 建立内部索引列表（排除两个端口）
    std::vector<Index> int_idx; int_idx.reserve(ni);
    for (Index j = 0; j < nb; ++j)
        if (j != p0 && j != p1) int_idx.push_back(j);
    // Z_ii (ni×ni)
    M Zii(ni, ni);
    for (Index a = 0; a < ni; ++a)
        for (Index b = 0; b < ni; ++b)
            Zii(a, b) = Z[int_idx[a]*nb + int_idx[b]];
    // Z_pi (2×ni): 行=端口[p0,p1]，列=内部
    M Zpi(2, ni);
    Index port_rows[2] = {p0, p1};
    for (Index q = 0; q < 2; ++q)
        for (Index b = 0; b < ni; ++b)
            Zpi(q, b) = Z[port_rows[q]*nb + int_idx[b]];
    // Z_ip (ni×2) = Z_pi 转置的 Hermitian（阻抗矩阵对称：Z[i,j]=Z[j,i]）
    M Zip = Zpi.transpose();
    // Z_pp (2×2)
    M Zpp(2, 2);
    for (Index q = 0; q < 2; ++q)
        for (Index r = 0; r < 2; ++r)
            Zpp(q, r) = Z[port_rows[q]*nb + port_rows[r]];
    // Schur 补：Zpp - Zpi·Zii⁻¹·Zip。用 LU 解（比 .inverse() 稳健）。
    // Zpi·Zii⁻¹·Zip = Zpi·(Zii⁻¹·Zip)，令 X = Zii⁻¹·Zip（解 Zii·X=Zip），则 Schur=Zpp-Zpi·X。
    M X = Zii.partialPivLu().solve(Zip);
    M Zport2_e = Zpp - Zpi * X;
    for (Index q = 0; q < 2; ++q)
        for (Index r = 0; r < 2; ++r) {
            Complex v = Zport2_e(q, r);
            // NaN/inf 防护：若 LU 失败，退化为只用 Zpp（忽略内部耦合）
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                v = Zpp(q, r);
            Zport2[q*2 + r] = v;
        }
    return true;
#else
    (void)Z; (void)nb; (void)p0; (void)p1;
    for (int i = 0; i < 4; ++i) Zport2[i] = Complex(0,0);
    return false;
#endif
}

TLParams extract_tl_open_short(const std::vector<Complex>& Z, Index nb,
                               Index port_in, Index port_out) {
    if (nb <= 2) throw std::runtime_error("extract_tl_open_short: nb<=2");

    Complex Zport2[4];
    if (!schur_2port(Z, nb, port_in, port_out, Zport2))
        throw std::runtime_error("extract_tl_open_short 需要 Eigen");

    // 2 端口阻抗矩阵（行主序）：Zport2[q*2+r]，q=观测端口、r=激励端口
    //   开路（I_out=0）：Z_oc = Zport2[0,0]
    //   短路（V_out=0）：Z_sc = Zport2[0,0] - Zport2[0,1]²/Zport2[1,1]
    const Complex z_oc = Zport2[0];  // (in,in)
    const Complex z_sc = (std::abs(Zport2[3]) > 0.0)
        ? Zport2[0] - Zport2[1] * Zport2[1] / Zport2[3]
        : Zport2[0];

    // 无损传输线：Z0 = sqrt(Z_oc·Z_sc)；βl = atan(sqrt(Z_sc/Z_oc))
    TLParams r;
    r.z_oc = z_oc;
    r.z_sc = z_sc;
    r.z0 = std::sqrt(z_oc * z_sc);
    const Complex ratio = (std::abs(z_oc) > 0.0) ? z_sc / z_oc : Complex(0,0);
    r.beta_l = std::real(std::atan(std::sqrt(ratio)));
    return r;
}

std::vector<Complex> schur_2port_export(const std::vector<Complex>& Z, Index nb,
                                        Index port_in, Index port_out) {
    Complex Zport2[4];
    if (!schur_2port(Z, nb, port_in, port_out, Zport2))
        throw std::runtime_error("schur_2port_export 需要 Eigen");
    return {Zport2[0], Zport2[1], Zport2[2], Zport2[3]};
}

std::vector<Complex> schur_nport_export(const std::vector<Complex>& Z, Index nb,
                                        const std::vector<Index>& ports) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    const Index np = Index(ports.size());
    if (np == 0) return {};
    if (np == nb) {
        // 全端口：直接返回 Z
        return Z;
    }
    // 内部索引（排除端口）
    std::vector<Index> int_idx;
    for (Index j = 0; j < nb; ++j) {
        bool is_port = false;
        for (Index p : ports) if (p == j) { is_port = true; break; }
        if (!is_port) int_idx.push_back(j);
    }
    const Index ni = Index(int_idx.size());
    if (ni == 0) {
        // 无内部自由度：返回 Z 的端口子矩阵
        std::vector<Complex> out(np * np);
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                out[q*np + r] = Z[ports[q]*nb + ports[r]];
        return out;
    }
    M Zii(ni, ni);
    for (Index a = 0; a < ni; ++a)
        for (Index b = 0; b < ni; ++b)
            Zii(a, b) = Z[int_idx[a]*nb + int_idx[b]];
    M Zpi(np, ni), Zip(ni, np), Zpp(np, np);
    for (Index q = 0; q < np; ++q) {
        for (Index b = 0; b < ni; ++b)
            Zpi(q, b) = Z[ports[q]*nb + int_idx[b]];
        for (Index r = 0; r < np; ++r)
            Zpp(q, r) = Z[ports[q]*nb + ports[r]];
    }
    for (Index a = 0; a < ni; ++a)
        for (Index q = 0; q < np; ++q)
            Zip(a, q) = Z[int_idx[a]*nb + ports[q]];
    // Schur 补：Zpp - Zpi·Zii⁻¹·Zip（用 LU 解）
    M X = Zii.partialPivLu().solve(Zip);
    M Zport = Zpp - Zpi * X;
    // NaN 防护
    std::vector<Complex> out(np * np);
    for (Index q = 0; q < np; ++q)
        for (Index r = 0; r < np; ++r) {
            Complex v = Zport(q, r);
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                v = Zpp(q, r);
            out[q*np + r] = v;
        }
    return out;
#else
    (void)Z; (void)nb; (void)ports;
    throw std::runtime_error("schur_nport_export 需要 Eigen");
#endif
}

std::vector<Complex> zport_n_to_sparam(const std::vector<Complex>& Zport, Index np, Real z0) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    if (np == 0) return {};
    if (np == 1) {
        Complex s = (Zport[0] - z0) / (Zport[0] + z0);
        return {s};
    }
    M A = Eigen::Map<const M>(Zport.data(), np, np);
    M Zmat = A;
    M I = M::Identity(np, np);
    M Am = A - z0 * I;       // Z - z0·I
    M Bp = A + z0 * I;       // Z + z0·I
    M S = Am * Bp.inverse();
    std::vector<Complex> out(np * np);
    for (Index q = 0; q < np; ++q)
        for (Index r = 0; r < np; ++r)
            out[q*np + r] = S(q, r);
    return out;
#else
    (void)Zport; (void)np; (void)z0;
    throw std::runtime_error("zport_n_to_sparam 需要 Eigen");
#endif
}

// —— 本征模法：从电流分布提取 β 与 Z0，避免 open-short 的电抗病态 ——
//
// 对均匀传输线，在中心节点注入单位电流源（delta-gap V=1），解 Z·I=V 得
// 电流分布 I(x)。沿线（远离端口反射的中间区）电流为传播+反射波叠加：
//   I_n = I+·e^{-jβ·n·dx} + I-·e^{+jβ·n·dx}
// 相邻样点比 r_n = I_{n+1}/I_n 满足：取中间段多个 r_n 平均得 e^{-jβ·dx}。
// 电压 V_n = Σ_j Z[n,j]·I_j，沿线模态阻抗 Z0 = V_n/I_n（中间段平均）。
TLParams extract_tl_eigenmode(const std::vector<Complex>& Z, Index nb, Real dx) {
    TLParams r;
    r.z_oc = Complex(0,0); r.z_sc = Complex(0,0);
    r.z0 = Complex(0,0); r.beta_l = 0.0;
    if (nb < 8) return r;
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    using Vc = Eigen::VectorXcd;
    M A(nb, nb);
    for (Index i = 0; i < nb; ++i)
        for (Index j = 0; j < nb; ++j)
            A(i, j) = Z[i * nb + j];
    // 中心节点注入 V=1
    Vc Vsrc = Vc::Zero(nb);
    const Index ic = nb / 2;
    Vsrc(ic) = Complex(1.0, 0.0);
    Vc I = A.partialPivLu().solve(Vsrc);

    // —— 提取 β：相邻电流比 r_n = I_{n+1}/I_n 的对数平均 ——
    // 中间段（避开端口反射，取 [nb/4, 3nb/4]）。
    const Index i0 = nb / 4, i1 = (3 * nb) / 4;
    Complex sum_log_r(0.0, 0.0);
    int cnt = 0;
    for (Index n = i0; n + 1 <= i1; ++n) {
        Complex r_n = I(n + 1) / I(n);
        if (std::abs(r_n) > 1e-30) {
            sum_log_r += std::log(r_n);
            ++cnt;
        }
    }
    if (cnt == 0) return r;
    Complex log_r_mean = sum_log_r / Complex(double(cnt), 0.0);
    // r = e^{-jβ·dx}（约定 e^{-jβx} 传播）；γ = -log(r)/dx = jβ（无损）
    Complex gamma_per_dx = -log_r_mean;          // γ·dx
    Real beta = std::real(gamma_per_dx / Complex(dx, 0.0));
    if (beta < 0) beta = -beta;
    r.beta_l = beta * (nb - 1) * dx;             // β·L

    // —— 提取 Z0：中间段模态阻抗 V_n/I_n 平均 ——
    // V_n = (Z·I)_n（沿线电压）。在传播区 V_n/I_n → Z0。
    Vc Vline = A * I;
    Complex sum_z0(0.0, 0.0);
    int cz = 0;
    for (Index n = i0; n <= i1; ++n) {
        if (std::abs(I(n)) > 1e-30) {
            sum_z0 += Vline(n) / I(n);
            ++cz;
        }
    }
    if (cz > 0) r.z0 = sum_z0 / Complex(double(cz), 0.0);
#else
    (void)dx;
#endif
    return r;
}

} // namespace mom
