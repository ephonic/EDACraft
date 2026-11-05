#pragma once
#include "isolated_relaxation.h"
#include "lattice_excess.h"
#include <mutex>

namespace tcad {
struct IsolatedRelaxationSnapshot {
    std::vector<std::string> state;
    double time=0;
};

// Explicit closed-cell mode. The accepted thermodynamic coordinates live here,
// never in rounded SimulationResult temperatures. A raw commit is a trust
// boundary: the public driver independently audits the prepared candidate.
class IsolatedRelaxationDeviceSession {
    mutable std::mutex mutex_;
    bool configured_=false, pending_=false;
    size_t serial_=0, token_=0;
    double time_=0, pending_time_=0;
    std::vector<std::string> parameters_, accepted_, candidate_;
    std::vector<double> vn_,vp_;
    std::vector<std::string> lattice_faces_,lattice_baths_,lattice_varshni_;
public:
    bool enabled() const {std::lock_guard<std::mutex> lock(mutex_);return configured_;}
    void configure(size_t count,const std::vector<std::string>& initial,
            const std::vector<std::string>& parameters,const std::vector<double>& vn,
            const std::vector<double>& vp,double time) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(configured_) throw std::logic_error("isolated relaxation configuration is immutable");
        if(count!=1 || initial.size()!=5 || parameters.size()!=16 || !std::isfinite(time) || time<0)
            throw std::invalid_argument("isolated relaxation requires one cell, valid configuration and clock");
        auto args=parameters;args.push_back("1");args.push_back("1e-27");
        const auto initialized=native_isolated_relaxation_raw(initial,args,vn,vp,true,256);
        auto accepted=initial;
        for(size_t i=0;i<3;++i) accepted[i+2]=initialized.at(i);
        auto p=parameters;auto n=vn,h=vp;
        parameters_.swap(p);vn_.swap(n);vp_.swap(h);accepted_.swap(accepted);
        time_=time;configured_=true;
    }
    void configure_lattice(size_t count,const std::vector<std::string>& initial,
            const std::vector<std::string>& parameters,const std::vector<std::string>& faces,
            const std::vector<double>& vn,const std::vector<double>& vp,double time,
            const std::vector<std::string>& baths={},const std::vector<std::string>& varshni={}) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(configured_)throw std::logic_error("isolated relaxation configuration is immutable");
        if(count<2 || count>64 || initial.size()!=5*count || parameters.size()!=16*count ||
                !std::isfinite(time) || time<0)
            throw std::invalid_argument("lattice excess cell coverage or clock invalid");
        auto accepted=initial;
        for(size_t i=0;i<count;++i) {
            std::vector<std::string> state(initial.begin()+5*i,initial.begin()+5*i+5);
            std::vector<std::string> args(parameters.begin()+16*i,parameters.begin()+16*i+16);
            args.push_back("1");args.push_back("1e-27");
            const auto raw=native_isolated_relaxation_raw(state,args,vn,vp,true,256);
            for(size_t k=0;k<3;++k)accepted[5*i+2+k]=raw.at(k);
        }
        lattice_excess_detail::Context checked(accepted,parameters,faces,{},vn,vp,1.,1e-27,baths,varshni);
        auto p=parameters,f=faces,b=baths,v=varshni;auto n=vn,h=vp;
        accepted_.swap(accepted);parameters_.swap(p);lattice_faces_.swap(f);lattice_baths_.swap(b);vn_.swap(n);vp_.swap(h);
        lattice_varshni_.swap(v);
        time_=time;configured_=true;
    }
    std::vector<std::string> prepare(double dt,double charge,double particle,double energy,int budget,
            const std::vector<std::string>& source={}) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_ || pending_) throw std::logic_error("isolated relaxation absent or candidate already pending");
        for(double v:{dt,charge,particle,energy})
            if(!std::isfinite(v) || v<=0) throw std::invalid_argument("finite positive isolated timestep and budgets required");
        const double next_time=time_+dt,actual_dt=next_time-time_;
        if(!std::isfinite(next_time) || actual_dt<=0)
            throw std::invalid_argument("isolated physical clock cannot advance");
        if(serial_==std::numeric_limits<size_t>::max()) throw std::overflow_error("isolated token exhausted");
        auto args=parameters_;
        args.push_back(isolated_relaxation_detail::text(real_t(actual_dt)));
        args.push_back(isolated_relaxation_detail::text(real_t(energy)));
        if(lattice_faces_.empty() && !source.empty()) {
            if(source.size()!=3)throw std::invalid_argument("three prescribed reservoir impulses required");
            args.insert(args.end(),source.begin(),source.end());
        }
        auto result=lattice_faces_.empty()?native_isolated_relaxation_raw(accepted_,args,vn_,vp_,false,budget):
            native_lattice_excess_raw(accepted_,parameters_,lattice_faces_,source,vn_,vp_,actual_dt,energy,budget,lattice_baths_,lattice_varshni_);
        auto next=accepted_;
        const size_t count=accepted_.size()/5,stride=lattice_faces_.empty()?0:13;
        for(size_t cell=0;cell<count;++cell)
            for(size_t i=0;i<3;++i) next[5*cell+i+2]=result.at(stride*cell+i);
        candidate_.swap(next);pending_time_=next_time;token_=++serial_;pending_=true;
        return result;
    }
    size_t token() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!pending_) throw std::logic_error("no pending isolated relaxation candidate");
        return token_;
    }
    void discard(size_t token) {
        std::lock_guard<std::mutex> lock(mutex_);require_token(token);
        candidate_.clear();pending_=false;
    }
    void commit(size_t token) {
        std::lock_guard<std::mutex> lock(mutex_);require_token(token);
        accepted_.swap(candidate_);candidate_.clear();time_=pending_time_;pending_=false;
    }
    IsolatedRelaxationSnapshot snapshot() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_) throw std::logic_error("isolated relaxation mode is not configured");
        return {accepted_,time_};
    }
private:
    void require_token(size_t token) const {
        if(!pending_ || token!=token_) throw std::logic_error("stale isolated relaxation candidate token");
    }
};
} // namespace tcad
