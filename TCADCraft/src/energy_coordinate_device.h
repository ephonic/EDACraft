#pragma once
#include "energy_coordinate_transport.h"
#include <mutex>

namespace tcad {
struct EnergyCoordinateSnapshot {
    EnergyCoordinateTransportResult result;
    double time=0;
    size_t token=0;
};

// Immutable explicit-cell configuration; all evolving thermodynamic coordinates
// live in this session. Raw commit is a trust boundary: the public adapter must
// independently audit the exported candidate before requesting its token.
class EnergyCoordinateDeviceSession {
    mutable std::mutex mutex_;
    bool configured_=false,pending_=false;
    size_t serial_=0,token_=0;
    double time_=0,pending_time_=0;
    std::vector<std::string> cells_,faces_,laws_,next_cells_;
    std::vector<double> vn_,vp_,parameters_;
    EnergyCoordinateTransportResult accepted_,candidate_;
public:
    bool enabled() const {std::lock_guard<std::mutex> lock(mutex_);return configured_;}
    void configure(size_t count,const std::vector<std::string>& cells,const std::vector<std::string>& faces,
            const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& parameters,
            const std::vector<std::string>& laws,const std::vector<std::string>& excess,double time) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(configured_)throw std::logic_error("energy-coordinate configuration is immutable");
        if(count<1 || count>64 || cells.size()!=17*count || !std::isfinite(time) || time<0)
            throw std::invalid_argument("energy-coordinate cell count or physical clock invalid");
        energy_coordinate_transport_detail::Context context(cells,faces,vn,vp,parameters,laws,excess);
        EnergyCoordinateTransportResult initial;
        auto& view=initial.transport;view.old_poisson=context.result.old_poisson;view.new_poisson=view.old_poisson;
        for(size_t i=0;i<count;++i) {
            view.n.push_back(fermi_energy_detail::text(context.C(i,3)));
            view.p.push_back(fermi_energy_detail::text(context.C(i,4)));
            view.temperature_l.push_back(double(context.C(i,10)));
            for(size_t s=0;s<2;++s) {
                const auto decoded=fermi_energy_detail::temperature(context.C(i,3+s),double(context.C(i,10)),
                    context.old_excess[2*i+s],context.C(i,13+s),s==0?vn:vp);
                (s==0?view.temperature_n:view.temperature_p).push_back(decoded.T);
                initial.excess.push_back(fermi_energy_detail::text(context.old_excess[2*i+s]));
            }
        }
        // All allocations precede publication. These vectors use standard
        // allocators; their swaps/moves and the scalar assignments cannot throw.
        auto c=cells,f=faces,l=laws;auto n=vn,p=vp,a=parameters;
        cells_.swap(c);faces_.swap(f);laws_.swap(l);
        vn_.swap(n);vp_.swap(p);parameters_.swap(a);accepted_=std::move(initial);
        time_=time;configured_=true;
    }
    EnergyCoordinateSnapshot prepare(double dt,double charge,double particle,double energy,int budget) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_ || pending_)throw std::logic_error("energy-coordinate mode absent or candidate already pending");
        for(double value:{dt,charge,particle,energy})
            if(!std::isfinite(value) || value<=0)throw std::invalid_argument("positive energy-coordinate timestep and budgets required");
        const double next_time=time_+dt,actual_dt=next_time-time_;
        if(!std::isfinite(next_time) || actual_dt<=0)throw std::invalid_argument("energy-coordinate physical clock cannot advance");
        if(serial_==std::numeric_limits<size_t>::max())throw std::overflow_error("energy-coordinate token exhausted");
        auto args=parameters_;args[0]=actual_dt;args[1]=charge;args[2]=particle;args[3]=energy;
        auto result=native_energy_coordinate_transport_raw(cells_,faces_,vn_,vp_,args,laws_,accepted_.excess,budget);
        auto next=cells_;
        for(size_t i=0;i<next.size()/17;++i) {
            next[17*i+3]=result.transport.n[i];next[17*i+4]=result.transport.p[i];
            next[17*i+10]=fermi_energy_detail::text(real_t(result.transport.temperature_l[i]));
        }
        EnergyCoordinateSnapshot exported{result,next_time,serial_+1};
        // Candidate export and the next input packet are allocated before a
        // token becomes visible. Commit only swaps already allocated storage.
        candidate_=std::move(result);next_cells_.swap(next);pending_time_=next_time;
        token_=++serial_;pending_=true;return exported;
    }
    void commit(size_t token) {
        std::lock_guard<std::mutex> lock(mutex_);require_token(token);
        cells_.swap(next_cells_);
        accepted_=std::move(candidate_);time_=pending_time_;pending_=false;
    }
    void discard(size_t token) {
        std::lock_guard<std::mutex> lock(mutex_);require_token(token);
        candidate_=EnergyCoordinateTransportResult{};next_cells_.clear();pending_=false;
    }
    EnergyCoordinateSnapshot snapshot() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!configured_)throw std::logic_error("energy-coordinate mode is not configured");
        return {accepted_,time_,0};
    }
private:
    void require_token(size_t token) const {
        if(!pending_ || token!=token_)throw std::logic_error("stale energy-coordinate candidate token");
    }
};
} // namespace tcad
