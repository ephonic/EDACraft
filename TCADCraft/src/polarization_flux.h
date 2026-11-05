#pragma once

#include "poisson_solver.h"

namespace tcad {

// Two equal half layers in series: D=eps*E+P gives
// P_face=eps_edge*(P_i/eps_i+P_j/eps_j)/2. Masked-out P is zero.
inline real_t polarization_face(const std::vector<char>& mask,
                                const std::vector<real_t>& polarization,
                                const std::vector<real_t>& eps,
                                size_t idx, size_t nbr, int axis,
                                real_t edge_eps) {
    if (edge_eps == TCAD_CONST(0.0) || eps[idx] <= TCAD_CONST(0.0) || eps[nbr] <= TCAD_CONST(0.0))
        return TCAD_CONST(0.0);
    const real_t left = mask[idx] ? polarization[3*idx+axis] / eps[idx] : TCAD_CONST(0.0);
    const real_t right = mask[nbr] ? polarization[3*nbr+axis] / eps[nbr] : TCAD_CONST(0.0);
    return edge_eps * (left + right) / TCAD_CONST(2.0);
}

// Divergence at every node, including the dielectric next to FE. Internal
// faces cancel in the volume integral. Omit exterior electric AND P fluxes
// for natural zero-normal-D boundaries; electrodes replace the row by phi BC.
// The callback must use the same edge epsilon as the electric Laplacian.
template <typename EdgePermittivity>
real_t polarization_divergence(const Grid3D& grid,
                              const std::vector<char>& mask,
                              const std::vector<real_t>& polarization,
                              const std::vector<real_t>& eps,
                              size_t i, size_t j, size_t k,
                              EdgePermittivity edge_eps) {
    if (mask.size() != grid.npts() || polarization.size() != 3*grid.npts())
        return TCAD_CONST(0.0);
    const size_t idx = grid.index(i, j, k);
    real_t divergence = TCAD_CONST(0.0);
    auto face = [&](size_t nbr, int axis, bool upper, real_t cell) {
        const real_t flux = polarization_face(mask, polarization, eps,
            idx, nbr, axis, edge_eps(axis, upper, idx, nbr));
        divergence += (upper ? flux : -flux) / cell;
    };
    if (i+1 < grid.nx) face(idx+1, 0, true, grid.dx_cell(i));
    if (i > 0) face(idx-1, 0, false, grid.dx_cell(i));
    if (j+1 < grid.ny) face(idx+grid.nx, 1, true, grid.dy_cell(j));
    if (j > 0) face(idx-grid.nx, 1, false, grid.dy_cell(j));
    if (k+1 < grid.nz) face(idx+grid.nx*grid.ny, 2, true, grid.dz_cell(k));
    if (k > 0) face(idx-grid.nx*grid.ny, 2, false, grid.dz_cell(k));
    return divergence;
}

} // namespace tcad
