// =====================================================================
// mom/solver/dense.cpp - dense direct solve + reduced port extraction
// =====================================================================
#include "mom/solver/dense.hpp"

#ifdef MOM_USE_EIGEN
#include <Eigen/Dense>
#include <Eigen/LU>
#endif

#include <cmath>
#include <stdexcept>
#include <vector>

namespace mom::solver {

std::vector<Complex> solve_dense(const std::vector<Complex>& Z,
                                 const std::vector<Complex>& V,
                                 Index nb) {
    if (nb <= 0) return {};
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    using Vc = Eigen::VectorXcd;

    M A(nb, nb);
    for (Index i = 0; i < nb; ++i)
        for (Index j = 0; j < nb; ++j)
            A(i, j) = Z[i * nb + j];

    Vc b(nb);
    for (Index i = 0; i < nb; ++i) b(i) = V[i];

    Vc x = A.partialPivLu().solve(b);
    std::vector<Complex> out(nb);
    for (Index i = 0; i < nb; ++i) out[i] = x(i);
    return out;
#else
    (void)Z;
    (void)V;
    throw std::runtime_error("solve_dense requires Eigen (MOM_USE_EIGEN)");
#endif
}

std::vector<Complex> port_impedance_matrix(const std::vector<Index>& port_basis,
                                           const std::vector<Complex>& Z,
                                           Index nb) {
    const Index np = Index(port_basis.size());
    std::vector<Complex> Zport(np * np, Complex(0.0, 0.0));
    if (np == 0 || nb <= 0) return Zport;

#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;

    std::vector<unsigned char> is_port(Size(nb), 0);
    for (Index p = 0; p < np; ++p) {
        const Index bi = port_basis[p];
        if (bi < 0 || bi >= nb)
            throw std::runtime_error("port_impedance_matrix: port basis index out of range");
        if (is_port[Size(bi)] != 0)
            throw std::runtime_error("port_impedance_matrix: duplicate port basis index");
        is_port[Size(bi)] = 1;
    }

    std::vector<Index> int_idx;
    int_idx.reserve(Size(nb - np));
    for (Index j = 0; j < nb; ++j) {
        if (!is_port[Size(j)]) int_idx.push_back(j);
    }

    const Index ni = Index(int_idx.size());
    if (ni == 0) {
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                Zport[q * np + r] = Z[port_basis[q] * nb + port_basis[r]];
        return Zport;
    }

    M Zii(ni, ni);
    for (Index a = 0; a < ni; ++a)
        for (Index b = 0; b < ni; ++b)
            Zii(a, b) = Z[int_idx[a] * nb + int_idx[b]];

    M Zpi(np, ni), Zip(ni, np), Zpp(np, np);
    for (Index q = 0; q < np; ++q) {
        for (Index b = 0; b < ni; ++b)
            Zpi(q, b) = Z[port_basis[q] * nb + int_idx[b]];
        for (Index r = 0; r < np; ++r)
            Zpp(q, r) = Z[port_basis[q] * nb + port_basis[r]];
    }
    for (Index a = 0; a < ni; ++a)
        for (Index q = 0; q < np; ++q)
            Zip(a, q) = Z[int_idx[a] * nb + port_basis[q]];

    M X = Zii.partialPivLu().solve(Zip);
    M Zport_e = Zpp - Zpi * X;
    for (Index q = 0; q < np; ++q) {
        for (Index r = 0; r < np; ++r) {
            Complex v = Zport_e(q, r);
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                v = Zpp(q, r);
            Zport[q * np + r] = v;
        }
    }
    return Zport;
#else
    (void)port_basis;
    (void)Z;
    (void)nb;
    throw std::runtime_error("port_impedance_matrix requires Eigen (MOM_USE_EIGEN)");
#endif
}

std::vector<Complex> zport_to_sparam(const std::vector<Complex>& Zport,
                                     Real z0, Index nport) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    const Complex z0c(z0, 0.0);
    if (nport <= 0) return {};

    M Zp(nport, nport);
    for (Index i = 0; i < nport; ++i)
        for (Index j = 0; j < nport; ++j)
            Zp(i, j) = Zport[i * nport + j];

    M I = M::Identity(nport, nport);
    M A = (Zp - z0c * M::Identity(nport, nport));
    M B = (Zp + z0c * M::Identity(nport, nport));
    M S = A * B.partialPivLu().solve(I);

    std::vector<Complex> out(nport * nport);
    for (Index i = 0; i < nport; ++i)
        for (Index j = 0; j < nport; ++j)
            out[i * nport + j] = S(i, j);
    return out;
#else
    (void)Zport;
    (void)z0;
    (void)nport;
    throw std::runtime_error("zport_to_sparam requires Eigen (MOM_USE_EIGEN)");
#endif
}

} // namespace mom::solver
