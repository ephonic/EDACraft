#pragma once
// Included after runtime.hpp by generated models with DSIM_PATH_ENABLED.
namespace dsim {
struct ModulePathArc {
    uint32_t input;
    uint8_t edge; // 0 any, 1 posedge, 2 negedge
    uint64_t delay[12];
};
inline int path_transition(int a,int b) {
    static const int8_t table[4][4]={{-1,0,6,2},{1,-1,8,4},{9,7,-1,10},{5,3,11,-1}};
    if(a<0||a>3||b<0||b>3)throw std::runtime_error("invalid path logic code");
    return table[a][b];
}
inline uint64_t module_path_delay(const Sim& s,const int* pins,const ModulePathArc* arcs,size_t count,int from,int to) {
    int transition=path_transition(from,to);
    if(transition<0)return 0;
    bool found=false;uint64_t latest=0,delay=0;
    for(size_t i=0;i<count;++i) {
        const auto& path=arcs[i];const auto& stamp=s.path_stamp(pins[path.input]);
        if(!stamp.valid)continue;
        int a=stamp.before,b=stamp.after;
        bool pos=(a==0&&b!=0)||(a>=2&&b==1);
        bool neg=(a==1&&b!=1)||(a>=2&&b==0);
        // VCS initializes module paths at time zero without filtering the
        // input edge, including #0 startup changes. Later changes are edged.
        if(s.now&&((path.edge==1&&!pos)||(path.edge==2&&!neg)))continue;
        if(path.edge>2)throw std::runtime_error("invalid module path edge");
        auto d=path.delay[transition];
        if(!found||stamp.time>latest){found=true;latest=stamp.time;delay=d;}
        else if(stamp.time==latest)delay=std::min(delay,d);
    }
    if(!found)return 0;
    if(delay>UINT64_MAX-latest)throw std::runtime_error("module path arrival overflow");
    auto arrival=latest+delay;
    return arrival>s.now?arrival-s.now:0;
}
#ifdef DSIM_CONDITIONAL_PATH_ENABLED
struct ConditionalModulePathArc {
    ModulePathArc path;
    uint32_t first=0,condition=0;
    bool ifnone=false;
};
using ModulePathCondition=bool(*)(Sim&,const int*);
inline uint64_t conditional_module_path_delay(Sim& s,const int* pins,const ConditionalModulePathArc* arcs,
                                              size_t count,int from,int to,const ModulePathCondition* conditions) {
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
                // An edge-qualified path is applicable only to its matching
                // source transition. VCS falls back to ifnone on the other
                // edge even when that explicit path's condition is true.
                if(s.now&&((other.path.edge==1&&!pos)||(other.path.edge==2&&!neg)))continue;
                if(conditions[other.condition](s,pins+other.first)) {
                    enabled=false;break;
                }
            }
        } else enabled=conditions[arc.condition](s,pins+arc.first);
        if(!enabled)continue;
        if(s.now&&((path.edge==1&&!pos)||(path.edge==2&&!neg)))continue;
        if(path.edge>2)throw std::runtime_error("invalid module path edge");
        auto d=path.delay[transition];
        if(!found||stamp.time>latest){found=true;latest=stamp.time;delay=d;}
        else if(stamp.time==latest)delay=std::min(delay,d);
    }
    if(!found)return 0;
    if(delay>UINT64_MAX-latest)throw std::runtime_error("module path arrival overflow");
    auto arrival=latest+delay;return arrival>s.now?arrival-s.now:0;
}
#endif
#ifdef DSIM_CHECKS_ENABLED
struct RuntimeTimingCheck {
    uint32_t first,data,reference,condition_data,condition_reference;
    uint16_t data_edges,reference_edges;
    uint8_t kind;
    uint64_t limit,second_limit,threshold;
    const char* label;
};
struct TimingCheckState {
    uint64_t data_time=0,reference_time=0;
    bool data_valid=false,reference_valid=false;
    // Called for every resolved change, including multiple changes in one
    // Active/NBA slot; this state is owned by a checkpointed compiled context.
    void change(Sim& s,const RuntimeTimingCheck& c,int role,int before,int after,bool enabled) {
        int transition=path_transition(before,after);if(transition<0)return;
        uint16_t bit=uint16_t(1u<<transition);
        auto violation=[&](uint64_t limit,uint8_t kind) {
            static const char* names[]={"SETUP","HOLD","RECOVERY","REMOVAL","SETUPHOLD","RECREM","WIDTH","PERIOD","SKEW"};
            auto message=std::string("TIMING kind=")+names[kind]+" time="+std::to_string(s.now)+" limit="+std::to_string(limit)+" "+c.label;
            std::string format;for(char ch:message){format+=ch;if(ch=='%')format+='%';}
            s.print(format,{});
        };
        if(c.kind==6) {
            if((c.data_edges&bit)&&enabled){data_time=s.now;data_valid=true;}
            else if(data_valid) {
                // End an edge-qualified pulse only on its opposite edge.
                bool pos=(before==0&&after!=0)||(before>=2&&after==1);
                bool neg=(before==1&&after!=1)||(before>=2&&after==0);
                uint16_t opposite=uint16_t(pos?((1<<1)|(1<<4)|(1<<5)|(1<<8)|(1<<9)):neg?((1<<0)|(1<<2)|(1<<3)|(1<<6)|(1<<7)):0);
                if(c.data_edges&opposite){auto width=s.now-data_time;if(width<c.limit&&width>=c.threshold)violation(c.limit,6);data_valid=false;}
            }
            return;
        }
        if(!enabled||!(bit&(role?c.reference_edges:c.data_edges)))return;
        if(c.kind==7) {
            if(data_valid&&s.now-data_time<c.limit)violation(c.limit,7);
            data_time=s.now;data_valid=true;return;
        }
        if(!role) {
            if((c.kind==1||c.kind==3||c.kind==4||c.kind==5)&&reference_valid) {
                auto limit=c.kind==4||c.kind==5?c.second_limit:c.limit;
                if(s.now-reference_time<limit&&(s.now>reference_time||c.kind==4||c.kind==5))violation(limit,c.kind==4?1:c.kind==5?3:c.kind);
            } else if(c.kind==8&&reference_valid&&s.now-reference_time>c.limit)violation(c.limit,8);
            data_time=s.now;data_valid=true;
        } else {
            if((c.kind==0||c.kind==2||c.kind==4||c.kind==5)&&data_valid&&s.now>data_time&&s.now-data_time<c.limit)violation(c.limit,c.kind==4?0:c.kind==5?2:c.kind);
            reference_time=s.now;reference_valid=true;
        }
    }
};
#endif
}
