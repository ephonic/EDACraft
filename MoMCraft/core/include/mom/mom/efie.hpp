#pragma once

#include "mom/common/types.hpp"
#include "mom/mesh/mesh.hpp"

#include <complex>
#include <functional>
#include <vector>

namespace mom::mom {

enum class Formulation { EFIE, AEFIE };

using GreenFn = Complex (*)(double* r_obs, double* r_src, void* ctx);

struct MPIEBlocks {
    std::vector<Complex> ZA;
    std::vector<Complex> ZPhi;
};

MPIEBlocks assemble_mpie(
    const mesh::RectMesh& mesh,
    const std::vector<mesh::RooftopBasis>& bases,
    GreenFn gA_direct,
    GreenFn gA_image,
    GreenFn gPhi_direct,
    GreenFn gPhi_image,
    void* gctx,
    int gauss_order
);

std::vector<Complex> build_impedance(
    const MPIEBlocks& blk,
    Real omega,
    Real eps_eff
);

using SpatialGreenFn = std::function<Complex(Real rho)>;

MPIEBlocks assemble_mpie_single(
    const mesh::RectMesh& mesh,
    const std::vector<mesh::RooftopBasis>& bases,
    SpatialGreenFn gA,
    SpatialGreenFn gPhi,
    int gauss_order,
    Real W
);

struct AEFIESystem {
    std::vector<Complex> A;
    std::vector<Complex> b;
    Index nb;
};

AEFIESystem build_aefie(
    const MPIEBlocks& blk,
    Real omega,
    Real eps_r,
    Real dx,
    Index nb
);

std::vector<Complex> solve_aefie_zport(
    const MPIEBlocks& blk,
    Real omega,
    Real eps_r,
    Real dx,
    Index nb,
    Index port_in,
    Index port_out
);

std::vector<Complex> aefie_to_zport(
    const AEFIESystem& sys,
    const std::vector<Complex>& x,
    Index nb,
    Real z0_ref
);

} // namespace mom::mom
