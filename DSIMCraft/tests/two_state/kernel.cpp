#include <dsim/runtime.hpp>
#include <cassert>
#include <iostream>
using namespace dsim;
int main() {
    for(int width:{1,8,16,32,64,65,80,130}) {
        Sim s;int typed=s.signal_two_state(width),ordinary=s.signal(width,false);
        assert(s.get(typed).same(V(0,0,width))&&s.get(ordinary).same(V::x(width)));
        auto input=V::from_words({{0xf0f0,0xff00},{0x55aa,0x0ff0},{3,1}},width);
        s.set(typed,input);auto actual=s.get(typed);
        for(int bit=0;bit<width;++bit)assert(actual.bit(bit)==(input.bit(bit)==1));
        auto cp=s.checkpoint();s.set(typed,V::x(width));assert(s.get(typed).same(V(0,0,width)));
        s.restore(cp);assert(s.get(typed).same(actual));
        s.assign_nba(typed,V::z(width));s.run();assert(s.get(typed).same(V(0,0,width)));
        s.restore(cp);assert(s.get(typed).same(actual));
        s.set(typed,V::x(width));assert(s.get(typed).same(V(0,0,width)));
    }
    Sim s;int q=s.signal_two_state(8);int wakes=0;
    int p=s.process([&]{++wakes;});s.wait(p,{{q,0}});
    s.set(q,V::x(8));s.run();assert(wakes==0); // Conversion precedes equality and event detection.
    s.set(q,V(0x80,0x7f,8));s.run();assert(wakes==1&&s.get(q).same(V(0x80,0,8)));
    std::cout<<"PASS two-state defaults, per-bit conversion, multiword storage, NBA, checkpoints and event suppression\n";
}
