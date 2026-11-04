#pragma once
// Included only by --gate-path-dictionary, after path.hpp. Runtime state and
// scheduling are unchanged; immutable transition delays are shared by index.
namespace dsim {
struct DictionaryModulePathArc {
    uint32_t input,table;
    uint8_t edge;
};
static_assert(sizeof(DictionaryModulePathArc)==12,"unexpected dictionary arc layout");
inline uint64_t dictionary_module_path_delay(const Sim& s,const int* pins,
        const DictionaryModulePathArc* arcs,size_t count,int from,int to,
        const uint64_t (*tables)[12]) {
    int transition=path_transition(from,to);if(transition<0)return 0;
    bool found=false;uint64_t latest=0,delay=0;
    for(size_t i=0;i<count;++i) {
        const auto& path=arcs[i];const auto& stamp=s.path_stamp(pins[path.input]);
        if(!stamp.valid)continue;
        int a=stamp.before,b=stamp.after;
        bool pos=(a==0&&b!=0)||(a>=2&&b==1),neg=(a==1&&b!=1)||(a>=2&&b==0);
        if(s.now&&((path.edge==1&&!pos)||(path.edge==2&&!neg)))continue;
        if(path.edge>2)throw std::runtime_error("invalid module path edge");
        auto d=tables[path.table][transition];
        if(!found||stamp.time>latest){found=true;latest=stamp.time;delay=d;}
        else if(stamp.time==latest)delay=std::min(delay,d);
    }
    if(!found)return 0;
    if(delay>UINT64_MAX-latest)throw std::runtime_error("module path arrival overflow");
    auto arrival=latest+delay;return arrival>s.now?arrival-s.now:0;
}
#ifdef DSIM_CONDITIONAL_PATH_ENABLED
struct DictionaryConditionalModulePathArc {
    DictionaryModulePathArc path;
    uint32_t first=0,condition=0;
    bool ifnone=false;
};
inline uint64_t dictionary_conditional_module_path_delay(Sim& s,const int* pins,
        const DictionaryConditionalModulePathArc* arcs,size_t count,int from,int to,
        const ModulePathCondition* conditions,const uint64_t (*tables)[12]) {
    int transition=path_transition(from,to);if(transition<0)return 0;
    bool found=false;uint64_t latest=0,delay=0;
    for(size_t i=0;i<count;++i) {
        const auto& arc=arcs[i];const auto& path=arc.path;
        const auto& stamp=s.path_stamp(pins[path.input]);if(!stamp.valid)continue;
        int a=stamp.before,b=stamp.after;
        bool pos=(a==0&&b!=0)||(a>=2&&b==1),neg=(a==1&&b!=1)||(a>=2&&b==0);
        bool enabled;
        if(arc.ifnone) {
            enabled=true;
            for(size_t j=0;j<count;++j) {
                const auto& other=arcs[j];
                if(other.path.input!=path.input||!other.condition)continue;
                if(s.now&&((other.path.edge==1&&!pos)||(other.path.edge==2&&!neg)))continue;
                if(conditions[other.condition](s,pins+other.first)){enabled=false;break;}
            }
        } else enabled=conditions[arc.condition](s,pins+arc.first);
        if(!enabled)continue;
        if(s.now&&((path.edge==1&&!pos)||(path.edge==2&&!neg)))continue;
        if(path.edge>2)throw std::runtime_error("invalid module path edge");
        auto d=tables[path.table][transition];
        if(!found||stamp.time>latest){found=true;latest=stamp.time;delay=d;}
        else if(stamp.time==latest)delay=std::min(delay,d);
    }
    if(!found)return 0;
    if(delay>UINT64_MAX-latest)throw std::runtime_error("module path arrival overflow");
    auto arrival=latest+delay;return arrival>s.now?arrival-s.now:0;
}
#endif
} // namespace dsim
