#include "device_simulator.h"
#include "device_simulator_double.h"
#include "newton_solver.h"
#include "gummel_solver.h"
#include <limits>
#include <iostream>
#include <stdexcept>
using namespace tcad;
namespace {
size_t checks=0, fd_cases=0, wide_checks=0;
void check(bool pass) {
    ++checks;
    if (!pass) throw std::runtime_error("HFS cutoff contract failed");
}
template<class Sim,class Scalar> void setters(Sim& sim) {
    check(sim.get_hfs_low_field_cutoff()==Scalar(0));
    sim.set_hfs_low_field_cutoff(Scalar(3e5));
    check(sim.get_hfs_low_field_cutoff()==Scalar(3e5));
    const Scalar inf=static_cast<Scalar>(std::numeric_limits<double>::infinity());
    const Scalar nan=static_cast<Scalar>(std::numeric_limits<double>::quiet_NaN());
    for(Scalar bad : {Scalar(-1),inf,-inf,nan}) {
        bool caught=false;
        try {sim.set_hfs_low_field_cutoff(bad);}catch(const std::invalid_argument&){caught=true;}
        check(caught);check(sim.get_hfs_low_field_cutoff()==Scalar(3e5));
    }
    sim.set_hfs_low_field_cutoff(Scalar(0));check(sim.get_hfs_low_field_cutoff()==Scalar(0));
}
}
int main() {
    try {
        Grid3D simple{3,1,1,TCAD_CONST(1e-7),1,1};
#ifndef TCAD_HFS_CUTOFF_PARENT
        DeviceSimulator native(2,1,1,TCAD_CONST(1e-7),1,1);
        DeviceSimulatorDouble facade(2,1,1,1e-7,1,1);
        setters<DeviceSimulator,real_t>(native);setters<DeviceSimulatorDouble,double>(facade);
        if(real_max_decimal_exponent()>std::numeric_limits<double>::max_exponent10) {
            const real_t wide=static_cast<real_t>(std::numeric_limits<double>::max())*2;
            native.set_hfs_low_field_cutoff(wide);check(native.get_hfs_low_field_cutoff()==wide);++wide_checks;
        }
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        for(real_t bad : {TCAD_CONST(-1.0),inf,-inf,nan}) for(bool enabled : {false,true}) {
            GummelOptions go;go.hfs.enabled=enabled;go.hfs.low_field_cutoff=bad;
            NewtonOptions no;no.hfs_enabled=enabled;no.hfs_low_field_cutoff=bad;
            bool gc=false,nc=false;
            try {GummelSolver s(simple,go);}catch(const std::invalid_argument&){gc=true;}
            try {NewtonSolver s(simple,no);}catch(const std::invalid_argument&){nc=true;}
            check(gc==enabled);check(nc==enabled);
        }
#endif
        for(int axis : {0,1,2}) for(bool graded : {false,true})
            for(bool logarithmic : {false,true}) for(int driving : {0,1})
            for(real_t cutoff : {TCAD_CONST(2e5),TCAD_CONST(1e6)}) {
                Grid3D grid{1,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
                if(axis==0)grid.nx=5;else if(axis==1)grid.ny=5;else grid.nz=5;
                if(graded) {
                    std::vector<real_t> x={0,TCAD_CONST(1e-7),TCAD_CONST(2.5e-7),TCAD_CONST(4e-7),TCAD_CONST(6e-7)};
                    if(axis==0)grid.xx=x;else if(axis==1)grid.yx=x;else grid.zx=x;
                }
                NewtonOptions opt;opt.hfs_enabled=true;opt.use_log_space=logarithmic;opt.hfs_driving=driving;
                opt.hfs_vsat_n=TCAD_CONST(5e4);opt.hfs_vsat_p=TCAD_CONST(4e4);
#ifndef TCAD_HFS_CUTOFF_PARENT
                opt.hfs_low_field_cutoff=cutoff;
#else
                (void)cutoff;
#endif
                NewtonSolver solver(grid,opt);
                std::vector<real_t> phi={0,TCAD_CONST(.025),TCAD_CONST(.07),TCAD_CONST(.13),TCAD_CONST(.205)},n(5),p(5);
                for(size_t i=0;i<5;++i){n[i]=TCAD_CONST(2e19)+i*TCAD_CONST(1e18);p[i]=TCAD_CONST(1.2e19)+i*TCAD_CONST(5e17);}
                solver.set_mobility(std::vector<real_t>(5,TCAD_CONST(.1)),std::vector<real_t>(5,TCAD_CONST(.05)));
                solver.set_effective_dos(std::vector<real_t>(5,TCAD_CONST(1e19)),std::vector<real_t>(5,TCAD_CONST(1e19)));
                solver.set_bandgap(std::vector<real_t>(5,0));
                solver.set_phi_dirichlet({{0,phi[0]},{4,phi[4]}});
                solver.set_electron_bc({{0,n[0]},{4,n[4]}});solver.set_hole_bc({{0,p[0]},{4,p[4]}});
                std::cerr<<"FD axis="<<axis<<" graded="<<graded<<" log="<<logarithmic<<" driving="<<driving<<" cutoff="<<(double)cutoff<<'\n';
                // The selected states and perturbations avoid the threshold.
                check(solver.debug_fd_jacobian_check(phi,n,p,1e-5,8)==0);++fd_cases;
            }
        std::cout<<"{\"checks\":"<<checks<<",\"fd_cases\":"<<fd_cases
                 <<",\"wide_checks\":"<<wide_checks<<",\"profile\":\""<<compiled_constants_profile_name()<<"\"}\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
