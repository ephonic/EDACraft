#include "liberty/liberty_parser.hh"
#include "liberty/liberty_binary.hh"
#include <cassert>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <vector>
using namespace edacraft::core;
int main(int argc,char** argv) {
    assert(argc==4);
    std::ifstream input(argv[1]); assert(input);
    std::string text{std::istreambuf_iterator<char>(input),{}};
    StringPool pool; LibertyDB db; te::parser::LibertyParser parser(text); parser.parse(db,pool);
    std::ifstream sequential(argv[3]); assert(sequential);
    std::string extra{std::istreambuf_iterator<char>(sequential),{}};
    te::parser::LibertyParser sequential_parser(extra); sequential_parser.parse(db,pool);
    size_t pins=0,tristates=0,cells=0,storage=0;
    for(uint32_t l=0;l<db.library_count();++l) for(uint32_t c=0;c<db.library(l).cells.size();++c) {
        ++cells; const auto& cell=db.library(l).cells[c];
        if(cell.sequential_kind) { ++storage; assert(pool.view(cell.ff_state)=="IQ"); assert(pool.view(cell.ff_state_inverse)=="IQN"); }
    }
    assert(storage==13);
    for(uint32_t l=0;l<db.library_count();++l) for(uint32_t c=0;c<db.library(l).cells.size();++c)
        for(const auto& pin:db.library(l).cells[c].pins) { ++pins; if(pin.three_state!=UINT32_MAX) { ++tristates; assert(pool.view(pin.three_state)=="!E"); } }
    assert(tristates==2);
    std::filesystem::create_directories(argv[2]);
    for(bool gzip:{false,true}) {
        auto path=std::filesystem::path(argv[2])/(gzip?"models.ftlib.gz":"models.ftlib");
        { std::ofstream out(path,std::ios::binary); assert(te::save_liberty_binary(db,pool,out,gzip)); }
        StringPool loaded_pool; loaded_pool.intern("different ID offset"); LibertyDB loaded;
        assert(te::load_liberty_binary(path.string(),loaded,loaded_pool));
        assert(db.library_count()==loaded.library_count());
        for(uint32_t l=0;l<db.library_count();++l) for(uint32_t c=0;c<db.library(l).cells.size();++c) {
            const auto& a=db.library(l).cells[c]; const auto& b=loaded.library(l).cells[c];
            assert(a.pins.size()==b.pins.size());
            assert(a.sequential_kind==b.sequential_kind);
            assert(a.sequential_unsupported==b.sequential_unsupported);
            for(auto pair : {std::pair{a.ff_state,b.ff_state},std::pair{a.ff_state_inverse,b.ff_state_inverse},
                            std::pair{a.ff_clocked_on,b.ff_clocked_on},std::pair{a.ff_next_state,b.ff_next_state},
                            std::pair{a.ff_clear,b.ff_clear},std::pair{a.ff_preset,b.ff_preset},std::pair{a.ff_enable,b.ff_enable},
                            std::pair{a.latch_data_in,b.latch_data_in},std::pair{a.clear_preset_var1,b.clear_preset_var1},std::pair{a.clear_preset_var2,b.clear_preset_var2}})
                assert(pool.view(pair.first)==loaded_pool.view(pair.second));
            for(size_t p=0;p<a.pins.size();++p) {
                assert(pool.view(a.pins[p].function)==loaded_pool.view(b.pins[p].function));
                assert(pool.view(a.pins[p].three_state)==loaded_pool.view(b.pins[p].three_state));
            }
        }
    }
    // Strip appended v14 fields to replay exact old v13/v12 layouts.
    std::ostringstream stream(std::ios::binary); assert(te::save_liberty_binary(db,pool,stream));
    auto current=stream.str(); uint32_t version; std::memcpy(&version,current.data()+8,4); assert(version==14);
    for(uint32_t legacy_version : {13,12}) {
        auto bytes=current;
        bytes.resize(bytes.size()-cells*6*sizeof(uint32_t)-(legacy_version==12?pins*sizeof(uint32_t):0));
        std::memcpy(bytes.data()+8,&legacy_version,4);
        uint64_t size=bytes.size(); std::memcpy(bytes.data()+16,&size,8);
        auto path=std::filesystem::path(argv[2])/("legacy-v"+std::to_string(legacy_version)+".ftlib");
        { std::ofstream out(path,std::ios::binary); out.write(bytes.data(),bytes.size()); }
        StringPool legacy_pool; LibertyDB legacy; assert(te::load_liberty_binary(path.string(),legacy,legacy_pool));
        size_t restored_three_state=0;
        for(uint32_t l=0;l<legacy.library_count();++l) for(uint32_t c=0;c<legacy.library(l).cells.size();++c) {
            const auto& cell=legacy.library(l).cells[c];
            assert(cell.sequential_kind==0 && cell.ff_state_inverse==UINT32_MAX && cell.latch_data_in==UINT32_MAX);
            for(const auto& pin:cell.pins) if(pin.three_state!=UINT32_MAX) ++restored_three_state;
        }
        assert(restored_three_state==(legacy_version==13?2:0));
    }
    std::cout<<"PASS Liberty ff/latch/function/three_state plain+gzip roundtrip, ID remap, v12/v13 compatibility\n";
}
