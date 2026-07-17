// =====================================================================
// mom/tl_extract.cpp - transmission-line parameter extraction helpers
// =====================================================================
#include "mom/tl_extract.hpp"

#ifdef MOM_USE_EIGEN
#include <Eigen/Dense>
#include <Eigen/LU>
#endif

#include <cmath>
#include <stdexcept>
#include <vector>

namespace mom {

namespace {

#ifdef MOM_USE_EIGEN
static Eigen::MatrixXcd build_port_projection_matrix(
    Index nb,
    const std::vector<std::vector<Index>>& edge_sets,
    const std::vector<std::vector<Real>>& signs) {
    using M = Eigen::MatrixXcd;

    const Index np = Index(edge_sets.size());
    M P = M::Zero(nb, np);
    for (Index p = 0; p < np; ++p) {
        const auto& set_p = edge_sets[p];
        if (set_p.empty()) continue;
        const std::vector<Real>& sp = (p < Index(signs.size()) && !signs[p].empty())
            ? signs[p] : std::vector<Real>(set_p.size(), Real(1.0));
        if (sp.size() != set_p.size())
            throw std::runtime_error("port signs size mismatch");
        for (Size k = 0; k < set_p.size(); ++k) {
            const Index bi = set_p[k];
            if (bi < 0 || bi >= nb)
                throw std::runtime_error("port basis index out of range");
            P(bi, p) += Complex(sp[k], 0.0);
        }
    }
    return P;
}
#endif

static bool schur_2port(const std::vector<Complex>& Z, Index nb,
                        Index p0, Index p1,
                        Complex Zport2[4]) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;

    if (nb <= 0)
        throw std::runtime_error("schur_2port: nb must be positive");
    if (p0 < 0 || p0 >= nb || p1 < 0 || p1 >= nb || p0 == p1)
        throw std::runtime_error("schur_2port: invalid port basis indices");

    const Index ni = nb - 2;
    if (ni <= 0) {
        Zport2[0] = Z[p0 * nb + p0];
        Zport2[1] = Z[p0 * nb + p1];
        Zport2[2] = Z[p1 * nb + p0];
        Zport2[3] = Z[p1 * nb + p1];
        return true;
    }

    std::vector<Index> int_idx;
    int_idx.reserve(Size(ni));
    for (Index j = 0; j < nb; ++j) {
        if (j != p0 && j != p1) int_idx.push_back(j);
    }

    M Zii(ni, ni);
    for (Index a = 0; a < ni; ++a)
        for (Index b = 0; b < ni; ++b)
            Zii(a, b) = Z[int_idx[a] * nb + int_idx[b]];

    Index port_rows[2] = {p0, p1};
    M Zpi(2, ni), Zip(ni, 2), Zpp(2, 2);
    for (Index q = 0; q < 2; ++q) {
        for (Index b = 0; b < ni; ++b)
            Zpi(q, b) = Z[port_rows[q] * nb + int_idx[b]];
        for (Index r = 0; r < 2; ++r)
            Zpp(q, r) = Z[port_rows[q] * nb + port_rows[r]];
    }
    for (Index a = 0; a < ni; ++a)
        for (Index q = 0; q < 2; ++q)
            Zip(a, q) = Z[int_idx[a] * nb + port_rows[q]];

    M X = Zii.partialPivLu().solve(Zip);
    M Zport2_e = Zpp - Zpi * X;
    for (Index q = 0; q < 2; ++q) {
        for (Index r = 0; r < 2; ++r) {
            Complex v = Zport2_e(q, r);
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                v = Zpp(q, r);
            Zport2[q * 2 + r] = v;
        }
    }
    return true;
#else
    (void)Z;
    (void)nb;
    (void)p0;
    (void)p1;
    for (int i = 0; i < 4; ++i) Zport2[i] = Complex(0.0, 0.0);
    return false;
#endif
}

} // namespace

TLParams extract_tl_open_short(const std::vector<Complex>& Z, Index nb,
                               Index port_in, Index port_out) {
    if (nb <= 2) throw std::runtime_error("extract_tl_open_short: nb<=2");

    Complex Zport2[4];
    if (!schur_2port(Z, nb, port_in, port_out, Zport2))
        throw std::runtime_error("extract_tl_open_short requires Eigen");

    const Complex z_oc = Zport2[0];
    const Complex z_sc = (std::abs(Zport2[3]) > 0.0)
        ? Zport2[0] - Zport2[1] * Zport2[2] / Zport2[3]
        : Zport2[0];

    TLParams r;
    r.z_oc = z_oc;
    r.z_sc = z_sc;
    r.z0 = std::sqrt(z_oc * z_sc);
    const Complex ratio = (std::abs(z_oc) > 0.0) ? z_sc / z_oc : Complex(0.0, 0.0);
    r.beta_l = std::real(std::atan(std::sqrt(ratio)));
    return r;
}

std::vector<Complex> schur_2port_export(const std::vector<Complex>& Z, Index nb,
                                        Index port_in, Index port_out) {
    Complex Zport2[4];
    if (!schur_2port(Z, nb, port_in, port_out, Zport2))
        throw std::runtime_error("schur_2port_export requires Eigen");
    return {Zport2[0], Zport2[1], Zport2[2], Zport2[3]};
}

std::vector<Complex> schur_nport_export(const std::vector<Complex>& Z, Index nb,
                                        const std::vector<Index>& ports) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;

    const Index np = Index(ports.size());
    if (np == 0) return {};
    if (nb <= 0)
        throw std::runtime_error("schur_nport_export: nb must be positive");

    std::vector<unsigned char> is_port(Size(nb), 0);
    for (Index p = 0; p < np; ++p) {
        const Index bi = ports[p];
        if (bi < 0 || bi >= nb)
            throw std::runtime_error("schur_nport_export: port basis index out of range");
        if (is_port[Size(bi)] != 0)
            throw std::runtime_error("schur_nport_export: duplicate port basis index");
        is_port[Size(bi)] = 1;
    }

    std::vector<Index> int_idx;
    int_idx.reserve(Size(nb - np));
    for (Index j = 0; j < nb; ++j) {
        if (!is_port[Size(j)]) int_idx.push_back(j);
    }

    const Index ni = Index(int_idx.size());
    std::vector<Complex> out(np * np, Complex(0.0, 0.0));
    if (ni == 0) {
        for (Index q = 0; q < np; ++q)
            for (Index r = 0; r < np; ++r)
                out[q * np + r] = Z[ports[q] * nb + ports[r]];
        return out;
    }

    M Zii(ni, ni);
    for (Index a = 0; a < ni; ++a)
        for (Index b = 0; b < ni; ++b)
            Zii(a, b) = Z[int_idx[a] * nb + int_idx[b]];

    M Zpi(np, ni), Zip(ni, np), Zpp(np, np);
    for (Index q = 0; q < np; ++q) {
        for (Index b = 0; b < ni; ++b)
            Zpi(q, b) = Z[ports[q] * nb + int_idx[b]];
        for (Index r = 0; r < np; ++r)
            Zpp(q, r) = Z[ports[q] * nb + ports[r]];
    }
    for (Index a = 0; a < ni; ++a)
        for (Index q = 0; q < np; ++q)
            Zip(a, q) = Z[int_idx[a] * nb + ports[q]];

    M X = Zii.partialPivLu().solve(Zip);
    M Zport = Zpp - Zpi * X;
    for (Index q = 0; q < np; ++q) {
        for (Index r = 0; r < np; ++r) {
            Complex v = Zport(q, r);
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                v = Zpp(q, r);
            out[q * np + r] = v;
        }
    }
    return out;
#else
    (void)Z;
    (void)nb;
    (void)ports;
    throw std::runtime_error("schur_nport_export requires Eigen");
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

    M A(np, np);
    for (Index q = 0; q < np; ++q)
        for (Index r = 0; r < np; ++r)
            A(q, r) = Zport[q * np + r];

    M I = M::Identity(np, np);
    M Am = A - z0 * I;
    M Bp = A + z0 * I;
    M S = Am * Bp.partialPivLu().solve(I);

    std::vector<Complex> out(np * np);
    for (Index q = 0; q < np; ++q)
        for (Index r = 0; r < np; ++r)
            out[q * np + r] = S(q, r);
    return out;
#else
    (void)Zport;
    (void)np;
    (void)z0;
    throw std::runtime_error("zport_n_to_sparam requires Eigen");
#endif
}

std::vector<Complex> schur_nport_multiedge_export(
    const std::vector<Complex>& Z, Index nb,
    const std::vector<std::vector<Index>>& edge_sets,
    const std::vector<std::vector<Real>>& signs) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;

    const Index np = Index(edge_sets.size());
    std::vector<Complex> out(np * np, Complex(0.0, 0.0));
    if (np == 0 || nb == 0) return out;

    M A(nb, nb);
    for (Index i = 0; i < nb; ++i)
        for (Index j = 0; j < nb; ++j)
            A(i, j) = Z[i * nb + j];

    M G = build_port_projection_matrix(nb, edge_sets, signs);

    auto lu = A.partialPivLu();
    M X = lu.solve(G);
    M Yport = G.transpose() * X;
    M Zport = Yport.partialPivLu().solve(M::Identity(np, np));

    for (Index q = 0; q < np; ++q) {
        for (Index p = 0; p < np; ++p) {
            Complex v = Zport(q, p);
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                throw std::runtime_error("multiedge port reduction produced NaN/Inf");
            out[q * np + p] = v;
        }
    }
    return out;
#else
    (void)Z;
    (void)nb;
    (void)edge_sets;
    (void)signs;
    throw std::runtime_error("schur_nport_multiedge_export requires Eigen");
#endif
}

std::vector<Complex> schur_nport_multiedge_dual_export(
    const std::vector<Complex>& Z, Index nb,
    const std::vector<std::vector<Index>>& test_edge_sets,
    const std::vector<std::vector<Real>>& test_signs,
    const std::vector<std::vector<Index>>& source_edge_sets,
    const std::vector<std::vector<Real>>& source_signs) {
#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;

    const Index np = Index(test_edge_sets.size());
    if (np == 0 || nb == 0) return {};
    if (Index(source_edge_sets.size()) != np)
        throw std::runtime_error("dual multiedge port count mismatch");

    std::vector<Complex> out(np * np, Complex(0.0, 0.0));

    M A(nb, nb);
    for (Index i = 0; i < nb; ++i)
        for (Index j = 0; j < nb; ++j)
            A(i, j) = Z[i * nb + j];

    M H = build_port_projection_matrix(nb, test_edge_sets, test_signs);
    M G = build_port_projection_matrix(nb, source_edge_sets, source_signs);

    auto lu = A.partialPivLu();
    M X = lu.solve(G);
    M Yport = H.transpose() * X;
    M Zport = Yport.partialPivLu().solve(M::Identity(np, np));

    for (Index q = 0; q < np; ++q) {
        for (Index p = 0; p < np; ++p) {
            Complex v = Zport(q, p);
            if (!std::isfinite(v.real()) || !std::isfinite(v.imag()))
                throw std::runtime_error("dual multiedge port reduction produced NaN/Inf");
            out[q * np + p] = v;
        }
    }
    return out;
#else
    (void)Z;
    (void)nb;
    (void)test_edge_sets;
    (void)test_signs;
    (void)source_edge_sets;
    (void)source_signs;
    throw std::runtime_error("schur_nport_multiedge_dual_export requires Eigen");
#endif
}

TLParams extract_tl_eigenmode(const std::vector<Complex>& Z, Index nb, Real dx) {
    TLParams r;
    r.z_oc = Complex(0.0, 0.0);
    r.z_sc = Complex(0.0, 0.0);
    r.z0 = Complex(0.0, 0.0);
    r.beta_l = 0.0;
    if (nb < 8) return r;

#ifdef MOM_USE_EIGEN
    using M = Eigen::MatrixXcd;
    using Vc = Eigen::VectorXcd;

    M A(nb, nb);
    for (Index i = 0; i < nb; ++i)
        for (Index j = 0; j < nb; ++j)
            A(i, j) = Z[i * nb + j];

    Vc Vsrc = Vc::Zero(nb);
    const Index ic = nb / 2;
    Vsrc(ic) = Complex(1.0, 0.0);
    Vc I = A.partialPivLu().solve(Vsrc);

    const Index i0 = nb / 4;
    const Index i1 = (3 * nb) / 4;
    Complex sum_log_r(0.0, 0.0);
    int cnt = 0;
    for (Index n = i0; n + 1 <= i1; ++n) {
        if (std::abs(I(n)) <= 1e-30) continue;
        Complex r_n = I(n + 1) / I(n);
        if (std::abs(r_n) > 1e-30) {
            sum_log_r += std::log(r_n);
            ++cnt;
        }
    }
    if (cnt == 0) return r;

    Complex log_r_mean = sum_log_r / Complex(double(cnt), 0.0);
    Complex gamma_per_dx = -log_r_mean;
    Real beta = std::real(gamma_per_dx / Complex(dx, 0.0));
    if (beta < 0) beta = -beta;
    r.beta_l = beta * (nb - 1) * dx;

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
