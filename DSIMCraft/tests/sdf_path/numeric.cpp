#include "sdf_delay.hpp"
#include <cassert>
#include <limits>
using namespace dsim;
using Table=std::array<uint64_t,12>;
using Mode=SdfEntry::Mode;
template<class F> static void rejects(F run){bool failed=false;try{run();}catch(const std::exception&){failed=true;}assert(failed);}
static const TimeScale ns_ps{1000000,1000},ns_10ps{1000000,10000};
static void updates() {
    SdfPathDelays a(ns_10ps,{"0","0"});
    a.apply(Mode::Absolute,{"0.004"},1000000);a.apply(Mode::Increment,{"0.004"},1000000);
    assert(a.ticks(1000)==Table{});
    a.apply(Mode::Absolute,{"0.005"},1000000);a.apply(Mode::Increment,{"0.005"},1000000);
    for(auto value:a.ticks(1000))assert(value==20);
    a.apply(Mode::Absolute,{"0.014"},1000000);a.apply(Mode::Increment,{"-0.005"},1000000);
    assert(a.ticks(1000)==Table{});
    SdfPathDelays b(ns_ps,{"0"});
    b.apply(Mode::Absolute,{"2"},1000);b.apply(Mode::Increment,{"-7"},1000);b.apply(Mode::Increment,{"6"},1000);
    for(auto value:b.ticks(1000))assert(value==6);
    b.apply(Mode::Absolute,{"0.010","0.001","0.020"},1000000);
    b.apply(Mode::Increment,{"0.001","0.010","0.001"},1000000);
    assert((b.ticks(1000)==Table{11,11,21,11,21,11,11,11,11,11,21,11}));
    // Independent X delays stay independent across increments, even when a
    // twelve-list initially equals the derived expansion of a three-list.
    b.apply(Mode::Absolute,{"10","1","20","10","20","1","10","10","1","1","20","1"},1000);
    b.apply(Mode::Increment,{"1","10","1"},1000);
    assert((b.ticks(1000)==Table{11,11,21,11,21,11,11,11,2,11,21,2}));
    b.apply(Mode::Absolute,{"10","1","20"},1000);
    b.apply(Mode::Increment,{std::nullopt,"4"},1000);
    assert((b.ticks(1000)==Table{10,5,20,10,24,5,10,10,5,5,24,5}));
}
static void expansion() {
    SdfPathDelays a(ns_ps,{"0"});
    a.apply(Mode::Absolute,{"3","9"},1000);
    assert((a.ticks(1000)==Table{3,9,3,3,9,9,3,3,9,9,9,3}));
    a.apply(Mode::Absolute,{"3","9","6"},1000);
    assert((a.ticks(1000)==Table{3,9,6,3,6,9,3,3,6,9,6,3}));
    a.apply(Mode::Absolute,{"3","9","5","11","7","13"},1000);
    assert((a.ticks(1000)==Table{3,9,5,11,7,13,3,11,7,13,7,11}));
    a.apply(Mode::Absolute,{"1","2","3","4","5","6","7","8","9","10","11","12"},1000);
    a.apply(Mode::Absolute,{std::nullopt,"4"},1000);
    assert((a.ticks(1000)==Table{1,4,3,4,4,4,7,8,4,4,4,12}));
    a.apply(Mode::Absolute,{"1","2","3","4","5","6","7","8","9","10","11","12"},1000);
    a.apply(Mode::Increment,{std::nullopt,"-4"},1000);
    assert((a.ticks(1000)==Table{1,0,3,4,1,2,7,8,5,6,11,8}));
    a.apply(Mode::Absolute,{"1","2","3","4","5","6","7","8","9","10","11","12"},1000);
    a.apply(Mode::Absolute,{std::nullopt,"-4"},1000);
    assert((a.ticks(1000)==Table{1,0,3,4,0,0,7,8,0,0,0,12}));
    int lookup[4][4]={{-1,0,6,2},{1,-1,8,4},{9,7,-1,10},{5,3,11,-1}};
    for(int i=0;i<4;++i)for(int j=0;j<4;++j)assert(SdfPathDelays::transition(i,j)==lookup[i][j]);
    rejects([]{SdfPathDelays::transition(-1,0);});rejects([]{SdfPathDelays::transition(0,4);});
}
static void boundaries() {
    for(auto scale:{TimeScale{0,1},TimeScale{1,10},TimeScale{3,1},TimeScale{10,3}})
        rejects([&]{SdfPathDelays a(scale,{"0"});});
    SdfPathDelays a(ns_ps,{"1","2"});const auto before=a.model_quanta();
    for(const auto& values:std::vector<std::vector<std::optional<std::string>>>{{},{"1","2","3","4"},{"1","bad"},{"1","1e80"}}) {
        rejects([&]{a.apply(Mode::Absolute,values,1000);});assert(a.model_quanta()==before);
    }
    rejects([&]{a.apply(Mode::TimingCheck,{"1"},1000);});assert(a.model_quanta()==before);
    for(uint64_t unit:{0,3})rejects([&]{a.apply(Mode::Absolute,{"0"},unit);});
    for(uint64_t global:{0,3,10000})rejects([&]{a.ticks(global);});
    SdfPathDelays max({1,1},{"18446744073709551615"});
    assert(max.model_quanta()[0]==std::numeric_limits<uint64_t>::max());
    rejects([&]{max.apply(Mode::Increment,{"1"},1);});assert(max.model_quanta()[0]==UINT64_MAX);
    max.apply(Mode::Increment,{"-18446744073709551615"},1);assert(max.ticks(1)==Table{});
    SdfPathDelays overflow({1000,1000},{"18446744073709551615"});
    rejects([&]{overflow.ticks(1);});assert(overflow.model_quanta()[0]==UINT64_MAX);
    // Auto-derived X values are recomputed after basic increments. Their old
    // maxima and delta maxima must not be added as independent intermediates.
    SdfPathDelays crossed({1,1},{"0","0","18446744073709551615","0","0","0"});
    crossed.apply(Mode::Increment,{"0","0","0","0","18446744073709551615","0"},1);
    assert(crossed.model_quanta()[10]==UINT64_MAX);
    SdfPathDelays partial(ns_ps,{"1","2","3","4","5","6","7","8","9","10","11","12"});
    partial.apply(Mode::Absolute,{std::nullopt,"0"},1000);const auto retained=partial.model_quanta();
    rejects([&]{partial.apply(Mode::Increment,{"0"},1000);});assert(partial.model_quanta()==retained);
    partial.apply(Mode::Absolute,{"4"},1000);partial.apply(Mode::Increment,{"1"},1000);
    for(auto value:partial.model_quanta())assert(value==5);
}
int main(){updates();expansion();
    // Explicitly check constructor overflow separately from update atomicity.
    rejects([]{SdfPathDelays a(ns_ps,{"18446744073709551615"});});
    // All remaining boundaries run without relying on disabled NDEBUG asserts.
    boundaries();
}
