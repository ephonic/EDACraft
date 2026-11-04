#define DSIM_PARALLEL_ENABLED 1
#define DSIM_SCAN_ENABLED 1
#define DSIM_FILE_IO_ENABLED 1
#define DSIM_STRING_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
int main(int argc,char** argv) {
 assert(argc==2);std::filesystem::create_directories(argv[1]);
 Sim s;
 auto r=s.scan_string("-18446744073709551617 xz?1", "%d%h",{{128,false},{128,false}});
 assert(r.count==2&&format(r.values[0].value,'h')=="fffffffffffffffeffffffffffffffff");
 assert(format(r.values[1].value,'h')=="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxzz1");
 r=s.scan_string("12 nope","%d%d",{{32,false},{32,false}});assert(r.count==1&&r.values[0].matched&&!r.values[1].matched);
 r=s.scan_string("12","%*d%d",{{32,false}});assert(r.count==-1&&!r.values[0].matched);
 r=s.scan_string("_","%d",{{32,false}});assert(r.count==0);
 r=s.scan_string("-","%d",{{32,false}});assert(r.count==-1);
 r=s.scan_string(" abc","%3c",{{32,false}});assert(r.count==1&&r.values[0].value.a==32);
 r=s.scan_string("","x",{},true);assert(r.count==0);r=s.scan_string("","x",{});assert(r.count==-1);
 const auto path=(std::filesystem::absolute(argv[1])/"scan.txt").string();
 {std::ofstream out(path);out<<"12x 34";}
 auto fd=s.file_open(path,"r+");s.freeze_topology();
 auto cp=s.checkpoint();
 r=s.scan_file(fd,"%d",{{32,false}});assert(r.count==1&&r.values[0].value.a==12&&s.file_tell(fd)==2&&!s.file_eof(fd));
 s.restore(cp);assert(s.file_tell(fd)==0);
 bool accept=s.predict_until(0,[&](Sim& p){auto v=p.scan_file(fd,"%d%d",{{32,false},{32,false}});assert(v.count==2&&p.file_tell(fd)==3);},[](const Sim&){return false;},[&](Sim& p){assert(p.file_tell(fd)==0);});
 assert(!accept&&s.file_tell(fd)==0);
 accept=s.predict_until(0,[&](Sim& p){auto v=p.scan_file(fd,"%d%d",{{32,false},{32,false}});assert(v.count==2);},[](const Sim&){return true;},[](Sim&){assert(false);});
 assert(accept&&s.file_tell(fd)==3);
 auto tx=s.begin_transaction();r=s.scan_file(fd,"%d ",{{32,false}});assert(r.count==1&&r.values[0].value.a==34&&s.file_eof(fd));
 s.rollback_transaction(tx);assert(s.file_tell(fd)==3&&!s.file_eof(fd));
 assert(s.file_ungetc('7',fd)==0);cp=s.checkpoint();r=s.scan_file(fd,"%d",{{32,false}});assert(r.count==1&&r.values[0].value.a==7);s.restore(cp);assert(s.file_getc(fd)=='7');
 const auto position=s.file_tell(fd);
 for(const auto& fmt:{"%f","%0d","%1048577d","%d%","%d%d",""}) {
  bool caught=false;try{(void)s.scan_file(fd,fmt,{{32,false}});}catch(const std::runtime_error&){caught=true;}
  assert(caught&&s.file_tell(fd)==position);
 }
 bool caught=false;try{(void)s.scan_file(fd,"%d",{{1,true}});}catch(const std::runtime_error&){caught=true;}assert(caught&&s.file_tell(fd)==position);
 s.file_close(fd);
 std::cout<<"PASS scan conversion, mismatch, cursor/EOF/pushback checkpoint and prediction\n";
}
