#include "newton_density_update_333.h"
#include "newton_solver.h"
#include "device_simulator.h"
#include "device_simulator_double.h"
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace tcad;
static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
int main() {
    try {
        // This must retain a correction that log(1+step) would round away.
        const real_t tiny=epsilon_q()*epsilon_q();
        real_t out=TCAD_CONST(19.0);
        require(additive_density_log_update_333(TCAD_CONST(0.0),tiny,out),"tiny update rejected");
        require(out>TCAD_CONST(0.0) && abs_q(out/tiny-TCAD_CONST(1.0))<TCAD_CONST(32.0)*epsilon_q(),"log1p lost tiny correction");
        for (real_t step : {TCAD_CONST(-0.9),TCAD_CONST(-0.25),TCAD_CONST(0.0),TCAD_CONST(1.0),TCAD_CONST(1000.0)}) {
            require(additive_density_log_update_333(TCAD_CONST(100.0),step,out),"valid update rejected");
            require(abs_q(exp_q(out-TCAD_CONST(100.0))-(TCAD_CONST(1.0)+step)) < TCAD_CONST(1000000.0)*epsilon_q()*(TCAD_CONST(1.0)+abs_q(step)),"physical density factor incorrect");
        }
        const real_t inf=real_t(std::numeric_limits<double>::infinity());
        const real_t nan=real_t(std::numeric_limits<double>::quiet_NaN());
        for (real_t step : {-TCAD_CONST(1.0),-TCAD_CONST(2.0),inf,-inf,nan}) {
            out=TCAD_CONST(19.0);
            require(!additive_density_log_update_333(TCAD_CONST(3.0),step,out) && out==TCAD_CONST(19.0),"invalid factor changed output");
        }
        for (real_t u : {inf,-inf,nan}) {
            out=TCAD_CONST(19.0);
            require(!additive_density_log_update_333(u,TCAD_CONST(0.0),out) && out==TCAD_CONST(19.0),"nonfinite state changed output");
        }
        NewtonOptions options;
        require(!options.additive_log_density_update,"native default changed");
        DeviceSimulator first(3,1,1,TCAD_CONST(1e-9),TCAD_CONST(1.0),TCAD_CONST(1.0));
        DeviceSimulator second(3,1,1,TCAD_CONST(1e-9),TCAD_CONST(1.0),TCAD_CONST(1.0));
        first.set_newton_log_density_update("additive");
        require(second.get_newton_log_density_update()=="exponential","instance leaked");
        for (const std::string& bad : std::vector<std::string>{"","ADDITIVE"," exponential",std::string("additive\0",9)}) {
            bool rejected=false;
            try {first.set_newton_log_density_update(bad);} catch (const std::invalid_argument&) {rejected=true;}
            require(rejected && first.get_newton_log_density_update()=="additive","native invalid setter not atomic");
        }
        first.set_newton_log_density_update("exponential");
        require(first.get_newton_log_density_update()=="exponential","native reset failed");
        DeviceSimulatorDouble wrapper(3,1,1,1e-9,1.0,1.0);
        require(wrapper.get_newton_log_density_update()=="exponential","double facade default changed");
        wrapper.set_newton_log_density_update("additive");
        bool rejected=false;
        try {wrapper.set_newton_log_density_update("ADDITIVE");} catch (const std::invalid_argument&) {rejected=true;}
        require(rejected && wrapper.get_newton_log_density_update()=="additive","double facade lost policy or exception");
        std::cout<<"density mapping, positivity, nonfinite rejection, native API and isolation passed; bits="<<real_mantissa_bits()<<"\n";
        return 0;
    } catch (const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
}
