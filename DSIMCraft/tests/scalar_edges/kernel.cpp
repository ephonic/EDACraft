#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
static V bit(int state,int width){return state==3?V::z(width):state==2?V::x(width):V(state,0,width);}
int main(){
 unsigned cases=0;
 for(int width:{1,7,64})for(int a=0;a<4;++a)for(int b=0;b<4;++b)for(bool higher:{false,true}){
  Sim s;int n=s.signal(width,false);s.set(n,bit(a,width));
  int wakes[3]={};
  for(int edge=0;edge<3;++edge){int p=s.process([&,edge]{++wakes[edge];});s.wait(p,{{n,edge}});}
  V next=bit(b,width);if(higher&&width>1)next.a^=uint64_t(1)<<(width-1);
  auto before=s.get(n);s.set(n,next);s.run_until(0);
  assert(wakes[0]==int(!before.same(next)));
  assert(wakes[1]==int((a==0&&b!=0)||(a>=2&&b==1)));
  assert(wakes[2]==int((a==1&&b!=1)||(a>=2&&b==0)));
  ++cases;
 }
 std::cout<<"PASS "<<cases<<" four-state/vector edge cases\n";
}
