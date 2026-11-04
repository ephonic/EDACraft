#include "sdf_delay.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace dsim {
namespace {
struct Change {bool negative=false;uint64_t magnitude=0;bool clamped=false;};
using Value=std::optional<Change>;
// Missing is ordered between a negative update and explicit nonnegative zero.
// In particular min(NULL,+d) stays missing, while min(NULL,-d) selects -d;
// max does the converse. Keep presence distinct from an explicit zero.
bool less(Change a,Change b) {
    if(a.negative!=b.negative)return a.negative;
    return a.negative?a.magnitude>b.magnitude:a.magnitude<b.magnitude;
}
Value minimum(Value a,Value b) {
    if(!a)return b&&b->negative?b:Value{};
    if(!b)return a->negative?a:Value{};
    return less(*a,*b)?a:b;
}
Value maximum(Value a,Value b) {
    if(!a)return b&&!b->negative?b:Value{};
    if(!b)return !a->negative?a:Value{};
    return less(*a,*b)?b:a;
}
std::array<Value,12> expand(const std::vector<Value>& v) {
    std::array<Value,12> d;
    switch(v.size()) {
    case 1:d.fill(v[0]);return d;
    case 2:d[0]=d[2]=d[3]=v[0];d[1]=d[4]=d[5]=v[1];break;
    case 3:d[0]=d[3]=v[0];d[1]=d[5]=v[1];d[2]=d[4]=v[2];break;
    case 6:for(size_t i=0;i<6;++i)d[i]=v[i];break;
    case 12:for(size_t i=0;i<12;++i)d[i]=v[i];return d;
    default:throw std::runtime_error("path delay list requires 1, 2, 3, 6 or 12 values");
    }
    d[6]=minimum(d[0],d[2]);d[7]=maximum(d[0],d[3]);
    d[8]=minimum(d[1],d[4]);d[9]=maximum(d[1],d[5]);
    d[10]=maximum(d[2],d[4]);d[11]=minimum(d[3],d[5]);
    return d;
}
}
SdfPathDelays::SdfPathDelays(TimeScale model,const std::vector<std::string>& initial):model_(model) {
    if(!model.unit_fs||!model.precision_fs||model.precision_fs>model.unit_fs)
        throw std::runtime_error("invalid cell model time unit/precision");
    (void)sdf_ticks("0",model.unit_fs,model.precision_fs);
    std::vector<std::optional<std::string>> values;for(const auto& s:initial)values.push_back(s);
    apply(SdfEntry::Mode::Absolute,values,model.unit_fs);
}
size_t SdfPathDelays::apply(SdfEntry::Mode mode,const std::vector<std::optional<std::string>>& selected,uint64_t unit_fs,bool absolute_maximum) {
    if(mode!=SdfEntry::Mode::Absolute&&mode!=SdfEntry::Mode::Increment)
        throw std::runtime_error("timing checks require signed check semantics, not path delay annotation");
    if(mode==SdfEntry::Mode::Increment&&partial_zero_readback_)
        throw std::runtime_error("unsupported VCS readback after partial ABSOLUTE with zero path delays");
    (void)sdf_ticks("0",unit_fs,model_.precision_fs);
    std::vector<Value> values;values.reserve(selected.size());
    for(const auto& raw:selected) {
        if(!raw){values.emplace_back();continue;}
        bool negative=!raw->empty()&&raw->front()=='-';
        // Quantize each selected update at model precision, then merge. Never
        // round an already merged physical sum or at the global TB precision.
        auto n=sdf_ticks(negative?raw->substr(1):*raw,unit_fs,model_.precision_fs);
        if(mode==SdfEntry::Mode::Absolute&&negative&&n)values.push_back(Change{false,0,true});
        else values.push_back(Change{negative&&n!=0,n,false});
    }
    bool independent=explicit_x_;
    bool missing=false;for(const auto& value:values)if(!value)missing=true;
    if(selected.size()==12)independent=true;
    else if(mode==SdfEntry::Mode::Absolute&&!missing)independent=false;
    const auto updates=expand(values);auto next=quanta_;size_t clamped=0;
    for(size_t i=0;i<(independent?12u:6u);++i)if(updates[i]) {
        auto change=*updates[i];uint64_t base=mode==SdfEntry::Mode::Increment?next[i]:0;
        if(change.clamped)++clamped;
        if(change.negative) {
            if(change.magnitude>base){next[i]=0;++clamped;}else next[i]=base-change.magnitude;
        } else {
            if(base>std::numeric_limits<uint64_t>::max()-change.magnitude)throw std::runtime_error("SDF path delay addition overflow");
            next[i]=base+change.magnitude;
        }
        if(absolute_maximum&&mode==SdfEntry::Mode::Absolute)next[i]=std::max(next[i],quanta_[i]);
    }
    // VCS keeps derived X transitions for complete 1/2/3/6-value paths.
    // Explicit twelve-value paths retain independent X delays on increments.
    // A partial update retains the existing derived/independent distinction.
    if(!independent) {
        next[6]=std::min(next[0],next[2]);next[7]=std::max(next[0],next[3]);
        next[8]=std::min(next[1],next[4]);next[9]=std::max(next[1],next[5]);
        next[10]=std::max(next[2],next[4]);next[11]=std::min(next[3],next[5]);
    }
    bool partial_zero=partial_zero_readback_;
    if(mode==SdfEntry::Mode::Absolute)
        partial_zero=missing&&std::find(next.begin(),next.end(),uint64_t(0))!=next.end();
    quanta_=next;explicit_x_=independent;partial_zero_readback_=partial_zero;return clamped;
}
std::array<uint64_t,12> SdfPathDelays::ticks(uint64_t global_fs) const {
    if(!global_fs||global_fs>model_.precision_fs||model_.precision_fs%global_fs)
        throw std::runtime_error("global precision must divide cell model precision");
    (void)sdf_ticks("0",global_fs,global_fs);
    const auto factor=model_.precision_fs/global_fs;auto result=quanta_;
    for(auto& value:result) {
        if(value>std::numeric_limits<uint64_t>::max()/factor)throw std::runtime_error("SDF path delay global tick overflow");
        value*=factor;
    }
    return result;
}
int SdfPathDelays::transition(int from,int to) {
    static const int lookup[4][4]={{-1,0,6,2},{1,-1,8,4},{9,7,-1,10},{5,3,11,-1}};
    if(from<0||from>3||to<0||to>3)throw std::runtime_error("invalid four-state transition");
    return lookup[from][to];
}
uint64_t SdfPathDelays::delay(int from,int to,uint64_t global_fs) const {
    auto index=transition(from,to);const auto values=ticks(global_fs);return index<0?0:values[size_t(index)];
}
}
