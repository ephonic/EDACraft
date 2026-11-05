// Extend the frozen three-level fixture without changing its helpers.
#define main three_level_fixture_main
#include "native_restart_time_convergence.cpp"
#undef main
int main(){
    bool passed=true;
    try{for(int d:{2,3})for(bool log:{false,true})for(int mode:{0,1,2,3})passed=convergence(d,log,mode,3)&&passed;}
    catch(const std::exception& e){std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return passed?0:1;
}
