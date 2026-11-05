#pragma once
#include "three_temperature_dispatch.h"
#include <mutex>

namespace tcad {
// A one-way explicit-cell mode. The legacy nodal coefficients are not inputs
// to this model. Configuration is copied once; the only evolving fields are
// n,p,Tn,Tp,Tl and the accepted physical clock. Raw commit is an explicit trust
// boundary: the public Python driver audits a candidate before requesting it.
class ThreeTemperatureDeviceSession {
    mutable std::mutex mutex_;
    bool configured_=false, pending_=false;
    size_t serial_=0, token_=0;
    double time_=0, pending_time_=0;
    std::vector<std::string> cells_,faces_;
    std::vector<double> vn_,vp_,parameters_;
    ThreeTemperatureDispatchResult accepted_,candidate_;
public:
    bool enabled() const { std::lock_guard<std::mutex> lock(mutex_); return configured_; }
    void configure(size_t count,const std::vector<std::string>& cells,
            const std::vector<std::string>& faces,const std::vector<double>& vn,
            const std::vector<double>& vp,const std::vector<double>& parameters,double time) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(configured_) throw std::logic_error("three-temperature configuration is immutable");
        if(cells.size()!=21*count || !std::isfinite(time) || time<0)
            throw std::invalid_argument("three-temperature cell count or clock invalid");
        three_temperature_dispatch_detail::Context context(cells,faces,vn,vp,parameters);
        auto initial=context.output;
        initial.new_poisson=initial.old_poisson;
        for(size_t i=0;i<count;++i) {
            initial.n.push_back(cells[21*i+3]);initial.p.push_back(cells[21*i+4]);
            initial.temperature_l.push_back(double(context.C(i,10)));
            initial.temperature_n.push_back(double(context.A(i,17)));
            initial.temperature_p.push_back(double(context.A(i,18)));
        }
        // Allocate all potentially throwing storage before making it visible.
        auto c=cells,f=faces;auto n=vn,p=vp,a=parameters;
        cells_.swap(c);faces_.swap(f);vn_.swap(n);vp_.swap(p);parameters_.swap(a);
        accepted_=std::move(initial);time_=time;configured_=true;
    }
    ThreeTemperatureDispatchResult prepare(double dt,double charge,double particle,double energy,int budget) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_ || pending_) throw std::logic_error("three-temperature mode absent or candidate already pending");
        if(!std::isfinite(dt) || dt<=0 || !std::isfinite(time_+dt) || time_+dt<=time_)
            throw std::invalid_argument("three-temperature physical clock cannot advance");
        if(serial_==std::numeric_limits<size_t>::max()) throw std::overflow_error("three-temperature token exhausted");
        auto args=parameters_;args[0]=dt;args[1]=charge;args[2]=particle;args[3]=energy;
        auto result=native_three_temperature_dispatch_raw(cells_,faces_,vn_,vp_,args,budget);
        auto exported=result; // An allocation failure must not leave a hidden pending candidate.
        candidate_=std::move(result);pending_time_=time_+dt;token_=++serial_;pending_=true;
        return exported;
    }
    size_t token() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!pending_) throw std::logic_error("no pending three-temperature candidate");
        return token_;
    }
    void discard(size_t token) {
        std::lock_guard<std::mutex> lock(mutex_);
        require_token(token);pending_=false;candidate_=ThreeTemperatureDispatchResult{};
    }
    ThreeTemperatureDispatchResult candidate(size_t token) const {
        std::lock_guard<std::mutex> lock(mutex_);require_token(token);return candidate_;
    }
    void commit(size_t token) {
        std::lock_guard<std::mutex> lock(mutex_);require_token(token);
        auto next=cells_;
        for(size_t i=0;i<next.size()/21;++i) {
            next[21*i+3]=candidate_.n[i];next[21*i+4]=candidate_.p[i];
            next[21*i+10]=three_temperature_dispatch_detail::text(real_t(candidate_.temperature_l[i]));
            next[21*i+17]=three_temperature_dispatch_detail::text(real_t(candidate_.temperature_n[i]));
            next[21*i+18]=three_temperature_dispatch_detail::text(real_t(candidate_.temperature_p[i]));
            if(!candidate_.trap_fraction.empty())
                next[21*i+6]=three_temperature_dispatch_detail::text(real_t(candidate_.trap_fraction[i]));
        }
        cells_.swap(next);accepted_=std::move(candidate_);time_=pending_time_;pending_=false;
    }
    ThreeTemperatureDispatchResult state() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_) throw std::logic_error("three-temperature mode is not configured");
        return accepted_;
    }
    double time() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_) throw std::logic_error("three-temperature mode is not configured");
        return time_;
    }
private:
    void require_token(size_t token) const {
        if(!pending_ || token!=token_) throw std::logic_error("stale three-temperature candidate token");
    }
};
} // namespace tcad
