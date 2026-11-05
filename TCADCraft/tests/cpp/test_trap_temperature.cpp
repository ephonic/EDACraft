// Independent trap occupancy/source, nonlinear root and Jacobian at multiple T.
#include "newton_solver.h"
#include <iostream>
#include <stdexcept>
using namespace tcad;

static real_t occupancy(real_t phi, real_t energy, real_t vt) {
    return TCAD_CONST(1.0)/(TCAD_CONST(1.0)+exp_q((energy-phi)/vt));
}
static void check(bool valid,const char* message) {
    if (!valid) throw std::runtime_error(message);
}
int main() {
    try {
        for (real_t temperature : {TCAD_CONST(100.0),TCAD_CONST(300.0),TCAD_CONST(1000.0)})
            for (real_t energy : {-TCAD_CONST(0.08),TCAD_CONST(0.15)}) {
                Grid3D grid{3,1,1,TCAD_CONST(2e-9),TCAD_CONST(3e-9),TCAD_CONST(4e-9)};
                const real_t vt=KB*temperature/QE, dit=TCAD_CONST(1e10), eps=EPS0*TCAD_CONST(11.7);
                std::vector<real_t> zero(3,TCAD_CONST(0.0)), dielectric(3,eps), phi{TCAD_CONST(0.0),TCAD_CONST(0.03),TCAD_CONST(0.1)};
                std::vector<real_t> n(3,EPSILON),p(3,EPSILON);
                std::vector<char> mask{0,1,0};
                PoissonSolver poisson(grid);
                poisson.set_permittivity(dielectric); poisson.set_doping(zero);
                poisson.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(0.1)}});
                poisson.set_boltzmann_linearization(false,vt);
                poisson.set_interface_traps(mask,dit,energy); poisson.set_leakage_field(phi);
                poisson.assemble(n,p);
                const real_t source=QE*dit*TCAD_CONST(1e4)*(occupancy(phi[1],energy,vt)-TCAD_CONST(0.5))/grid.dx;
                check(abs_q(poisson.rhs()[1]-source)<std::max(TCAD_CONST(1e-24),
                    TCAD_CONST(64.0)*epsilon_q())*abs_q(source),
                      "Poisson trap charge does not use configured thermal voltage");
                for (bool logarithmic : {false,true}) {
                    NewtonOptions opt; opt.temperature=temperature;
                    opt.use_log_space=logarithmic; opt.linear_solver=SolverType::DENSE_DIRECT;
                    opt.max_iter=60; opt.tol=TCAD_CONST(1e-16);
                    NewtonSolver solver(grid,opt); solver.set_thermal_voltage(vt);
                    solver.set_permittivity(dielectric); solver.set_mobility(zero,zero);
                    solver.set_doping(zero); solver.set_phi_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(0.1)}});
                    solver.set_effective_dos(std::vector<real_t>(3,TCAD_CONST(1e16)),std::vector<real_t>(3,TCAD_CONST(1e16)));
                    solver.set_bandgap(std::vector<real_t>(3,TCAD_CONST(6.0)));
                    solver.set_trap_charge(mask,dit,energy,zero);
                    std::vector<real_t> solution=phi;
                    check(solver.debug_fd_jacobian_check(solution,n,p,1e-5,8)==0,
                          "trap Jacobian differs from finite differences");
                    check(solver.solve(solution,n,p),"Newton trap solve failed");
                    real_t lo=-TCAD_CONST(1.0),hi=TCAD_CONST(1.0);
                    for (int iter=0;iter<110;++iter) {
                        const real_t mid=(lo+hi)/TCAD_CONST(2.0);
                        const real_t rho=-QE*dit*TCAD_CONST(1e4)*(occupancy(mid,energy,vt)-TCAD_CONST(0.5))/grid.dx;
                        const real_t residual=eps*(TCAD_CONST(0.1)-TCAD_CONST(2.0)*mid)/(grid.dx*grid.dx)+rho;
                        if (residual>0) lo=mid; else hi=mid;
                    }
                    check(abs_q(solution[1]-(lo+hi)/TCAD_CONST(2.0))<TCAD_CONST(1e-15),
                          "Newton trap root differs from independent thermal occupancy equation");
                    std::cout << "T=" << (double)temperature << " Et=" << (double)energy
                              << " log=" << logarithmic << " phi=" << (double)solution[1] << '\n';
                }
            }
    } catch(const std::exception& error) { std::cerr << error.what() << '\n';return 1; }
    return 0;
}
