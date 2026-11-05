// Analytic one-sided roots, impossible domains, strict budgets and fatal errors.
#include "fermi_newton.h"
#include <iostream>
#include <string>
using namespace tcad;
static void check(bool good,const char* why) {if(!good)throw std::runtime_error(why);}
struct Context {
    int sign=1,calls=0,rejected=0,fatal_call=0;bool nonlinear=false,isolated=false,invalid_initial=false;
    double last=0;
    static int callback(void* pointer,const std::vector<double>& x,std::vector<double>& r,double* merit) {
        auto& c=*static_cast<Context*>(pointer);++c.calls;c.last=x[0];
        if(c.calls==c.fatal_call)throw std::invalid_argument("fatal fallback schema");
        if(c.invalid_initial || (c.isolated?x[0]!=0:c.sign*x[0]<-1e-15)) {
            ++c.rejected;throw FermiStateDomainError("one-sided physical domain");
        }
        r={c.nonlinear?std::exp(c.sign*x[0])-std::exp(.1):c.sign*x[0]-.1};
        *merit=std::abs(r[0])/1e-11;return 0;
    }
};
int main() {
    try {
        int checks=0;
        for(int sign:{-1,1}) for(bool nonlinear:{false,true}) {
            Context c;c.sign=sign;c.nonlinear=nonlinear;
            auto result=native_fermi_newton_raw({0.},{-1.},{1.},400,Context::callback,&c);
            check(std::abs(result[0][0]-.1*sign)<1e-10,"wrong one-sided analytic root");
            check(c.rejected>=16 && result[1][2]>=c.rejected,"unaccounted domain rejections");
            check(result[1][0]==c.calls && c.last==result[0][0],"accepted cache or budget mismatch");++checks;
        }
        {Context c;c.isolated=true;bool failed=false;
            try {native_fermi_newton_raw({0.},{-1.},{1.},400,Context::callback,&c);}
            catch(const std::runtime_error& e) {check(std::string(e.what())=="native Newton constitutive derivative domain exhausted","wrong impossible-domain failure");failed=true;}
            check(failed && c.calls==49 && c.rejected==48,"impossible domain accepted or retried without bound");++checks;
        }
        for(int budget:{18,19}) {
            Context c;c.sign=-1;bool failed=false;
            try {native_fermi_newton_raw({0.},{-1.},{1.},budget,Context::callback,&c);}
            catch(const std::runtime_error& e) {check(std::string(e.what())=="native Newton evaluation budget exhausted","wrong budget failure");failed=true;}
            check(failed && c.calls==budget,"fallback bypassed max_nfev");++checks;
        }
        for(int fatal_call:{18,19}) {
            Context c;c.sign=-1;c.fatal_call=fatal_call;bool failed=false;
            try {native_fermi_newton_raw({0.},{-1.},{1.},400,Context::callback,&c);}
            catch(const std::invalid_argument& e) {check(std::string(e.what())=="fatal fallback schema","unrelated error swallowed");failed=true;}
            check(failed && c.calls==fatal_call,"fatal fallback retried");++checks;
        }
        {Context c;c.invalid_initial=true;bool failed=false;
            try {native_fermi_newton_raw({0.},{-1.},{1.},400,Context::callback,&c);}
            catch(const FermiStateDomainError&) {failed=true;}
            check(failed && c.calls==1,"invalid initial state recovered");++checks;
        }
        std::cout<<"passed "<<checks<<" one-sided domain checks\n";return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
