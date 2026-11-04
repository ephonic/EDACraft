#define DSIM_WIDE_VALUES 1
#define DSIM_REPLICATION_ENABLED 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
static V value(const std::vector<int>& bits) {
 std::vector<V::Word> words((bits.size()+63)/64,{0,0});
 for(size_t i=0;i<bits.size();++i){if(bits[i]==1||bits[i]==2)words[i/64].a|=uint64_t(1)<<(i%64);if(bits[i]>=2)words[i/64].b|=uint64_t(1)<<(i%64);}
 return V::from_words(std::move(words),int(bits.size()));
}
static void equal(const V& actual,const std::vector<int>& expected) {
 assert(actual.w==int(expected.size()));for(int i=0;i<actual.w;++i)if(actual.bit(i)!=expected[size_t(i)]){std::cerr<<"mismatch width "<<actual.w<<" bit "<<i<<" got "<<actual.bit(i)<<" expected "<<expected[size_t(i)]<<"\n";std::abort();}
}
int main() {
 uint32_t state=0x12345678;auto random=[&]{state^=state<<13;state^=state>>17;state^=state<<5;return state;};
 for(int source_width:{1,2,7,8,31,32,63,64,65,127,128})for(int width:{1,8,32,64,65,128})for(int sample=0;sample<40;++sample) {
  std::vector<int> source(size_t(source_width),0),bits(size_t(width),0);
  for(int& bit:source)bit=sample<4?sample:int(random()%(sample%2?4:2));
  for(int i=0;i<std::min(source_width,width);++i)bits[size_t(i)]=source[size_t(i)];
  auto v=value(source);equal(unary_op<Unary::Plus>(v,width),bits);
  std::vector<int> inverted=bits,negative(bits.size());bool unknown=false,one=false,zero=false;int parity=0;
  for(size_t i=0;i<bits.size();++i){int b=bits[i];unknown|=b>=2;one|=b==1;zero|=b==0;parity^=b==1;inverted[i]=b>=2?2:1-b;}
  equal(unary_op<Unary::BitNot>(v,width),inverted);
  int carry=1;for(size_t i=0;i<bits.size();++i){int sum=1-bits[i]+carry;negative[i]=sum&1;carry=sum>>1;}
  if(unknown)std::fill(negative.begin(),negative.end(),2);
  equal(unary_op<Unary::Minus>(v,width),negative);
  equal(unary_op<Unary::LogicalNot>(v,width),{one?0:unknown?2:1});
  equal(unary_op<Unary::ReduceAnd>(v,width),{zero?0:unknown?2:1});
  equal(unary_op<Unary::ReduceOr>(v,width),{one?1:unknown?2:0});
  equal(unary_op<Unary::ReduceXor>(v,width),{unknown?2:parity});
 }
 for(int bit=0;bit<4;++bit)for(int count=1;count<=256;++count)equal(replicate(value({bit}),unsigned(count)),std::vector<int>(size_t(count),bit));
 for(int width:{2,3,7,8,31,32,63,64})for(int count=1;count<=4;++count) {
  std::vector<int> bits(size_t(width),0);for(int& b:bits)b=int(random()%4);
  std::vector<int> expected;for(int i=0;i<count;++i)expected.insert(expected.end(),bits.begin(),bits.end());
  equal(replicate(value(bits),unsigned(count)),expected);
 }
 for(unsigned count:{0u,1048577u}) {bool caught=false;try{(void)replicate(V(1),count);}catch(const std::runtime_error&){caught=true;}assert(caught);}
 std::cout<<"PASS scalar/wide unary four-state oracle and replication boundaries\n";
}
