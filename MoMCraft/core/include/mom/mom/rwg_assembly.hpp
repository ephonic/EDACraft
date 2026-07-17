#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/mesh/trimesh.hpp"
#include "mom/green/dyadic.hpp"
#include "mom/green/spectral.hpp"
#include "mom/mom/efie.hpp"

#include <functional>
#include <vector>

namespace mom::mom {

struct RwgMPIEBlocks {
    std::vector<Complex> ZA;
    std::vector<Complex> ZPhi;
};

RwgMPIEBlocks assemble_rwg(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    int gauss_order = 5
);

RwgMPIEBlocks assemble_rwg_fast(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    int gauss_order = 5,
    Size n_lookup = 2000
);

RwgMPIEBlocks assemble_rwg_pfft(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    int gauss_order = 5,
    Size n_grid = 0
);

RwgMPIEBlocks assemble_rwg_layered(
    const mesh::TriMesh& mesh,
    const green::spectral::LayeredMedium& med,
    Real freq,
    int gauss_order = 5,
    Size n_lookup = 2000
);

inline MPIEBlocks to_mpie_blocks(const RwgMPIEBlocks& rwg) {
    MPIEBlocks blk;
    blk.ZA = rwg.ZA;
    blk.ZPhi = rwg.ZPhi;
    return blk;
}

std::vector<Complex> build_rwg_impedance(
    const RwgMPIEBlocks& rwg,
    const mesh::TriMesh& mesh,
    Real omega
);

std::vector<Complex> build_rwg_lambda(const mesh::TriMesh& mesh);

AEFIESystem build_rwg_aefie(
    const RwgMPIEBlocks& blk,
    Real omega,
    Real eps_r,
    const mesh::TriMesh& mesh
);

} // namespace mom::mom
