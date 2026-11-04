#define DSIM_NAMED_EVENTS_ENABLED 1
#define DSIM_WAIT_ORDER_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
    Sim s;int a=s.named_event(),b=s.named_event(),c=s.named_event(),x=s.named_event();
    auto counts=std::make_shared<std::pair<int,int>>(0,0);s.register_state(counts);
    int site=-1;
    int p=s.process([&]{if(s.wait_order_succeeded(site))++counts->first;else ++counts->second;});
    site=s.add_wait_order_site(p,{a,b,c});
    int ordinary=s.add_wait_site(p,{{x,0}});
    int repeated=s.add_wait_order_site(p,{a,a,b});
    s.arm_wait(site);s.trigger_event(x);s.trigger_event(a);s.trigger_event(a);
    auto partial=s.checkpoint();
    s.trigger_event(b);s.trigger_event(c);s.trigger_event(b);s.run();
    assert(*counts==std::make_pair(1,0));
    s.restore(partial);assert(*counts==std::make_pair(0,0));
    s.trigger_event(c);s.run();assert(*counts==std::make_pair(0,1));
    s.arm_wait(site);s.trigger_event_nba(a);s.trigger_event_nba(b);s.trigger_event_nba(c);
    auto queued=s.checkpoint();s.run();assert(*counts==std::make_pair(1,1));
    s.restore(queued);s.run();assert(*counts==std::make_pair(1,1));
    s.arm_wait(site);s.trigger_event_after(a,2);s.trigger_event_after(b,3);s.trigger_event_after(c,4);
    bool accepted=s.predict_until(4,[](Sim&){},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted&&s.prediction_stats.rollbacks==1&&*counts==std::make_pair(2,1));
    // A later wait in the same process invalidates the ordered subscription.
    s.arm_wait(site);s.trigger_event(a);s.arm_wait(ordinary);
    s.trigger_event(c);s.trigger_event(b);s.run();assert(*counts==std::make_pair(2,1));
    // A rearm starts from zero and cannot reuse a successful prior sequence.
    s.arm_wait(site);s.trigger_event(b);s.run();assert(*counts==std::make_pair(2,2));
    site=repeated;
    s.arm_wait(repeated);s.trigger_event(a);s.trigger_event(b);
    assert(!s.wait_order_succeeded(repeated));s.run();assert(*counts==std::make_pair(2,3));
    s.arm_wait(repeated);s.trigger_event(a);s.trigger_event(a);s.trigger_event(b);
    assert(s.wait_order_succeeded(repeated));s.run();assert(*counts==std::make_pair(3,3));
    std::cout<<"PASS wait_order: occurrence ordering, duplicate names, generations, NBA, snapshots and rollback\n";
}
