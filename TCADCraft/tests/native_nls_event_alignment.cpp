// Reuse the frozen public fixture and read-only observer from stage475.
// -fno-access-control is used only for this test translation unit.
#define main restart_fixture_main
#include "native_restart_time_convergence.cpp"
#undef main
namespace {
constexpr real_t reversal_time=TCAD_CONST(1.93e-12);
constexpr real_t bracket_half_width=TCAD_CONST(1e-18);
real_t original_voltage(real_t t){
    return t<=TCAD_CONST(1e-12)?TCAD_CONST(.001)*t/TCAD_CONST(1e-12):
        TCAD_CONST(.001)-TCAD_CONST(.002)*(t-TCAD_CONST(1e-12))/TCAD_CONST(1.5e-12);
}
Values event_knots(int schedule){
    if(schedule==0)return {0,TCAD_CONST(1e-12),final_time};
    Values times;
    for(int i=0;i<=10;++i)times.push_back(i*TCAD_CONST(.25e-12));
    if(schedule==2)times.push_back(reversal_time);
    if(schedule==3){times.push_back(reversal_time-bracket_half_width);times.push_back(reversal_time+bracket_half_width);}
    std::sort(times.begin(),times.end());return times;
}
std::unique_ptr<DeviceSimulator> event_fixture(int dimension,bool log,int level,int schedule){
    auto s=fixed_fixture(dimension,log,2,level);
    if(schedule){
        const auto knots=event_knots(schedule);Values voltages;
        for(real_t t:knots)voltages.push_back(original_voltage(t));
        std::map<size_t,Values> waveforms;
        for(size_t k=0;k<(dimension==3?3u:1u);++k)for(size_t j=0;j<3;++j)waveforms[2+3*(j+3*k)]=voltages;
        s->set_transient_voltage_waveforms(knots,waveforms);
    }
    return s;
}
bool event_alignment(int dimension,bool log,int level,int schedule){
    auto s=event_fixture(dimension,log,level,schedule);
    const Snapshot entry(*s);const auto full=s->solve_transient();const auto full_trace=s->transient_attempt_history();const Snapshot after(*s);
    if(!accepted(full))throw std::runtime_error("event-aligned full trajectory rejected");
    const real_t desired_cut=schedule==2?reversal_time:schedule==3?reversal_time-bracket_half_width:TCAD_CONST(1.75e-12);
    const auto found=std::find_if(full.begin(),full.end(),[&](const SimulationResult& r){return tcad::abs_q(r.time-desired_cut)<=TCAD_CONST(1e-30)*final_time;});
    if(found==full.end())throw std::runtime_error("event restart cut missing from actual accepted trajectory");
    const real_t cut=found->time;
    const size_t index=found-full.begin();auto tail_sim=event_fixture(dimension,log,level,schedule);
    seed(*tail_sim,*found,after.play,2,cut);const Snapshot tail_entry(*tail_sim);
    const auto tail=tail_sim->solve_transient();const auto tail_trace=tail_sim->transient_attempt_history();const Snapshot tail_after(*tail_sim);
    bool good=accepted(tail) && index+tail.size()==full.size() && returned_timeline_matches(full,full_trace) && returned_timeline_matches(tail,tail_trace)
        && after.phi==entry.phi && after.n==entry.n && after.p==entry.p && after.contacts==entry.contacts
        && tail.front().P==found->P && tail_entry.P==found->P && tail_after.P==tail.back().P
        && tail_after.phi==tail_entry.phi && tail_after.n==tail_entry.n && tail_after.p==tail_entry.p && tail_after.contacts==entry.contacts;
    std::cout<<"{\"dimension\":"<<dimension<<",\"logarithmic\":"<<log<<",\"mode\":2,\"nls\":1,\"natural\":0,\"level\":"<<level<<",\"schedule\":"<<schedule;
    std::cout<<",\"knots\":";values(event_knots(schedule));
    Values voltages;for(real_t t:event_knots(schedule))voltages.push_back(original_voltage(t));
    std::cout<<",\"voltages\":";values(voltages);
    std::cout<<",\"index\":"<<index<<",\"cut\":";values({cut});
    std::cout<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(full_trace);
    std::cout<<",\"tail\":";history(tail);std::cout<<",\"tail_trace\":";trace(tail_trace);
    std::cout<<",\"entry\":";snapshot(tail_entry);std::cout<<",\"after\":";snapshot(tail_after);
    std::cout<<",\"passed\":"<<good<<"}"<<std::endl;return good;
}
}
int main(){
    bool passed=true;
    try{for(int d:{2,3})for(bool log:{false,true})for(int schedule:{0,1,2,3})for(int level:{0,1,2,3})passed=event_alignment(d,log,level,schedule)&&passed;}
    catch(const std::exception& e){std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return passed?0:1;
}
