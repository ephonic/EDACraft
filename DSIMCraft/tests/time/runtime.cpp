#include <dsim/runtime.hpp>
#include "time.hpp"
#include <cassert>
#include <limits>
using namespace dsim;
int main() {
 auto ns=parse_timescale("1ns / 100ps");
 assert(delay_ticks("0.149",ns,1000)==100);
 assert(delay_ticks("0.05",ns,1000)==100);
 assert(delay_ticks("1.25e0",ns,1000)==1300);
 assert(delay_ticks("1e-1000",ns,1000)==0);
 for(uint64_t fs=1;fs<=100000000000000000ULL;fs*=10) {
  assert(parse_time_unit(time_unit_name(fs))==fs);
  if(fs==100000000000000000ULL)break;
 }
 bool rejected=false;try{delay_ticks("100000",parse_timescale("1s/1fs"),1);}catch(const std::exception&){rejected=true;}assert(rejected);
 Sim s;s.set_time_precision(1000);s.now=UINT64_MAX;
 assert(s.local_time(1000000)==18446744073709552ULL);
 TimeFormat f{1000000,2,0," ns"};
 assert(format_time(V(UINT64_MAX,0,64),100000000000000000ULL,f)=="1844674407370955161500000000000.00 ns");
 assert(format_time(V(0),10000000,f)=="0.00 ns");
 f={100,0,0,""};assert(format_time(V(50,0,64),1,f)=="0");assert(format_time(V(150,0,64),1,f)=="2");
 assert(format_time(V(250,0,64),1,f)=="2");assert(format_time(V(251,0,64),1,f)=="3");
 Sim replay;replay.set_time_precision(1000);auto cp=replay.checkpoint();
 replay.timeformat(-9,2," ns",12);replay.restore(cp);
 assert(replay.time_format.unit_fs==1000&&replay.time_format.digits==0&&replay.time_format.suffix.empty());
 std::ostringstream captured;auto* old=std::cout.rdbuf(captured.rdbuf());
 auto accepted=replay.predict_until(10,[](Sim& p){p.timeformat(-9,2," ns",0);p.print("%0t",{V(12,0,64)},true,1000000);},[](const Sim&){return false;},[](Sim& p){p.print("%0t",{V(2,0,64)},true,1000000);});
 std::cout.rdbuf(old);assert(!accepted&&captured.str()=="2000\n");
 captured.str("");old=std::cout.rdbuf(captured.rdbuf());
 replay.print("%0t",{V(12,0,64)});std::cout.rdbuf(old);assert(captured.str()=="12\n");
 assert(replay.time_format.unit_fs==1000&&replay.time_format.suffix.empty());
 std::cout<<"PASS physical time, exact delays, rounding, overflow, formatting and rollback\n";
}
