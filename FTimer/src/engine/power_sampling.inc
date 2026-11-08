// Included inside estimate_power_detail: all state belongs to this call.
auto sample_parallel=[&]() -> bool {
    bool asynchronous=false;
    for (const auto& o:outputs) asynchronous|=o.clear.valid || o.preset.valid || o.latch;
    const auto boundary_option=std::getenv("FTIMER_POWER_FEEDBACK_BOUNDARY");
    const bool boundary_requested=boundary_option && std::string(boundary_option)=="1";
    if (!(sample_hz>0) || (outputs.size()<=4096 && !asynchronous && !boundary_requested)) return false;
    struct Function { std::vector<uint32_t> nets; std::vector<uint32_t> terms; uint16_t code=0; bool valid=false; };
    auto compile=[](const Truth& t) {
        Function f; f.nets=t.nets; f.valid=t.valid;
        if (!t.valid) return f;
        if (t.values.size()<=16) for (size_t i=0;i<t.values.size();++i)
            if(t.values[i]) f.code|=uint16_t(1u<<i);
        // Algebraic normal form: XOR of AND monomials. This evaluates every
        // Boolean lane together and preserves shared-net identities exactly.
        std::vector<uint8_t> a(t.values.begin(),t.values.end());
        for (size_t bit=1;bit<a.size();bit<<=1)
            for (size_t mask=0;mask<a.size();++mask) if (mask&bit) a[mask]^=a[mask^bit];
        for (size_t mask=0;mask<a.size();++mask) if (a[mask]) f.terms.push_back(uint32_t(mask));
        return f;
    };
    struct Gate { uint32_t net; Function data,clock,clear,preset; bool inverted,latch; };
    std::vector<Gate> gates; gates.reserve(outputs.size());
    std::vector<int> driver(activity.size(),-1);
    std::vector<size_t> sequential,comb;
    for (const auto& o:outputs) {
        if (activity[o.net].source!="default") continue;
        if (driver[o.net]>=0) return false; // Explicit multiple-driver fallback.
        const auto i=gates.size(); driver[o.net]=int(i);
        gates.push_back({o.net,compile(o.truth),compile(o.clock),compile(o.clear),compile(o.preset),o.inverted,o.latch});
        (o.sequential?sequential:comb).push_back(i);
    }
    // Clock edges are evaluated as Boolean events, so buffered, inverted and
    // gated clocks and different integer clock periods share the same model.
    // Large reconvergent combinational cones use the same lane evaluator;
    // requiring a register here discarded correlation in wide arithmetic.
    std::vector<unsigned> pending(gates.size());
    std::vector<std::vector<size_t>> users(gates.size());
    std::vector<bool> is_sequential(gates.size(),false);
    for (auto i:sequential) is_sequential[i]=true;
    std::vector<size_t> order;
    for (auto i:comb) {
        for (auto n:gates[i].data.nets) if (driver[n]>=0 && !is_sequential[size_t(driver[n])]) {
            ++pending[i]; users[size_t(driver[n])].push_back(i);
        }
        if (!pending[i]) order.push_back(i);
    }
    for (size_t at=0;at<order.size();++at)
        for (auto i:users[order[at]]) if (!--pending[i]) order.push_back(i);
    if (order.size()!=comb.size()) return false;
    if (!asynchronous) {
        // Independent acyclic cones have exact analytical joint statistics.
        // Detect feedback/reconvergence before spending a sampling budget.
        std::vector<uint64_t> support(activity.size());
        for (uint32_t n=0;n<activity.size();++n) if (driver[n]<0)
            support[n]=uint64_t{1}<<(n%64);
        std::vector<unsigned> degree(gates.size());
        std::vector<std::vector<size_t>> all_users(gates.size());
        std::vector<size_t> all_order;
        for (size_t i=0;i<gates.size();++i) {
            for (auto n:gates[i].data.nets) if (driver[n]>=0) {
                ++degree[i];all_users[size_t(driver[n])].push_back(i);
            }
            if (!degree[i]) all_order.push_back(i);
        }
        bool reconvergent=false;
        for (size_t at=0;at<all_order.size();++at) {
            const auto i=all_order[at];auto& roots=support[gates[i].net];
            for (auto n:gates[i].data.nets) {reconvergent|=(roots&support[n])!=0;roots|=support[n];}
            for (auto user:all_users[i]) if (!--degree[user]) all_order.push_back(user);
        }
        if (all_order.size()==gates.size() && !reconvergent) return false;
    }
    std::mt19937_64 random(0x4654494d455232ULL);
    auto bernoulli=[&](double p) {
        if (!(p>0)) return uint64_t{0};
        if (p>=1) return ~uint64_t{0};
        uint64_t result=0,undecided=~uint64_t{0};
        // Compare 64 independent binary uniform variates against p. No
        // per-lane floating point draws or probability quantization is needed.
        for (unsigned bit=0;bit<53 && undecided;++bit) {
            const uint64_t r=random(); p*=2;
            if (p>=1) { result|=undecided&~r; undecided&=r; p-=1; }
            else undecided&=~r;
            if (p==0) break;
        }
        return result;
    };
    std::vector<uint64_t> state(activity.size()),previous(activity.size());
    for (size_t n=0;n<state.size();++n) state[n]=bernoulli(activity[n].probability);
    // PrimeTime's unannotated initial sequential state resolves X to zero.
    // A self-holding register therefore has P(1)=0, rather than retaining an
    // arbitrary random initial value throughout the activity simulation.
    for (auto i:sequential) state[gates[i].net]=gates[i].inverted?~uint64_t{0}:0;
    auto evaluate=[&](const Function& f) {
        // Common primitives avoid interpreting their monomials at every
        // simulation phase. These are exact Boolean identities.
        if(f.nets.empty()) return f.code?~uint64_t{0}:uint64_t{0};
        const auto a=state[f.nets[0]];
        if(f.nets.size()==1) {
            switch(f.code) {case 0:return uint64_t{0};case 1:return ~a;case 2:return a;case 3:return ~uint64_t{0};}
        }
        if(f.nets.size()==2) {
            const auto b=state[f.nets[1]];
            switch(f.code) {
                case 1:return ~(a|b);case 6:return a^b;case 7:return ~(a&b);
                case 8:return a&b;case 9:return ~(a^b);case 14:return a|b;
            }
        }
        if(f.nets.size()==3) {
            const auto b=state[f.nets[1]],c=state[f.nets[2]];
            switch(f.code) {
                case 0x96:return a^b^c;case 0x69:return ~(a^b^c);
                case 0xe8:return (a&b)|((a|b)&c);case 0x17:return ~((a&b)|((a|b)&c));
            }
        }
        uint64_t result=0;
        for (auto term:f.terms) {
            uint64_t value=~uint64_t{0};
            while (term) {
                unsigned bit=0;auto low=term&(~term+1);
                while ((uint32_t{1}<<bit)!=low) ++bit;
                value&=state[f.nets[bit]]; term^=low;
            }
            result^=value;
        }
        return result;
    };
    struct Root { uint32_t net; double up,down; };
    std::vector<Root> roots;
    struct Clock { uint32_t net; uint64_t period,rise,fall; };
    std::vector<Clock> clocks;
    if (impl_->sdc) for (const auto& c:impl_->sdc->clocks()) if (c.period>0)
        for (auto p:c.sources) if (p.id<network.pin_count()) {
            const auto n=network.pin(p).net;
            if (valid(n) && activity[n.id].source=="clock") {
                // Phase sampling resolves clocks only when both edges align
                // with the fastest clock's half-cycle observation grid.
                const double period=c.period*1e-9,rise=std::max(0.f,c.rise_time)*1e-9;
                const double fall=(c.fall_time>=0?c.fall_time:.5*c.period)*1e-9;
                for (double t:{period,rise,fall}) {
                    const double ticks=t*2*sample_hz;
                    if (!(ticks>=0 && ticks<1e12) || std::abs(ticks-std::round(ticks))>1e-4) return false;
                }
                const auto ticks=uint64_t(std::llround(period*2*sample_hz));
                if (!ticks) return false;
                clocks.push_back({n.id,ticks,uint64_t(std::llround(rise*2*sample_hz))%ticks,
                    uint64_t(std::llround(fall*2*sample_hz))%ticks});
            }
        }
    #include "power_feedback_boundary.inc"
    // With no abstraction boundaries, retain the existing small-cone solver
    // and its activity-dependent sampling budget.
    if (boundary_requested && result.feedback_boundary_nets==0 &&
        outputs.size()<=4096 && !asynchronous) return false;
    std::vector<bool> needed(activity.size(),false);
    for (const auto& g:gates) for (const auto* f:{&g.data,&g.clock,&g.clear,&g.preset})
        for (auto n:f->nets) needed[n]=true;
    for (uint32_t n=0;n<activity.size();++n) if (needed[n] && driver[n]<0 && activity[n].source!="clock") {
        const auto& a=activity[n];
        const double q=std::clamp(a.rate/(2*sample_hz),0.,2*std::min(a.probability,1-a.probability));
        if (a.rate>2*sample_hz) return false;
        roots.push_back({n,a.probability<1?.5*q/(1-a.probability):0,a.probability>0?.5*q/a.probability:0});
    }
    auto settle=[&]() { for (auto i:order) if (!feedback_boundary[gates[i].net])
        state[gates[i].net]=evaluate(gates[i].data); };
    std::vector<uint64_t> old_clock(sequential.size()),next(sequential.size());
    std::vector<uint64_t> ones(gates.size()),changes(gates.size());
    auto budget=[](const char* name,unsigned fallback) {
        const auto value=std::getenv(name);
        if(!value) return fallback;
        size_t used=0;const auto count=std::stoul(value,&used);
        if(value[used]!='\0' || count>1048576 || !count)
            throw std::invalid_argument(std::string("Invalid power sampling budget: ")+name);
        return unsigned(count);
    };
    const unsigned burn_cycles=budget("FTIMER_POWER_BURN_CYCLES",128);
    const unsigned cycles=budget("FTIMER_POWER_SAMPLE_CYCLES",1024);
    constexpr unsigned lanes=64;
    // Set the clock phase preceding the first observation before detecting
    // edges. Random clock initial values otherwise suppress the first edge
    // in half the lanes and permanently alter feedback-register state.
    for(const auto& c:clocks) {
        const auto position=(2*c.period-1-c.rise)%c.period;
        const auto high=(c.fall+c.period-c.rise)%c.period;
        state[c.net]=position<high?~uint64_t{0}:0;
    }
    settle();
    for (unsigned phase=0;phase<2*(burn_cycles+cycles);++phase) {
        for (size_t i=0;i<sequential.size();++i) old_clock[i]=evaluate(gates[sequential[i]].clock);
        for (const auto& r:roots) {
            const auto old=state[r.net];
            state[r.net]^=(bernoulli(r.up)&~old)|(bernoulli(r.down)&old);
        }
        for (const auto& c:clocks) {
            // Aligned clock edges are integer events. Repeated floating point
            // modulo drifts for rounded SDC periods such as .714286/1.42857.
            const auto position=(uint64_t(phase)+c.period-c.rise)%c.period;
            const auto high=(c.fall+c.period-c.rise)%c.period;
            state[c.net]=position<high?~uint64_t{0}:0;
        }
        settle();
        for (size_t i=0;i<sequential.size();++i) {
            const auto& g=gates[sequential[i]];
            const auto edge=g.latch?evaluate(g.clock):~old_clock[i]&evaluate(g.clock);
            auto value=(state[g.net]&~edge)|(evaluate(g.data)&edge);
            if (g.clear.valid) {const auto mask=evaluate(g.clear);value=(value&~mask)|(g.inverted?mask:0);}
            if (g.preset.valid) {const auto mask=evaluate(g.preset);value=(value&~mask)|(g.inverted?0:mask);}
            next[i]=value;
        }
        for (size_t i=0;i<sequential.size();++i) state[gates[sequential[i]].net]=next[i];
        settle();
        if (phase>=2*burn_cycles) for (size_t i=0;i<gates.size();++i) {
            const auto n=gates[i].net;
            auto popcount=[](uint64_t value) {
                value-=((value>>1)&UINT64_C(0x5555555555555555));
                value=(value&UINT64_C(0x3333333333333333))+((value>>2)&UINT64_C(0x3333333333333333));
                value=(value+(value>>4))&UINT64_C(0x0f0f0f0f0f0f0f0f);
                return unsigned((value*UINT64_C(0x0101010101010101))>>56);
            };
            ones[i]+=popcount(state[n]);changes[i]+=popcount(state[n]^previous[n]);
        }
        for (const auto& g:gates) previous[g.net]=state[g.net];
    }
    const double observations=double(cycles)*lanes;
    for (size_t i=0;i<gates.size();++i)
        activity[gates[i].net]={changes[i]*sample_hz/observations,ones[i]/(2*observations),"propagated"};
    result.activity_samples=cycles*lanes;
    return true;
};
