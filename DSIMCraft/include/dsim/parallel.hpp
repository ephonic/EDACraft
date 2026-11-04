#pragma once
// Experimental conservative partition execution. Include before runtime.hpp.
// Each partition owns a separate Sim. Cross-partition channels require a
// strictly positive integral delay; zero-delay domains stay in one partition.
#ifndef DSIM_PARALLEL_ENABLED
#define DSIM_PARALLEL_ENABLED 1
#endif
#include "runtime.hpp"
#include "partition.hpp"
#include <atomic>
#include <condition_variable>
#include <exception>
#include <mutex>
#include <thread>

namespace dsim {
namespace parallel_detail {
class Workers {
    std::vector<std::thread> threads;
    std::mutex mutex;
    std::condition_variable work,done;
    bool stopping=false;
    uint64_t generation=0;
    size_t remaining=0,total=0;
    std::atomic<size_t> next{0};
    std::function<void(size_t)> task;
    std::exception_ptr failure;
public:
    explicit Workers(size_t count) {
        if(!count)throw std::runtime_error("parallel worker count must be positive");
        try {
            for(size_t i=0;i<count;++i)threads.emplace_back([this]{
                uint64_t seen=0;
                for(;;) {
                    std::unique_lock<std::mutex> lock(mutex);
                    work.wait(lock,[&]{return stopping||generation!=seen;});
                    if(stopping)return;
                    seen=generation;lock.unlock();
                    for(;;) {
                        auto index=next.fetch_add(1,std::memory_order_relaxed);if(index>=total)break;
                        try{task(index);}catch(...){std::lock_guard<std::mutex> hold(mutex);if(!failure)failure=std::current_exception();}
                    }
                    lock.lock();if(--remaining==0)done.notify_one();
                }
            });
        }catch(...){stop();throw;}
    }
    Workers(const Workers&)=delete;
    Workers& operator=(const Workers&)=delete;
    void stop() {
        {std::lock_guard<std::mutex> hold(mutex);stopping=true;}work.notify_all();
        for(auto& thread:threads)if(thread.joinable())thread.join();
    }
    ~Workers(){stop();}
    void each(size_t count,std::function<void(size_t)> fn) {
        std::unique_lock<std::mutex> lock(mutex);
        task=std::move(fn);total=count;next.store(0,std::memory_order_relaxed);
        remaining=threads.size();failure=nullptr;++generation;work.notify_all();
        done.wait(lock,[&]{return remaining==0;});task={};
        if(failure)std::rethrow_exception(failure);
    }
};
}
class ConservativeSim {
    struct Link {int source,destination,signal,driver;uint64_t delay;};
    struct Message {size_t link;uint64_t time;V value;};
    struct Output {uint64_t time;size_t partition,order;std::string text;};
    struct Partition {
        Sim sim;
        std::vector<Link> links;
        std::vector<Message> outbox;
        std::vector<Output> output;
    };
    // Stable addresses: process closures and observers refer to these Sims.
    std::vector<std::unique_ptr<Partition>> partitions;
    // Weak ownership lets sinks detach without leaving a dangling callback.
    // The coordinator invokes these only after all partition effects commit.
    std::vector<std::weak_ptr<std::function<void(uint64_t)>>> window_observers;
    parallel_detail::Workers workers;
    uint64_t lookahead=UINT64_MAX,next_start=0,max_window;
    bool started=false,failed=false,transactional_finish=false,stopped=false;
    uint64_t stop_time=0;
    size_t stop_partition=0;
    void check_setup() const {if(started)throw std::runtime_error("parallel topology is already frozen");}
#ifdef DSIM_FINAL_ENABLED
    bool finalization_done=false;
    void finalize_partitions() {
        if(finalization_done)return;
        finalization_done=true;
        uint64_t time=0;for(const auto& p:partitions)time=std::max(time,p->sim.now);
        if(stopped)time=stop_time;
        try {
            for(auto& p:partitions){p->sim.now=time;p->sim.finalize();}
            for(auto& weak:window_observers)if(auto observer=weak.lock())(*observer)(time);
            std::vector<Output> output;
            for(auto& p:partitions){for(auto& item:p->output)output.push_back(std::move(item));p->output.clear();}
            std::stable_sort(output.begin(),output.end(),[](const Output& a,const Output& b){return a.partition!=b.partition?a.partition<b.partition:a.order<b.order;});
            for(const auto& item:output)std::cout<<item.text;
        }catch(...){failed=true;throw;}
    }
#endif
public:
    struct Stats {uint64_t windows=0,messages=0,window_replays=0;size_t partitions=0;} stats;
    explicit ConservativeSim(size_t worker_count,uint64_t window_ticks=1024):workers(worker_count),max_window(window_ticks) {
        if(!max_window)throw std::runtime_error("parallel window must be positive");
    }
    ConservativeSim(const ConservativeSim&)=delete;
    ConservativeSim& operator=(const ConservativeSim&)=delete;
    size_t partition() {
        check_setup();size_t id=partitions.size();partitions.push_back(std::make_unique<Partition>());
        auto* p=partitions.back().get();
        p->sim.redirect_output([p,id](uint64_t time,const std::string& text){p->output.push_back({time,id,p->output.size(),text});});
        stats.partitions=partitions.size();return id;
    }
    Sim& kernel(size_t id) {return partitions.at(id)->sim;}
    size_t partition_count() const {return partitions.size();}
    Sim& partition_kernel(size_t id) {return kernel(id);}
    std::shared_ptr<std::function<void(uint64_t)>> observe_committed_windows(std::function<void(uint64_t)> fn) {
        check_setup();
        auto token=std::make_shared<std::function<void(uint64_t)>>(std::move(fn));
        window_observers.push_back(token);return token;
    }
    void enable_global_finish() {check_setup();transactional_finish=true;}
    bool finished() const {return stopped;}
    uint64_t finish_time() const {
        if(!stopped)throw std::runtime_error("parallel engine has not finished");
        return stop_time;
    }
    size_t finish_partition() const {
        if(!stopped)throw std::runtime_error("parallel engine has not finished");
        return stop_partition;
    }
    void connect(size_t from,int source,size_t to,int destination,uint64_t delay,int driver=-1) {
        check_setup();if(!delay)throw std::runtime_error("parallel channels require positive delay");
        auto& left=*partitions.at(from);auto& right=*partitions.at(to);
        if(left.sim.now||right.sim.now)throw std::runtime_error("configure parallel channels before simulation");
        if(left.sim.get(source).w!=right.sim.get(destination).w)throw std::runtime_error("parallel channel width mismatch");
#ifdef DSIM_COMPACT_GATES
        if((driver>=0)!=right.sim.is_net(destination))throw std::runtime_error("parallel net input requires a driver; variable input requires -1");
#else
        if((driver>=0)!=right.sim.signals.at(destination).net)throw std::runtime_error("parallel net input requires a driver; variable input requires -1");
#endif
        // Independent partitions need no resolved-value observer. Besides
        // avoiding a callback on every store, this leaves guarded native
        // integer loops available. Install only before the first real channel.
        if(left.links.empty()) {
            auto* p=&left;
            p->sim.observe_resolved([p](uint64_t time,int signal,V value){
                for(size_t i=0;i<p->links.size();++i)if(p->links[i].source==signal) {
                    auto delay=p->links[i].delay;
                    if(delay>UINT64_MAX-time)throw std::runtime_error("parallel channel time overflow");
                    p->outbox.push_back({i,time+delay,value});
                }
            });
        }
        auto index=left.links.size();left.links.push_back({source,int(to),destination,driver,delay});
        left.outbox.push_back({index,delay,left.sim.get(source)});
        lookahead=std::min(lookahead,delay);
    }
    void run() {
        if(failed)throw std::runtime_error("parallel engine is in a failed state");
#ifdef DSIM_FINAL_ENABLED
        if(finalization_done)return;
#endif
        if(!started)run_until(0);
        while(!stopped) {
            bool found=false;uint64_t next=0;
            for(auto& p:partitions) {
                uint64_t time=0;
                if(p->sim.next_event_time(time)&&(!found||time<next)){next=time;found=true;}
                for(const auto& message:p->outbox)if(!found||message.time<next){next=message.time;found=true;}
            }
            if(!found){
                // Idle workers retain their own last event time during a
                // natural window. The design ends at the last real activity,
                // independently of window size (and before any final blocks).
                uint64_t time=0;for(auto& p:partitions)time=std::max(time,p->sim.now);
                for(auto& p:partitions)p->sim.now=time;
                next_start=time+1;
#ifdef DSIM_FINAL_ENABLED
                finalize_partitions();
#endif
                return;
            }
            if(next==UINT64_MAX)throw std::runtime_error("parallel activity at UINT64_MAX is not supported");
            // Skip empty gaps, then batch a lookahead-safe span. Kernels do
            // not advance idle time; future channel messages cannot arrive in
            // this window, and global finish uses the existing rollback fence.
            if(next<next_start)throw std::runtime_error("parallel event precedes committed frontier");
            auto width=std::min(max_window,lookahead);
            auto end=UINT64_MAX-1-next>=width-1?next+width-1:UINT64_MAX-1;
            next_start=next;run_windows(end,true);
        }
#ifdef DSIM_FINAL_ENABLED
        finalize_partitions();
#endif
    }
    void run_until(uint64_t horizon) {run_windows(horizon,false);}
private:
    void run_windows(uint64_t horizon,bool natural) {
        if(failed||horizon==UINT64_MAX)throw std::runtime_error("parallel engine requires a finite horizon and a valid state");
#ifdef DSIM_FINAL_ENABLED
        if(finalization_done)return;
#endif
        if(stopped)return;
        if(started&&horizon<next_start)throw std::runtime_error("parallel time cannot move backwards");
        if(!started) {
            for(const auto& p:partitions)if(p->sim.time_precision_fs!=partitions.front()->sim.time_precision_fs)
                throw std::runtime_error("parallel partitions require the same physical time precision");
            for(auto& p:partitions)p->sim.freeze_topology();
        }
        started=true;
#ifdef DSIM_FINAL_ENABLED
        for(auto& p:partitions)p->sim.defer_finalization=true;
#endif
        std::vector<Sim::Checkpoint> transactions;
        auto rollback=[&] {
            for(size_t i=0;i<transactions.size();++i)
                if(partitions[i]->sim.transaction_pending(transactions[i]))
                    partitions[i]->sim.rollback_transaction(transactions[i]);
            transactions.clear();
        };
        auto begin=[&] {
            transactions.reserve(partitions.size());
            for(auto& p:partitions)transactions.push_back(p->sim.begin_transaction());
        };
        try {
            // A message produced at t cannot arrive before t+lookahead.
            // Every worker completes [start,end] before messages are delivered
            // for the next window; there is no shared mutable kernel state.
            while(next_start<=horizon) {
                for(auto& p:partitions) {
                    for(const auto& message:p->outbox) {
                        const auto& link=p->links[message.link];
                        partitions.at(size_t(link.destination))->sim.deliver_at(message.time,link.signal,link.driver,message.value);
                        ++stats.messages;
                    }
                    p->outbox.clear();
                }
                auto width=std::min(max_window,lookahead);
                uint64_t end=horizon-next_start>=width-1?next_start+(width-1):horizon;
                if(transactional_finish)begin();
                std::vector<std::exception_ptr> errors(transactional_finish?partitions.size():0);
                workers.each(partitions.size(),[&](size_t i){
                    auto run=[&]{
                        if(natural)partitions[i]->sim.run_available(end);
                        else partitions[i]->sim.run_until(end);
                    };
                    if(!transactional_finish)run();
                    else try{run();}catch(...){errors[i]=std::current_exception();}
                });
                size_t winner=partitions.size();uint64_t finish=end;
                for(size_t i=0;i<partitions.size();++i)if(partitions[i]->sim.finished&&(!transactional_finish||!errors[i])) {
                    if(!transactional_finish)throw std::runtime_error("partition-local finish requires enable_global_finish()");
                    if(winner==partitions.size()||partitions[i]->sim.now<finish) {
                        winner=i;finish=partitions[i]->sim.now;
                    }
                }
                // A speculative failure beyond the global finish fence never
                // occurs in the committed execution. Earlier failures remain errors.
                size_t first_error=partitions.size();
                for(size_t i=0;i<errors.size();++i)if(errors[i]) {
                    auto time=partitions[i]->sim.now;
                    if(winner!=partitions.size()&&(time>finish||(time==finish&&i>winner)))continue;
                    if(first_error==partitions.size()||time<partitions[first_error]->sim.now)first_error=i;
                }
                if(first_error!=partitions.size())std::rethrow_exception(errors[first_error]);
                if(winner!=partitions.size()) {
                    if(finish<next_start)throw std::runtime_error("partition finish predates the current window");
                    rollback();begin();
                    // Existing output order is (time, partition, local order).
                    // At the finish tick, later partitions execute no events.
                    workers.each(partitions.size(),[&](size_t i){
                        if(i<=winner)partitions[i]->sim.run_until(finish);
                        else if(finish)partitions[i]->sim.run_until(finish-1);
                    });
                    ++stats.window_replays;
                    stopped=true;stop_time=finish;stop_partition=winner;
                    end=finish;
                }
                for(size_t i=0;i<transactions.size();++i)
                    partitions[i]->sim.commit_transaction(transactions[i]);
                transactions.clear();
                uint64_t committed=end;
                if(natural&&!stopped) {
                    committed=0;for(auto& p:partitions)committed=std::max(committed,p->sim.now);
                }
                for(auto it=window_observers.begin();it!=window_observers.end();) {
                    if(auto observer=it->lock()) {(*observer)(committed);++it;}
                    else it=window_observers.erase(it);
                }
                std::vector<Output> output;
                for(auto& p:partitions) {
                    for(auto& event:p->output)output.push_back(std::move(event));
                    p->output.clear();
                }
                std::stable_sort(output.begin(),output.end(),[](const Output& a,const Output& b){return a.time!=b.time?a.time<b.time:a.partition!=b.partition?a.partition<b.partition:a.order<b.order;});
                for(const auto& event:output)std::cout<<event.text;
                ++stats.windows;next_start=end+1;
                if(stopped)break;
            }
        }catch(...){
            failed=true;
            // A failing sink may already have committed some partitions.
            // Only transactions whose external effects are still private rewind.
            for(size_t i=0;i<transactions.size();++i)try {
                if(partitions[i]->sim.transaction_pending(transactions[i]))
                    partitions[i]->sim.rollback_transaction(transactions[i]);
            }catch(...){}
            throw;
        }
#ifdef DSIM_FINAL_ENABLED
        if(stopped)finalize_partitions();
#endif
    }
};

// Installs graph nodes into automatically assigned kernels. The graph must
// describe every dependency before installation. Zero-delay edges are net
// aliases; positive edges preserve every resolved transition, even when a
// worker owns both endpoints. Keeping that boundary rule independent of the
// number of workers makes one-worker execution a useful reference.
class AutoConservativeSim {
    PartitionGraph graph;
    PartitionGraph::Plan assignment;
    ConservativeSim engine;
    std::vector<bool> connected;
    bool started=false;
public:
    AutoConservativeSim(PartitionGraph topology,size_t workers,uint64_t window=1024)
        :graph(std::move(topology)),assignment(graph.plan(workers)),engine(workers,window),connected(graph.edges().size(),false) {
        for(size_t i=0;i<assignment.loads.size();++i)engine.partition();
    }
    const PartitionGraph::Plan& plan() const {return assignment;}
    const ConservativeSim::Stats& stats() const {return engine.stats;}
    void enable_global_finish() {engine.enable_global_finish();}
    bool finished() const {return engine.finished();}
    uint64_t finish_time() const {return engine.finish_time();}
    size_t finish_partition() const {return engine.finish_partition();}
    Sim& kernel(size_t node) {return engine.kernel(assignment.owner.at(node));}
    size_t partition_count() const {return engine.partition_count();}
    Sim& partition_kernel(size_t id) {return engine.kernel(id);}
    std::shared_ptr<std::function<void(uint64_t)>> observe_committed_windows(std::function<void(uint64_t)> fn) {
        return engine.observe_committed_windows(std::move(fn));
    }
    void connect(size_t edge,int source,int destination,int driver=-1) {
        if(started)throw std::runtime_error("automatic partition topology is already frozen");
        const auto& e=graph.edges().at(edge);
        if(connected.at(edge))throw std::runtime_error("automatic partition edge already connected");
        auto from=assignment.owner[e.from],to=assignment.owner[e.to];
        if(e.delay)engine.connect(from,source,to,destination,e.delay,driver);
        else {
            auto& s=engine.kernel(from);
            if(driver!=-1||s.get(source).w!=s.get(destination).w)throw std::runtime_error("zero-delay graph edges require equal-width net aliases and driver -1");
            for(int bit=0;bit<s.get(source).w;++bit)s.connect_net(source,bit,destination,bit);
        }
        connected[edge]=true;
    }
    void run_until(uint64_t horizon) {
        for(bool ready:connected)if(!ready)throw std::runtime_error("automatic partition edge is not connected");
        started=true;engine.run_until(horizon);
    }
    void run() {
        for(bool ready:connected)if(!ready)throw std::runtime_error("automatic partition edge is not connected");
        started=true;engine.run();
    }
};
}
