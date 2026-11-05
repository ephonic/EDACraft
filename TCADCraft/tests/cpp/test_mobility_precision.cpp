// Golden values come from Python Decimal, not from the native pow backend.
#include "mobility_model.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
using namespace tcad;
static real_t number(const std::string& text) {
#ifdef TCAD_USE_FLOAT128
    return strtoflt128(text.c_str(),nullptr);
#else
    return strtold(text.c_str(),nullptr);
#endif
}
int main(int argc,char** argv) {
    if(argc!=2) {std::cerr<<"Expected independent reference TSV\n";return 2;}
    std::ifstream input(argv[1]);
    if(!input) {std::cerr<<"Cannot read reference TSV\n";return 2;}
    int checks=0,failures=0,rows=0;
    auto require=[&](bool condition,const char* name) {
        ++checks;
        if(!condition) {++failures;std::cerr<<name<<"\n";}
    };
    const real_t tolerance=real_mantissa_bits()>80?TCAD_CONST(3e-31):
        real_mantissa_bits()>53?TCAD_CONST(2e-18):TCAD_CONST(3e-14);
    std::string line;
    while(std::getline(input,line)) {
        if(line.empty()||line[0]=='#') continue;
        std::istringstream stream(line);int model,electron;std::string t,nd,na,value,extra;
        if(!(stream>>model>>electron>>t>>nd>>na>>value)||(stream>>extra)) return 2;
        real_t expected=number(value);
        real_t actual=evaluate_mobility(model==1?MobilityModelType::ARORA:MobilityModelType::LOW_TEMP,
            electron,number(t),number(nd),number(na),0);
        require(isfinite_q(actual)&&abs_q(actual/expected-1)<=tolerance,"independent reference mismatch");
        ++rows;
    }
    if(rows!=12) return 2;
    // At 300 K the perturbation is resolvable in real_t but lost in double.
    const real_t delta=pow_q(TCAD_CONST(2.0),real_mantissa_bits()>80?-TCAD_CONST(70.0):-TCAD_CONST(54.0));
    if(real_mantissa_bits()>53) for(auto model : {MobilityModelType::ARORA,MobilityModelType::LOW_TEMP}) {
        for(bool electron : {true,false}) {
            real_t cold=evaluate_mobility(model,electron,TCAD_CONST(300.0),0,0,0);
            real_t hot=evaluate_mobility(model,electron,TCAD_CONST(300.0)*(1+delta),0,0,0);
            real_t offset=model==MobilityModelType::ARORA?
                (electron?TCAD_CONST(52.2):TCAD_CONST(49.9))*TCAD_CONST(1e-4):TCAD_CONST(0.0);
            real_t beta=model==MobilityModelType::ARORA?
                (electron?-TCAD_CONST(.66):-TCAD_CONST(2.05)):-TCAD_CONST(1.5);
            real_t slope=(hot-cold)/(cold-offset)/delta;
            real_t slope_tolerance=real_mantissa_bits()>80?TCAD_CONST(1e-8):TCAD_CONST(.02);
            require(hot<cold,"sub-double temperature signal was lost");
            require(abs_q(slope-beta)<=slope_tolerance,"temperature derivative disagrees with analytic limit");
        }
    }
    std::cout<<"{\"checks\":"<<checks<<",\"failures\":"<<failures<<",\"reference_cases\":"<<rows<<",\"mantissa_bits\":"<<real_mantissa_bits()<<"}\n";
    return failures?1:0;
}
