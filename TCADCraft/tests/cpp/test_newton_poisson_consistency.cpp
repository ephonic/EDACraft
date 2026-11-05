// Compare independent equation assembly, including sign, units and geometry.
#include "newton_solver.h"
#include <iostream>
#include <stdexcept>

using namespace tcad;

static void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static void check_equations(bool traps, bool log_space) {
    Grid3D grid{9, 1, 3, TCAD_CONST(2.0e-9), TCAD_CONST(4.0e-9), TCAD_CONST(3.0e-9)};
    const size_t count = grid.npts();
    std::vector<real_t> eps(count, EPS0 * TCAD_CONST(15.0)), zero(count, TCAD_CONST(0.0));
    std::vector<real_t> phi(count, TCAD_CONST(0.0)), n(count, EPSILON), p(count, EPSILON);
    std::vector<char> mask(count, 0);
    std::vector<real_t> polarization(3 * count, TCAD_CONST(0.0)), oxide_charge(count, TCAD_CONST(0.0));
    std::map<size_t, real_t> bc;
    for (size_t i = 0; i < grid.nx; ++i) {
        bc[grid.index(i, 0, 0)] = TCAD_CONST(0.0);
        bc[grid.index(i, 0, 2)] = TCAD_CONST(0.2);
        mask[grid.index(i, 0, 1)] = 1;
        if (!traps) {
            // A z-normal FE layer creates nonzero divergence at the middle
            // plane through an x-varying Px; a uniform slab would hide a sign bug.
            polarization[3 * grid.index(i, 0, 1)] = TCAD_CONST(1.0e-3) * (real_t)i;
        } else {
            oxide_charge[grid.index(i, 0, 1)] = TCAD_CONST(1000.0);
        }
    }

    NewtonOptions options;
    options.max_iter = 60;
    options.tol = TCAD_CONST(1e-12);
    options.linear_solver = SolverType::DENSE_DIRECT;
    options.use_log_space = log_space;
    NewtonSolver coupled(grid, options);
    coupled.set_permittivity(eps);
    coupled.set_mobility(zero, zero);
    coupled.set_doping(zero);
    coupled.set_effective_dos(std::vector<real_t>(count, TCAD_CONST(2.8e25)),
                              std::vector<real_t>(count, TCAD_CONST(1.04e25)));
    coupled.set_bandgap(std::vector<real_t>(count, TCAD_CONST(5.5)));
    coupled.set_phi_dirichlet(bc);

    PoissonSolver reference(grid);
    reference.set_permittivity(eps);
    reference.set_doping(zero);
    reference.set_dirichlet(bc);
    if (traps) {
        // Nonzero E_t exposes the eV/thermal-voltage mismatch. The layer's
        // 3 nm normal thickness differs from the 2 nm x mesh spacing.
        coupled.set_trap_charge(mask, TCAD_CONST(1e10), TCAD_CONST(0.15), oxide_charge);
        reference.set_interface_traps(mask, TCAD_CONST(1e10), TCAD_CONST(0.15));
        reference.set_oxide_traps(oxide_charge);
    } else {
        coupled.set_ferroelectric_polarization(mask, polarization);
        reference.set_ferroelectric(mask, -TCAD_CONST(1e8), TCAD_CONST(1e18));
        reference.set_fe_polarization(polarization);
    }
    check(coupled.solve(phi, n, p), "Newton did not converge");
    reference.set_leakage_field(phi);
    const real_t residual = reference.residual_norm(phi, n, p);
    std::cout << "traps=" << traps << " log_space=" << log_space
              << " independent Poisson residual=" << (double)residual << '\n';
    check(residual < TCAD_CONST(1e-8), "Newton and Poisson equations disagree");
}

int main() {
    try {
        for (bool log_space : {false, true}) {
            check_equations(false, log_space);
            check_equations(true, log_space);
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
