// Independent Gauss-law and half-layer continuum integration, with injected P
// so neither FE kinetics nor two solvers sharing a stencil hide a sign error.
#include "newton_solver.h"
#include "polarization_flux.h"
#include <algorithm>
#include <iostream>
#include <stdexcept>

using namespace tcad;

static void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static void layered(int axis, bool stretched, bool log_space, bool override_eps) {
    Grid3D g{1, 1, 1, TCAD_CONST(1e-8), TCAD_CONST(1e-8), TCAD_CONST(1e-8)};
    if (axis == 0) g.nx = 9;
    if (axis == 1) g.ny = 9;
    if (axis == 2) g.nz = 9;
    std::vector<real_t> x{TCAD_CONST(0.0), TCAD_CONST(.3e-8), TCAD_CONST(.9e-8), TCAD_CONST(1.8e-8), TCAD_CONST(3e-8),
                          TCAD_CONST(4.7e-8), TCAD_CONST(5.6e-8), TCAD_CONST(7.2e-8), TCAD_CONST(8e-8)};
    if (!stretched) for (size_t i=0; i<9; ++i) x[i] = (real_t)i*TCAD_CONST(1e-8);
    if (axis == 0) g.xx = x;
    if (axis == 1) g.yx = x;
    if (axis == 2) g.zx = x;
    const size_t N = g.npts();
    std::vector<char> mask(N, 0);
    std::vector<real_t> eps(N), P(3*N, TCAD_CONST(17.0)), zero(N, TCAD_CONST(0.0));
    std::vector<real_t> scalar_P(N, TCAD_CONST(0.0)), compliance(8), source(8), expected(N, TCAD_CONST(0.0));
    for (size_t i=0; i<N; ++i) {
        mask[i] = i>=2 && i<=6;
        eps[i] = EPS0*(mask[i] ? TCAD_CONST(25.0) : TCAD_CONST(4.0));
        // Deliberate stale values outside FE and in other components: mask
        // suppression and differentiation along the correct axis matter.
        if (mask[i]) {
            for (int c=0; c<3; ++c) P[3*i+c] = TCAD_CONST(0.0);
            scalar_P[i] = TCAD_CONST(.002)*(TCAD_CONST(1.0) + TCAD_CONST(.1)*(real_t)i);
            P[3*i+axis] = scalar_P[i];
        }
    }
    std::vector<real_t> plus(N, TCAD_CONST(0.0)), minus(N, TCAD_CONST(0.0)), empty;
    real_t sum_compliance=TCAD_CONST(0.0), sum_source=TCAD_CONST(0.0);
    for (size_t i=0; i+1<N; ++i) {
        real_t edge = TCAD_CONST(2.0)*eps[i]*eps[i+1]/(eps[i]+eps[i+1]);
        if (override_eps) edge *= TCAD_CONST(.7);
        plus[i] = minus[i+1] = edge;
        const real_t h = x[i+1]-x[i];
        compliance[i] = h/edge;
        source[i] = h/TCAD_CONST(2.0)*(scalar_P[i]/eps[i]+scalar_P[i+1]/eps[i+1]);
        sum_compliance += compliance[i]; sum_source += source[i];
    }
    const real_t voltage=-TCAD_CONST(.1);
    const real_t D = (-voltage+sum_source)/sum_compliance;
    for (size_t i=1; i<N; ++i)
        expected[i] = expected[i-1]+source[i-1]-D*compliance[i-1];
    std::map<size_t, real_t> bc{{0, TCAD_CONST(0.0)}, {8, voltage}};
    auto set_edges = [&](auto& solver) {
        if (!override_eps) return;
        solver.set_edge_permittivity(axis==0?plus:empty, axis==0?minus:empty,
            axis==1?plus:empty, axis==1?minus:empty,
            axis==2?plus:empty, axis==2?minus:empty);
    };
    PoissonSolver poisson(g);
    poisson.set_permittivity(eps); set_edges(poisson);
    poisson.set_doping(zero); poisson.set_dirichlet(bc);
    poisson.set_ferroelectric(mask, -TCAD_CONST(1e8), TCAD_CONST(1e12));
    poisson.set_fe_polarization(P);
    SolverOptions linear;
    linear.type = SolverType::DENSE_DIRECT;
    poisson.set_solver_options(linear);
    poisson.assemble(zero, zero);
    std::vector<real_t> phi(N, TCAD_CONST(0.0));
    check(poisson.solve(phi), "Poisson layer solve failed");
    for (size_t i=0; i<N; ++i)
        check(abs_q(phi[i]-expected[i])<TCAD_CONST(1e-12), "Poisson violates layered Gauss law");
    NewtonOptions opt;
    opt.max_iter=80; opt.tol=TCAD_CONST(1e-12); opt.use_log_space=log_space;
    opt.linear_solver=SolverType::DENSE_DIRECT;
    NewtonSolver newton(g,opt);
    newton.set_permittivity(eps); set_edges(newton);
    newton.set_mobility(zero,zero); newton.set_doping(zero);
    newton.set_effective_dos(std::vector<real_t>(N,TCAD_CONST(1e16)), std::vector<real_t>(N,TCAD_CONST(1e16)));
    newton.set_bandgap(std::vector<real_t>(N,TCAD_CONST(6.0)));
    newton.set_phi_dirichlet(bc);
    newton.set_electron_bc({{0,TCAD_CONST(0.0)},{8,TCAD_CONST(0.0)}});
    newton.set_hole_bc({{0,TCAD_CONST(0.0)},{8,TCAD_CONST(0.0)}});
    newton.set_ferroelectric_polarization(mask,P);
    phi.assign(N,TCAD_CONST(0.0));
    std::vector<real_t> n(N,EPSILON), p(N,EPSILON);
    n[0]=n[8]=p[0]=p[8]=TCAD_CONST(0.0);
    check(newton.solve(phi,n,p), "Newton layer solve failed");
    check(n[0]==TCAD_CONST(0.0) && p[0]==TCAD_CONST(0.0) && n[8]==TCAD_CONST(0.0) && p[8]==TCAD_CONST(0.0),
          "Zero carrier contacts must remain exact");
    for (size_t i=0; i<N; ++i)
        check(abs_q(phi[i]-expected[i])<TCAD_CONST(1e-12), "Newton violates layered Gauss law");
    for (size_t i=0; i+1<N; ++i) {
        const real_t measured=(source[i]-(phi[i+1]-phi[i]))/compliance[i];
        check(abs_q(measured-D)<TCAD_CONST(1e-14), "Displacement jumps without free sheet charge");
    }
}

static void closed_volume() {
    Grid3D g{5,4,3,TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(1.0)};
    g.xx={TCAD_CONST(0.0),TCAD_CONST(.2),TCAD_CONST(.7),TCAD_CONST(1.9),TCAD_CONST(3.0)};
    g.yx={TCAD_CONST(0.0),TCAD_CONST(.3),TCAD_CONST(1.1),TCAD_CONST(2.5)};
    g.zx={TCAD_CONST(0.0),TCAD_CONST(.5),TCAD_CONST(2.0)};
    const size_t N=g.npts();
    std::vector<char> mask(N,0);
    std::vector<real_t> eps(N), P(3*N);
    for (size_t idx=0; idx<N; ++idx) {
        mask[idx] = idx%3 != 0;
        eps[idx] = EPS0*(TCAD_CONST(4.0)+(real_t)(idx%7));
        for (int c=0; c<3; ++c)
            P[3*idx+c] = TCAD_CONST(.003)*((real_t)((idx+2*c)%11)-TCAD_CONST(5.0));
    }
    auto edge=[&](int,bool,size_t a,size_t b) {
        return TCAD_CONST(2.0)*eps[a]*eps[b]/(eps[a]+eps[b]);
    };
    real_t integral=TCAD_CONST(0.0), absolute=TCAD_CONST(0.0);
    for (size_t k=0; k<g.nz; ++k)
        for (size_t j=0; j<g.ny; ++j)
            for (size_t i=0; i<g.nx; ++i) {
                const real_t charge=-polarization_divergence(g,mask,P,eps,i,j,k,edge);
                const real_t volume=g.dx_cell(i)*g.dy_cell(j)*g.dz_cell(k);
                integral += charge*volume; absolute += abs_q(charge*volume);
            }
    check(absolute>TCAD_CONST(0.0), "Closed-volume test has no bound charge");
    check(abs_q(integral)<std::max(TCAD_CONST(1e-25),TCAD_CONST(256.0)*epsilon_q())*absolute,
          "Internal polarization faces fail to cancel");
}

static void interface_trap_sign_and_jacobian(real_t energy) {
    Grid3D g{9,1,1,TCAD_CONST(1e-8),TCAD_CONST(1.0),TCAD_CONST(1.0)};
    const size_t N=g.npts();
    std::vector<char> mask(N,1);
    std::vector<real_t> eps(N,EPS0*TCAD_CONST(20.0)), zero(N,TCAD_CONST(0.0));
    std::vector<real_t> phi(N,TCAD_CONST(0.0)), n(N,EPSILON), p(N,EPSILON);
    std::map<size_t,real_t> bc{{0,TCAD_CONST(0.0)},{8,TCAD_CONST(0.0)}};
    const real_t dit=TCAD_CONST(1e10), thickness=(real_t)N*g.dx;
    // Saturated occupancy gives an independent constant-charge parabola.
    const real_t occupancy=energy>TCAD_CONST(0.0) ? TCAD_CONST(0.0) : TCAD_CONST(1.0);
    const real_t charge=-QE*dit*TCAD_CONST(1e4)*(occupancy-TCAD_CONST(.5))/thickness;
    PoissonSolver poisson(g);
    poisson.set_permittivity(eps); poisson.set_doping(zero);
    poisson.set_dirichlet(bc); poisson.set_interface_traps(mask,dit,energy);
    poisson.set_leakage_field(phi);
    SolverOptions linear; linear.type=SolverType::DENSE_DIRECT;
    poisson.set_solver_options(linear); poisson.assemble(zero,zero);
    check(poisson.solve(phi), "Interface trap Poisson failed");
    for (size_t i=0; i<N; ++i) {
        const real_t x=(real_t)i*g.dx, L=(real_t)(N-1)*g.dx;
        check(abs_q(phi[i]-charge*x*(L-x)/(TCAD_CONST(2.0)*eps[i]))<TCAD_CONST(1e-12),
              "Interface trap physical charge sign is wrong");
    }
    NewtonOptions opt; opt.max_iter=80; opt.tol=TCAD_CONST(1e-12);
    opt.linear_solver=SolverType::DENSE_DIRECT;
    NewtonSolver newton(g,opt);
    newton.set_permittivity(eps); newton.set_mobility(zero,zero);
    newton.set_doping(zero);
    newton.set_effective_dos(std::vector<real_t>(N,TCAD_CONST(1e16)),std::vector<real_t>(N,TCAD_CONST(1e16)));
    newton.set_bandgap(std::vector<real_t>(N,TCAD_CONST(6.0))); newton.set_phi_dirichlet(bc);
    newton.set_trap_charge(mask,dit,energy,zero);
    phi.assign(N,TCAD_CONST(0.0));
    check(newton.solve(phi,n,p), "Interface trap Newton failed");
    for (size_t i=0; i<N; ++i) {
        const real_t x=(real_t)i*g.dx, L=(real_t)(N-1)*g.dx;
        check(abs_q(phi[i]-charge*x*(L-x)/(TCAD_CONST(2.0)*eps[i]))<TCAD_CONST(1e-12),
              "Interface trap Newton charge sign is wrong");
    }
    // Near half occupancy the derivative is resolvable. Check the assembled
    // Jacobian against finite differences instead of another solver's sign.
    newton.set_trap_charge(mask,TCAD_CONST(1e12),TCAD_CONST(.005),zero);
    check(newton.debug_fd_jacobian_check(phi,n,p,1e-6,5)==0,
          "Interface trap Jacobian disagrees with residual");
}

int main() {
    try {
        for (int axis: {0,1,2}) for (bool stretched: {false,true})
            for (bool log_space: {false,true}) for (bool override_eps: {false,true})
                layered(axis,stretched,log_space,override_eps);
        closed_volume();
        interface_trap_sign_and_jacobian(TCAD_CONST(2.0));
        interface_trap_sign_and_jacobian(-TCAD_CONST(2.0));
        std::cout << "24 layered cases, 3D flux cancellation and signed trap/Jacobian checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
    return 0;
}
