// Independent dimensional three-node equations and adversarial acceptance.
#include "poisson_solver.h"
#include "gummel_solver.h"
#include <iostream>
#include <stdexcept>
#include <limits>
using namespace tcad;

static void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
template<class F> static void rejects(F action) {
    try { action(); } catch (const std::invalid_argument&) { return; }
    throw std::runtime_error("invalid Poisson audit input was accepted");
}
int main() {
    try {
        Grid3D grid{3, 1, 1, TCAD_CONST(1e-7), TCAD_CONST(1e-7), TCAD_CONST(1e-7)};
        PoissonSolver op(grid);
        const real_t vt = TCAD_CONST(0.02585), eps = TCAD_CONST(1e-10);
        const real_t c = eps / (grid.dx * grid.dx), density = TCAD_CONST(1e21);
        Vector n(3, density), p(n), phi(3, 0), doping(3, 0);
        op.set_permittivity(Vector(3, eps));
        op.set_dirichlet({{0, 0}, {2, 0}});
        // A tiny neutral cancellation used to have unit raw residual.
        n[1] += density * TCAD_CONST(1e-30);
        op.set_leakage_field(phi);
        check(op.residual_norm(phi,n,p) > TCAD_CONST(0.99), "baseline did not reproduce");
        check(op.scaled_residual_norm(phi,n,p,vt) < TCAD_CONST(1e-28), "neutrality rejected");
        n[1] = density;
        phi[1] = TCAD_CONST(0.01);
        const real_t denominator = vt*4*c + QE*2*density;
        const real_t expected = 2*c*phi[1]/denominator;
        const real_t measured = op.scaled_residual_norm(phi,n,p,vt);
        check(abs_q(measured/expected-1) < TCAD_CONST(1e-15), "independent curvature mismatch");
        check(measured > TCAD_CONST(1e-3), "local potential error hidden");
        // Stabilization at a large common potential must not dilute the error.
        const real_t offset = TCAD_CONST(1e6);
        for (auto& value : phi) value += offset;
        op.set_dirichlet({{0,offset},{2,offset}});
        check(abs_q(op.scaled_residual_norm(phi,n,p,vt)/expected-1) < TCAD_CONST(1e-12),
              "potential gauge diluted physical error");
        phi.assign(3,offset); phi[0] += TCAD_CONST(1e-4);
        check(op.scaled_residual_norm(phi,n,p,vt) >= TCAD_CONST(0.99e-4)/vt,
              "boundary voltage error hidden by gauge");
        phi.assign(3,0); op.set_dirichlet({{0,0},{2,0}});
        for (const real_t fraction : {TCAD_CONST(0.0),TCAD_CONST(0.2),TCAD_CONST(1.0)}) {
            op.set_charge_volume_fraction(Vector(3,fraction));
            p[1] = density * TCAD_CONST(1.1);
            const real_t charge = QE*fraction*(p[1]-n[1]);
            const real_t independent = charge / (vt*4*c + QE*fraction*(p[1]+n[1]) + charge);
            check(abs_q(op.scaled_residual_norm(phi,n,p,vt)-independent) < TCAD_CONST(1e-18),
                  "partial-volume charge scale mismatch");
            if (fraction > 0) check(independent > TCAD_CONST(1e-5), "carrier error not detected");
        }
        // A vanishing net RHS must not hide non-cancelling trap charge.
        p = n; op.set_charge_volume_fraction(Vector(3,1));
        Vector traps(3,0); traps[1] = TCAD_CONST(100.0); op.set_oxide_traps(traps);
        check(op.scaled_residual_norm(phi,n,p,vt) > TCAD_CONST(1e-2), "oxide charge ignored");
        op.set_oxide_traps(Vector(3,0));
        // Audit must not replace the live stabilized matrix or leakage cache.
        op.set_leakage_field(phi); op.assemble(n,p);
        const auto vals = op.matrix().vals();
        Vector changed(phi); changed[1] = TCAD_CONST(0.02);
        op.scaled_residual_norm(changed,n,p,vt);
        check(op.matrix().vals() == vals, "audit mutated live operator");
        rejects([&]{op.scaled_residual_norm({},n,p,vt);});
        rejects([&]{op.scaled_residual_norm(phi,n,p,0);});
        rejects([&]{op.scaled_residual_norm(phi,n,p,-vt);});
        Vector bad(n); bad[1] = -1;
        rejects([&]{op.scaled_residual_norm(phi,bad,p,vt);});
        const real_t nan = static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        bad = phi; bad[1] = nan;
        rejects([&]{op.scaled_residual_norm(bad,n,p,vt);});
        rejects([&]{op.scaled_residual_norm(phi,n,p,nan);});
        bad = n; bad[1] = nan;
        rejects([&]{op.scaled_residual_norm(phi,n,bad,vt);});
        // A frozen vacuum row uses volts even in a carrier-filled input.
        op.set_permittivity(Vector(3,0)); phi[1]=TCAD_CONST(0.01);
        check(abs_q(op.scaled_residual_norm(phi,n,p,vt)-phi[1]/vt) < TCAD_CONST(1e-15),
              "vacuum voltage constraint has charge units");
        // Neutral n=p errors are invisible to Poisson. Both transport
        // equations must independently reject an interior density bulge.
        GummelOptions options;
        options.enable_quantum = false;
        GummelSolver carriers(grid, options);
        carriers.set_mobility(Vector(3,TCAD_CONST(0.1)),Vector(3,TCAD_CONST(0.05)));
        carriers.set_effective_dos(Vector(3,density),Vector(3,density));
        carriers.set_bandgap(Vector(3,0));
        carriers.set_recombination(Vector(3,TCAD_CONST(1e100)),Vector(3,TCAD_CONST(1e100)));
        carriers.set_electron_bc({{0,density},{2,density}});
        carriers.set_hole_bc({{0,density},{2,density}});
        phi.assign(3,0); n.assign(3,density); p=n;
        check(carriers.compute_continuity_residual(phi,n,p) < TCAD_CONST(1e-18),
              "uniform equilibrium continuity rejected");
        n[1] *= TCAD_CONST(1.1); p=n;
        const Vector saved_n(n), saved_p(p);
        check(abs_q(carriers.compute_continuity_residual(phi,n,p)-TCAD_CONST(1.0)/21) < TCAD_CONST(1e-15),
              "neutral carrier bulge did not match independent continuity equation");
        check(n==saved_n && p==saved_p, "continuity audit changed carriers");
        n.assign(3,density); p=n;
        carriers.set_optical_generation(Vector(3,TCAD_CONST(1e28)));
        check(carriers.compute_continuity_residual(phi,n,p) > TCAD_CONST(1e-6),
              "continuity audit ignored generation");
        std::cout << "neutral cancellation, curvature, gauge, BC, cut volume, traps, isolation and invalid inputs passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
