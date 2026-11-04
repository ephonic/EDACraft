#define DSIM_SELECTION_CHECKS_ENABLED 1
#include "dsim/runtime.hpp"
#include <array>
#include <cassert>
#include <sstream>
using namespace dsim;

// Retire the middle owner's short and heap-backed strings, preserving the
// other owners' report order. Stop with reports pending to exercise deep copies.
int main() {
    const std::string large(257,'L');
    const std::string expected="first-0 time=0\n"+large+"0 time=0\nfirst-2 time=0\n"+large+"2 time=0\nreplacement time=0\n";
    unsigned checks=0;
    for(unsigned budget=0;budget<10;++budget) {
        Sim s;auto counts=std::make_shared<std::array<int,3>>();s.register_state(counts);
        int signal=s.signal(1,false);s.set(signal,V(0));
        std::array<int,3> ids{};
        for(int owner=0;owner<3;++owner)ids[owner]=s.process([&,owner] {
            if((*counts)[owner]++==0) {
                s.selection_report("first-"+std::to_string(owner));
                s.selection_report(large+std::to_string(owner));
                s.wait(ids[owner],{{signal,0}});
            } else if(owner==1)s.selection_report("replacement");
        });
        // Only the middle process watches the signal which changes.
        int idle=s.signal(1,false);s.set(idle,V(0));
        // Replace the outer owners' waits from a later Active callback.
        int retire=s.process([&] {
            s.wait(ids[0],{{idle,0}});s.wait(ids[2],{{idle,0}});
            s.set(signal,V(1));
        });
        for(int id:ids)s.enqueue(id);
        s.enqueue(retire);
        std::ostringstream output;auto* original=std::cout.rdbuf(output.rdbuf());
        s.limit=budget;
        try{s.run_until(0);}catch(const std::runtime_error& e) {
            assert(std::string(e.what()).find("execution budget exhausted")!=std::string::npos);
        }
        s.limit=1000;
        auto cp=s.checkpoint();const std::string prefix=output.str();
        for(int mode=0;mode<3;++mode) {
            if(mode)s.restore(cp);
            output.str(prefix);output.clear();
            if(mode==0)s.run_until(0);
            else {
                bool accept=mode==1;
                assert(s.predict_until(0,[](Sim&){},[accept](const Sim&){return accept;},[](Sim&){})==accept);
            }
            assert(output.str()==expected);
            assert((*counts)[0]==1&&(*counts)[1]==2&&(*counts)[2]==1);
            ++checks;
        }
        std::cout.rdbuf(original);
    }
    std::cout<<"PASS "<<checks<<" pending-report budget/checkpoint/prediction checks\n";
}
