// =====================================================================
// mom/tl_extract.hpp - transmission-line parameter extraction helpers
// =====================================================================
#pragma once

#include "mom/common/types.hpp"

#include <complex>
#include <vector>

namespace mom {

struct TLParams {
    Complex z_oc;
    Complex z_sc;
    Complex z0;
    Real beta_l;
};

// Extract TL parameters from a full MoM impedance matrix by first reducing the
// system to the true 2-port terminal Z-matrix.
TLParams extract_tl_open_short(const std::vector<Complex>& Z, Index nb,
                               Index port_in, Index port_out);

// Estimate the modal characteristic impedance and electrical length from the
// current distribution of a roughly uniform line.
TLParams extract_tl_eigenmode(const std::vector<Complex>& Z, Index nb, Real dx);

// Export the reduced 2-port Z-matrix in row-major order:
// [Z00, Z01, Z10, Z11].
std::vector<Complex> schur_2port_export(const std::vector<Complex>& Z, Index nb,
                                        Index port_in, Index port_out);

// Export the reduced n-port Z-matrix in row-major order for the selected port
// basis functions.
std::vector<Complex> schur_nport_export(const std::vector<Complex>& Z, Index nb,
                                        const std::vector<Index>& ports);

// Convert a row-major n-port Z-matrix to S-parameters with uniform reference
// impedance z0.
std::vector<Complex> zport_n_to_sparam(const std::vector<Complex>& Zport, Index np, Real z0);

// Reduce a full-basis impedance matrix to an n-port Z-matrix for multi-edge
// port groups. Each port is represented by a signed basis-function set, and the
// reduction is performed as Z_port = (G^T Z^{-1} G)^{-1}.
std::vector<Complex> schur_nport_multiedge_export(
    const std::vector<Complex>& Z, Index nb,
    const std::vector<std::vector<Index>>& edge_sets,
    const std::vector<std::vector<Real>>& signs);

// Dual multi-edge reduction with separate response/test and excitation/source
// modal vectors:
//   Y_port = H^T Z^{-1} G,  Z_port = Y_port^{-1}
// where each column of H/G is assembled from a signed basis-function group.
std::vector<Complex> schur_nport_multiedge_dual_export(
    const std::vector<Complex>& Z, Index nb,
    const std::vector<std::vector<Index>>& test_edge_sets,
    const std::vector<std::vector<Real>>& test_signs,
    const std::vector<std::vector<Index>>& source_edge_sets,
    const std::vector<std::vector<Real>>& source_signs);

} // namespace mom
