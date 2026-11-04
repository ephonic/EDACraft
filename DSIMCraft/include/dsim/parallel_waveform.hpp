#pragma once
// Include before runtime.hpp. Workers record private streams; only the
// coordinator writes the shared VCD/DWF after a window has committed.
#ifndef DSIM_WAVE_ENABLED
#define DSIM_WAVE_ENABLED 1
#endif
#include "parallel.hpp"
#include "waveform.hpp"

namespace dsim {
class ParallelWaveCapture {
    struct Event {uint64_t time;size_t slot;V value;};
    struct Source {
        Sim* sim;
        std::vector<int> slots;
#ifdef DSIM_COMPACT_GATES
        std::vector<int> compact_slots;
#endif
        std::vector<Event> events;
        explicit Source(Sim& kernel):sim(&kernel) {}
    };
    struct Signal {size_t partition;int local;};
    std::vector<std::unique_ptr<Source>> sources;
    std::vector<Signal> signals;
    std::map<std::pair<size_t,int>,int> ids;
    wave_detail::Capture capture;
    std::function<std::shared_ptr<std::function<void(uint64_t)>>(std::function<void(uint64_t)>)> subscribe;
    std::shared_ptr<std::function<void(uint64_t)>> subscription;
    uint64_t current_time=0,committed_end=0;
    bool started=false,closed=false,sink_failed=false;
    static void change_hook(void* context,uint64_t time,int id,V value) {
        auto& source=*static_cast<Source*>(context);
#ifdef DSIM_COMPACT_GATES
        int slot=id<0?source.compact_slots.at(size_t(-int64_t(id)-1)):source.slots.at(size_t(id));
#else
        int slot=source.slots.at(size_t(id));
#endif
        if(slot>=0)source.events.push_back({time,size_t(slot),value});
    }
    // Partition-local tick callbacks are intentionally not written. The merged
    // stream emits ticks around value changes and once at the final horizon,
    // independently of worker count and conservative window size.
    static void tick_hook(void*,uint64_t) {}
    void commit(uint64_t end) {
        struct Cursor {size_t partition,index;};
        auto later=[this](Cursor a,Cursor b) {
            const auto& left=sources[a.partition]->events[a.index];
            const auto& right=sources[b.partition]->events[b.index];
            return left.time!=right.time?left.time>right.time:
                a.partition!=b.partition?a.partition>b.partition:a.index>b.index;
        };
        std::priority_queue<Cursor,std::vector<Cursor>,decltype(later)> ready(later);
        for(size_t i=0;i<sources.size();++i)if(!sources[i]->events.empty())ready.push({i,0});
        while(!ready.empty()) {
            auto cursor=ready.top();ready.pop();
            const auto& events=sources[cursor.partition]->events;
            const auto& event=events[cursor.index];
            if(event.time<current_time||event.time>end)
                throw std::runtime_error("parallel waveform event outside the committed window");
            if(event.time!=current_time) {capture.tick(current_time);current_time=event.time;}
            capture.change(event.time,event.slot,event.value);
            if(++cursor.index<events.size())ready.push(cursor);
        }
        capture.tick(current_time);
        for(auto& source:sources)source->events.clear();
        committed_end=end;
    }
    void detach() {
        subscription.reset();
        for(auto& source:sources)source->sim->attach_wave(nullptr,nullptr,nullptr);
        started=false;
    }
public:
    // Engine may be ConservativeSim or AutoConservativeSim. Both must outlive
    // this capture. Use physical partition IDs (plan().owner[node] for Auto).
    template<class Engine> ParallelWaveCapture(Engine& engine,int argc,char** argv,const std::string& compiled_timescale={})
        :capture(argc,argv,compiled_timescale) {
        for(size_t i=0;i<engine.partition_count();++i) {
            sources.push_back(std::make_unique<Source>(engine.partition_kernel(i)));
            if(capture.has_event_limit)sources.back()->sim->limit=capture.event_limit;
        }
        subscribe=[&engine](std::function<void(uint64_t)> fn){return engine.observe_committed_windows(std::move(fn));};
    }
    ParallelWaveCapture(const ParallelWaveCapture&)=delete;
    ParallelWaveCapture& operator=(const ParallelWaveCapture&)=delete;
    bool enabled() const {return capture.enabled();}
    void declare(size_t partition,int signal,std::vector<std::string> scope,std::string name,
                 int high,int low,bool net,bool packed) {
        if(!enabled())return;
        if(started||closed)throw std::runtime_error("parallel wave dictionary already finalized");
        auto& sim=*sources.at(partition)->sim;
        auto found=ids.emplace(std::make_pair(partition,signal),int(signals.size()));
        if(found.second)signals.push_back({partition,signal});
        capture.declare(found.first->second,sim.get(signal).w,std::move(scope),std::move(name),high,low,net,packed,wave_detail::real_width(sim.get(signal)));
    }
    void gate_net(size_t partition,int signal,const std::vector<std::string>& scope,const std::string& name) {
        declare(partition,signal,scope,name,0,0,true,false);
    }
    void start() {
        if(!enabled())return;
        if(started||closed)throw std::runtime_error("parallel wave capture already started or closed");
        if(sources.empty())throw std::runtime_error("parallel wave capture requires partitions");
        const auto precision=sources.front()->sim->time_precision_fs;
        for(auto& source:sources) {
            if(source->sim->now||source->sim->time_precision_fs!=precision)
                throw std::runtime_error("start parallel wave capture at tick zero with equal time precision");
            source->slots.assign(source->sim->signals.size(),-1);
#ifdef DSIM_COMPACT_GATES
            source->compact_slots.assign(source->sim->compact_signal_count(),-1);
#endif
        }
        const auto& selected=capture.signals();
        for(size_t slot=0;slot<selected.size();++slot) {
            const auto& signal=signals.at(size_t(selected[slot]));auto& source=*sources[signal.partition];
#ifdef DSIM_COMPACT_GATES
            if(signal.local<0)source.compact_slots.at(size_t(-int64_t(signal.local)-1))=int(slot);else
#endif
            source.slots.at(size_t(signal.local))=int(slot);
        }
        // Register before opening the file so a frozen engine fails cleanly.
        subscription=subscribe([this](uint64_t end){
            try {commit(end);}catch(...) {sink_failed=true;throw;}
        });
        size_t attached=0;
        try {
            capture.start(0,[this](int id){const auto& signal=signals.at(size_t(id));return sources[signal.partition]->sim->get(signal.local);});
            for(auto& source:sources) {
                source->sim->attach_wave(source.get(),change_hook,tick_hook);++attached;
            }
            started=true;
        }catch(...) {
            for(size_t i=0;i<attached;++i)sources[i]->sim->attach_wave(nullptr,nullptr,nullptr);
            subscription.reset();throw;
        }
    }
    void close() {
        if(!started)return;
        detach();closed=true;
        // Partial work from a failed/uncommitted window is never published.
        for(auto& source:sources)source->events.clear();
        if(!sink_failed)capture.tick(committed_end);
        capture.close();
    }
    ~ParallelWaveCapture() {if(started)detach();}
};
} // namespace dsim
