// Public fixture mutation only. The frozen Snapshot reads private state via
// -fno-access-control on this test translation unit, never in the core.
#define main restart_fixture_main
#include "native_restart_time_convergence.cpp"
#undef main
namespace allocation_fault {
long budget=-1;size_t calls=0;
void* allocate(size_t bytes){++calls;if(budget==0){budget=-1;throw std::bad_alloc();}if(budget>0)--budget;void* p=std::malloc(bytes?bytes:1);if(!p)throw std::bad_alloc();return p;}
}
void* operator new(size_t bytes){return allocation_fault::allocate(bytes);}
void* operator new[](size_t bytes){return allocation_fault::allocate(bytes);}
void operator delete(void* p) noexcept{std::free(p);}
void operator delete[](void* p) noexcept{std::free(p);}
void operator delete(void* p,size_t) noexcept{std::free(p);}
void operator delete[](void* p,size_t) noexcept{std::free(p);}
namespace {
real_t knot_width(int family){return family?TCAD_CONST(1e-20):TCAD_CONST(1e-18);}
Values event_roots(){const real_t v=TCAD_CONST(500.0)*TCAD_CONST(2.4e-7);return {v/TCAD_CONST(.001)*TCAD_CONST(1e-12),TCAD_CONST(1e-12)+(TCAD_CONST(.001)-v)/TCAD_CONST(.002)*TCAD_CONST(1.5e-12)};}
real_t knot_voltage(real_t t){return t<=TCAD_CONST(1e-12)?TCAD_CONST(.001)*t/TCAD_CONST(1e-12):TCAD_CONST(.001)-TCAD_CONST(.002)*(t-TCAD_CONST(1e-12))/TCAD_CONST(1.5e-12);}
real_t checkpoint(int mode,int family){const real_t root=event_roots().front();return mode==0?root:mode==1?root-TCAD_CONST(3.7)*knot_width(family):mode==2?root+TCAD_CONST(3.7)*knot_width(family):TCAD_CONST(1.37e-12);}
Values knot_times(int family,int mode,bool manual){
    Values knots;for(int i=0;i<=10;++i)knots.push_back(i*TCAD_CONST(.25e-12));
    for(real_t root:event_roots()){knots.push_back(root);if(manual){knots.push_back(root-knot_width(family));knots.push_back(root+knot_width(family));}}
    knots.push_back(checkpoint(mode,family));std::sort(knots.begin(),knots.end());knots.erase(std::unique(knots.begin(),knots.end()),knots.end());return knots;
}
std::unique_ptr<DeviceSimulator> knot_fixture(int dim,bool log,int level,int family,int mode,bool manual){
    auto s=fixed_fixture(dim,log,2,level);s->set_ferroelectric_builtin_field(TCAD_CONST(-500.0));
    const Values knots=knot_times(family,mode,manual);Values voltages;for(real_t t:knots)voltages.push_back(knot_voltage(t));
    std::map<size_t,Values> offsets;for(size_t k=0;k<(dim==3?3u:1u);++k)for(size_t j=0;j<3;++j)offsets[2+3*(j+3*k)]=voltages;
    s->set_transient_voltage_waveforms(knots,offsets);s->set_transient_nls_event_control(!manual,knot_width(family));return s;
}
bool has_sides(const std::vector<SimulationResult>& full,int family){
    for(real_t root:event_roots())for(int side:{-1,0,1}){
        const real_t wanted=root+side*knot_width(family);
        if(std::count_if(full.begin(),full.end(),[&](const SimulationResult& r){return tcad::abs_q(r.time-wanted)<TCAD_CONST(1e-40);})!=1)return false;
    }return true;
}
void metadata(int dim,bool log,int level,int family,int mode){
    std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"mode\":2,\"nls\":1,\"natural\":0,\"variant\":1,\"family\":"<<family<<",\"level\":"<<level<<",\"checkpoint_mode\":"<<mode;
    std::cout<<",\"builtin\":";values({TCAD_CONST(-500.0)});std::cout<<",\"width\":";values({knot_width(family)});std::cout<<",\"roots\":";values(event_roots());std::cout<<",\"knots\":";values(knot_times(family,mode,false));
}
bool probe(){
    auto s=knot_fixture(2,false,0,0,0,false);const auto full=s->solve_transient();const bool pass=accepted(full)&&has_sides(full,0);
    metadata(2,false,0,0,0);std::cout<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(s->transient_attempt_history());std::cout<<",\"side_samples\":"<<has_sides(full,0)<<",\"passed\":"<<pass<<"}"<<std::endl;return pass;
}
bool knot_case(int dim,bool log,int level,int family,int mode){
    auto s=knot_fixture(dim,log,level,family,mode,false);const Snapshot entered(*s);const auto full=s->solve_transient();const auto ft=s->transient_attempt_history();const Snapshot finished(*s);
    if(!accepted(full)||!has_sides(full,family))throw std::runtime_error("event coincident with waveform knot lost a side sample");
    const real_t wanted=checkpoint(mode,family);const auto found=std::find_if(full.begin(),full.end(),[&](const SimulationResult& r){return tcad::abs_q(r.time-wanted)<TCAD_CONST(1e-40);});
    if(found==full.end())throw std::runtime_error("arbitrary checkpoint not retained");
    const size_t index=found-full.begin();auto tail_sim=knot_fixture(dim,log,level,family,mode,false);seed(*tail_sim,*found,finished.play,2,found->time);
    const Snapshot entry(*tail_sim);const auto tail=tail_sim->solve_transient();const auto tt=tail_sim->transient_attempt_history();const Snapshot after(*tail_sim);
    auto control=knot_fixture(dim,log,level,family,mode,true);const auto manual=control->solve_transient();const auto mt=control->transient_attempt_history();
    const bool passed=accepted(tail)&&accepted(manual)&&has_sides(manual,family)&&tail.size()+index==full.size()&&returned_timeline_matches(full,ft)&&returned_timeline_matches(tail,tt)&&returned_timeline_matches(manual,mt)
        && entered.phi==finished.phi&&entered.n==finished.n&&entered.p==finished.p&&entered.contacts==finished.contacts
        && entry.P==found->P&&after.P==tail.back().P&&entry.phi==after.phi&&entry.n==after.n&&entry.p==after.p&&entry.contacts==after.contacts;
    metadata(dim,log,level,family,mode);std::cout<<",\"index\":"<<index<<",\"cut\":";values({found->time});
    std::cout<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(ft);std::cout<<",\"tail\":";history(tail);std::cout<<",\"tail_trace\":";trace(tt);
    std::cout<<",\"manual\":";history(manual);std::cout<<",\"manual_trace\":";trace(mt);std::cout<<",\"entry\":";snapshot(entry);std::cout<<",\"after\":";snapshot(after);std::cout<<",\"passed\":"<<passed<<"}"<<std::endl;return passed;
}
void knot_guards(){
    auto s=knot_fixture(2,false,0,0,0,false);const Snapshot original(*s);s->begin_reliability_transaction();const auto h=s->solve_transient();s->rollback_reliability_transaction();
    if(!accepted(h)||!has_sides(h,0)||!(Snapshot(*s)==original))throw std::runtime_error("knot event transaction rollback failed");
    auto measure=knot_fixture(2,false,0,0,0,false);allocation_fault::calls=0;const auto baseline=measure->solve_transient();const size_t total=allocation_fault::calls;
    if(!accepted(baseline))throw std::runtime_error("allocation baseline failed");int caught=0;
    for(size_t limit:{total/10,total/2,total-2}){
        auto faulted=knot_fixture(2,false,0,0,0,false);const Snapshot before(*faulted);bool threw=false;allocation_fault::budget=static_cast<long>(limit);
        try{faulted->solve_transient();}catch(const std::bad_alloc&){threw=true;}allocation_fault::budget=-1;
        if(!threw||!(Snapshot(*faulted)==before))throw std::runtime_error("knot event exception did not restore state");
        for(const auto& group:faulted->transient_attempt_history())for(const auto& trial:group.trials)if(group.accepted||trial.retained)throw std::runtime_error("knot event exception retained dwell");
        ++caught;
    }
    std::cout<<"{\"transaction_rollback\":true,\"allocation_faults_restored\":"<<caught<<"}"<<std::endl;
}
}
int main(int argc,char** argv){try{
    if(argc==2&&std::string(argv[1])=="--probe")return probe()?0:3;
    if(argc==2&&std::string(argv[1])=="--guards"){knot_guards();return 0;}
    bool passed=true;for(int d:{2,3})for(bool log:{false,true})for(int f:{0,1})for(int mode:{0,1,2,3})for(int level:{0,1,2,3}){
        if(mode!=0&&level!=0&&level!=3)continue;
        passed=knot_case(d,log,level,f,mode)&&passed;
    }knot_guards();return passed?0:1;
}catch(const std::exception& e){std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}}
