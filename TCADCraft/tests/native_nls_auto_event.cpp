// Automatic event integration uses only public setters; private access is
// read-only through the frozen475 Snapshot observer in this test TU.
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
real_t voltage(real_t t){return t<=TCAD_CONST(1e-12)?TCAD_CONST(.001)*t/TCAD_CONST(1e-12):TCAD_CONST(.001)-TCAD_CONST(.002)*(t-TCAD_CONST(1e-12))/TCAD_CONST(1.5e-12);}
real_t builtin(int variant){return variant?TCAD_CONST(-500.0):TCAD_CONST(1000.0);}
real_t width(int family){return family?TCAD_CONST(1e-20):TCAD_CONST(1e-18);}
Values roots(int variant){
    const real_t value=-builtin(variant)*TCAD_CONST(2.4e-7);Values result;
    if(value>0 && value<TCAD_CONST(.001))result.push_back(value/TCAD_CONST(.001)*TCAD_CONST(1e-12));
    result.push_back(TCAD_CONST(1e-12)+(TCAD_CONST(.001)-value)/TCAD_CONST(.002)*TCAD_CONST(1.5e-12));return result;
}
std::unique_ptr<DeviceSimulator> automatic(int dim,bool log,int level,int variant,int family,bool manual){
    auto s=fixed_fixture(dim,log,2,level);s->set_ferroelectric_builtin_field(builtin(variant));Values knots;
    for(int i=0;i<=10;++i)knots.push_back(i*TCAD_CONST(.25e-12));
    if(manual)for(real_t root:roots(variant)){knots.push_back(root-width(family));knots.push_back(root+width(family));}
    std::sort(knots.begin(),knots.end());Values v;for(auto t:knots)v.push_back(voltage(t));std::map<size_t,Values> offsets;
    for(size_t k=0;k<(dim==3?3u:1u);++k)for(size_t j=0;j<3;++j)offsets[2+3*(j+3*k)]=v;
    s->set_transient_voltage_waveforms(knots,offsets);s->set_transient_nls_event_control(!manual,width(family));return s;
}
bool run_case(int dim,bool log,int level,int variant,int family){
    auto s=automatic(dim,log,level,variant,family,false);const Snapshot entry(*s);
    const auto full=s->solve_transient();const auto ft=s->transient_attempt_history();const Snapshot after(*s);
    if(!accepted(full))throw std::runtime_error("automatic full failed");
    const real_t desired=roots(variant).front()-width(family);
    const auto found=std::find_if(full.begin(),full.end(),[&](const SimulationResult& r){return tcad::abs_q(r.time-desired)<TCAD_CONST(1e-40);});
    if(found==full.end())throw std::runtime_error("automatic incoming side missing");
    const size_t index=found-full.begin();const auto cut=found->time;auto tail_sim=automatic(dim,log,level,variant,family,false);
    seed(*tail_sim,*found,after.play,2,cut);const Snapshot te(*tail_sim);const auto tail=tail_sim->solve_transient();const auto tt=tail_sim->transient_attempt_history();const Snapshot ta(*tail_sim);
    auto control=automatic(dim,log,level,variant,family,true);const auto manual=control->solve_transient();const auto mt=control->transient_attempt_history();
    bool good=accepted(tail)&&accepted(manual)&&tail.size()+index==full.size()&&returned_timeline_matches(full,ft)&&returned_timeline_matches(tail,tt)&&returned_timeline_matches(manual,mt)
        && entry.phi==after.phi&&entry.n==after.n&&entry.p==after.p&&entry.contacts==after.contacts&&tail.front().P==found->P&&te.P==found->P&&ta.P==tail.back().P
        && ta.phi==te.phi&&ta.n==te.n&&ta.p==te.p&&ta.contacts==te.contacts;
    std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"mode\":2,\"nls\":1,\"natural\":0,\"level\":"<<level<<",\"variant\":"<<variant<<",\"family\":"<<family;
    std::cout<<",\"builtin\":";values({builtin(variant)});std::cout<<",\"width\":";values({width(family)});std::cout<<",\"roots\":";values(roots(variant));
    std::cout<<",\"index\":"<<index<<",\"cut\":";values({cut});std::cout<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(ft);
    std::cout<<",\"tail\":";history(tail);std::cout<<",\"tail_trace\":";trace(tt);std::cout<<",\"manual\":";history(manual);std::cout<<",\"manual_trace\":";trace(mt);
    std::cout<<",\"entry\":";snapshot(te);std::cout<<",\"after\":";snapshot(ta);std::cout<<",\"passed\":"<<good<<"}"<<std::endl;return good;
}
void guards(){
    int count=0;
    for(int mode=0;mode<8;++mode){auto s=automatic(2,false,0,0,0,false);const size_t N=s->npts();
        if(mode==0)s->set_ferroelectric_depol(TCAD_CONST(25.0));
        if(mode==1){std::vector<char> mask(N,1);mask[4]=0;s->set_ferroelectric_params(mask,TCAD_CONST(1e8),TCAD_CONST(1e12));}
        if(mode==2)s->clear_transient_voltage_waveforms();
        if(mode==3)s->set_transient_nls_error_control(true,TCAD_CONST(.01),TCAD_CONST(1e-8),TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8),TCAD_CONST(1e-17),20);
        if(mode==4)s->set_transient_nls_event_control(true,TCAD_CONST(1e-12));
        if(mode==5)s->set_ferroelectric_model(1);
        // The public setter merges contacts; add an interior contact to
        // construct an unsupported topology without private-state mutation.
        if(mode==6)s->set_dirichlet_potential({{4,TCAD_CONST(0.0)}});
        if(mode==7)s->set_transient_nls_event_control(true,TCAD_CONST(1e-50));
        const Snapshot before(*s);bool rejected=false;try{s->solve_transient();}catch(const std::invalid_argument&){rejected=true;}
        if(!rejected || !(Snapshot(*s)==before) || !s->transient_attempt_history().empty())
            throw std::runtime_error("scope preflight failed for mode "+std::to_string(mode));
        ++count;
    }
    auto s=automatic(2,false,0,0,0,false);for(real_t bad:{TCAD_CONST(0.0),TCAD_CONST(-1.0),static_cast<real_t>(std::numeric_limits<double>::infinity())}){
        bool rejected=false;try{s->set_transient_nls_event_control(true,bad);}catch(const std::invalid_argument&){rejected=true;}
        if(!rejected)throw std::runtime_error("invalid width accepted");
        ++count;
    }
    // Public transaction rollback must recover accepted material memory, and
    // a rejected width setter must not disable the previously valid controller.
    const Snapshot before(*s);s->begin_reliability_transaction();const auto history=s->solve_transient();s->rollback_reliability_transaction();
    if(!accepted(history)||!(Snapshot(*s)==before))throw std::runtime_error("automatic transaction rollback failed");
    auto failing=automatic(2,false,0,0,0,false);failing->set_gummel_max_iter(1);const Snapshot failed_entry(*failing);
    const auto failed=failing->solve_transient();
    if(failed.back().converged || failed.back().accepted_dt!=0 || failing->fe_polarization()!=failed.back().P || Snapshot(*failing).contacts!=failed_entry.contacts || Snapshot(*failing).phi!=failed_entry.phi)
        throw std::runtime_error("ordinary solver failure did not retain accepted state");
    auto measure=automatic(2,false,0,0,0,false);allocation_fault::calls=0;const auto measured=measure->solve_transient();const size_t total=allocation_fault::calls;
    if(!accepted(measured))throw std::runtime_error("allocation baseline failed");
    int caught=0;
    for(size_t limit:{total/10,total/2,total-2}){
        auto faulted=automatic(2,false,0,0,0,false);const Snapshot entered(*faulted);bool threw=false;
        allocation_fault::budget=static_cast<long>(limit);
        try{faulted->solve_transient();}catch(const std::bad_alloc&){threw=true;}
        allocation_fault::budget=-1;
        if(!threw || !(Snapshot(*faulted)==entered))throw std::runtime_error("exception did not restore material/contact state");
        for(const auto& group:faulted->transient_attempt_history())for(const auto& trial:group.trials)if(group.accepted || trial.retained)throw std::runtime_error("exception retained physical dwell");
        ++caught;
    }
    std::cout<<"{\"scope_rejections\":"<<count<<",\"transaction_rollback\":true,\"solver_failure_restored\":true,\"allocation_faults_restored\":"<<caught<<"}"<<std::endl;
}
}
int main(int argc,char** argv){bool pass=true;try{
    if(argc==2 && std::string(argv[1])=="--guards"){guards();return 0;}
    for(int d:{2,3})for(bool log:{false,true})for(int v:{0,1})for(int f:{0,1})for(int l:{0,1,2,3})pass=run_case(d,log,l,v,f)&&pass;
    guards();
}catch(const std::exception& e){std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}return pass?0:1;}
