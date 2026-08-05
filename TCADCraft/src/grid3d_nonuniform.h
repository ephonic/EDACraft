// Non-uniform grid extension for Grid3D.
// Supports per-node position arrays for intelligent local refinement.
// When positions are set, edge/cell spacing is computed from them.
// When unset, falls back to uniform dx/dy/dz (backward compatible).

// === Changes to poisson_solver.h (Grid3D struct) ===
// Add after the existing members:

struct Grid3D {
    size_t nx, ny, nz;
    real_t dx, dy, dz;  // uniform spacing (fallback)
    // Non-uniform position arrays (empty = uniform mode)
    std::vector<real_t> zx;  // z-positions, size nz
    std::vector<real_t> xx;  // x-positions, size nx
    std::vector<real_t> yx;  // y-positions, size ny

    size_t npts() const { return nx * ny * nz; }
    size_t index(size_t i, size_t j, size_t k) const {
        return i + nx * (j + ny * k);
    }

    // Edge spacing: distance from node n to n+1 along axis
    real_t dx_edge(size_t i) const {
        return xx.empty() ? dx : (xx[i+1] - xx[i]);
    }
    real_t dy_edge(size_t j) const {
        return yx.empty() ? dy : (yx[j+1] - yx[j]);
    }
    real_t dz_edge(size_t k) const {
        return zx.empty() ? dz : (zx[k+1] - zx[k]);
    }

    // Cell size at node n (FV cell = between midpoints of left and right edges)
    real_t dx_cell(size_t i) const {
        if (xx.empty()) return dx;
        real_t left = (i > 0) ? (xx[i] - xx[i-1]) / 2 : dx / 2;
        real_t right = (i+1 < nx) ? (xx[i+1] - xx[i]) / 2 : dx / 2;
        return left + right;
    }
    real_t dy_cell(size_t j) const {
        if (yx.empty()) return dy;
        real_t left = (j > 0) ? (yx[j] - yx[j-1]) / 2 : dy / 2;
        real_t right = (j+1 < ny) ? (yx[j+1] - yx[j]) / 2 : dy / 2;
        return left + right;
    }
    real_t dz_cell(size_t k) const {
        if (zx.empty()) return dz;
        real_t left = (k > 0) ? (zx[k] - zx[k-1]) / 2 : dz / 2;
        real_t right = (k+1 < nz) ? (zx[k+1] - zx[k]) / 2 : dz / 2;
        return left + right;
    }

    // Combined edge*cell product (replaces dx*dx in the uniform code)
    real_t dx_ec(size_t i) const { return dx_edge(i) * dx_cell(i); }
    real_t dy_ec(size_t j) const { return dy_edge(j) * dy_cell(j); }
    real_t dz_ec(size_t k) const { return dz_edge(k) * dz_cell(k); }

    // Edge spacing for SG flux on edge (i -> i+1)
    real_t dx_sg(size_t i) const { return dx_edge(i); }
    real_t dy_sg(size_t j) const { return dy_edge(j); }
    real_t dz_sg(size_t k) const { return dz_edge(k); }
};
