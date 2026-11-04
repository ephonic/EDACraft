#define DSIM_WAVE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <dsim/runtime.hpp>
#include <dsim/waveform.hpp>
#include <atomic>
#include <cassert>
#include <filesystem>
#include <fstream>
using namespace dsim;
using namespace wave_detail;
static std::string contents(const std::filesystem::path& path) {
 std::ifstream f(path,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};
}
struct Probe:Sink {
 std::thread::id owner=std::this_thread::get_id();std::shared_ptr<std::atomic<int>> calls;
 int fail;
 Probe(std::shared_ptr<std::atomic<int>> p,int n):calls(std::move(p)),fail(n) {}
 ~Probe() override {assert(owner==std::this_thread::get_id());}
 void check(){assert(owner==std::this_thread::get_id());if(++*calls==fail)throw std::runtime_error("injected writer failure");}
 void time(uint64_t) override {check();}
 void value(size_t,V) override {check();}
 void control(const std::string&) override {check();}
 void close() override {check();}
 uint64_t bytes() const override {assert(owner==std::this_thread::get_id());return 0;}
};
struct GatedProbe:Probe {
 std::shared_ptr<std::promise<void>> entered;
 std::shared_future<void> release;
 bool first=true;
 GatedProbe(std::shared_ptr<std::atomic<int>> calls,std::shared_ptr<std::promise<void>> entered_,std::shared_future<void> release_)
  :Probe(std::move(calls),-1),entered(std::move(entered_)),release(std::move(release_)) {}
 void value(size_t,V) override {
  check();if(first){first=false;entered->set_value();release.wait();}
 }
};
int main(int argc,char** argv) {
 assert(argc==2);std::filesystem::path out=argv[1];std::filesystem::create_directories(out);
 Dictionary dictionary;
 for(int width:{1,65,1024,4096}) {
  size_t id=dictionary.widths.size();dictionary.signal_ids.push_back(int(id));dictionary.widths.push_back(width);
  dictionary.aliases.push_back({id,{"top"},"v"+std::to_string(width),"reg",width-1,0,true});
 }
 dictionary.aliases.push_back({0,{"top","child"},"alias","wire",0,0,false});dictionary.finalize("1ps","ordered");
 auto produce=[](Sink& sink) {
  sink.time(0);sink.control("$dumpvars");
  for(uint64_t t=0;t<120;++t) {
   sink.time(t/3);
   for(size_t i=0;i<4;++i) {
    int width=i==0?1:i==1?65:i==2?1024:4096;
    std::vector<V::Word> words(size_t((width+63)/64));
    for(size_t j=0;j<words.size();++j)words[j]={0x123456789abcdef0ull^(t*127+j),t%7==0?~uint64_t(0):uint64_t(0)};
    auto value=V::from_words(std::move(words),width);sink.value(i,value);
    value=V::x(width); // producer storage is reused immediately
   }
  }
  sink.control("$end");sink.close();
 };
 Dwf sync((out/"sync.dwf").string(),dictionary,17,true);produce(sync);
 AsyncSink async([&]{return std::make_unique<Dwf>((out/"async.dwf").string(),dictionary,17,true);},8192);produce(async);
 assert(contents(out/"sync.dwf")==contents(out/"async.dwf"));
 assert(async.values==sync.values&&async.blocks==sync.blocks&&async.bytes()==sync.bytes());
 auto stats=async.queue_stats();assert(stats[0]>0&&stats[0]<=8192);
 auto calls=std::make_shared<std::atomic<int>>(0);auto main_thread=std::this_thread::get_id();
 // Model a stalled disk without sleeps in the writer. With this budget only
 // one wide event fits; the producer cannot finish until the disk is released.
 {auto entered=std::make_shared<std::promise<void>>();auto started=entered->get_future();
  std::promise<void> release;auto gate=release.get_future().share();
  AsyncSink writer([&]{return std::make_unique<GatedProbe>(calls,entered,gate);},2048);
  auto producer=std::async(std::launch::async,[&]{for(int i=0;i<3;++i)writer.value(0,V::x(4096));writer.close();});
  assert(started.wait_for(std::chrono::seconds(5))==std::future_status::ready);
  assert(producer.wait_for(std::chrono::milliseconds(30))==std::future_status::timeout);
  release.set_value();producer.get();assert(calls->load()==4);
  assert(writer.queue_stats()[0]<=2048);
 }
 calls->store(0);
 {AsyncSink writer([&]{assert(main_thread!=std::this_thread::get_id());return std::make_unique<Probe>(calls,-1);},1024);
  for(int i=0;i<200;++i)writer.value(0,V(i,0,32));} // destructor drains and joins
 assert(calls->load()==201);
 bool failed=false;
 try {AsyncSink writer([]()->std::unique_ptr<Sink>{throw std::runtime_error("injected startup failure");},1024);}
 catch(const std::runtime_error& e){failed=std::string(e.what())=="injected startup failure";}assert(failed);
 failed=false;calls->store(0);
 try {AsyncSink writer([&]{return std::make_unique<Probe>(calls,17);},1024);for(int i=0;i<10000;++i)writer.time(i);writer.close();}
 catch(const std::runtime_error& e){failed=std::string(e.what())=="injected writer failure";}assert(failed);
 // Closing also runs on the receiver, including failures while writing the
 // final block/index. Repeated close must retain the original error.
 calls->store(0);
 {AsyncSink writer([&]{return std::make_unique<Probe>(calls,1);},1024);
  for(int i=0;i<2;++i) {
   failed=false;try {writer.close();}
   catch(const std::runtime_error& e){failed=std::string(e.what())=="injected writer failure";}assert(failed);
  }
  assert(calls->load()==1);
 }
 calls->store(0);
 {AsyncSink writer([&]{return std::make_unique<Probe>(calls,-1);},1024);
  writer.close();writer.close();assert(calls->load()==1);
  failed=false;try {writer.time(0);}
  catch(const std::runtime_error& e){failed=std::string(e.what())=="asynchronous waveform writer is closed";}assert(failed);
 }
 failed=false;
 try {AsyncSink writer([&]{return std::make_unique<Dwf>((out/"sync.dwf").string(),dictionary,17,true);},1024);}
 catch(const std::runtime_error&){failed=true;}assert(failed);
 failed=false;
 try {AsyncSink writer([&]{return std::make_unique<Probe>(calls,-1);},1024);writer.value(0,V::x(65536));}
 catch(const std::runtime_error& e){failed=std::string(e.what())=="waveform event exceeds asynchronous buffer budget";}assert(failed);
 std::cout<<"PASS asynchronous encoding/compression/I/O, ordered immutable snapshots, bounded queue, exceptions and joined shutdown\n";
}
