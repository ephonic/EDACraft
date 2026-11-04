#define DSIM_NAMED_EVENTS_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
struct Counts {int occurrences=0,queries=0,rises=0,falls=0,fresh=0,batches=0;};
int main() {
    Sim s;
    auto counts=std::make_shared<Counts>();s.register_state(counts);
    int event=s.named_event(),batch=s.named_event();
    assert(!s.event_triggered(event));
    int occurrence_site=-1,query_site=-1,rise_site=-1,fall_site=-1,fresh_site=-1,batch_site=-1;
    int occurrence=s.process([&]{++counts->occurrences;s.arm_wait(occurrence_site);});
    int query=s.process([&]{++counts->queries;s.arm_wait(query_site);});
    int rise=s.process([&]{++counts->rises;s.arm_wait(rise_site);});
    int fall=s.process([&]{++counts->falls;s.arm_wait(fall_site);});
    int fresh=s.process([&]{++counts->fresh;s.arm_wait(fresh_site);});
    int batch_waiter=s.process([&]{++counts->batches;s.arm_wait(batch_site);});
    occurrence_site=s.add_wait_site(occurrence,{{event,0}});
    query_site=s.add_wait_site(query,{{event,3}});
    rise_site=s.add_wait_site(rise,{{event,3}});
    fall_site=s.add_wait_site(fall,{{event,4}});
    fresh_site=s.add_wait_site(fresh,{{event,3}});
    batch_site=s.add_wait_site(batch_waiter,{{batch,0}});
    for(int site:{occurrence_site,query_site,rise_site,fall_site,batch_site})s.arm_wait(site);
    s.trigger_event(event);s.trigger_event(event);
    assert(s.event_triggered(event));s.run_until(1);
    assert(counts->occurrences==1&&counts->queries==1&&counts->rises==1&&counts->falls==0);
    assert(!s.event_triggered(event));
    s.arm_wait(fresh_site);s.trigger_event(event);s.run_until(1);
    assert(counts->occurrences==2&&counts->fresh==1&&counts->queries==1&&counts->rises==1);
    // A query armed at true keeps that sampled baseline after time advances.
    // A newly armed query at false sees the next occurrence.
    s.trigger_event_after(event,4);
    auto pending=s.checkpoint();
    bool accepted=s.predict_until(5,[](Sim&){},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted&&s.prediction_stats.rollbacks==1&&counts->occurrences==3);
    assert(s.event_triggered(event)&&counts->queries==1&&counts->falls==0);
    s.restore(pending);assert(s.now==1&&counts->occurrences==2&&s.event_triggered(event));
    s.run_until(2);assert(!s.event_triggered(event));
    s.run_until(5);assert(counts->occurrences==3&&s.event_triggered(event));
    s.trigger_event_nba(batch);s.trigger_event_nba(batch);s.run();
    assert(counts->batches==1&&s.event_triggered(batch));
    s.trigger_event_nba(batch);auto queued=s.checkpoint();s.run();assert(counts->batches==2);
    s.restore(queued);assert(counts->batches==1);s.run();assert(counts->batches==2);
    std::cout<<"PASS named event kernel: occurrence/query baselines, NBA batches, delayed triggers and rollback\n";
}
