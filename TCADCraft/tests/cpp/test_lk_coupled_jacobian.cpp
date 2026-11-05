// Numerical derivatives of eliminated LK residual against the analytical
// susceptibility, including second-neighbour and masked dielectric rows.
#include "newton_solver.h"
#include <iostream>
#include <stdexcept>
using namespace tcad;

int main() {
    try {
        for (int dimensions : {1, 2, 3})
            for (bool logarithmic : {false, true}) {
                Grid3D grid{5, dimensions >= 2 ? 3u : 1u, dimensions >= 3 ? 3u : 1u,
                            TCAD_CONST(1e-8), TCAD_CONST(2e-8), TCAD_CONST(3e-8)};
                grid.xx = {TCAD_CONST(0.0), TCAD_CONST(0.3e-8), TCAD_CONST(1.2e-8), TCAD_CONST(2.7e-8), TCAD_CONST(4e-8)};
                if (grid.ny > 1) grid.yx = {TCAD_CONST(0.0), TCAD_CONST(1.3e-8), TCAD_CONST(4e-8)};
                if (grid.nz > 1) grid.zx = {TCAD_CONST(0.0), TCAD_CONST(2.2e-8), TCAD_CONST(6e-8)};
                const size_t N = grid.npts();
                std::vector<real_t> phi(N), n(N, TCAD_CONST(1e16)), p(N, TCAD_CONST(1e16)),
                    zero(N, TCAD_CONST(0.0)), eps(N), old(3*N, TCAD_CONST(0.0));
                std::vector<char> mask(N, 1);
                std::map<size_t, real_t> bc;
                for (size_t k=0; k<grid.nz; ++k)
                    for (size_t j=0; j<grid.ny; ++j)
                        for (size_t i=0; i<grid.nx; ++i) {
                            const size_t idx = grid.index(i,j,k);
                            eps[idx] = EPS0*(TCAD_CONST(10.0)+i+TCAD_CONST(2.0)*j+TCAD_CONST(3.0)*k);
                            phi[idx] = -TCAD_CONST(.002)*i+TCAD_CONST(.001)*j-TCAD_CONST(.0008)*k*k;
                            mask[idx] = idx%4 != 0;
                            for (int c=0;c<3;++c) old[3*idx+c] = mask[idx] ? TCAD_CONST(.0001)*(idx+c) : TCAD_CONST(0.0);
                            if (i == 0 || i+1 == grid.nx ||
                                (grid.ny > 1 && (j == 0 || j+1 == grid.ny)) ||
                                (grid.nz > 1 && (k == 0 || k+1 == grid.nz))) bc[idx] = phi[idx];
                        }
                NewtonOptions opt;
                opt.transient_enabled = true; opt.transient_dt = TCAD_CONST(1e-10);
                opt.n_prev = n; opt.p_prev = p; opt.use_log_space = logarithmic;
                NewtonSolver solver(grid, opt);
                solver.set_permittivity(eps); solver.set_mobility(zero, zero);
                solver.set_doping(zero); solver.set_phi_dirichlet(bc);
                solver.set_effective_dos(n,p); solver.set_bandgap(std::vector<real_t>(N, TCAD_CONST(6.0)));
                solver.set_transient_lk(mask, old, -TCAD_CONST(1e8), TCAD_CONST(1e12), TCAD_CONST(.1), TCAD_CONST(2e5), TCAD_CONST(30.0), dimensions-1);
                const size_t mismatches = solver.debug_fd_jacobian_check(phi,n,p,1e-5,8);
                std::cout << "dimensions=" << dimensions << " log=" << logarithmic
                          << " LK Jacobian mismatches=" << mismatches << '\n';
                if (mismatches) throw std::runtime_error("coupled LK analytic Jacobian disagrees with finite differences");
            }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
    return 0;
}
