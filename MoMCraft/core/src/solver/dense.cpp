// =====================================================================
// mom/solver/dense.cpp —— 稠密直接求解 + 端口 + S 参数
// =====================================================================
#include "mom/solver/dense.hpp"

#ifdef MOM_USE_EIGEN
#include <Eigen/Dense>
#include <Eigen/LU>
#endif

#include <vector>
#include <stdexcept>

namespace mom::solver {

std::vector<Complex> solve_dense(const std::vector<Complex>& Z,
                                 const std::vector<Complex>& V,
                                 Index nb) {
    if (nb <= 0) return {};
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    using Vc = Eigen::VectorXcd;
    // Eigen 默认列主序；Z 给的是行主序，转成列主序矩阵。
    M A(nb, nb);
    for (Index i = 0; i < nb; ++i)
        for (Index j = 0; j < nb; ++j)
            A(i, j) = Z[Index(i) * nb + j];
    Vc b(nb);
    for (Index i = 0; i < nb; ++i) b(i) = V[i];
    Vc x = A.partialPivLu().solve(b);
    std::vector<Complex> out(nb);
    for (Index i = 0; i < nb; ++i) out[i] = x(i);
    return out;
#else
    (void)Z; (void)V;
    throw std::runtime_error("solve_dense 需要 Eigen（MOM_USE_EIGEN）");
#endif
}

std::vector<Complex> port_impedance_matrix(const std::vector<Index>& port_basis,
                                           const std::vector<Complex>& Z,
                                           Index nb) {
    const Index np = Index(port_basis.size());
    std::vector<Complex> Zport(np * np, Complex(0.0, 0.0));
    if (np == 0) return Zport;

    for (Index p = 0; p < np; ++p) {
        // delta-gap：在第 p 个端口基函数上施加 1V
        std::vector<Complex> V(nb, Complex(0.0, 0.0));
        V[port_basis[p]] = Complex(1.0, 0.0);
        const auto I = solve_dense(Z, V, nb);

        // 端口电压 = 激励电压（delta-gap 端口处）；电流 = 该基函数电流。
        // 端口 q 的电压由其基函数处的电位定义：这里取激励端口 V=1，
        // 其余端口电压 = Z 对应基函数的电压降 = Σ Z(q,j) I(j)。
        // 简化（参考面在基函数上）：V_q = δ_{q,p}（端口 q 开路电压）。
        for (Index q = 0; q < np; ++q) {
            // 端口 q 的电压 = 该端口基函数上的电压（=端口处电位差）
            // 用阻抗矩阵关系 V_q = Σ_j Z(q_basis, j) I_j
            Complex Vq(0.0, 0.0);
            for (Index j = 0; j < nb; ++j)
                Vq += Z[port_basis[q] * nb + j] * I[j];
            // 端口电流（流入）取端口 q 基函数的电流（带符号）
            const Complex Iq = I[port_basis[q]];
            // Z_port[p,q]：以 p 激励、q 观测；这里存为 Zport[q,p]=V_q/I_p
            // 约定行主序，行=观测 q，列=激励 p
            if (std::abs(I[port_basis[p]]) > 0.0)
                Zport[q * np + p] = Vq / I[port_basis[p]];
        }
    }
    return Zport;
}

std::vector<Complex> zport_to_sparam(const std::vector<Complex>& Zport,
                                     Real z0, Index nport) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    const Complex z0c(z0, 0.0);
    M Zp(nport, nport);
    for (Index i = 0; i < nport; ++i)
        for (Index j = 0; j < nport; ++j)
            Zp(i, j) = Zport[i * nport + j];
    // S = (Z - Z0 I)(Z + Z0 I)^{-1}
    M A = (Zp - z0c * M::Identity(nport, nport));
    M B = (Zp + z0c * M::Identity(nport, nport));
    M S = A * B.inverse();
    std::vector<Complex> out(nport * nport);
    for (Index i = 0; i < nport; ++i)
        for (Index j = 0; j < nport; ++j)
            out[i * nport + j] = S(i, j);
    return out;
#else
    (void)Zport; (void)z0; (void)nport;
    throw std::runtime_error("zport_to_sparam 需要 Eigen（MOM_USE_EIGEN）");
#endif
}

} // namespace mom::solver
