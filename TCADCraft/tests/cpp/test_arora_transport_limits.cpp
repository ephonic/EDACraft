#include "device_simulator.h"
#include <iostream>
#include <stdexcept>
using namespace tcad;
static int calls=0, checks=0;
static void require(bool condition,const char* message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}
static SimulationResult solve(int axis,bool newton,bool arora,bool feedback) {
    const size_t nx=axis==0?5:1,ny=axis==1?5:1,nz=axis==2?5:1;
    const real_t h=TCAD_CONST(2.5e-8),bias=TCAD_CONST(.02);
    DeviceSimulator sim(nx,ny,nz,h,h,h);
    auto values=[](real_t value) {return std::vector<real_t>(5,value);};
    sim.set_permittivity(values(TCAD_CONST(1e-10)));
    sim.set_mobility(values(TCAD_CONST(.1417)),values(TCAD_CONST(.04705)));
    sim.set_doping(values(TCAD_CONST(0.0)));
    sim.set_effective_dos(values(TCAD_CONST(1e21)),values(TCAD_CONST(1e21)));
    sim.set_bandgap(values(TCAD_CONST(0.0)));
    sim.set_temperature(TCAD_CONST(300.0));
    sim.set_thermal_voltage(TCAD_CONST(8.617333262e-5)*TCAD_CONST(300.0));
    sim.set_dirichlet_potential({{0,0},{4,bias}});
    sim.set_electron_bc({{0,TCAD_CONST(1e21)},{4,TCAD_CONST(1e21)}});
    sim.set_hole_bc({{0,TCAD_CONST(1e21)},{4,TCAD_CONST(1e21)}});
    auto phi=values(0);
    for (size_t i=0;i<5;++i) phi[i]=bias*i/4;
    sim.set_initial_guess(phi,values(TCAD_CONST(1e21)),values(TCAD_CONST(1e21)));
    sim.set_use_newton(newton);
    sim.set_newton_use_log_space(true);
    sim.set_newton_use_log_damping(true);
    sim.set_gummel_max_iter(100);
    sim.set_tolerance(TCAD_CONST(1e-11));
    sim.set_mobility_model(arora?1:0);
    sim.set_thermal_coupling_enabled(true);
    sim.set_thermal_conductivity(values(TCAD_CONST(.001)));
    sim.set_thermal_dirichlet({{0,TCAD_CONST(300.0)},{4,TCAD_CONST(300.0)}});
    sim.set_lattice_mobility_feedback(feedback,120,TCAD_CONST(1e-7),TCAD_CONST(.5));
    ++calls;
    return sim.solve();
}
int main() {
    try {
        for (int axis=0;axis<3;++axis) {
            SimulationResult reference;
            for (bool newton : {false,true}) {
                auto constant=solve(axis,newton,false,false);
                auto arora=solve(axis,newton,true,false);
                require(constant.converged && arora.converged,"isothermal transport failed");
                require(arora.thermal.available,"mobility ledger absent");
                const auto& jn=axis==0?arora.Jn_x:axis==1?arora.Jn_y:arora.Jn_z;
                const auto& jp=axis==0?arora.Jp_x:axis==1?arora.Jp_y:arora.Jp_z;
                const auto& cn=axis==0?constant.Jn_x:axis==1?constant.Jn_y:constant.Jn_z;
                const auto& cp=axis==0?constant.Jp_x:axis==1?constant.Jp_y:constant.Jp_z;
                real_t expected_n=-QE*TCAD_CONST(.1417)*TCAD_CONST(1e21)*TCAD_CONST(.02)/TCAD_CONST(1e-7);
                real_t expected_p=-QE*TCAD_CONST(.04705)*TCAD_CONST(1e21)*TCAD_CONST(.02)/TCAD_CONST(1e-7);
                for (size_t i=0;i<4;++i) {
                    require(abs_q(jn[i]/expected_n-1)<TCAD_CONST(1e-9),"electron drift-current limit");
                    require(abs_q(jp[i]/expected_p-1)<TCAD_CONST(1e-9),"hole drift-current limit");
                    require(abs_q(jn[i]/cn[i]-1)<TCAD_CONST(1e-9) && abs_q(jp[i]/cp[i]-1)<TCAD_CONST(1e-9),"Arora differs from equal constant mobilities");
                }
                for (size_t i=0;i<5;++i) {
                    require(abs_q(arora.thermal.mobility_n[i]/TCAD_CONST(.1417)-1)<TCAD_CONST(1e-14),"electron ledger missing floor");
                    require(abs_q(arora.thermal.mobility_p[i]/TCAD_CONST(.04705)-1)<TCAD_CONST(1e-14),"hole ledger missing floor");
                }
                reference=arora;
            }
            auto hot=solve(axis,true,true,true);
            require(hot.converged && hot.thermal.feedback_converged,"thermal fixed point failed");
            require(hot.temperature[2]>TCAD_CONST(300.0),"feedback fixture did not heat");
            for (size_t i=0;i<5;++i) {
                real_t t=hot.thermal.mobility_temperature[i]/TCAD_CONST(300.0);
                real_t n=(TCAD_CONST(52.2)+TCAD_CONST(1364.8)*pow_q(t,-TCAD_CONST(.66)))*TCAD_CONST(1e-4);
                real_t p=(TCAD_CONST(49.9)+TCAD_CONST(420.6)*pow_q(t,-TCAD_CONST(2.05)))*TCAD_CONST(1e-4);
                require(abs_q(hot.thermal.mobility_n[i]/n-1)<TCAD_CONST(3e-14),"feedback electron mobility formula");
                require(abs_q(hot.thermal.mobility_p[i]/p-1)<TCAD_CONST(3e-14),"feedback hole mobility formula");
            }
        }
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<"\n";
        std::cout<<"{\"valid\":false,\"native_solver_calls\":"<<calls<<",\"checks\":"<<checks<<"}\n";
        return 1;
    }
    std::cout<<"{\"valid\":true,\"native_solver_calls\":"<<calls<<",\"checks\":"<<checks<<",\"mantissa_bits\":"<<real_mantissa_bits()<<"}\n";
}
