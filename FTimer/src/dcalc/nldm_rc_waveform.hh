#pragma once

#include "rc_waveform_dcalc.hh"
#include "nldm_table.hh"
#include "rc_linear_system.hh"
#include "rc_reduced_model.hh"
#include <algorithm>
#include <cmath>
#include <limits>

namespace te {

namespace nldm_detail {
// Determine the load derivative without cancellation from weighted sums of
// equal float table values. This predicate only selects the no-positive-R
// fallback; the actual characterized table values retain normal lookup rules.
inline double stable_delay_lookup(const edacraft::core::NldmTable& table,double input,double cap) {
    auto coordinate=[](const std::vector<float>& axis,double x,size_t& low,size_t& high) {
        low=high=0;
        if(axis.size()<2)return 0.;
        auto it=std::lower_bound(axis.begin(),axis.end(),x);
        high=it==axis.end()?axis.size()-1:std::max(size_t(1),size_t(it-axis.begin()));
        low=high-1;
        const double width=double(axis[high])-axis[low];
        return width!=0.?(x-axis[low])/width:0.;
    };
    size_t r0,r1,c0,c1;
    const double fr=coordinate(table.axis1,input,r0,r1),fc=coordinate(table.axis2,cap,c0,c1);
    const double a=table.values[r0*table.cols+c0],b=table.values[r0*table.cols+c1];
    const double c=table.values[r1*table.cols+c0],d=table.values[r1*table.cols+c1];
    const double top=a+fc*(b-a),bottom=c+fc*(d-c);
    return top+fr*(bottom-top);
}
inline double single_pole_ramp(double t,double duration,double tau) {
    if(t<=0.)return 0.;
    if(duration<=1e-12*std::max(tau,1e-30))
        return tau>0.?-std::expm1(-t/tau):1.;
    if(tau<=0.)return std::min(t/duration,1.);
    if(t<=duration)return (t+tau*std::expm1(-t/tau))/duration;
    return 1.-tau/duration*(-std::expm1(-duration/tau))*std::exp(-(t-duration)/tau);
}
// Select the threshold root's region at each trial capacitance. During a
// safeguarded Newton step the voltage probe can lie in the other region.
// Keep the finite characterization residual independent of that probe.
inline std::optional<double> characterized_effective_cap(double maximum,double minimum,
    double rd,double duration,double time,double threshold) {
    if (!(minimum>0. && minimum<maximum && rd>0. && time>0.))
        return std::nullopt;
    auto residual=[&](double cap) {
        return (single_pole_ramp(time,duration,rd*cap)-threshold)/threshold;
    };
    if (residual(minimum)<residual(maximum)) return std::nullopt;
    double lo=minimum,hi=maximum,cap=.5*(lo+hi),tolerance=.001;
    for (unsigned i=1;i<50;++i) {
        const double value=residual(cap);
        if (std::fabs(value)<tolerance) return cap;
        if (value<0.) hi=cap;else lo=cap;
        const double tau=rd*cap,x=time/tau;
        double derivative;
        if (duration<=1e-12*std::max(tau,1e-30))
            derivative=-x*std::exp(-x)/cap;
        else if (single_pole_ramp(duration,duration,tau)>=threshold)
            derivative=rd*((1.+x)*std::exp(-x)-1.)/duration;
        else {
            const double y=(time-duration)/tau;
            derivative=rd*((1.+x)*std::exp(-x)-(1.+y)*std::exp(-y))/duration;
        }
        const double next=cap-value*threshold/derivative;
        cap=std::isfinite(next) && next>lo && next<hi?next:.5*(lo+hi);
        if (i%10==0) tolerance*=2.;
    }
    return std::nullopt;
}

// The bounded source accepts a relative voltage residual from a fresh
// offset bracket, just as its ramp solve accepts a finite slew residual.
// An exact crossing or a reused offset changes the characterized source.
inline std::optional<double> bounded_source_reference(double cap,double rd,double width,
    double duration,double table_delay,double lower,double upper,double threshold) {
    if(!(cap>0. && rd>0. && width>0. && duration>0. && lower>0. &&
         lower<threshold && threshold<upper && upper<1.))return std::nullopt;
    const double maximum=width/(upper-lower),tau=rd*cap;
    double lo=table_delay-(1.+threshold)*maximum,hi=table_delay;
    double offset=table_delay-threshold*maximum;
    const bool in_ramp=single_pole_ramp(duration,duration,tau)>=threshold;
    for(unsigned i=0;i<49;++i) {
        const double time=table_delay-offset;
        const double value=single_pole_ramp(time,duration,tau)-threshold;
        if(std::fabs(value)<.001*threshold)return table_delay-offset;
        if(value<0.)hi=offset;else lo=offset;
        const double slope=in_ramp ? -std::expm1(-time/tau)/duration
            : std::exp(-(time-duration)/tau)*(-std::expm1(-duration/tau))/duration;
        const double next=offset+value/slope;
        offset=std::isfinite(next) && next>=lo && next<=hi?next:.5*(lo+hi);
    }
    return std::nullopt;
}
// The single-pole response after the ramp ends is one exponential. Nested
// source fitting calls this crossing repeatedly; solve its tail directly
// instead of bisecting the same exponential 48 times.
inline std::optional<double> single_pole_tail_crossing(double target,double duration,double tau) {
    if (!(target>0. && target<1. && duration>=0. && tau>=0.)) return std::nullopt;
    if (tau==0.) return target*duration;
    if (duration<=1e-12*std::max(tau,1e-30)) return -tau*std::log1p(-target);
    const double ratio=duration/tau;
    const double gain=-std::expm1(-ratio)/ratio;
    if (target<1.-gain || !(gain>0.)) return std::nullopt;
    return duration+tau*(std::log(gain)-std::log1p(-target));
}
inline std::optional<double> single_pole_crossing(double target,double duration,double tau) {
    if (const auto tail=single_pole_tail_crossing(target,duration,tau)) return tail;
    if (!(target>0. && target<1. && duration>0. && tau>0.) ||
        !std::isfinite(duration/tau)) return std::nullopt;
    // During the ramp, u + exp(-u) - 1 = target * duration/tau.
    // Solve in pole-time coordinates with a bracketed Newton step. Match
    // the original 48-bisection time bracket; source-fit tolerances stay
    // independent of this numerical crossing solver.
    const double ratio=duration/tau,q=target*ratio;
    const double tolerance=std::ldexp(ratio+64.,-50);
    double lo=0.,hi=ratio,u=q<1.?std::sqrt(2.*q)+q/3.:q+1.;
    u=std::clamp(u,lo,hi);
    for (unsigned i=0;i<48;++i) {
        const double residual=u+std::expm1(-u)-q;
        if (residual<0.) lo=u;else hi=u;
        const double next=u-residual/(-std::expm1(-u));
        if (std::isfinite(next) && std::fabs(next-u)<=tolerance) return tau*next;
        u=std::isfinite(next) && next>lo && next<hi?next:.5*(lo+hi);
        if (hi-lo<=tolerance) return tau*.5*(lo+hi);
    }
    return tau*u;
}
}

// A voltage-ramp/Thevenin interpretation of NLDM, with delay matching on a
// reduced driving-point model and crossings on the complete passive network.
// All internal times/caps use the driving library's units.
class NldmRcWaveformCalc {
    struct Poles { double slow, fast, first; std::vector<std::pair<double,double>> modes; };
    struct Driver { double cap, resistance, ramp, crossing; Poles poles;
        double reference_crossing=0.; bool characterized=false,rc009=false; double network_resistance=0.; bool zero_slope=false; };

    // Keep loaded charge separate from the extraction's float node storage.
    // The virtual characterization source retains its fitted double value;
    // extracted resistor elements keep their original representation.
    struct NetworkCaps {
        const FullRcNetwork* network;
        const std::vector<double>* precise;
        const FullRcNetwork* reference;
        NetworkCaps(const FullRcNetwork* p=nullptr,const std::vector<double>* c=nullptr,
                    const FullRcNetwork* r=nullptr):network(p),precise(c),reference(r) {}
        explicit operator bool() const {return network!=nullptr;}
        const FullRcNetwork* operator->() const {return network;}
        double cap(size_t i) const {return precise?(*precise)[i]:double(network->nodes[i].gnd_cap);}
    };
    static std::optional<Poles> distributed_poles(const NetworkCaps& rc,double cap_unit,double time_unit,double rd) {
        if(!rc || !(rd>0.) || rc->driver_node_id>=rc->nodes.size())return std::nullopt;
        const size_t n=rc->nodes.size();const auto driver=rc->driver_node_id;
        std::vector<double> caps(n),branch(n,0.);std::vector<RcLinearSystem::Edge> edges;
        for(size_t i=0;i<n;++i) {
            caps[i]=rc.cap(i)*double(rc->cap_scale)/cap_unit;
            if(!(caps[i]>=0.) || !std::isfinite(caps[i]))return std::nullopt;
        }
        for(const auto& e:rc->resistors) {
            if(e.node1>=n || e.node2>=n || e.node1==e.node2)return std::nullopt;
            const double r=double(e.resistance)*double(rc->res_scale)*cap_unit/time_unit;
            if(!(r>0.) || !std::isfinite(r))return std::nullopt;
            edges.push_back({e.node1,e.node2,1./r});
            if(e.node1==driver)branch[e.node2]+=1./r;
            if(e.node2==driver)branch[e.node1]+=1./r;
        }
        // Preserve the exact two-pole path and its characterized crossings.
        bool equivalent=true;double tau=0.;
        for(size_t i=0;i<n;++i)if(i!=driver){if(!(caps[i]>0. && branch[i]>0.)){equivalent=false;break;}const double x=caps[i]/branch[i];if(tau==0.)tau=x;else if(std::fabs(x-tau)>1e-6*std::max(x,tau)){equivalent=false;break;}}
        if(equivalent)return std::nullopt;
        RcReducedModel rom;
        std::vector<double> nominal=caps;
        if(rc.reference && rc.reference->nodes.size()==n)
            for(size_t i=0;i<n;++i)nominal[i]=double(rc.reference->nodes[i].gnd_cap)*rc.reference->cap_scale/cap_unit;
        if(!rom.initialize_receivers(nominal,edges,driver,1./rd,1./rd,1e-13/time_unit) || !rom.update_receivers(caps,driver))return std::nullopt;
        Poles p{0.,1e300,1.};double sum=0.;
        for(size_t i=0;i<rom.eigen.size();++i){if(!(rom.eigen[i]>0.))return std::nullopt;const double t=1./rom.eigen[i],weight=rom.b[i]*rom.b[i]/(rd*rom.eigen[i]);p.modes.push_back({t,weight});p.slow=std::max(p.slow,t);p.fast=std::min(p.fast,t);sum+=weight;}
        if(std::fabs(sum-1.)>1e-5)return std::nullopt;
        return p;
    }
    static double pole_ramp(double t, double duration, double tau) {
        return nldm_detail::single_pole_ramp(t,duration,tau);
    }
    static double response(double t, double duration, const Poles& p) {
        if(!p.modes.empty()){double v=0.;for(const auto& mode:p.modes)v+=mode.second*pole_ramp(t,duration,mode.first);return v;}
        return p.first * pole_ramp(t,duration,p.slow) +
            (1.-p.first) * pole_ramp(t,duration,p.fast);
    }
    static double crossing(double target, double duration, const Poles& p) {
        if (p.first==1. && p.fast==0.)
            if (const auto exact=nldm_detail::single_pole_crossing(target,duration,p.slow)) return *exact;
        double lo=0., hi=duration+64.*p.slow;
        for (unsigned i=0;i<48;++i) {
            const double mid=.5*(lo+hi);
            if (response(mid,duration,p)<target) lo=mid; else hi=mid;
        }
        return .5*(lo+hi);
    }
    // Characterization source fitting has a finite inverse-coordinate grid.
    // Generate each inverse from its mathematical equation rather than
    // embedding a precomputed table. Keep the physical waveform solver exact.
    static double fit_crossing(double target,double duration,const Poles& p) {
        const double tau=p.slow;
        if (!(tau>0.) || duration<=1e-12*std::max(tau,1e-30))
            return crossing(target,duration,p);
        const double ratio=duration/tau,x=1.+target*ratio;
        if (x<1.0001) return -tau*std::log1p(-target);
        double u=x;
        if (x<=10.) {
            // Compute the inverse grid once from u+exp(-u)=x. No
            // captured model/table data is used to construct this cache.
            static const std::vector<double> inverse=[] {
                std::vector<double> values(90001,0.);
                for(size_t j=1;j<values.size();++j) {
                    const double q=double(j+10000)/10000.-1.;
                    double lo=0.,hi=q+1.;
                    double u=q<1.?std::sqrt(2.*q)+q/3.:q+1.;
                    for(unsigned i=0;i<40;++i) {
                        const double residual=u+std::expm1(-u)-q;
                        if(residual<0.)lo=u;else hi=u;
                        if(hi-lo<1e-12)break;
                        const double next=u-residual/(-std::expm1(-u));
                        u=std::isfinite(next) && next>lo && next<hi?next:.5*(lo+hi);
                    }
                    values[j]=std::round(u*1e6)/1e6;
                }
                return values;
            }();
            const size_t index=size_t(std::floor(x*10000.))-10000;
            u=inverse[std::min(index,inverse.size()-1)];
        }
        const double result=tau*u;
        if (result<=duration) return result;
        return duration+tau*std::log((-std::expm1(-ratio))/(ratio*(1.-target)));
    }
    static std::optional<double> fit_ramp(double cap,double rd,double width,
                                          double lower,double upper,
                                          double relative_tolerance=.001,
                                          double start=-1.) {
        const Poles lumped{rd*cap,0.,1.};
        if (!(rd>0. && cap>0. && width>0.) ||
            fit_crossing(upper,0.,lumped)-fit_crossing(lower,0.,lumped)>width*(1.+1e-10))
            return std::nullopt;
        double lo=0.,hi=width/(upper-lower);
        double tolerance=relative_tolerance;
        double mid=start>=lo && start<=hi?start:.5*(lo+hi);
        for (unsigned i=1;i<50;++i) {
            const double measured=fit_crossing(upper,mid,lumped)-fit_crossing(lower,mid,lumped);
            // The characterized source uses a relative slew residual. Its
            // accepted ramp is subsequently reused by the Ceff iteration;
            // converging this independent solve further changes that model.
            if (std::fabs(measured-width)<tolerance*width) return mid;
            if (measured<width) lo=mid;else hi=mid;
            mid=.5*(lo+hi);
            if (i%10==0) tolerance*=2.;
        }
        return relative_tolerance==0.?std::optional<double>{.5*(lo+hi)}:std::nullopt;
    }
    struct SourceFit { double resistance,ramp,reference; };
    // Fit the three independent characterization constraints: transition
    // width, threshold voltage at the table delay, and threshold voltage at
    // a neighbouring load's delay. In particular, retaining arcs need not
    // have the same source resistance as an ordinary clock-to-output arc.
    static std::optional<SourceFit> fit_characterized_source(double cap,double next_cap,
        double table_delay,double next_delay,double width,double lower,double upper,
        double threshold,double minimum_resistance) {
        if (!(cap>0. && next_cap>cap && next_delay>table_delay && width>0.))
            return std::nullopt;
        const double maximum_ramp=width/(upper-lower);
        double rd=.9*width/(cap*std::log((1.-lower)/(1.-upper)));
        double duration=.5*maximum_ramp,offset=table_delay-threshold*maximum_ramp;
        auto voltage=[&](double t,double c) {return pole_ramp(t,duration,rd*c);};
        for (unsigned iteration=0;iteration<50;++iteration) {
            auto ramp=fit_ramp(cap,rd,width,lower,upper,.001,duration);
            if (!ramp) {
                rd=.9*width/(cap*std::log((1.-lower)/(1.-upper)));
                ramp=fit_ramp(cap,rd,width,lower,upper,.001,duration);
            }
            if (!ramp) return std::nullopt;
            duration=*ramp;
            double lo=table_delay-(1.+threshold)*maximum_ramp,hi=table_delay;
            bool converged=false;
            for (unsigned i=0;i<49;++i) {
                const double value=voltage(table_delay-offset,cap)-threshold;
                if (std::fabs(value)<.001*threshold) {converged=true;break;}
                if (value<0.) hi=offset;else lo=offset;
                // The root region is selected from V at the ramp endpoint.
                // Newton probes can temporarily lie in the opposite region;
                // retain the selected branch's derivative for those probes.
                const double time=table_delay-offset,tau=rd*cap;
                const double slope=voltage(duration,cap)>=threshold
                    ? -std::expm1(-time/tau)/duration
                    : std::exp(-(time-duration)/tau)*(-std::expm1(-duration/tau))/duration;
                const double next=offset+value/slope;
                offset=std::isfinite(next) && next>=lo && next<=hi?next:.5*(lo+hi);
            }
            if (!converged) return std::nullopt;
            lo=minimum_resistance;
            hi=(offset-table_delay)/(cap*std::log(1.-threshold));
            if (!(hi>lo)) return std::nullopt;
            converged=false;
            for (unsigned i=0;i<49;++i) {
                const double time=next_delay-offset,value=voltage(time,next_cap)-threshold;
                if (std::fabs(value)<.001*threshold) {converged=true;break;}
                if (value<0.) hi=rd;else lo=rd;
                const double tau=rd*next_cap,x=time/tau;
                double derivative;
                // Preserve the characterized root region throughout Newton probes.
                // This in-ramp residual uses the reference characterization C;
                // the voltage response itself is evaluated at its neighbour C.
                if (voltage(duration,next_cap)>=threshold)
                    derivative=((tau+time)*std::exp(-x)/rd-cap)/duration;
                else {
                    const double y=(time-duration)/tau;
                    derivative=next_cap*((1.+x)*std::exp(-x)-
                                          (1.+y)*std::exp(-y))/duration;
                }
                const double next=rd-value/derivative;
                rd=std::isfinite(next) && next>=lo && next<=hi?next:.5*(lo+hi);
            }
            if (!converged) return std::nullopt;
            const Poles lumped{rd*cap,0.,1.};
            const double residual=std::fabs((fit_crossing(upper,duration,lumped)-
                fit_crossing(lower,duration,lumped)-width)/width)+
                std::fabs(voltage(table_delay-offset,cap)/threshold-1.)+
                std::fabs(voltage(next_delay-offset,next_cap)/threshold-1.);
            if (residual<.010001*double(uint64_t{1} << (iteration/10)))
                return SourceFit{rd,duration,table_delay-offset};
        }
        return std::nullopt;
    }
    static double network_total_cap(const PiModel& pi,const NetworkCaps& network,
                                    double cap_unit,double accumulated_cap=-1.) {
        if(accumulated_cap>0. && std::isfinite(accumulated_cap))return accumulated_cap;
        if(network && cap_unit>0.) {
            double total=0.;
            for(size_t i=0;i<network->nodes.size();++i)
                total+=network.cap(i)*network->cap_scale/cap_unit;
            if(total>0. && std::isfinite(total))return total;
        }
        return double(pi.c1)+pi.c2;
    }
    static Poles network_pi_poles(const PiModel& pi,const NetworkCaps& network,
        double cap_unit,double time_unit,double rd,double accumulated_cap) {
        double c1=pi.c1,c2=pi.c2;
        // Only a physically equivalent far group permits reconstruction;
        // an arbitrary reduced Pi must keep its original moment matching.
        bool exact=network && network->nodes.size()==2;
        if(network && network->nodes.size()>2 && network->driver_node_id<network->nodes.size()) {
            const auto source=network->driver_node_id;const size_t n=network->nodes.size();
            std::vector<double> branch(n,0.);bool connected=true;
            for(const auto& edge:network->resistors) {
                if(edge.node1>=n || edge.node2>=n || !(edge.resistance>0.)) {connected=false;break;}
                const double g=1./(double(edge.resistance)*network->res_scale*cap_unit/time_unit);
                if(edge.node1==source)branch[edge.node2]+=g;
                if(edge.node2==source)branch[edge.node1]+=g;
            }
            double tau=0.,far=0.;
            for(size_t i=0;i<n && connected;++i)if(i!=source) {
                const double cap=network.cap(i)*network->cap_scale/cap_unit;
                if(!(cap>0. && branch[i]>0.)) {connected=false;break;}
                const double value=cap/branch[i];far+=cap;
                if(tau==0.)tau=value;
                else if(std::fabs(value-tau)>64.*std::numeric_limits<double>::epsilon()*std::max(value,tau))connected=false;
            }
            const double near=network.cap(source)*network->cap_scale/cap_unit;
            exact=connected && std::fabs(pi.c2-near)<=1e-6*accumulated_cap &&
                std::fabs(pi.c1-far)<=1e-6*accumulated_cap &&
                std::fabs(pi.rpi*cap_unit/time_unit*far-tau)<=1e-6*tau;
        }

        if(accumulated_cap>=0. && network && exact &&
           network->driver_node_id<network->nodes.size()) {
            // A two-node network, or equipotential parallel far branches,
            // is an exact Pi. Preserve its separately accumulated charge.
            c2=network.cap(network->driver_node_id)*network->cap_scale/cap_unit;
            c1=accumulated_cap-c2;
        }
        return pi_poles(c1,pi.rpi*cap_unit/time_unit,c2,rd);
    }
    static std::optional<Driver> unconstrained_driver(const PiModel& pi,double input,
        const edacraft::core::NldmTable& delay,const edacraft::core::NldmTable& slew,
        double lower,double upper,double derate,double threshold,double resistance_scale,
        double minimum_cap,const NetworkCaps& network,double cap_unit,double time_unit,
        double accumulated_cap) {
        // The reduced Pi rounds each capacitance independently. Refitting a
        // characterized source from their sum can amplify that roundoff into
        // a different finite-residual solution. Keep the physical network's
        // accumulated charge as the Ceff starting point and upper bound.
        const double total=network_total_cap(pi,network,cap_unit,accumulated_cap);
        const double r=pi.rpi*resistance_scale;
        double cap=total;std::optional<Poles> network_poles;double network_rd=0.;
        for (unsigned iteration=0;iteration<50;++iteration) {
            const double next_cap=std::max(cap*1.01,cap+minimum_cap);
            const double table_delay=lookup_nldm(delay,float(input),float(cap));
            const double next_delay=lookup_nldm(delay,float(input),float(next_cap));
            const double width=double(lookup_nldm(slew,float(input),float(cap)))*derate;
            const auto source=fit_characterized_source(cap,next_cap,table_delay,next_delay,
                width,lower,upper,threshold,.01*resistance_scale);
            if (!source) return std::nullopt;
            // Reuse the network response while source admittance remains
            // within the characterized five-percent region. A Ceff refit
            // can cross that region; retaining the first poles indefinitely
            // distorts the source tail and can miss a bounded-source restart.
            if(!network_poles || std::fabs(network_rd/source->resistance-1.)>.05){network_poles=distributed_poles(network,cap_unit,time_unit,source->resistance);if(!network_poles)network_poles=network_pi_poles(pi,network,cap_unit,time_unit,source->resistance,accumulated_cap);network_rd=source->resistance;}
            const auto poles=*network_poles;
            const auto actual=characterized_crossing(threshold,source->ramp,poles);
            if (!actual) return std::nullopt;
            // Reclassify after each Ceff refit. A source can become bounded
            // after an ordinary first pass; the caller restarts at total C.
            if(2.*std::fabs(response(*actual,0.,poles)-threshold)<.45)
                return Driver{cap,source->resistance,source->ramp,*actual,poles,
                              source->reference,true,true,network_rd};
            const double shift=*actual-source->reference;
            if (std::fabs(shift)<=.01*std::max(std::fabs(table_delay+shift),width*1e-3))
                return Driver{cap,source->resistance,source->ramp,*actual,poles,
                              source->reference,true,false,network_rd};
            const auto next=nldm_detail::characterized_effective_cap(total,minimum_cap,source->resistance,
                                              source->ramp,*actual,threshold);
            if (!next || std::fabs(*next-cap)<total*1e-10) return std::nullopt;
            cap=*next;
        }
        return std::nullopt;
    }
    static double response_slope(double t,double duration,const Poles& p) {
        auto slope=[&](double tau) {
            if (t<=0.) return 0.;
            if (duration<=1e-12*std::max(tau,1e-30)) return std::exp(-t/tau)/tau;
            if (t<=duration) return -std::expm1(-t/tau)/duration;
            return std::exp(-(t-duration)/tau)*(-std::expm1(-duration/tau))/duration;
        };
        if(!p.modes.empty()){double v=0.;for(const auto& mode:p.modes)v+=mode.second*slope(mode.first);return v;}
        return p.first*slope(p.slow)+(1.-p.first)*slope(p.fast);
    }
    // The characterized runtime keeps the first threshold crossing within
    // 0.001 of normalized voltage. The initial upper bound uses the slow
    // pole and the sum of absolute residues, before safeguarded Newton steps.
    static std::optional<double> characterized_crossing(double target,double duration,
                                                       const Poles& p,double start=0.) {
        if (!(duration>0. && p.slow>0. && p.fast>0. && target>0. && target<1.))
            return std::nullopt;
        double lo=start;
        if (std::fabs(response(lo,duration,p)-target)<.001) return lo;
        if (response(lo,duration,p)>target) return std::nullopt;
        double hi=std::max(duration,lo);
        if (response(hi,duration,p)<target) {
            lo=hi;
            double residues=std::fabs(p.first)+std::fabs(1.-p.first);
            if(!p.modes.empty()){residues=0.;for(const auto& mode:p.modes)residues+=std::fabs(mode.second);}
            const double x=duration/p.slow;
            hi=duration+p.slow*std::log(residues*(-std::expm1(-x))/(x*(1.-target)));
        }
        if (!(hi>lo && response(hi,duration,p)>=target)) return std::nullopt;
        double time=hi;
        for (unsigned i=0;i<100;++i) {
            const double value=response(time,duration,p);
            if (std::fabs(value-target)<.001) return time;
            if (value<target) lo=time;else hi=time;
            const double next=time+(target-value)/response_slope(time,duration,p);
            time=std::isfinite(next) && next>lo && next<hi?next:.5*(lo+hi);
        }
        return std::nullopt;
    }
    // A characterized voltage source has a load-dependent ramp. In a highly
    // shielded net the unconstrained source fit is ill-conditioned. Bound its
    // resistance using the upper half of the characterized transition, then
    // refit the ramp at every effective load. This is the RC-009 model, rather
    // than a correction to the receiving cell's delay.
    static std::optional<Driver> characterized_driver(const PiModel& pi,double input,
        const edacraft::core::NldmTable& delay,const edacraft::core::NldmTable& slew,
        double lower,double upper,double derate,double threshold,double resistance_scale,
        double minimum_cap,const NetworkCaps& network,double cap_unit,double time_unit,
        double accumulated_cap) {
        const double total=network_total_cap(pi,network,cap_unit,accumulated_cap);
        const double r=pi.rpi*resistance_scale;
        if (!(pi.c1>0. && pi.c2>0. && r>0. && threshold>lower && threshold<upper))
            return std::nullopt;
        const double width=double(lookup_nldm(slew,float(input),float(total)))*derate;
        const double step_width=std::log((1.-lower)/(1.-upper));
        const double initial_rd=.9995*width/(total*step_width);
        if (!(initial_rd>0. && r>=initial_rd*1e-3)) return std::nullopt;
        const auto dynamic=unconstrained_driver(pi,input,delay,slew,lower,upper,
                                                derate,threshold,resistance_scale,minimum_cap,network,cap_unit,time_unit,accumulated_cap);
        if(!dynamic || !dynamic->rc009)return dynamic;
        const double rd=(upper-threshold)*width/((upper-lower)*total*
            std::log((1.-threshold)/(1.-upper)));
        const auto physical=distributed_poles(network,cap_unit,time_unit,rd);
        const auto poles=physical?*physical:network_pi_poles(pi,network,cap_unit,time_unit,rd,accumulated_cap);
        // Each bounded Ceff iteration starts a fresh ramp bracket. A prior
        // accepted ramp selects a different finite-residual solution.
        double cap=total;
        for (unsigned iteration=0;iteration<50;++iteration) {
            const double local_width=double(lookup_nldm(slew,float(input),float(cap)))*derate;
            const auto duration=fit_ramp(cap,rd,local_width,lower,upper,.001);
            if (!duration) return std::nullopt;
            const auto actual_crossing=characterized_crossing(threshold,*duration,poles);
            if (!actual_crossing) return std::nullopt;
            const double actual=*actual_crossing;
            const double table_delay=lookup_nldm(delay,float(input),float(cap));
            const auto source_reference=nldm_detail::bounded_source_reference(cap,rd,local_width,
                *duration,table_delay,lower,upper,threshold);
            if(!source_reference)return std::nullopt;
            const double reference=*source_reference;
            const double cell_delay=table_delay+actual-reference;
            // Convergence is a delay criterion. Solving Ceff to machine
            // precision refits a different driver and changes both slew and
            // delay relative to the characterized iterative model.
            if (std::fabs(actual-reference)<=.01*std::max(std::fabs(cell_delay),local_width*1e-3))
                return Driver{cap,rd,*duration,actual,poles,reference,true,true};
            const auto next=nldm_detail::characterized_effective_cap(total,minimum_cap,rd,*duration,actual,threshold);
            if (!next || std::fabs(*next-cap)<total*1e-10) return std::nullopt;
            cap=*next;
        }
        return std::nullopt;
    }
    static Poles pi_poles(double c1, double r, double c2, double rd) {
        const double b=rd*(c1+c2)+r*c1, a=rd*r*c1*c2;
        const double slow=.5*(b+std::sqrt(std::max(0.,b*b-4.*a)));
        const double fast=slow>0.?a/slow:0.;
        const double weight=(slow-r*c1)/(slow-fast);
        return {slow,fast,weight};
    }
    static double fit_resistance(double cap, double duration, double width,
                                 double lower, double upper) {
        const double step_width=std::log((1.-lower)/(1.-upper));
        double lo=0., hi=2.*width/(cap*step_width);
        for (unsigned i=0;i<36;++i) {
            const double rd=.5*(lo+hi), tau=rd*cap;
            const Poles single{tau,0.,1.};
            const double measured=crossing(upper,duration,single)-crossing(lower,duration,single);
            if (measured<width) lo=rd; else hi=rd;
        }
        return .5*(lo+hi);
    }
    static std::optional<Driver> driver(const PiModel& pi, double input,
        const edacraft::core::NldmTable& slew, double lower, double upper,
        double derate, double threshold, double resistance_scale) {
        const double total=double(pi.c1)+pi.c2;
        if (!(pi.c1>0. && pi.c2>0. && pi.rpi>0. && total>0.)) return std::nullopt;
        const double unloaded=std::max(0.,double(lookup_nldm(slew,float(input),0.f)))*derate;
        const double duration=unloaded/(upper-lower);
        const double r=pi.rpi*resistance_scale;
        auto at=[&](double cap)->std::optional<Driver> {
            const double width=double(lookup_nldm(slew,float(input),float(cap)))*derate;
            if (!(width>unloaded && std::isfinite(width))) return std::nullopt;
            const double rd=fit_resistance(cap,duration,width,lower,upper);
            if (!(rd>0. && std::isfinite(rd))) return std::nullopt;
            const auto poles=pi_poles(pi.c1,r,pi.c2,rd);
            return Driver{cap,rd,duration,crossing(threshold,duration,poles),poles};
        };
        auto residual=[&](const Driver& d) {
            return d.crossing-crossing(threshold,d.ramp,Poles{d.resistance*d.cap,0.,1.});
        };
        double lo=pi.c2,hi=total;
        auto left=at(lo),right=at(hi);
        // Preserve the capacitive limit used by DMP: resolving a wire whose
        // resistance is negligible compared with the driver adds numerical
        // noise to a load that is already equipotential at timing precision.
        if (left && r<left->resistance*1e-3) return std::nullopt;
        if (!left || !right || residual(*left)<0. || residual(*right)>0.) return std::nullopt;
        for (unsigned i=0;i<32;++i) {
            const double cap=.5*(lo+hi);auto d=at(cap);
            if (!d) return std::nullopt;
            if (residual(*d)>0.) lo=cap; else hi=cap;
        }
        return at(.5*(lo+hi));
    }

public:
    std::optional<RcWaveformResult> calculate(
        const FullRcNetwork& rc, const PiModel& loaded_pi, double input_slew,
        const edacraft::core::NldmTable& delay, const edacraft::core::NldmTable& slew,
        double lower, double upper, double derate, double driver_threshold,
        double load_threshold, double cap_unit=1e-12, double time_unit=1e-9,
        const RcDelayThresholds* load_thresholds=nullptr,
        const RcSlewThresholds* load_windows=nullptr,
        bool use_characterized_driver=false, bool minimum=false, double receiver_pin_cap=-1.,
        double accumulated_cap=-1.,const FullRcNetwork* wire_network=nullptr,const FullRcNetwork* reference_network=nullptr,
        const std::vector<double>* precise_caps=nullptr) const {
        if (!(cap_unit>0. && time_unit>0. && lower>0. && upper<1. && lower<upper &&
              derate>0. && driver_threshold>0. && driver_threshold<1. &&
              load_threshold>0. && load_threshold<1.) || delay.values.empty() ||
              slew.values.empty()) return std::nullopt;
        const size_t n=rc.nodes.size();const uint32_t source=rc.driver_node_id;
        if (n<2 || source>=n || (precise_caps && precise_caps->size()!=n)) return std::nullopt;
        const NetworkCaps network(&rc,use_characterized_driver?precise_caps:nullptr,reference_network);
        // Known pin charge and a balanced extracted star define a short
        // charge-weighted response. Larger/unbalanced networks retain ROM.
        if(use_characterized_driver && n>=2 && n<=10 && receiver_pin_cap>=0. &&
           (n==2 || (wire_network && wire_network->nodes.size()==n && rc.resistors.size()==n-1))) {
            const double total=network_total_cap(loaded_pi,network,cap_unit,accumulated_cap);
            bool connected=true;double resistance_sum=0.,conductance=0.,first_r=-1.,first_wire=-1.;
            std::vector<bool> seen(n,false);seen[source]=true;
            for(const auto& edge:rc.resistors) {
                const size_t sink=edge.node1==source?edge.node2:(edge.node2==source?edge.node1:n);
                if(sink>=n || (n>2 && seen[sink]) || !valid(rc.nodes[sink].pin) || !(edge.resistance>0.)) {connected=false;break;}
                seen[sink]=true;
                const auto window=rc_slew_window(uint32_t(sink),float(lower),float(upper),float(derate),load_windows);
                double threshold=load_threshold;
                if(load_thresholds) {const auto it=load_thresholds->find(uint32_t(sink));if(it!=load_thresholds->end())threshold=it->second;}
                if(std::fabs(threshold-driver_threshold)>1e-6 || std::fabs(window.lower-lower)>1e-6 ||
                   std::fabs(window.upper-upper)>1e-6 || std::fabs(window.derate-derate)>1e-6) {connected=false;break;}
                if(n>2 && first_r>=0. && edge.resistance!=first_r) {connected=false;break;}
                first_r=edge.resistance;
                if(wire_network) {
                    const double wire=wire_network->nodes[sink].gnd_cap;
                    if(first_wire>=0. && std::fabs(wire-first_wire)>4.*std::numeric_limits<float>::epsilon()*std::max(wire,first_wire)) {connected=false;break;}
                    first_wire=wire;
                }
                const double resistance=double(edge.resistance)*rc.res_scale*cap_unit/time_unit;
                resistance_sum+=resistance;conductance+=1./resistance;
            }
            if(n==2 && conductance>0.)resistance_sum=1./conductance;
            const double wire=total-receiver_pin_cap,fanout=n-1;
            const double beta=resistance_sum*(wire/(fanout+1.)+receiver_pin_cap/fanout);
            const double next=std::max(total*1.01,total+1e-21/cap_unit);
            const bool positive=nldm_detail::stable_delay_lookup(delay,input_slew,next)>nldm_detail::stable_delay_lookup(delay,input_slew,total);
            if(connected && wire>0. && beta>0. && beta*time_unit<2e-12 && positive) {
                const double width=std::log((1.-lower)/(1.-upper))/derate;
                const double corrected=lookup_nldm(slew,float(input_slew),float(total))-.3*beta*width;
                if(corrected>0.) {
                    RcWaveformResult result;
                    result.driver.delay=Delay{float(lookup_nldm(delay,float(input_slew),float(total))+.3*beta*std::log(1.-driver_threshold))};
                    result.driver.output_slew=Slew{float(corrected)};result.driver.ceff=float(total);result.driver.source=DelayModelSource::Nldm;
                    for(size_t sink=0;sink<n;++sink)if(sink!=source) {
                        auto& load=result.loads[rc.nodes[sink].pin.id];load.delay=Delay{float(-beta*std::log(1.-driver_threshold))};
                        load.output_slew=Slew{float(std::hypot(corrected,beta*width))};load.ceff=float(total);load.source=DelayModelSource::Nldm;
                    }
                    return result;
                }
            }
        }
        auto model=use_characterized_driver ? characterized_driver(loaded_pi,input_slew,
            delay,slew,lower,upper,derate,driver_threshold,cap_unit/time_unit,
            // Native lower Ceff bound is 1e-9 pF; keep it in physical units.
            1e-21/cap_unit,network,cap_unit,time_unit,accumulated_cap) : std::nullopt;
        // A table with a nonpositive local delay slope cannot define a
        // positive source resistance. Use its loaded late/unloaded early
        // voltage ramp, retaining the distributed receiving-node response.
        if(use_characterized_driver) {
            const double total=double(loaded_pi.c1)+loaded_pi.c2;
            const double next=std::max(total*1.01,total+1e-21/cap_unit);
            if(total>0. && nldm_detail::stable_delay_lookup(delay,input_slew,next)<=nldm_detail::stable_delay_lookup(delay,input_slew,total)) {
                const double cap=minimum?0.:total;
                const double duration=double(lookup_nldm(slew,float(input_slew),float(cap)))*derate/(upper-lower);
                const double rd=cap_unit/time_unit;
                auto poles=distributed_poles(network,cap_unit,time_unit,rd);
                if(!poles)poles=pi_poles(loaded_pi.c1,loaded_pi.rpi*cap_unit/time_unit,loaded_pi.c2,rd);
                if(poles && duration>0.)model=Driver{cap,rd,duration,driver_threshold*duration,*poles,driver_threshold*duration,true,false,rd,true};
            }
        }
        if (!model) model=driver(loaded_pi,input_slew,slew,lower,upper,derate,
                                 driver_threshold,cap_unit/time_unit);
        if (!model) return std::nullopt;
        // The bounded source models a shielded network. Its early envelope
        // propagates the source transition without additional net degradation;
        // delay still comes from the receiving node's physical crossing.
        auto finish=[&](RcWaveformResult result) {
            if(model->zero_slope) {
                result.driver.delay=Delay{lookup_nldm(delay,float(input_slew),float(model->cap))};
                result.driver.output_slew=Slew{lookup_nldm(slew,float(input_slew),float(model->cap))};
            }
            if (minimum && model->characterized && model->rc009) {
                for (size_t i=0;i<n;++i) if (i!=source && valid(rc.nodes[i].pin)) {
                    const auto window=rc_slew_window(uint32_t(i),float(lower),float(upper),float(derate),load_windows);
                    auto& value=result.loads.at(rc.nodes[i].pin.id);
                    // The nondegrading early envelope is a transition-width
                    // convention, including receiving rails with different
                    // windows. Net delay retains the physical crossing above.
                    // This is an upper envelope, not a replacement for a
                    // physically narrower receiving-voltage window.
                    value.output_slew=Slew{std::min(value.output_slew.value,
                        float(result.driver.output_slew.value*
                        (window.upper-window.lower)/(upper-lower)*derate/window.derate))};
                }
            }
            return result;
        };
        std::vector<double> caps(n),cd(n),voltage(n),next(n),current(n),rhs(n);
        std::vector<RcLinearSystem::Edge> edges;
        std::vector<std::array<double,3>> targets(n),times(n);
        const double nan=std::numeric_limits<double>::quiet_NaN();
        double latest=upper,total=0.;size_t remaining=0;
        for (size_t i=0;i<n;++i) {
            if (rc.nodes[i].id!=i) return std::nullopt;
            caps[i]=network.cap(i)*double(rc.cap_scale)/cap_unit;total+=caps[i];
            if (!(caps[i]>=0. && std::isfinite(caps[i]))) return std::nullopt;
            auto window=rc_slew_window(uint32_t(i),float(lower),float(upper),float(derate),load_windows);
            double threshold=load_threshold;
            if (load_thresholds) {
                const auto found=load_thresholds->find(uint32_t(i));
                if (found!=load_thresholds->end()) threshold=found->second;
            }
            if (i==source) { window={float(lower),float(upper),float(derate)};threshold=driver_threshold; }
            targets[i]={window.lower,threshold,window.upper};times[i]={nan,nan,nan};
            if (!(window.lower>0. && window.upper<1. && window.lower<window.upper &&
                  window.derate>0. && threshold>0. && threshold<1.)) return std::nullopt;
            latest=std::max({latest,threshold,double(window.upper)});
            if (i==source || valid(rc.nodes[i].pin)) remaining+=3;
        }
        if (std::fabs(total-loaded_pi.c1-loaded_pi.c2)>1e-4*total) return std::nullopt;
        for (const auto& e:rc.resistors) {
            if (e.node1>=n || e.node2>=n || e.node1==e.node2) return std::nullopt;
            const double r=e.resistance*double(rc.res_scale)*cap_unit/time_unit;
            if (!(r>0. && std::isfinite(r))) return std::nullopt;
            edges.push_back({e.node1,e.node2,1./r});
        }
        // An equipotential far group is exactly a two-pole network when all
        // branches have the same R*C. Resistors inside that group carry no
        // current. Verify this from the full extraction, including its caps;
        // a moment-matched Pi alone does not establish this equivalence.
        if (model->characterized && !model->zero_slope) {
            std::vector<double> branch(n,0.);
            for (const auto& e:edges) {
                if (e.a==source) branch[e.b]+=e.g;
                if (e.b==source) branch[e.a]+=e.g;
            }
            double tau=0.;bool equivalent=true;
            for (size_t i=0;i<n;++i) if(i!=source) {
                if (!(caps[i]>0. && branch[i]>0.)) {equivalent=false;break;}
                const double value=caps[i]/branch[i];
                if (tau==0.) tau=value;
                else if (std::fabs(value-tau)>1e-6*std::max(value,tau)) {equivalent=false;break;}
            }
            const double far=total-caps[source];
            const double r=loaded_pi.rpi*cap_unit/time_unit;
            equivalent=equivalent && std::fabs(caps[source]-loaded_pi.c2)<=1e-6*total &&
                std::fabs(far-loaded_pi.c1)<=1e-6*total &&
                std::fabs(tau-r*far)<=1e-6*tau;
            if (equivalent) {
                RcWaveformResult result;bool complete=true;
                for (size_t i=0;i<n;++i) if(i==source || valid(rc.nodes[i].pin)) {
                    auto poles=model->poles;
                    if(i!=source) poles.first=poles.slow/(poles.slow-poles.fast);
                    const auto a=characterized_crossing(targets[i][0],model->ramp,poles);
                    const auto b=characterized_crossing(targets[i][1],model->ramp,poles);
                    const auto c=a?characterized_crossing(targets[i][2],model->ramp,poles,*a):std::nullopt;
                    if(!a || !b || !c || !(*a<*c)) {complete=false;break;}
                    times[i]={*a,*b,*c};
                }
                if(complete) {
                    result.driver.delay=Delay{float(lookup_nldm(delay,float(input_slew),float(model->cap))+
                        times[source][1]-model->reference_crossing)};
                    result.driver.output_slew=Slew{float((times[source][2]-times[source][0])/derate)};
                    result.driver.ceff=float(model->cap);result.driver.source=DelayModelSource::Nldm;
                    for(size_t i=0;i<n;++i) if(i!=source && valid(rc.nodes[i].pin)) {
                        const auto window=rc_slew_window(uint32_t(i),float(lower),float(upper),float(derate),load_windows);
                        auto& value=result.loads[rc.nodes[i].pin.id];
                        value.delay=Delay{float(times[i][1]-times[source][1])};
                        value.output_slew=Slew{float((times[i][2]-times[i][0])/window.derate)};
                        value.ceff=float(total);value.source=DelayModelSource::Nldm;
                    }
                    return finish(result);
                }
            }
        }
        if (model->characterized) {
            const double fitted=model->network_resistance>0.?model->network_resistance:model->resistance;
            const double rd=fitted;
            RcReducedModel rom;
            // RF changes update the capacitance matrix without rebuilding
            // the physical-voltage Krylov space from a different reference.
            std::vector<double> nominal=caps;
            if(reference_network && reference_network->nodes.size()==n)
                for(size_t i=0;i<n;++i)
                    nominal[i]=double(reference_network->nodes[i].gnd_cap)*
                        double(reference_network->cap_scale)/cap_unit;
            if (rom.initialize_receivers(nominal,edges,source,1./rd,1./rd,1e-13/time_unit) &&
                rom.update_receivers(caps,source)) {
                RcWaveformResult result;bool complete=true;
                const auto low=characterized_crossing(lower,model->ramp,model->poles);
                const auto high=low?characterized_crossing(upper,model->ramp,model->poles,*low):std::nullopt;
                if (!low || !high) complete=false;
                else {
                    result.driver.delay=Delay{float(lookup_nldm(delay,float(input_slew),float(model->cap))+model->crossing-model->reference_crossing)};
                    result.driver.output_slew=Slew{float((*high-*low)/derate)};
                    result.driver.ceff=float(model->cap);result.driver.source=DelayModelSource::Nldm;
                    for(size_t i=0;i<n;++i) if(i!=source && valid(rc.nodes[i].pin)) {
                        Poles poles{0.,1e300,1.};double dc=0.;
                        for(size_t j=0;j<rom.eigen.size();++j) {
                            if(!(rom.eigen[j]>0.)) {complete=false;break;}
                            const double tau=1./rom.eigen[j],weight=rom.output[i][j]*rom.b[j]/(rd*rom.eigen[j]);
                            poles.modes.push_back({tau,weight});poles.slow=std::max(poles.slow,tau);poles.fast=std::min(poles.fast,tau);dc+=weight;
                        }
                        if(!complete || std::fabs(dc-1.)>1e-5) {complete=false;break;}
                        const auto a=characterized_crossing(targets[i][0],model->ramp,poles);
                        const auto b=characterized_crossing(targets[i][1],model->ramp,poles);
                        const auto c=a?characterized_crossing(targets[i][2],model->ramp,poles,*a):std::nullopt;
                        if(!a || !b || !c || !(*a<*c)) {complete=false;break;}
                        const auto window=rc_slew_window(uint32_t(i),float(lower),float(upper),float(derate),load_windows);
                        auto& value=result.loads[rc.nodes[i].pin.id];
                        value.delay=Delay{float(*b-model->crossing)};
                        value.output_slew=Slew{float((*c-*a)/window.derate)};
                        value.ceff=float(total);value.source=DelayModelSource::Nldm;
                    }
                }
                if(complete)return finish(result);
            }
        }
        const double horizon=model->ramp+(8.-std::log(1.-latest))*model->poles.slow;
        double step=horizon/16384.;
        if (model->ramp>0.) step=std::min(step,model->ramp/32.);
        // Bound work for an extremely short intrinsic ramp; trapezoidal
        // integration remains passive even when a fast pole is unresolved.
        step=std::max(step,horizon/65536.);
        const double conductance=1./(model->network_resistance>0.?model->network_resistance:model->resistance);
        if (model->ramp==0.) current[source]=conductance;
        for (size_t i=0;i<n;++i) cd[i]=2.*caps[i]/step;
        auto diagonal=cd;diagonal[source]+=conductance;
        RcLinearSystem system;
        if (!system.initialize(n,source,edges) || !system.factor(diagonal)) return std::nullopt;
        for (unsigned tick=1;tick<=65536 && remaining;++tick) {
            const double t=tick*step;
            for (size_t i=0;i<n;++i) rhs[i]=cd[i]*voltage[i]+current[i];
            rhs[source]+=conductance*(model->ramp>0.?std::min(t/model->ramp,1.):1.);
            if (!system.reduce(rhs)) return std::nullopt;
            system.back_substitute(system.driver_rhs/system.driver_diagonal,next);
            for (size_t i=0;i<n;++i) {
                if (!std::isfinite(next[i])) return std::nullopt;
                if (i==source || valid(rc.nodes[i].pin)) for (unsigned j=0;j<3;++j)
                    if (!std::isfinite(times[i][j]) && voltage[i]<targets[i][j] && next[i]>=targets[i][j]) {
                        times[i][j]=t-step+step*(targets[i][j]-voltage[i])/(next[i]-voltage[i]);--remaining;
                    }
                current[i]=cd[i]*(next[i]-voltage[i])-current[i];
            }
            voltage.swap(next);
        }
        if (remaining) return std::nullopt;
        if(model->characterized) {
            // Source characterization uses its reduced driving-point response.
            // The distributed integration supplies receiving-node crossings.
            const auto low=characterized_crossing(lower,model->ramp,model->poles);
            const auto high=low?characterized_crossing(upper,model->ramp,model->poles,*low):std::nullopt;
            if(low && high) times[source]={*low,model->crossing,*high};
        }
        RcWaveformResult result;
        result.driver.delay=Delay{lookup_nldm(delay,float(input_slew),float(model->cap))};
        if (model->characterized) result.driver.delay.value+=
            float(times[source][1]-model->reference_crossing);
        result.driver.output_slew=Slew{float((times[source][2]-times[source][0])/derate)};
        result.driver.ceff=float(model->cap);result.driver.source=DelayModelSource::Nldm;
        for (size_t i=0;i<n;++i) if (i!=source && valid(rc.nodes[i].pin)) {
            const auto window=rc_slew_window(uint32_t(i),float(lower),float(upper),float(derate),load_windows);
            auto& value=result.loads[rc.nodes[i].pin.id];
            value.delay=Delay{float(times[i][1]-times[source][1])};
            value.output_slew=Slew{float((times[i][2]-times[i][0])/window.derate)};
            value.ceff=float(total);value.source=DelayModelSource::Nldm;
        }
        return finish(result);
    }
};
} // namespace te
