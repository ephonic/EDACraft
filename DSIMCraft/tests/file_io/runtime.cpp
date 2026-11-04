#define DSIM_FILE_IO_ENABLED 1
#define DSIM_STRING_ENABLED 1
#define DSIM_MEMORY_IO_ENABLED 1
#define DSIM_PARALLEL_ENABLED 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
static std::string disk(const std::string& p) {
    std::ifstream in(p,std::ios::binary);return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
int main(int argc,char** argv) {
    assert(argc==2);std::filesystem::create_directories(argv[1]);
    const auto base=std::filesystem::absolute(argv[1]);
    const auto a=(base/"existing.txt").string(),b=(base/"new.txt").string();
    {std::ofstream out(a);out<<"original";}std::filesystem::remove(b);
    Sim s;auto h=s.file_open(a,"r+");assert(h);s.freeze_topology();
    assert(s.file_getc(h)=='o');auto cp=s.checkpoint();assert(s.file_getc(h)=='r');s.restore(cp);assert(s.file_tell(h)==1);
    bool accept=s.predict_until(0,[&](Sim& p){
        auto replacement=p.file_open(a,"w+");assert(replacement);p.file_write(replacement,"rejected");
        assert(p.file_seek(h,0,0)==0&&p.file_gets(h).text=="rejected");
        auto fresh=p.file_open(b,"w+");p.file_write(fresh,"ghost");p.file_close(fresh);
        assert(disk(a)=="original"&&!std::filesystem::exists(b));
    },[](const Sim&){return false;},[&](Sim& p){assert(p.file_tell(h)==1&&p.file_getc(h)=='r');});
    assert(!accept&&s.prediction_stats.rollbacks==1&&disk(a)=="original"&&!std::filesystem::exists(b));
    auto tx=s.begin_transaction();
    assert(s.file_seek(h,0,2)==0);s.file_write(h,"+accepted");
    auto fresh=s.file_open(b,"w+");s.file_write(fresh,"one");
    s.write_memory_file(b,"01 2a ff\n");assert(s.file_seek(fresh,0,0)==0);assert(s.file_gets(fresh).text=="01 2a ff\n");
    assert(s.read_memory_file(a)=="original+accepted");
    assert(disk(a)=="original"&&!std::filesystem::exists(b));
    s.commit_transaction(tx);
    assert(disk(a)=="original+accepted"&&disk(b)=="01 2a ff\n");
    tx=s.begin_transaction();s.file_write(h,"bad");s.file_ungetc(65,fresh);s.file_close(h);s.rollback_transaction(tx);
    assert(s.file_tell(h)==17&&disk(a)=="original+accepted");
    accept=s.predict_until(0,[&](Sim& p){
        p.file_write(h,"!");assert(disk(a)=="original+accepted");
    },[](const Sim&){return true;},[](Sim&){assert(false);});
    assert(accept&&s.prediction_stats.commits==1&&disk(a)=="original+accepted!");
    // Committed external effects are not replayed after an OS failure.
    const auto parent=base/"temporary";std::filesystem::create_directories(parent);
    auto failed=s.begin_transaction();assert(s.file_open((parent/"lost.txt").string(),"w"));
    std::filesystem::remove(parent);bool caught=false;
    try{s.commit_transaction(failed);}catch(const std::runtime_error&){caught=true;}assert(caught&&!s.transaction_pending(failed));
    caught=false;try{s.commit_transaction(failed);}catch(const std::runtime_error&){caught=true;}assert(caught);
    assert(!s.file_open((base/"missing/no.txt").string(),"w"));
    s.file_close(h);s.file_close(fresh);
    std::cout<<"PASS file I/O transaction isolation, cursor restore, read-your-writes and commit failure\n";
}
