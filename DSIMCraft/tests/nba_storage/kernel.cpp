#define DSIM_COMPACT_NBA_STORAGE 1
#define DSIM_DELAYED_NBA_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#include "dsim/runtime.hpp"
#include <cassert>
#include <iostream>
using namespace dsim;

int main() {
    Sim s;
    int narrow=s.signal(3,false),wide=s.signal(64,false),two=s.signal_two_state(8);
    s.assign_nba(narrow,V(0xff,0x55,8));s.assign_nba(wide,V(0x25,0x12,8));
    s.assign_nba(two,V(0xff,0xf0,8));
    auto pending=s.checkpoint();s.run();
    assert(s.get(narrow).same(V(7,5,3))&&s.get(wide).same(V(0x25,0x12,64))&&s.get(two).same(V(15,0,8)));
    s.restore(pending);s.assign_nba(wide,V(0xabc,0,64));s.run();assert(s.get(wide).same(V(0xabc,0,64)));
    s.restore(pending);s.run();assert(s.get(wide).same(V(0x25,0x12,64)));

    // A selected RHS retains its original width: out-of-range selection is X.
    Sim parts;int d=parts.signal(16,false);parts.set(d,V(0,0,16));
    std::vector<Part> targets{{d,0,8,0},{d,8,8,8}};
    parts.assign_parts(targets,V(0xa5,0,8),true);targets[0].lo=4;
    auto partial=parts.checkpoint();parts.run();assert(parts.get(d).same(V(0xffa5,0xff00,16)));
    for(int i=0;i<4;++i) {
        parts.restore(partial);parts.assign_parts({{d,0,4,0}},V(i,0,4),true);parts.run();
        assert(parts.get(d).same(V(0xffa0|i,0xff00,16)));
    }
    parts.restore(partial);parts.run();assert(parts.get(d).same(V(0xffa5,0xff00,16)));

    // Mixed whole/partial insertion order, owned delayed payloads and slot reuse.
    Sim delayed;int q=delayed.signal(16,false);
    delayed.assign_nba_after(q,V(0x1234,0,16),5);
    delayed.assign_parts_after({{q,0,4,0}},V(0xf,0,4),5);
    auto before=delayed.checkpoint();
    delayed.run_until(5);assert(delayed.get(q).same(V(0x123f,0,16)));
    delayed.assign_nba_after(q,V::z(16),2);delayed.run_until(7);assert(delayed.get(q).same(V::z(16)));
    delayed.restore(before);delayed.run_until(5);assert(delayed.get(q).same(V(0x123f,0,16)));
    delayed.assign_parts_after({{q,8,8,0}},V(0x55,0xaa,8),2);
    auto staged=delayed.checkpoint();
    delayed.predict_until(7,[](Sim&){},[](const Sim&){return false;},[](Sim&){});
    assert(delayed.prediction_stats.rollbacks==1&&delayed.get(q).same(V(0x553f,0xaa00,16)));
    delayed.restore(staged);delayed.run_until(7);assert(delayed.get(q).same(V(0x553f,0xaa00,16)));
    std::cout<<"PASS scalar NBA: four-state resizing, two-state conversion, partial RHS width, queue ownership, FIFO, delayed slot reuse, checkpoints and rollback\n";
}
