#include "device_simulator.h"
#include "device_simulator_double.h"
#include "newton_solver.h"
#include <limits>
#include <iostream>
#include <stdexcept>

using namespace tcad;
namespace {
size_t checks=0, fd_cases=0, wide_checks=0;
void check(bool pass) {
    ++checks;
    if (!pass) throw std::runtime_error("II floor contract failed");
}
template<class Sim, class Scalar> void setters(Sim& sim) {
    check(sim.get_ii_field_floor()==Scalar(1e5));
    sim.set_ii_field_floor(Scalar(3e5));
    check(sim.get_ii_field_floor()==Scalar(3e5));
    const Scalar inf=static_cast<Scalar>(std::numeric_limits<double>::infinity());
    const Scalar nan=static_cast<Scalar>(std::numeric_limits<double>::quiet_NaN());
    for (Scalar bad : {Scalar(-1),Scalar(0),inf,-inf,nan}) {
        bool caught=false;
        try { sim.set_ii_field_floor(bad); }
        catch (const std::invalid_argument&) { caught=true; }
        check(caught);check(sim.get_ii_field_floor()==Scalar(3e5));
    }
}
}
int main() {
    try {
#ifndef TCAD_II_FLOOR_PARENT
        DeviceSimulator native(2,1,1,TCAD_CONST(1e-7),1,1);
        DeviceSimulatorDouble facade(2,1,1,1e-7,1,1);
        setters<DeviceSimulator,real_t>(native);setters<DeviceSimulatorDouble,double>(facade);
        if (real_max_decimal_exponent()>std::numeric_limits<double>::max_exponent10) {
            const real_t wide=static_cast<real_t>(std::numeric_limits<double>::max())*2;
            native.set_ii_field_floor(wide);check(native.get_ii_field_floor()==wide);++wide_checks;
        }
#endif
        for (int axis : {0,1,2}) for (bool graded : {false,true})
            for (bool logarithmic : {false,true}) for (real_t floor : {TCAD_CONST(2e5),TCAD_CONST(1e6)}) {
                Grid3D grid{1,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
                if (axis==0) grid.nx=5;else if (axis==1) grid.ny=5;else grid.nz=5;
                if (graded) {
                    std::vector<real_t> position={0,TCAD_CONST(1e-7),TCAD_CONST(2.5e-7),TCAD_CONST(4e-7),TCAD_CONST(6e-7)};
                    if (axis==0)grid.xx=position;else if(axis==1)grid.yx=position;else grid.zx=position;
                }
                NewtonOptions opt;opt.enable_ii=true;opt.ii_E_floor=floor;
                opt.ii_A_n=TCAD_CONST(1e5);opt.ii_B_n=TCAD_CONST(2e5);
                opt.ii_A_p=TCAD_CONST(2e5);opt.ii_B_p=TCAD_CONST(3e5);opt.use_log_space=logarithmic;
                NewtonSolver solver(grid,opt);
                std::vector<real_t> phi={0,TCAD_CONST(.025),TCAD_CONST(.07),TCAD_CONST(.13),TCAD_CONST(.205)},n(5),p(5);
                for(size_t i=0;i<5;++i){n[i]=TCAD_CONST(2e19)+i*TCAD_CONST(1e18);p[i]=TCAD_CONST(1.2e19)+i*TCAD_CONST(5e17);}
                solver.set_mobility(std::vector<real_t>(5,TCAD_CONST(.1)),std::vector<real_t>(5,TCAD_CONST(.05)));
                solver.set_effective_dos(std::vector<real_t>(5,TCAD_CONST(1e19)),std::vector<real_t>(5,TCAD_CONST(1e19)));
                solver.set_bandgap(std::vector<real_t>(5,0));
                solver.set_phi_dirichlet({{0,phi[0]},{4,phi[4]}});
                solver.set_electron_bc({{0,n[0]},{4,n[4]}});solver.set_hole_bc({{0,p[0]},{4,p[4]}});
                // States stay away from the discontinuous threshold and |J|=0.
                check(solver.debug_fd_jacobian_check(phi,n,p,1e-5,8)==0);++fd_cases;
            }
        std::cout << "{\"checks\":" << checks << ",\"fd_cases\":" << fd_cases
                  << ",\"wide_checks\":" << wide_checks << ",\"profile\":\""
                  << compiled_constants_profile_name() << "\"}\n";
        return 0;
    } catch(const std::exception& e) {std::cerr << e.what() << '\n';return 1;}
}
