// Independent memory invariants; no fitting to the calibration loop.
#include "poisson_solver.h"
#include <stdexcept>
#include <iostream>

using namespace tcad;

static void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static PoissonSolver ensemble() {
    Grid3D grid{3, 1, 1, TCAD_CONST(1e-9), TCAD_CONST(1.0), TCAD_CONST(1.0)};
    PoissonSolver solver(grid);
    solver.set_ferroelectric(std::vector<char>(3, 1), -TCAD_CONST(1e8), TCAD_CONST(1e18));
    solver.set_ferroelectric_model(3);
    solver.set_ferroelectric_preisach(TCAD_CONST(0.20), TCAD_CONST(5e7), TCAD_CONST(1e8) / log_q(TCAD_CONST(4.0)));
    return solver;
}

static real_t advance(PoissonSolver& solver, real_t field) {
    solver.update_ferroelectric_polarization({TCAD_CONST(0.0), -field * TCAD_CONST(1e-9),
                                             -field * TCAD_CONST(2e-9)});
    return solver.fe_polarization()[3];
}

int main() {
    try {
        auto solver = ensemble();
        check(advance(solver, TCAD_CONST(0.0)) == TCAD_CONST(0.0), "initial P is not zero");
        // Crossing the preset initial turning point must be continuous.
        const real_t Eb = TCAD_CONST(5e7) + (TCAD_CONST(5e7) / log_q(TCAD_CONST(4.0))) * log_q(TCAD_CONST(1.5));
        const real_t below = advance(solver, Eb - TCAD_CONST(1.0));
        const real_t above = advance(solver, Eb + TCAD_CONST(1.0));
        check(abs_q(above - below) < TCAD_CONST(1e-8), "initial branch jumps at wipeout");
        check(solver.fe_play_state().size() == 10, "initial memory not erased");
        const real_t peak = advance(solver, TCAD_CONST(1.2e8));
        check(abs_q(advance(solver, TCAD_CONST(1.2e8) - TCAD_CONST(1.0)) - peak) < TCAD_CONST(1e-8),
              "polarization jumps at reversal");
        advance(solver, TCAD_CONST(0.8e8));
        const real_t return_point = advance(solver, TCAD_CONST(0.9e8));
        advance(solver, TCAD_CONST(0.85e8));
        const real_t restored = advance(solver, TCAD_CONST(0.9e8));
        check(abs_q(restored - return_point) < TCAD_CONST(1e-25),
              "nested loop does not recover its return point");
        const real_t after_wipeout = advance(solver, TCAD_CONST(1.21e8));
        check(solver.fe_play_state().size() == 10, "nested memory not erased");
        auto direct = ensemble();
        advance(direct, TCAD_CONST(0.0));
        check(abs_q(advance(direct, TCAD_CONST(1.21e8)) - after_wipeout) < TCAD_CONST(1e-25),
              "wiped history changes the enclosing branch");
        const auto memory = solver.fe_play_state();
        for (int retry = 0; retry < 5; ++retry)
            check(advance(solver, TCAD_CONST(1.21e8)) == after_wipeout,
                  "same field changes polarization");
        check(solver.fe_play_state() == memory, "same field grows memory");
        std::cout << "Initial continuity, reversal continuity, return-point "
                     "memory, wipeout and fixed-field idempotence passed.\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
