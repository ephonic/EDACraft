#define DSIM_STRING_ENABLED 1
#define DSIM_FILE_IO_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
int main(int argc,char** argv) {
 assert(argc==2);std::filesystem::create_directories(argv[1]);
 const auto path=(std::filesystem::absolute(argv[1])/"bytes.bin").string();
 {std::ofstream out(path,std::ios::binary);for(unsigned c:{0x12u,0x34u,0x56u,0x78u,0x9au,0xbcu,0xdeu,0xf0u,1u})out.put(char(c));}
 Sim s;const auto fd=s.file_open(path,"rb");assert(fd);s.freeze_topology();
 auto w=s.file_read_word(fd,12);assert(w.count==2&&w.value.same(V(0x234,0,12))&&s.file_tell(fd)==2);
 auto cp=s.checkpoint();s.file_ungetc(0,fd);w=s.file_read_word(fd,16);assert(w.count==2&&w.value.a==0x56);s.restore(cp);assert(s.file_tell(fd)==2);
 bool accepted=s.predict_until(0,[&](Sim& p){p.file_seek(fd,8,0);auto short_word=p.file_read_word(fd,24);assert(short_word.count==1&&short_word.value.a==0x10000&&p.file_eof(fd));},[](const Sim&){return false;},[&](Sim& p){assert(p.file_tell(fd)==2&&!p.file_eof(fd));});
 assert(!accepted&&s.prediction_stats.rollbacks==1);
 s.file_rewind(fd);w=s.file_read_word(fd,80);assert(w.count==9&&slice(w.value,16,64).a==0x123456789abcdef0ull&&slice(w.value,0,16).a==0x100);
 assert(s.file_eof(fd));w=s.file_read_word(fd,80);assert(w.count==0&&w.value.same(V(0,0,80)));
 s.restore(cp);accepted=s.predict_until(0,[&](Sim& p){auto word=p.file_read_word(fd,16);assert(word.count==2&&word.value.a==0x5678);},[](const Sim&){return true;},[](Sim&){assert(false);});
 assert(accepted&&s.prediction_stats.commits==1&&s.file_tell(fd)==4);
 s.file_seek(fd,0,0);s.file_read_word(fd,8*9);assert(!s.file_eof(fd));s.file_read_word(fd,1);assert(s.file_eof(fd));
 s.file_close(fd);std::cout<<"PASS binary widths, byte order, short reads, EOF, pushback, checkpoint and prediction cursors\n";
}
