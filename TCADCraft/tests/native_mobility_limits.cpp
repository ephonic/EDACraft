// Independent limiting cases of the public mobility_model.h contract.
#include "mobility_model.h"
#include <iostream>
using namespace tcad;
int main() {
    int checks=0, failures=0;
    auto near=[&](real_t got, real_t expected, const char* name) {
        ++checks;
        if (!isfinite_q(got) || abs_q(got-expected)>TCAD_CONST(3e-14)*abs_q(expected)) {
            ++failures; std::cerr<<name<<": got="<<(double)got<<" expected="<<(double)expected<<"\n";
        }
    };
    for (bool electron : {true,false}) {
        real_t lo=electron?TCAD_CONST(52.2):TCAD_CONST(49.9);
        real_t hi=electron?TCAD_CONST(1417.0):TCAD_CONST(470.5);
        real_t ref=electron?TCAD_CONST(9.68e22):TCAD_CONST(2.23e23); // m^-3
        near(evaluate_mobility(MobilityModelType::ARORA,electron,TCAD_CONST(300.0),0,0,0),hi*TCAD_CONST(1e-4),"zero doping maximum");
        near(evaluate_mobility(MobilityModelType::ARORA,electron,TCAD_CONST(300.0),ref,0,0),(hi+lo)*TCAD_CONST(5e-5),"reference doping midpoint");
        near(evaluate_mobility(MobilityModelType::ARORA,electron,TCAD_CONST(300.0),TCAD_CONST(1e100),0,0),lo*TCAD_CONST(1e-4),"high doping floor");
        real_t t=TCAD_CONST(600.0);
        real_t beta=electron?-TCAD_CONST(.66):-TCAD_CONST(2.05);
        near(evaluate_mobility(MobilityModelType::ARORA,electron,t,ref,0,0),(lo+(hi-lo)*TCAD_CONST(.5)*pow_q(TCAD_CONST(2.0),beta))*TCAD_CONST(1e-4),"temperature convention");
        near(evaluate_mobility(MobilityModelType::ARORA,electron,t,ref/2,ref/2,0),evaluate_mobility(MobilityModelType::ARORA,electron,t,ref,0,0),"compensated total dopants");
        for (real_t temperature : {TCAD_CONST(150.0),TCAD_CONST(300.0),TCAD_CONST(600.0)}) {
            real_t previous=TCAD_CONST(100.0);
            for (real_t density : {TCAD_CONST(0.0),ref/10,ref,10*ref,TCAD_CONST(1e100)}) {
                real_t mu=evaluate_mobility(MobilityModelType::ARORA,electron,temperature,density,0,0);
                ++checks;
                if (!isfinite_q(mu) || mu<lo*TCAD_CONST(1e-4) || mu>previous) {++failures;std::cerr<<"monotonic/floor limit failed\n";}
                previous=mu;
                near(evaluate_mobility(MobilityModelType::CONSTANT,electron,temperature,density,0,TCAD_CONST(.0123)),TCAD_CONST(.0123),"constant mobility control");
            }
        }
    }
    std::cout<<"{\"checks\":"<<checks<<",\"failures\":"<<failures<<",\"mantissa_bits\":"<<real_mantissa_bits()<<"}\n";
    return failures?1:0;
}
