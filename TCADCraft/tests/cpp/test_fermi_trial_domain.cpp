// Typed native state-domain rejection, budgets, cache and fatal error boundary.
#include "fermi_newton.h"
#include <iostream>
#include <string>
using namespace tcad;
static void check(bool good,const char* why) {if(!good)throw std::runtime_error(why);}
struct Context {
    int mode=0,calls=0,rejected=0;double last=0;
    static int callback(void* pointer,const std::vector<double>& x,std::vector<double>& r,double* merit) {
        auto& c=*static_cast<Context*>(pointer);++c.calls;c.last=x[0];
        if(c.mode==1 && x[0]<-2e-8) {++c.rejected;throw FermiStateDomainError("probe domain");}
        if(c.mode==2)throw FermiStateDomainError("initial domain");
        if(c.mode==3 && x[0]>1.5)throw std::invalid_argument("fatal schema");
        if(c.mode==4 && c.calls==2)throw std::runtime_error("fatal physics");
        if((c.mode==0 || c.mode==5) && x[0]>1.5) {++c.rejected;throw FermiStateDomainError("trial domain");}
        r={c.mode==1 ? x[0]-.1 : std::exp(x[0])-2};*merit=std::abs(r[0])/1e-12;return 0;
    }
};
int main() {
    try {
        int checks=0;
        for(int mode:{0,1}) {
            Context c;c.mode=mode;
            auto result=native_fermi_newton_raw({mode==1?0.:-4.},{-5.},{5.},400,Context::callback,&c);
            check(std::abs(result[0][0]-(mode==1?.1:std::log(2.)))<1e-12,"wrong root");
            check(c.rejected>0 && result[1][2]>=c.rejected,"domain rejection not counted");
            check(result[1][0]==c.calls && c.last==result[0][0],"budget or accepted cache mismatch");++checks;
        }
        for(int mode:{2,3,4}) {
            Context c;c.mode=mode;bool failed=false;
            try {native_fermi_newton_raw({-4.},{-5.},{5.},400,Context::callback,&c);}
            catch(const std::exception& error) {
                const std::string expected=mode==2?"initial domain":mode==3?"fatal schema":"fatal physics";
                check(error.what()==expected,"unrelated error was swallowed");failed=true;
            }
            check(failed,"fatal failure missing");if(mode==2)check(c.calls==1,"initial state retried");++checks;
        }
        {Context c;c.mode=5;bool failed=false;
            try {native_fermi_newton_raw({-4.},{-5.},{5.},4,Context::callback,&c);}
            catch(const std::runtime_error& error) {check(std::string(error.what()).find("budget exhausted")!=std::string::npos,"wrong budget failure");failed=true;}
            check(failed && c.calls==4,"rejected callback bypassed evaluation budget");++checks;
        }
        std::cout<<"passed "<<checks<<" native trial-domain checks\n";return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
