#define DSIM_WAVE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <atomic>
#include <cassert>
#include <filesystem>
#include <thread>
#include <zstd.h>
#include "dsim/runtime.hpp"
#ifdef DSIM_TEST_COMPRESSION_ERROR
static const auto owner=std::this_thread::get_id();
static size_t injected_compress(ZSTD_CCtx* ctx,void* dst,size_t capacity,const void* src,size_t size,int level) {
    if(std::this_thread::get_id()!=owner)throw std::runtime_error("injected worker compression failure");
    return ZSTD_compressCCtx(ctx,dst,capacity,src,size,level);
}
#define ZSTD_compressCCtx injected_compress
#endif
#include "dsim/waveform.hpp"
using namespace dsim;

static uint64_t next(uint64_t& state) {state^=state<<13;state^=state>>7;state^=state<<17;return state;}
int main(int argc,char** argv) {
    try {
        assert(argc==2);std::filesystem::path out=argv[1];std::filesystem::create_directories(out);
        wave_detail::Dictionary dictionary;
        for(int i=0;i<64;++i) {
            dictionary.signal_ids.push_back(i);dictionary.widths.push_back(1024);
            dictionary.aliases.push_back({size_t(i),{"top"},"s"+std::to_string(i),"reg",1023,0,true});
        }
        dictionary.aliases.push_back({0,{"top","child"},"alias","wire",1023,0,true});
        dictionary.finalize("1ps","ordered");
#ifdef DSIM_TEST_COMPRESSION_ERROR
        bool failed=false;
        try {
            wave_detail::Dwf writer((out/"worker-failure.dwf").string(),dictionary,1,true,4);
            writer.time(0);writer.value(0,V::x(1024));writer.close();
        } catch(const std::runtime_error& e) {failed=std::string(e.what())=="injected worker compression failure";}
        assert(failed);std::cout<<"PASS worker exception and joined shutdown\n";
#else
        for(size_t jobs:{1,2,4,16}) {
            // A deliberately small embedding budget forces byte backpressure,
            // independently of worker speed or the number of completed tasks.
            wave_detail::Dwf writer((out/("wide-"+std::to_string(jobs)+".dwf")).string(),dictionary,65,true,jobs,65536);
            uint64_t rng=1017;
            for(uint64_t cycle=0;cycle<80;++cycle) {
                writer.time(cycle);
                for(size_t i=0;i<64;++i) {
                    std::vector<V::Word> words;
                    for(int k=0;k<16;++k){auto a=next(rng),b=next(rng);words.push_back({a,b});}
                    auto value=cycle%5==0?V::x(1024):V::from_words(std::move(words),1024);
                    writer.value(i,value);
                }
            }
            writer.close();auto peaks=writer.pending_peaks();
            assert(peaks.first<=2*jobs&&peaks.second<=65536);
            if(jobs>1)assert(peaks.first>=2&&peaks.second>32768);
            std::cout<<"PASS budget jobs="<<jobs<<" peak_records="<<peaks.first<<" peak_bytes="<<peaks.second<<"\n";
        }
        bool rejected=false;
        try {
            wave_detail::Dwf writer((out/"budget-failure.dwf").string(),dictionary,65,true,2,32);
            writer.time(0);writer.value(0,V::x(1024));writer.close();
        } catch(const std::runtime_error& e) {rejected=std::string(e.what())=="DWF1 block exceeds asynchronous compression buffer budget";}
        assert(rejected);std::cout<<"PASS oversized block budget failure\n";
#endif
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
