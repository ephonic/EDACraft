#pragma once
// Optional native waveform backend. Included after runtime.hpp in generated code.
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <condition_variable>
#include <deque>
#include <future>
#include <memory>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <zstd.h>
namespace dsim {
namespace wave_detail {
inline int real_width(const V& value) {
#ifdef DSIM_REAL_ENABLED
    return value.real_width;
#else
    (void)value;return 0;
#endif
}
using Bytes=std::vector<uint8_t>;
inline void number(Bytes& b,uint64_t n) {
    while(n>=128) {b.push_back(uint8_t(n)|128);n>>=7;} b.push_back(uint8_t(n));
}
inline void little(Bytes& b,uint64_t n,int count) {for(int i=0;i<count;++i) {b.push_back(uint8_t(n));n>>=8;}}
inline uint32_t crc(const Bytes& b) {
    static const auto table=[] { std::array<uint32_t,256> t{};
        for(uint32_t i=0;i<256;++i) {uint32_t c=i;for(int k=0;k<8;++k)c=(c>>1)^((c&1)?0xedb88320U:0);t[i]=c;} return t; }();
    uint32_t c=~uint32_t(0);for(auto x:b)c=table[(c^x)&255]^(c>>8);return ~c;
}
inline std::string json(const std::string& s) {
    std::string out="\""; const char* hex="0123456789abcdef";
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') {out+='\\';out+=char(c);}
        else if(c<32||c>=127) {out+="\\u00";out+=hex[c>>4];out+=hex[c&15];}
        else out+=char(c);
    } return out+'"';
}
inline std::string array(const std::vector<std::string>& tokens) {
    std::string out="[";for(const auto& t:tokens) {if(out.size()>1)out+=',';out+=json(t);}return out+']';
}
inline std::string code(size_t id) {
    std::string s;do {s+=char(33+id%94);id/=94;} while(id);return s;
}
inline std::string identifier(std::string name) {
    if(!name.empty() && name.front()=='\\')name.erase(0,1);
    if(name.empty())throw std::runtime_error("empty waveform name");
    bool plain=(name[0]>='a'&&name[0]<='z')||(name[0]>='A'&&name[0]<='Z')||name[0]=='_';
    for(unsigned char c:name) {
        if(c<=32||c>=127)throw std::runtime_error("waveform names require printable ASCII");
        if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='$'))plain=false;
    } return plain?name:"\\"+name;
}
struct Alias {size_t id; std::vector<std::string> scope; std::string name,type; int high,low;bool packed;};
struct Dictionary {
    struct Node {std::map<std::string,Node> children;std::vector<const Alias*> names;};
    std::vector<int> signal_ids,widths,real_types;
    std::vector<Alias> aliases;
    std::vector<std::vector<std::string>> header;
    static void walk(const Node& n,std::vector<std::vector<std::string>>& header) {
        for(auto a:n.names) {
            std::vector<std::string> t={"$var",a->type,std::to_string(std::abs(int64_t(a->high)-a->low)+1),code(a->id),identifier(a->name)};
            if(a->packed)t.push_back("["+std::to_string(a->high)+":"+std::to_string(a->low)+"]");
            t.push_back("$end");header.push_back(std::move(t));
        }
        for(const auto& pair:n.children) {
            header.push_back({"$scope","module",identifier(pair.first),"$end"});walk(pair.second,header);
            header.push_back({"$upscope","$end"});
        }
    }
    void finalize(const std::string& timescale,const std::string& mode) {
        Node root;
        for(const auto& a:aliases) {auto* n=&root;for(const auto& p:a.scope)n=&n->children[p];n->names.push_back(&a);}
        header={{"$version","dsim","0.13.0","$end"},{"$comment","capture="+mode,"tick="+timescale,"$end"},
                {"$timescale",timescale,"$end"}};
        walk(root,header);header.push_back({"$enddefinitions","$end"});
    }
    std::string metadata() const {
        // Header carries alias and hierarchy declarations; no duplicate alias JSON.
        const bool reals=std::any_of(real_types.begin(),real_types.end(),[](int width){return width!=0;});
        std::string out=std::string("{\"schema\":\"dsim.wave.prototype.")+(reals?"v2":"v1")+"\",\"header\":[";
        bool first=true;for(const auto& h:header) {if(!first)out+=',';first=false;out+=array(h);}out+="],\"signals\":[";
        for(size_t i=0;i<widths.size();++i) {if(i)out+=',';out+="{\"code\":"+json(code(i))+",\"width\":"+std::to_string(widths[i]);if(i<real_types.size()&&real_types[i])out+=",\"type\":\"real\"";out+="}";}
        return out+"]}";
    }
};
class File {
    FILE* f=nullptr;
public:
    uint64_t bytes=0;
    explicit File(const std::string& path) {
        f=std::fopen(path.c_str(),"wbx");
        if(!f)throw std::runtime_error("cannot create waveform "+path+": "+std::strerror(errno)+" (existing files are protected)");
    }
    File(const File&)=delete;File& operator=(const File&)=delete;
    ~File() {if(f)std::fclose(f);}
    void write(const void* p,size_t n) {if(std::fwrite(p,1,n,f)!=n)throw std::runtime_error("waveform write failed");bytes+=n;}
    void write(const std::string& s) {write(s.data(),s.size());}
    void write(const Bytes& b) {write(b.data(),b.size());}
    void close() {auto* old=f;f=nullptr;if(std::fclose(old)!=0)throw std::runtime_error("waveform close failed");}
};
struct Sink {
    uint64_t values=0,blocks=0;
    virtual ~Sink()=default;
    virtual void time(uint64_t)=0;
    virtual void value(size_t,V)=0;
    virtual void control(const std::string&)=0;
    virtual void close()=0;
    virtual uint64_t bytes() const=0;
};
class Vcd final:public Sink {
    File f;uint64_t now=0;bool started=false;
public:
    Vcd(const std::string& path,const Dictionary& dict):f(path) {
        for(const auto& h:dict.header) {for(size_t i=0;i<h.size();++i) {if(i)f.write(" ");f.write(h[i]);}f.write("\n");}
    }
    void time(uint64_t n) override {if(!started||now!=n) {f.write("#"+std::to_string(n)+"\n");now=n;started=true;}}
    void value(size_t id,V v) override {
#ifdef DSIM_REAL_ENABLED
        if(v.real_width){++values;f.write("r"+real_format(v.real_value())+" "+code(id)+"\n");return;}
#endif
        ++values;f.write((v.w==1?format(v,'b'):"b"+format(v,'b')+" ")+code(id)+"\n");
    }
    void control(const std::string& name) override {f.write(name+"\n");}
    void close() override {f.close();}
    uint64_t bytes() const override {return f.bytes;}
};
// Workers only own encoded bytes and a private Zstd context. The simulation
// thread retains dictionary/state ownership and commits records in FIFO order.
class BlockCompressor {
public:
    struct Result {Bytes payload;uint32_t raw_size,checksum;uint8_t codec;};
private:
    struct Work {Bytes raw;std::promise<Result> result;};
    std::mutex mutex;
    std::condition_variable ready;
    std::deque<Work> work;
    std::vector<std::thread> workers;
    bool stopping=false;
    void loop() {
        std::unique_ptr<ZSTD_CCtx,decltype(&ZSTD_freeCCtx)> context{nullptr,ZSTD_freeCCtx};
        for(;;) {
            Work next;
            {
                std::unique_lock<std::mutex> lock(mutex);
                ready.wait(lock,[this]{return stopping||!work.empty();});
                if(work.empty())return;
                next=std::move(work.front());work.pop_front();
            }
            try {
                if(!context){context.reset(ZSTD_createCCtx());if(!context)throw std::bad_alloc();}
                auto checksum=crc(next.raw);auto size=uint32_t(next.raw.size());
                Bytes packed(ZSTD_compressBound(next.raw.size()));
                auto n=ZSTD_compressCCtx(context.get(),packed.data(),packed.size(),next.raw.data(),next.raw.size(),3);
                if(ZSTD_isError(n))throw std::runtime_error(std::string("Zstd compression failed: ")+ZSTD_getErrorName(n));
                if(n<next.raw.size()) {packed.resize(n);next.result.set_value({std::move(packed),size,checksum,2});}
                else next.result.set_value({std::move(next.raw),size,checksum,0});
            } catch(...) {next.result.set_exception(std::current_exception());}
        }
    }
    void stop() noexcept {
        {std::lock_guard<std::mutex> lock(mutex);stopping=true;}
        ready.notify_all();for(auto& worker:workers)if(worker.joinable())worker.join();
    }
public:
    explicit BlockCompressor(size_t jobs) {
        if(jobs<1||jobs>16)throw std::runtime_error("compression jobs must be 1..16");
        try {for(size_t i=0;i<jobs;++i)workers.emplace_back([this]{loop();});}
        catch(...) {stop();throw;}
    }
    BlockCompressor(const BlockCompressor&)=delete;
    BlockCompressor& operator=(const BlockCompressor&)=delete;
    ~BlockCompressor() {stop();}
    std::future<Result> submit(Bytes raw) {
        Work item{std::move(raw),{}};auto result=item.result.get_future();
        {std::lock_guard<std::mutex> lock(mutex);work.push_back(std::move(item));}
        ready.notify_one();return result;
    }
};
class Dwf final:public Sink {
    static constexpr size_t limit=64*1024*1024;
    File f;size_t block_limit;bool compress;
    struct Index {uint64_t first,last,offset,end,count;};
    std::vector<Index> index;
    std::vector<V> state;std::vector<bool> seen;
    Bytes checkpoint,body,packed;uint64_t now=0,first=0,count=0;
    std::unique_ptr<ZSTD_CCtx,decltype(&ZSTD_freeCCtx)> ctx{nullptr,ZSTD_freeCCtx};
    struct Pending {uint64_t first,last,count;size_t raw_size;std::future<BlockCompressor::Result> result;};
    std::unique_ptr<BlockCompressor> compressor;
    std::deque<Pending> pending_blocks;
    size_t pending_bytes=0,pending_limit=0,pending_budget=limit,peak_pending_bytes=0,peak_pending_records=0;
    struct Small {
        std::array<uint8_t,40> data{};size_t size=0;
        void push(uint8_t b) {data[size++]=b;}
        void integer(uint64_t n) {while(n>=128) {push(uint8_t(n)|128);n>>=7;}push(uint8_t(n));}
        void plane(uint64_t n,int count) {for(int i=0;i<count;++i) {push(uint8_t(n));n>>=8;}}
        void append(const Small& b) {std::copy_n(b.data.begin(),b.size,data.begin()+size);size+=b.size;}
    };
    static Small encode(V v,const V* old) {
        Small b;auto m=mask(v.w);int size=(v.w+7)/8;
        if(v.b==0 && (v.a==0||v.a==m)) {b.push(v.a==0?0:1);return b;}
        if(v.b==m && (v.a==m||v.a==0)) {b.push(v.a==m?2:3);return b;}
        b.push(v.b?5:4);b.plane(v.a,size);if(v.b)b.plane(v.b,size);
        if(old) {
            Small delta;delta.push(6);
            for(auto x:{v.a^old->a,v.b^old->b}) {int n=0;for(auto y=x;y;y>>=8)++n;delta.integer(n);delta.plane(x,n);}
            if(delta.size<b.size)return delta;
        } return b;
    }
#ifdef DSIM_WIDE_VALUES
    static Bytes encode_wide(const V& v,const V* old) {
        if(wide_detail::all(v,0,0))return {0};
        if(wide_detail::all(v,~uint64_t(0),0))return {1};
        if(wide_detail::all(v,~uint64_t(0),~uint64_t(0)))return {2};
        if(wide_detail::all(v,0,~uint64_t(0)))return {3};
        const size_t count=size_t((v.w+7)/8);bool unknown=v.unknown();Bytes full{uint8_t(unknown?5:4)};
        for(size_t i=0;i<count;++i)full.push_back(uint8_t(v.word_a(i/8)>>(8*(i%8))));
        if(unknown)for(size_t i=0;i<count;++i)full.push_back(uint8_t(v.word_b(i/8)>>(8*(i%8))));
        if(old) {
            Bytes delta{6};
            for(int plane=0;plane<2;++plane){Bytes changes;changes.reserve(count);
                for(size_t i=0;i<count;++i){auto word=plane?v.word_b(i/8)^old->word_b(i/8):v.word_a(i/8)^old->word_a(i/8);changes.push_back(uint8_t(word>>(8*(i%8))));}
                while(!changes.empty()&&changes.back()==0)changes.pop_back();number(delta,changes.size());delta.insert(delta.end(),changes.begin(),changes.end());}
            if(delta.size()<full.size())return delta;
        }
        return full;
    }
#endif
    void record(const char* tag,const Bytes& raw) {
        if(raw.size()>limit)throw std::runtime_error("DWF1 record exceeds 64 MiB; reduce dump scope or block size");
        size_t n=raw.size();const uint8_t* data=raw.data();uint8_t codec=0;
        if(compress) {
            packed.resize(ZSTD_compressBound(raw.size()));
            auto result=ZSTD_compressCCtx(ctx.get(),packed.data(),packed.size(),raw.data(),raw.size(),3);
            if(ZSTD_isError(result))throw std::runtime_error(std::string("Zstd compression failed: ")+ZSTD_getErrorName(result));
            if(result<n) {n=result;data=packed.data();codec=2;}
        }
        Bytes head(tag,tag+4);head.push_back(codec);head.resize(8,0);
        little(head,raw.size(),4);little(head,n,4);little(head,crc(raw),4);f.write(head);f.write(data,n);
    }
    void reset() {
        checkpoint.clear();first=now;number(checkpoint,now);number(checkpoint,state.size());
        for(size_t i=0;i<state.size();++i) {
            if(!seen[i])checkpoint.push_back(8);
#ifdef DSIM_WIDE_VALUES
            else if(state[i].w>64){auto b=encode_wide(state[i],nullptr);checkpoint.insert(checkpoint.end(),b.begin(),b.end());}
#endif
            else {auto b=encode(state[i],nullptr);checkpoint.insert(checkpoint.end(),b.data.begin(),b.data.begin()+b.size);}
        }
        if(checkpoint.size()>limit/2)throw std::runtime_error("DWF1 checkpoint exceeds 32 MiB; reduce dump scope");
    }
    void commit_one() {
        auto item=std::move(pending_blocks.front());pending_blocks.pop_front();pending_bytes-=item.raw_size;
        auto record=item.result.get();
        Bytes head{'B','L','K','1',record.codec,0,0,0};
        little(head,record.raw_size,4);little(head,record.payload.size(),4);little(head,record.checksum,4);
        auto offset=f.bytes;f.write(head);f.write(record.payload);
        index.push_back({item.first,item.last,offset,f.bytes,item.count});++blocks;
    }
    void flush() {
        if(!count)return;
        Bytes raw=checkpoint;number(raw,count);raw.insert(raw.end(),body.begin(),body.end());
        if(compressor) {
            if(raw.size()>limit)throw std::runtime_error("DWF1 record exceeds 64 MiB; reduce dump scope or block size");
            if(raw.size()>pending_budget)throw std::runtime_error("DWF1 block exceeds asynchronous compression buffer budget");
            // At most two jobs per worker and 64 MiB of uncommitted raw data.
            // Completed results retain their raw-size charge until committed.
            while(!pending_blocks.empty()&&(pending_blocks.size()>=pending_limit||raw.size()>pending_budget-pending_bytes))commit_one();
            auto size=raw.size();auto result=compressor->submit(std::move(raw));
            pending_blocks.push_back({first,now,count,size,std::move(result)});pending_bytes+=size;
            peak_pending_bytes=std::max(peak_pending_bytes,pending_bytes);peak_pending_records=std::max(peak_pending_records,pending_blocks.size());
        } else {
            auto offset=f.bytes;record("BLK1",raw);index.push_back({first,now,offset,f.bytes,count});++blocks;
        }
        body.clear();count=0;reset();
    }
    void event(const Bytes& b) {
        if(body.size()+checkpoint.size()+b.size()+20>limit)flush();
        body.insert(body.end(),b.begin(),b.end());++count;
    }
    void event(const Small& b) {
        if(body.size()+checkpoint.size()+b.size+20>limit)flush();
        body.insert(body.end(),b.data.begin(),b.data.begin()+b.size);++count;
    }
    void boundary() {if(count>=block_limit)flush();}
public:
    Dwf(const std::string& path,const Dictionary& d,size_t block,bool zstd,size_t jobs=1,size_t budget=limit):f(path),block_limit(block),compress(zstd),
        state(d.widths.size()),seen(d.widths.size(),false) {
        if(jobs<1||jobs>16||(!zstd&&jobs!=1))throw std::runtime_error("DWF compression jobs must be 1..16 and require Zstd when greater than 1");
        if(!budget||budget>limit)throw std::runtime_error("DWF asynchronous compression buffer must be 1 byte..64 MiB");
        pending_budget=budget;
        if(compress) {ctx.reset(ZSTD_createCCtx());if(!ctx)throw std::bad_alloc();}
        body.reserve(std::min(block_limit*size_t(5),size_t(4*1024*1024)));
        f.write("DWF1P001");auto meta=d.metadata();record("META",Bytes(meta.begin(),meta.end()));reset();
        if(jobs>1){compressor=std::make_unique<BlockCompressor>(jobs);pending_limit=2*jobs;}
    }
    void time(uint64_t n) override {
        if(n<now)throw std::runtime_error("waveform time moved backwards");
        if(n!=now||(!count&&index.empty()&&pending_blocks.empty())) {Small b;b.push(0);b.integer(n-now);event(b);now=n;boundary();}
    }
    void value(size_t id,V v) override {
#ifdef DSIM_WIDE_VALUES
        if(v.w>64){auto b=encode_wide(v,seen[id]?&state[id]:nullptr);Bytes event_bytes{1};number(event_bytes,id);event_bytes.insert(event_bytes.end(),b.begin(),b.end());event(event_bytes);state[id]=v;seen[id]=true;++values;boundary();return;}
#endif
        auto b=encode(v,seen[id]?&state[id]:nullptr);Small event_bytes;event_bytes.push(1);event_bytes.integer(id);event_bytes.append(b);
        event(event_bytes);state[id]=v;seen[id]=true;++values;boundary();
    }
    void control(const std::string& name) override {
        auto s=array({name});Bytes b{2};number(b,s.size());b.insert(b.end(),s.begin(),s.end());event(b);boundary();
    }
    void close() override {
        flush();while(!pending_blocks.empty())commit_one();compressor.reset();std::string text="[";
        for(const auto& r:index) {if(text.size()>1)text+=',';text+='['+std::to_string(r.first)+','+std::to_string(r.last)+','+std::to_string(r.offset)+','+std::to_string(r.end)+','+std::to_string(r.count)+']';}
        text+=']';auto offset=f.bytes;record("INDX",Bytes(text.begin(),text.end()));Bytes footer;little(footer,offset,8);f.write(footer);f.write("DWFEND01");f.close();
    }
    uint64_t bytes() const override {return f.bytes;}
    std::pair<size_t,size_t> pending_peaks() const {return {peak_pending_records,peak_pending_bytes};}
};
// One producer hands immutable value snapshots to one writer. Encoding,
// compression, CRC, file ownership and index finalization live on that thread.
// Select an inclusive time interval without changing the simulation. Preserve
// the state immediately before the interval as an explicit initial snapshot.
// In async mode this adapter, like the encoder, belongs to the writer thread.
class WindowSink final:public Sink {
    std::unique_ptr<Sink> output;
    std::vector<V> state;
    uint64_t begin,end;
    bool seen=false,opened=false,ended=false;
public:
    WindowSink(std::unique_ptr<Sink> sink,const std::vector<int>& widths,uint64_t first,uint64_t last)
        :output(std::move(sink)),begin(first),end(last) {
        for(int width:widths)state.push_back(V::x(width));
    }
    void time(uint64_t time) override {
        if(ended)return;
        const bool initial=!seen;seen=true;
        if(time<begin)return;
        // A late $dumpvars cannot reconstruct state before its first sample.
        if(initial&&time>end){ended=true;return;}
        if(!opened) {
            if(!initial) {
                output->time(begin);output->control("$dumpvars");
                for(size_t i=0;i<state.size();++i)output->value(i,state[i]);
                output->control("$end");
            }
            opened=true;
        }
        output->time(std::min(time,end));
        if(time>end)ended=true;
    }
    void value(size_t id,V value) override {
        if(ended)return;
        if(opened)output->value(id,std::move(value));
        else state.at(id)=std::move(value);
    }
    void control(const std::string& text) override {if(opened&&!ended)output->control(text);}
    void close() override {output->close();values=output->values;blocks=output->blocks;}
    uint64_t bytes() const override {return output->bytes();}
};

class AsyncSink final:public Sink {
    struct Event {uint64_t time=0;size_t id=0;V value;std::string control;uint8_t kind=0;};
    struct Batch {std::vector<Event> events;size_t bytes=0;};
    static constexpr size_t batch_events=256,batch_bytes=65536;
    std::mutex mutex;
    std::condition_variable ready,space;
    std::deque<Batch> queue;
    Batch current;
    std::thread worker;
    std::exception_ptr failure;
    size_t budget,pending_bytes=0,peak_bytes=0,peak_batches=0,waits=0;
    bool finishing=false,closed=false;
    uint64_t output_bytes=0;
    void check() const {if(failure)std::rethrow_exception(failure);}
    void submit() {
        if(current.events.empty())return;
        std::unique_lock<std::mutex> lock(mutex);
        if(current.bytes>budget-pending_bytes)++waits;
        space.wait(lock,[&]{return failure||current.bytes<=budget-pending_bytes;});check();
        pending_bytes+=current.bytes;peak_bytes=std::max(peak_bytes,pending_bytes);
        queue.push_back(std::move(current));current=Batch{};
        peak_batches=std::max(peak_batches,queue.size());lock.unlock();ready.notify_one();
    }
    void append(Event event,size_t charge) {
        if(closed)throw std::runtime_error("asynchronous waveform writer is closed");
        if(charge>budget)throw std::runtime_error("waveform event exceeds asynchronous buffer budget");
        const size_t limit=std::min(budget,batch_bytes);
        if(!current.events.empty()&&(current.events.size()>=batch_events||current.bytes>=limit||charge>limit-current.bytes))submit();
        current.bytes+=charge;current.events.push_back(std::move(event));
        if(current.events.size()>=batch_events||current.bytes>=std::min(budget,batch_bytes))submit();
    }
    void loop(std::function<std::unique_ptr<Sink>()> create,std::promise<void> startup) noexcept {
        bool announced=false;
        try {
            auto sink=create();startup.set_value();announced=true;
            for(;;) {
                Batch batch;
                {
                    std::unique_lock<std::mutex> lock(mutex);
                    ready.wait(lock,[&]{return finishing||!queue.empty();});
                    if(queue.empty())break;
                    batch=std::move(queue.front());queue.pop_front();
                }
                for(auto& event:batch.events) {
                    if(event.kind==0)sink->time(event.time);
                    else if(event.kind==1)sink->value(event.id,std::move(event.value));
                    else sink->control(event.control);
                }
                {std::lock_guard<std::mutex> lock(mutex);pending_bytes-=batch.bytes;}
                space.notify_one();
            }
            sink->close();values=sink->values;blocks=sink->blocks;output_bytes=sink->bytes();
        } catch(...) {
            auto error=std::current_exception();
            {std::lock_guard<std::mutex> lock(mutex);failure=error;queue.clear();pending_bytes=0;}
            space.notify_all();
            if(!announced)try {startup.set_exception(error);}catch(...) {}
        }
    }
    void join() noexcept {
        {std::lock_guard<std::mutex> lock(mutex);finishing=true;}
        ready.notify_one();if(worker.joinable())worker.join();
    }
public:
    AsyncSink(std::function<std::unique_ptr<Sink>()> create,size_t bytes):budget(bytes) {
        if(!budget||budget>64*1024*1024)throw std::runtime_error("asynchronous waveform buffer must be 1 byte..64 MiB");
        std::promise<void> startup;auto initialized=startup.get_future();
        worker=std::thread([this,create=std::move(create),startup=std::move(startup)]() mutable {loop(std::move(create),std::move(startup));});
        try {initialized.get();}catch(...) {join();throw;}
    }
    ~AsyncSink() override {if(!closed)try {close();}catch(...) {join();}}
    void time(uint64_t time) override {Event event;event.time=time;append(std::move(event),sizeof(Event));}
    void value(size_t id,V value) override {
        const size_t charge=sizeof(Event)+(size_t(value.w)+63)/64*16;
        Event event;event.kind=1;event.id=id;event.value=std::move(value);append(std::move(event),charge);
    }
    void control(const std::string& text) override {Event event;event.kind=2;event.control=text;append(std::move(event),sizeof(Event)+text.size());}
    void close() override {
        if(closed){check();return;}
        try {submit();}catch(...) {closed=true;join();throw;}
        closed=true;join();check();
    }
    uint64_t bytes() const override {return closed?output_bytes:0;}
    std::array<size_t,3> queue_stats() const {return {peak_bytes,peak_batches,waits};}
};
} // namespace wave_detail

namespace wave_detail {
// Capture policy and codecs shared by serial and merged parallel streams.
class Capture {
    std::string path,format="dwf",mode="settled",timescale="1ns",codec="zstd";
    std::vector<std::string> scope_filters,includes,excludes;
    uint64_t window_begin=0,window_end=UINT64_MAX;
    bool time_window=false;
    size_t block_events=16384;
    size_t compression_jobs=1,buffer_bytes=8*1024*1024;
    bool async_output=false,explicit_buffer=false;
    bool explicit_path=false;
    size_t depth=0;
    bool stats=false,started=false,first=true;
    size_t declaration_count=0;
    wave_detail::Dictionary dict;
    std::unordered_map<int,size_t> ids;
    std::vector<uint8_t> dirty;
    std::vector<V> last_values,current_values;
    std::vector<size_t> pending;
    std::unique_ptr<wave_detail::Sink> sink;
    static uint64_t integer(const std::string& text) {
        if(text.empty()||text.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("waveform option requires unsigned integer");
        size_t used=0;auto n=std::stoull(text,&used);if(used!=text.size())throw std::runtime_error("invalid waveform integer");return n;
    }
    // '*' and '?' are globs; brackets are literal so unpacked array names
    // such as top.mem[3] need no shell-style character-class escaping.
    static bool matches(const std::string& pattern,const std::string& name) {
        size_t p=0,n=0,star=std::string::npos,retry=0;
        while(n<name.size()) {
            if(p<pattern.size()&&(pattern[p]=='?'||pattern[p]==name[n])){++p;++n;}
            else if(p<pattern.size()&&pattern[p]=='*'){star=p++;retry=n;}
            else if(star!=std::string::npos){p=star+1;n=++retry;}
            else return false;
        }
        while(p<pattern.size()&&pattern[p]=='*')++p;
        return p==pattern.size();
    }
public:
    uint64_t event_limit=0;
    bool has_event_limit=false;
    void change(uint64_t time,size_t slot,V value) {
        if(mode=="ordered") {sink->time(time);sink->value(slot,value);}
        else {current_values[slot]=value;if(!dirty[slot]) {dirty[slot]=1;pending.push_back(slot);}}
    }
    void tick(uint64_t time) {
        sink->time(time);
        if(mode=="ordered")return;
        if(first)sink->control("$dumpvars");
        for(auto id:pending) {auto value=current_values[id];if(first||!last_values[id].same(value)) {sink->value(id,value);last_values[id]=value;}dirty[id]=0;}
        pending.clear();if(first) {sink->control("$end");first=false;}
    }
public:
    Capture(int argc,char** argv,const std::string& compiled_timescale={},bool dump_tasks=false) {
        if(!compiled_timescale.empty())timescale=compiled_timescale;
        if(dump_tasks){path="verilog.dump";format="vcd";}
        bool options=false,explicit_format=false;
        for(int i=1;i<argc;++i) {
            std::string a=argv[i];
            if(a=="--wave-stats") {stats=true;options=true;continue;}
            if(a=="--wave-async") {async_output=true;options=true;continue;}
            if(i+1>=argc)throw std::runtime_error("missing value for "+a);
            std::string v=argv[++i];
            if(a=="--max-events") {event_limit=integer(v);has_event_limit=true;continue;}
            options=true;
            if(a=="--waveform"){path=v;explicit_path=true;}
            else if(a=="--wave-format"){format=v;explicit_format=true;}
            else if(a=="--wave-mode")mode=v;
            else if(a=="--wave-scope"||a=="--wave-include"||a=="--wave-exclude") {
                if(v.empty())throw std::runtime_error(a+" requires a nonempty selector");
                (a=="--wave-scope"?scope_filters:a=="--wave-include"?includes:excludes).push_back(v);
            }
            else if(a=="--wave-start") {window_begin=integer(v);time_window=true;}
            else if(a=="--wave-end") {window_end=integer(v);time_window=true;}
            else if(a=="--wave-timescale")timescale=v;
            else if(a=="--wave-codec")codec=v;
            else if(a=="--wave-block-events") {auto n=integer(v);if(n<1||n>1000000)throw std::runtime_error("wave block events must be 1..1000000");block_events=size_t(n);}
            else if(a=="--wave-compression-jobs") {auto n=integer(v);if(n<1||n>16)throw std::runtime_error("wave compression jobs must be 1..16");compression_jobs=size_t(n);}
            else if(a=="--wave-buffer-bytes") {auto n=integer(v);if(n<1024||n>64*1024*1024)throw std::runtime_error("wave buffer bytes must be 1024..67108864");buffer_bytes=size_t(n);explicit_buffer=true;}
            else if(a=="--wave-depth") {auto n=integer(v);if(n>10000)throw std::runtime_error("wave depth must be 0..10000");depth=size_t(n);}
            else throw std::runtime_error("unknown simulation option "+a);
        }
        if(!explicit_format&&explicit_path) {
            const auto suffix=path.size()>=4?path.substr(path.size()-4):std::string();
            if(suffix==".vcd")format="vcd";
            else if(suffix==".dwf")format="dwf";
        }
        if(path.empty()&&options)throw std::runtime_error("wave options require --waveform PATH");
        if(format!="dwf"&&format!="vcd")throw std::runtime_error("wave format must be dwf or vcd");
        if(mode!="ordered"&&mode!="settled")throw std::runtime_error("wave mode must be ordered or settled");
        if(codec!="raw"&&codec!="zstd")throw std::runtime_error("native wave codec must be raw or zstd");
        if(compression_jobs>1&&(format!="dwf"||codec!="zstd"))throw std::runtime_error("wave compression jobs greater than 1 require DWF/Zstd");
        if(async_output&&(format!="dwf"||codec!="zstd"||compression_jobs!=1))throw std::runtime_error("wave async requires DWF/Zstd and exactly one compression job");
        if(explicit_buffer&&!async_output)throw std::runtime_error("wave buffer bytes requires --wave-async");
        if(window_begin>window_end)throw std::runtime_error("wave start must not exceed wave end");
        bool valid=false;for(const auto& scale:{"1","10","100"})for(const auto& unit:{"s","ms","us","ns","ps","fs"})if(timescale==std::string(scale)+unit)valid=true;
        if(!valid)throw std::runtime_error("wave timescale must be 1/10/100 followed by s/ms/us/ns/ps/fs");
        if(!compiled_timescale.empty()&&timescale!=compiled_timescale)throw std::runtime_error("wave timescale must match compiled simulation precision "+compiled_timescale);
    }
    bool enabled() const {return !path.empty();}
    bool ordered() const {return mode=="ordered";}
    void dumpfile(const std::string& file) {
        if(started||explicit_path)return;
        if(file.empty()||file.find('\0')!=std::string::npos)throw std::runtime_error("$dumpfile requires a nonempty filename without NUL");
        path=file;
    }
    void declare(int signal,int width,std::vector<std::string> scope,std::string name,int high,int low,bool net,bool packed,int real_type=0) {
        if(!enabled())return;
        std::string full;
        bool selected=scope_filters.empty()&&(!depth||scope.size()-std::min(scope.size(),size_t(1))<depth);
        for(size_t i=0;i<scope.size();++i) {
            auto& p=scope[i];if(!p.empty()&&p.front()=='\\')p.erase(0,1);
            if(!full.empty())full+='.';full+=p;
            if((!depth||scope.size()-i-1<depth)&&std::find(scope_filters.begin(),scope_filters.end(),full)!=scope_filters.end())selected=true;
        }
        if(!selected)return;
        if(!full.empty())full+='.';
        full+=!name.empty()&&name.front()=='\\'?name.substr(1):name;
        if(!includes.empty()&&std::none_of(includes.begin(),includes.end(),[&](const auto& pattern){return matches(pattern,full);}))return;
        if(std::any_of(excludes.begin(),excludes.end(),[&](const auto& pattern){return matches(pattern,full);}))return;
        if(started)throw std::runtime_error("wave dictionary already finalized");
        if(std::abs(int64_t(high)-low)+1!=width)throw std::runtime_error("wave declaration width mismatch");
        auto found=ids.emplace(signal,dict.signal_ids.size());
        if(found.second) {dict.signal_ids.push_back(signal);dict.widths.push_back(width);dict.real_types.push_back(real_type);}
        wave_detail::identifier(name);for(const auto& p:scope)wave_detail::identifier(p);
        dict.aliases.push_back({found.first->second,std::move(scope),std::move(name),real_type?"real":net?"wire":"reg",high,low,real_type?false:packed});
    }
    const std::vector<int>& signals() const {return dict.signal_ids;}
    template<class Get> void start(uint64_t now,Get get) {
        if(!enabled())return;
        if(started)throw std::runtime_error("wave capture already started");
        if(dict.signal_ids.empty())throw std::runtime_error("wave scope selected no signals (check scope/include/exclude/depth)");
        dict.finalize(timescale,mode);
        if(async_output) {
            // Copy the finalized dictionary before capture releases its metadata.
            sink=std::make_unique<wave_detail::AsyncSink>([file=path,dictionary=dict,block=block_events,window=time_window,begin=window_begin,end=window_end]() -> std::unique_ptr<Sink> {
                std::unique_ptr<Sink> output=std::make_unique<Dwf>(file,dictionary,block,true,1);
                if(window)output=std::make_unique<WindowSink>(std::move(output),dictionary.widths,begin,end);
                return output;
            },buffer_bytes);
        }
        else {
            if(format=="vcd")sink=std::make_unique<Vcd>(path,dict);
            else sink=std::make_unique<Dwf>(path,dict,block_events,codec=="zstd",compression_jobs);
            if(time_window)sink=std::make_unique<WindowSink>(std::move(sink),dict.widths,window_begin,window_end);
        }
        declaration_count=dict.aliases.size();
        std::vector<wave_detail::Alias>().swap(dict.aliases);
        std::vector<std::vector<std::string>>().swap(dict.header);
        std::vector<int>().swap(dict.widths);
        std::unordered_map<int,size_t>().swap(ids);
        if(mode=="settled") {dirty.assign(dict.signal_ids.size(),0);last_values.resize(dict.signal_ids.size());current_values.resize(dict.signal_ids.size());}
        sink->time(now);
        if(mode=="ordered") {
            sink->control("$dumpvars");for(size_t i=0;i<dict.signal_ids.size();++i)sink->value(i,get(dict.signal_ids[i]));sink->control("$end");
        } else for(size_t i=0;i<dict.signal_ids.size();++i) {current_values[i]=get(dict.signal_ids[i]);dirty[i]=1;pending.push_back(i);}
        started=true;
    }
    template<class Get> void snapshot(uint64_t time,const std::string& control,Get get,bool scalar_unknown=false) {
        tick(time);sink->control(control);
        for(size_t i=0;i<dict.signal_ids.size();++i) {
            auto value=get(dict.signal_ids[i]);
            // VCS W-2024.09's default VCD dumpoff invalidates scalar
            // streams and retains vector values. Keep this observable policy.
            if(scalar_unknown&&value.w!=1)continue;
            if(scalar_unknown)value=V::x(value.w);
            sink->value(i,value);
            if(mode=="settled")last_values[i]=value;
        }
        sink->control("$end");
    }
    void close() {
        if(!started)return;
        sink->close();started=false;
        if(stats)std::cerr<<"WAVE {\"signals\":"<<dict.signal_ids.size()<<",\"declarations\":"<<declaration_count<<",\"values\":"<<sink->values<<",\"blocks\":"<<sink->blocks<<",\"bytes\":"<<sink->bytes()<<"}\n";
        if(stats&&async_output) {
            const auto peaks=static_cast<AsyncSink*>(sink.get())->queue_stats();
            std::cerr<<"WAVE_ASYNC {\"writer_threads\":1,\"buffer_bytes\":"<<buffer_bytes<<",\"peak_pending_bytes\":"<<peaks[0]<<",\"peak_batches\":"<<peaks[1]<<",\"backpressure_waits\":"<<peaks[2]<<"}\n";
        }
    }

};

} // namespace wave_detail

class WaveCapture {
    Sim& sim;
    wave_detail::Capture capture;
    bool started=false;
    std::vector<int> slots;
    bool task_mode=false,selected=false,capturing=false,dumping=true;
    uint64_t first_selection=0,control_time=UINT64_MAX;
    unsigned control_seen=0,control_pending=0;
    std::vector<wave_detail::Alias> catalog;
    std::vector<int> catalog_signals,writer_slots;
    std::unordered_map<int,size_t> catalog_ids;
    std::vector<V> observed;
    std::vector<V> initial_values;
    std::vector<std::pair<size_t,V>> initial_changes;
public:
    struct Target {std::vector<std::string> scope;std::string name;};
private:
    struct Selection {uint64_t depth;std::vector<Target> targets;};
    std::vector<Selection> selections;
    static std::string plain(std::string name) {
        if(!name.empty()&&name.front()=='\\')name.erase(0,1);
        return name;
    }
    bool wanted(const wave_detail::Alias& alias) const {
        for(const auto& request:selections)for(const auto& target:request.targets) {
            if(alias.scope.size()<target.scope.size()||!std::equal(target.scope.begin(),target.scope.end(),alias.scope.begin()))continue;
            if(!target.name.empty()) {
                if(alias.scope==target.scope&&alias.name==target.name)return true;
            } else if(!request.depth||alias.scope.size()-target.scope.size()<request.depth)return true;
        }
        return false;
    }
    V observed_value(int id) const {return observed.at(catalog_ids.at(id));}
    void task_tick(uint64_t time) {
        if(!selected)return;
        if(!capturing) {
            for(const auto& alias:catalog)if(wanted(alias))
                capture.declare(catalog_signals[alias.id],observed[alias.id].w,alias.scope,alias.name,
                                alias.high,alias.low,alias.type=="wire",alias.packed,wave_detail::real_width(observed[alias.id]));
            writer_slots.assign(catalog_signals.size(),-1);
            const auto& ids=capture.signals();
            for(size_t i=0;i<ids.size();++i)writer_slots[catalog_ids.at(ids[i])]=int(i);
            capture.start(first_selection,[this](int id){
                return capture.ordered()?initial_values.at(catalog_ids.at(id)):observed_value(id);
            });
            capturing=true;
            for(const auto& change:initial_changes) {
                int slot=writer_slots.at(change.first);
                if(slot>=0)capture.change(first_selection,size_t(slot),change.second);
            }
            std::vector<V>().swap(initial_values);
            std::vector<std::pair<size_t,V>>().swap(initial_changes);
        }
        capture.tick(time);
        auto get=[this](int id){return observed_value(id);};
        if(control_pending&1)capture.snapshot(time,"$dumpoff",get,true);
        if(control_pending&2)capture.snapshot(time,"$dumpon",get);
        if(control_pending&4)capture.snapshot(time,"$dumpall",get);
        if(control_pending&1)dumping=false;
        if(control_pending&2)dumping=true;
        control_pending=0;
    }
#ifdef DSIM_COMPACT_GATES
    std::vector<int> compact_slots;
#endif
    static void change_hook(void* self,uint64_t time,int id,V value) {
        auto& wave=*static_cast<WaveCapture*>(self);
#ifdef DSIM_COMPACT_GATES
        int slot=id<0?wave.compact_slots.at(size_t(-int64_t(id)-1)):wave.slots.at(size_t(id));
#else
        int slot=wave.slots.at(size_t(id));
#endif
        if(slot<0)return;
        if(wave.task_mode) {
            wave.observed[size_t(slot)]=value;
            if(wave.selected&&!wave.capturing&&wave.capture.ordered())wave.initial_changes.emplace_back(size_t(slot),value);
            if(!wave.capturing||!wave.dumping)return;
            slot=wave.writer_slots.at(size_t(slot));
        }
        if(slot>=0)wave.capture.change(time,size_t(slot),value);
    }
    static void tick_hook(void* self,uint64_t time) {
        auto& wave=*static_cast<WaveCapture*>(self);
        if(wave.task_mode)wave.task_tick(time);else wave.capture.tick(time);
    }
public:
    WaveCapture(Sim& s,int argc,char** argv,const std::string& compiled_timescale={},bool dump_tasks=false)
        :sim(s),capture(argc,argv,compiled_timescale,dump_tasks),task_mode(dump_tasks) {
        if(capture.has_event_limit)sim.limit=capture.event_limit;
    }
    WaveCapture(const WaveCapture&)=delete;
    WaveCapture& operator=(const WaveCapture&)=delete;
    bool enabled() const {return capture.enabled();}
    void declare(int signal,std::vector<std::string> scope,std::string name,int high,int low,bool net,bool packed) {
        if(task_mode) {
            if(started)throw std::runtime_error("wave dictionary already finalized");
            auto found=catalog_ids.emplace(signal,catalog_signals.size());
            if(found.second)catalog_signals.push_back(signal);
            for(auto& p:scope)p=plain(p);
            catalog.push_back({found.first->second,std::move(scope),plain(std::move(name)),wave_detail::real_width(sim.get(signal))?"real":net?"wire":"reg",high,low,packed});
            return;
        }
        if(enabled())capture.declare(signal,sim.get(signal).w,std::move(scope),std::move(name),high,low,net,packed,wave_detail::real_width(sim.get(signal)));
    }
    void dumpfile(const std::string& path) {if(!capturing)capture.dumpfile(path);}
    void dumpvars(uint64_t time,V depth,std::vector<Target> targets) {
        // Depth is evaluated at the call, not later at speculative commit.
        bool invalid=depth.b!=0;
#ifdef DSIM_WIDE_VALUES
        for(size_t i=1;i<size_t((depth.w+63)/64);++i)invalid=invalid||depth.word_a(i)||depth.word_b(i);
#endif
        if(invalid||depth.a>10000)throw std::runtime_error("$dumpvars depth must be a known integer in 0..10000");
        if(selected&&(capturing||time!=first_selection))return;
        if(!selected){selected=true;first_selection=time;if(capture.ordered())initial_values=observed;}
        for(auto& target:targets){for(auto& p:target.scope)p=plain(p);target.name=plain(target.name);}
        selections.push_back({depth.a,std::move(targets)});
    }
    void dump_control(uint64_t time,unsigned kind) {
        if(!selected)return;
        if(control_time!=time){control_time=time;control_seen=control_pending=0;}
        // Opposite controls cancel an outstanding request. Each kind is
        // scheduled at most once at this timestamp (including cancelled ones).
        // This retains VCS's observed off/on/off behaviour in one time slot.
        if(kind==1)control_pending&=~2U;
        else if(kind==2)control_pending&=~1U;
        if(control_seen&kind)return;
        control_seen|=kind;control_pending|=kind;
        if(capturing)capture.tick(time);
    }
    void gate_net(int signal,const std::vector<std::string>& scope,const std::string& name) {
        declare(signal,scope,name,0,0,true,false);
    }
    void start() {
        if(!enabled())return;
        if(started)throw std::runtime_error("wave capture already started");
        slots.assign(sim.signals.size(),-1);
#ifdef DSIM_COMPACT_GATES
        compact_slots.assign(sim.compact_signal_count(),-1);
#endif
        const auto& signals=task_mode?catalog_signals:capture.signals();
        for(size_t i=0;i<signals.size();++i) {
            int id=signals[i];
#ifdef DSIM_COMPACT_GATES
            if(id<0)compact_slots.at(size_t(-int64_t(id)-1))=int(i);else
#endif
            slots.at(size_t(id))=int(i);
        }
        if(task_mode)for(int id:signals)observed.push_back(sim.get(id));
        else capture.start(sim.now,[this](int id){return sim.get(id);});
        sim.attach_wave(this,change_hook,tick_hook);started=true;
    }
    void close() {
        if(!started)return;
        sim.attach_wave(nullptr,nullptr,nullptr);started=false;capture.close();
    }
    ~WaveCapture() {if(started)sim.attach_wave(nullptr,nullptr,nullptr);}
};
} // namespace dsim
