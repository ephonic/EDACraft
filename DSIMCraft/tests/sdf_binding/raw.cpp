#include "sdf_binding.hpp"
#include <cassert>
#include <sstream>
using namespace dsim;
namespace {
template<class F> void rejects(F run) {
    bool failed=false;try{run();}catch(const std::exception&){failed=true;}assert(failed);
}
std::string file(const std::string& entries,const std::string& unit="1ns") {
    return "(DELAYFILE (SDFVERSION \"3.0\") "+(unit.empty()?std::string{}:"(TIMESCALE "+unit+")")+
        " (CELL (CELLTYPE \"INV\") (INSTANCE v) (DELAY "+entries+")))";
}
}
void raw_binding_tests(const std::string& base) {
    // Raw binding is also available on executable topology with timing names.
    auto design=parse_gate(base+"/net.v","dut",{base+"/../gate/cells.lib"},{false,true,false});
    assert(!design.timing_only&&design.timing_names);
    SdfBindOptions raw;raw.numeric_preview=false;
    for(int corner:{0,1,2}) {
        raw.corner=corner;size_t count=0,conditional=0;
        auto stats=bind_sdf_file(base+"/timing.sdf",design,raw,[&](const SdfBoundEntry& e) {
            ++count;assert(!e.numeric_preview&&e.values.empty()&&e.retain.empty());
            assert(e.unit_fs==1000000&&e.corner==corner);
            if(!e.syntax->condition.empty()) {
                ++conditional;assert(e.syntax->label=="low"&&e.syntax->ports[0].edge=="posedge");
                assert(*e.syntax->retain[0][0].delay.corner[corner]=="0.1");
                assert(*e.syntax->values[0].reject->corner[corner]=="0.01");
            }
        });
        assert(count==16&&conditional==1&&stats.bound_entries==16&&stats.interconnects==5);
        assert(stats.missing_values==uint64_t(corner==1)&&!stats.numeric_preview&&stats.tick_fs==0);
        assert(stats.report().find("\"negative_selected_values\":null")!=std::string::npos);
    }
    raw.corner=1;
    auto small=file("(ABSOLUTE (IOPATH A Y (0.004))) (INCREMENT (IOPATH A Y (0.004)))");
    SdfBindOptions preview;preview.tick_fs=10000;
    std::istringstream a(small);size_t rounded=0;
    bind_sdf(a,"preview",design,preview,[&](const SdfBoundEntry& e){assert(e.numeric_preview&&e.values[0].delay->magnitude==0);++rounded;});
    assert(rounded==2);
    // This tests raw preservation, not a path-annotation merge policy. VCS
    // quantizes each update at model precision before merging increments.
    std::vector<std::optional<std::string>> selected;
    auto apply=[&](const SdfBoundEntry& e) {
        assert(!e.numeric_preview&&e.values.empty());
        assert(e.unit_fs==1000000&&e.corner==1);
        selected.push_back(e.syntax->values[0].delay.corner.at(e.corner));
    };
    std::istringstream b(small);bind_sdf(b,"merge",design,raw,apply);
    assert(selected.size()==2&&*selected[0]=="0.004"&&*selected[1]=="0.004");
    // Raw binding retains large decimals and missing corners without imposing
    // a numeric annotation policy or overflowing a preview conversion.
    auto huge=file("(ABSOLUTE (IOPATH A Y (1e80))) (INCREMENT (IOPATH A Y (-1e80))) (INCREMENT (IOPATH A Y (0.004))) (INCREMENT (IOPATH A Y (1::3)))");
    std::istringstream c(huge);auto wide=bind_sdf(c,"cancel",design,raw,apply);
    assert(wide.missing_values==1&&selected.size()==6);
    assert(*selected[2]=="1e80"&&*selected[3]=="-1e80"&&*selected[4]=="0.004"&&!selected[5]);
    std::istringstream d(file("(INCREMENT (IOPATH A Y (4)))","1ps"));
    bind_sdf(d,"mixed-unit",design,raw,[&](const SdfBoundEntry& e){
        assert(e.unit_fs==1000&&e.corner==1&&*e.syntax->values[0].delay.corner[1]=="4");
    });
    size_t callbacks=0;
    rejects([&]{std::istringstream in(huge);bind_sdf(in,"overflow-preview",design,preview,[&](const SdfBoundEntry&){++callbacks;});});assert(callbacks==0);
    // Unit defaults and invalid options still receive strict validation.
    raw.default_unit_fs=1000000;
    std::istringstream fallback(file("(ABSOLUTE (IOPATH A Y (1)))",""));
    assert(bind_sdf(fallback,"fallback",design,raw).unit_fs==1000000);
    std::istringstream wins(file("(ABSOLUTE (IOPATH A Y (1)))","1ps"));
    assert(bind_sdf(wins,"header-wins",design,raw).unit_fs==1000);
    for(uint64_t invalid:{uint64_t(0),uint64_t(3)}) {
        auto bad=raw;bad.default_unit_fs=invalid;
        rejects([&]{std::istringstream in(small);bind_sdf(in,"bad-unit",design,bad);});
    }
    for(int invalid:{-1,3}) {
        auto bad=raw;bad.corner=invalid;
        rejects([&]{std::istringstream in(small);bind_sdf(in,"bad-corner",design,bad);});
    }
    raw.tick_fs=3;rejects([&]{std::istringstream in(small);bind_sdf(in,"bad-tick",design,raw);});raw.tick_fs=0;
    raw.default_unit_fs.reset();
    rejects([&]{std::istringstream in(file("(ABSOLUTE (IOPATH A Y (1)))",""));bind_sdf(in,"missing-unit",design,raw);});
    rejects([&]{std::istringstream in(file("(ABSOLUTE (IOPATH BAD Y (1e80)))"));bind_sdf(in,"bad-pin",design,raw);});
    rejects([&]{std::istringstream in(file("(ABSOLUTE (IOPATH A Y (1e)))"));bind_sdf(in,"bad-decimal",design,raw);});
    preview.tick_fs=0;rejects([&]{std::istringstream in(small);bind_sdf(in,"preview-needs-tick",design,preview);});
}
