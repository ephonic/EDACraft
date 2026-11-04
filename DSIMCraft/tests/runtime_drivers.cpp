#define DSIM_PARALLEL_ENABLED 1
#define DSIM_FORCE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include "dsim/runtime.hpp"
#include <cassert>
#include <iostream>
using namespace dsim;
static V value(int bit,int width) {
    return bit==3?V::z(width):bit==2?V::x(width):V(bit?mask(width):0,0,width);
}
static int merge(int a,int b) {return a==3?b:b==3?a:a==b?a:2;}
int main() {
    // Driver insertion order and signed IDs cannot change strong resolution.
    for(int width:{1,64})for(int a=0;a<4;++a)for(int b=0;b<4;++b)for(int c=0;c<4;++c) {
        for(auto ids:{std::vector<int>{-5,9,2},std::vector<int>{9,2,-5}}) {
            Sim s;int n=s.signal(width,true);
            s.drive(n,ids[0],value(a,width));s.drive(n,ids[1],value(b,width));
            auto cp=s.checkpoint();
            s.drive(n,ids[2],value(c,width));
            assert(s.get(n).same(value(merge(merge(a,b),c),width)));
            // Mutate an existing overflow driver and add another one. A
            // checkpoint must own all driver storage, including overflow.
            s.drive(n,ids[1],value((b+1)%4,width));s.drive(n,77,value(1,width));
            s.restore(cp);assert(s.get(n).same(value(merge(a,b),width)));
            s.drive(n,ids[1],value(c,width));assert(s.get(n).same(value(merge(a,c),width)));
            s.restore(cp);assert(s.get(n).same(value(merge(a,b),width)));
        }
    }
    Sim s;int n=s.signal(64,true);int expected[64];std::fill(expected,expected+64,3);
    for(int driver=0;driver<128;++driver) {
        uint64_t a=0,b=0;
        for(int bit=0;bit<64;++bit) {
            int state=(driver*7+bit*3)%4;
            if(state==1||state==2)a|=uint64_t(1)<<bit;
            if(state>=2)b|=uint64_t(1)<<bit;
            expected[bit]=merge(expected[bit],state);
        }
        s.drive(n,driver,V(a,b,64));
        for(int bit=0;bit<64;++bit)assert(s.get(n).bit(bit)==expected[bit]);
    }
    // The first drive may finalize aliases lazily. Newly created isolated nets
    // after finalization must still take the independent resolution path.
    for(int a=0;a<4;++a)for(int b=0;b<4;++b) {
        Sim alias;int left=alias.signal(64,true),right=alias.signal(1,true);
        alias.connect_net(left,63,right,0);alias.drive(left,-7,value(a,64));
        assert(alias.get(right).bit(0)==a);
        int late=alias.signal(1,true);alias.drive(late,0,V::z(1));auto cp=alias.checkpoint();
        alias.drive(right,13,value(b,1));alias.drive(late,1,V(1));
        assert(alias.get(left).bit(63)==merge(a,b)&&alias.get(right).bit(0)==merge(a,b));
        assert(alias.get(left).bit(0)==a&&alias.get(late).bit(0)==1);
        alias.restore(cp);assert(alias.get(left).bit(63)==a&&alias.get(right).bit(0)==a&&alias.get(late).bit(0)==3);
    }
    // Repeated updates must retain a driver's current value under force and
    // across checkpoints, including when a second driver is introduced later.
    for(int width:{1,64,65,129}) {
        Sim single;int id=single.signal(width,true);std::vector<V> observed;
        single.observe_resolved([&](uint64_t,int changed,V v){assert(changed==id);observed.push_back(v);});
        single.drive(id,-9,V::z(width));single.drive(id,-9,V(1,0,width));
        auto before=single.checkpoint();
        single.force_value(id,17,V::x(width));single.drive(id,-9,V(0,0,width));
        assert(single.get(id).same(V::x(width)));single.release_value(id);
        assert(single.get(id).same(V(0,0,width)));
        single.drive(id,8,V(1,0,width));assert(single.get(id).bit(0)==2);
        single.restore(before);assert(single.get(id).same(V(1,0,width)));
        single.drive(id,-9,V::z(width));single.drive(id,8,V(0,0,width));
        assert(single.get(id).same(V(0,0,width)));
        assert(!observed.empty());
    }
    std::cout<<"PASS driver truth tables, order, signed IDs, deep checkpoints, 128-driver mixed vectors, lazy aliases and late isolated nets; sizeof(Signal)="<<sizeof(Signal)<<'\n';
}
