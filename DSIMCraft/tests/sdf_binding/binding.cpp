#include "sdf_binding.hpp"
#include <cassert>
#include <fstream>
#include <sstream>
#include <iostream>
using namespace dsim;
void raw_binding_tests(const std::string& base);
int main(int argc,char** argv) {
    assert(argc==2);std::string base=argv[1];
    auto design=parse_gate(base+"/net.v","dut",{base+"/../gate/cells.lib"},{false,true,true});
    assert(design.timing_only&&design.timing_names&&design.timing_names->sorted_instances.size()==3);
    auto& names=*design.timing_names;int u=names.find_instance({"h","u"}),v=names.find_instance({"v"}),escaped=names.find_instance({"literal/slash"});
    assert(u>=0&&v>=0&&escaped>=0&&names.find_instance({"literal","slash"})<0);
    assert(sdf_path_parts("a\\/b/c",'/')==std::vector<std::string>({"a/b","c"}));
    assert(sdf_path_parts("a\\.b.c",'.')==std::vector<std::string>({"a.b","c"}));
    bool failed=false;try{sdf_path_parts("a/",'/');}catch(const std::exception&){failed=true;}assert(failed);
    SdfBindOptions options;options.tick_fs=1000;
    size_t count=0,fanout=0;
    auto stats=bind_sdf_file(base+"/timing.sdf",design,options,[&](const SdfBoundEntry& entry) {
        const auto& syntax=*entry.syntax;++count;
        if(syntax.kind=="IOPATH"&&syntax.condition.empty()&&!syntax.conditional_else&&syntax.mode==SdfEntry::Mode::Absolute&&entry.values.size()==2) {
            assert(!entry.cell.scope&&(int(entry.cell.id)==u||int(entry.cell.id)==v||int(entry.cell.id)==escaped));
            assert(entry.ports[0].pin==0&&entry.ports[1].pin==1);
            assert(entry.values[0].delay->magnitude==1000&&entry.values[1].delay->magnitude==1200);++fanout;
        }
        if(syntax.mode==SdfEntry::Mode::Increment)assert(entry.values[0].delay->negative&&entry.values[0].delay->magnitude==200);
        if(syntax.kind=="PORT")assert(!entry.values[0].delay);
        if(!syntax.condition.empty()) {
            assert(syntax.label=="low"&&syntax.ports[0].edge=="posedge");
            assert(entry.retain[0][0].delay->magnitude==100);
            assert(entry.values[0].delay->magnitude==200&&entry.values[0].reject->magnitude==10&&entry.values[0].xlimit->magnitude==20);
        }
    });
    assert(count==16&&fanout==3&&stats.bound_entries==16&&stats.interconnects==5&&stats.target_cells==6&&stats.missing_values==1&&stats.negative_values==1);
    for(int corner:{0,2}) {
        options.corner=corner;int paths=0;
        auto selected=bind_sdf_file(base+"/timing.sdf",design,options,[&](const SdfBoundEntry& entry) {
            if(entry.syntax->kind=="IOPATH"&&entry.values.size()==2) {assert(entry.values[0].delay->magnitude==uint64_t(corner==0?500:1500));++paths;}
            if(entry.syntax->kind=="PORT")assert(entry.values[0].delay->magnitude==uint64_t(corner==0?1000:3000));
        });assert(paths==3&&selected.missing_values==0);
    }
    options.corner=1;options.tick_fs=1;
    std::istringstream extreme("(DELAYFILE (SDFVERSION \"3.0\") (TIMESCALE 1fs) (CELL (CELLTYPE \"INV\") (INSTANCE v) (DELAY (INCREMENT (IOPATH A Y (-18446744073709551615))))))");
    auto wide=bind_sdf(extreme,"extreme",design,options,[](const SdfBoundEntry& e){assert(e.values[0].delay->negative&&e.values[0].delay->magnitude==UINT64_MAX);});assert(wide.negative_values==1);
    // Optional metadata and topology-only parsing never permit code generation.
    failed=false;try{design.cpp();}catch(const std::exception&){failed=true;}assert(failed);
    auto regular=parse_gate(base+"/net.v","dut",{base+"/../gate/cells.lib"});assert(!regular.timing_names&&!regular.timing_only);
    failed=false;try{std::istringstream empty;bind_sdf(empty,"empty",regular,options);}catch(const std::exception&){failed=true;}assert(failed);
    raw_binding_tests(base);
    std::cout<<"PASS hierarchy/escaped names, wildcard IDs/pins, connectivity, corners/missing/signed values, conditions/retain and optional metadata\n";
}
