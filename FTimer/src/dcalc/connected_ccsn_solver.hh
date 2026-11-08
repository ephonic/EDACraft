#pragma once
#include "coupled_rc_solver.hh"
#include <set>

namespace te {
// Bounded nonlinear MNA for explicitly connected experimental CCSN-data CCBs.
// Inputs are physical nodes, so Miller C draws input current and feeds back
// receiver output motion. Current relaxation remains an explicit hypothesis.
class ConnectedCcsnSolver {
public:
    using Rc=CoupledRcSolver;
    struct Stage {
        size_t input, output;
        Rc::DynamicStage table;
        double input_pf=0.; // intrinsic input-to-ground C, excluding Miller C
        // Explicit intrinsic differential Cq(Vo), (V,pF), in addition to Cout.
        // PWL C integrates to continuous quadratic Q; endpoint C is constant.
        std::vector<std::pair<double,double>> output_cap_profile;
    };
    struct Source {
        size_t node;
        double ohms=0.; // zero is exact Dirichlet boundary
        std::vector<double> time, voltage;
    };
    struct Current { double value, input_derivative, output_derivative; };
    struct OutputCharge {
        std::vector<std::pair<double,double>> knots;
        std::vector<double> charge;
        explicit OutputCharge(const std::vector<std::pair<double,double>>& p):knots(p) {
            if(p.empty())return;
            if(p.size()<2 || p.size()>4096)throw std::runtime_error("Invalid connected CCSN charge profile size");
            charge.resize(p.size(),0.);
            for(size_t k=0;k<p.size();++k) {
                if(!std::isfinite(p[k].first) || !std::isfinite(p[k].second) || p[k].second<0 ||
                    (k && !(p[k].first>p[k-1].first)))
                    throw std::runtime_error("Invalid connected CCSN differential capacitance profile");
                if(k)charge[k]=charge[k-1]+.5*(p[k-1].second+p[k].second)*(p[k].first-p[k-1].first);
                if(!std::isfinite(charge[k]))throw std::runtime_error("Connected CCSN charge profile overflow");
            }
        }
        // Returns Q and dQ/dV. Q's arbitrary additive constant is zero at knot0.
        std::pair<double,double> at(double v) const {
            if(knots.empty())return {0.,0.};
            if(v<=knots.front().first)return {knots.front().second*(v-knots.front().first),knots.front().second};
            if(v>=knots.back().first)return {charge.back()+knots.back().second*(v-knots.back().first),knots.back().second};
            const size_t k=std::upper_bound(knots.begin(),knots.end(),v,
                [](double a,const auto& b){return a<b.first;})-knots.begin()-1;
            const double u=v-knots[k].first,slope=(knots[k+1].second-knots[k].second)/(knots[k+1].first-knots[k].first);
            return {charge[k]+knots[k].second*u+.5*slope*u*u,knots[k].second+slope*u};
        }
    };
    static Current current(const Rc::DynamicStage& d,double vi,double vo) {
        const auto& x=d.input_voltage;const auto& y=d.output_voltage;
        if(x.size()<2 || y.size()<2 || x.size()>8000000/y.size() ||
            d.current_ma.size()!=x.size()*y.size() || !std::isfinite(vi) || !std::isfinite(vo) ||
            vi<x.front() || vi>x.back() || vo<y.front() || vo>y.back())
            throw std::runtime_error("Connected CCSN voltage outside characterized domain");
        auto interval=[](const auto& axis,double v) {
            size_t k=std::upper_bound(axis.begin(),axis.end(),v)-axis.begin();
            return std::min(std::max(k,size_t(1)),axis.size()-1)-1;
        };
        const size_t i=interval(x,vi),j=interval(y,vo),ny=y.size();
        const double f=(vi-x[i])/(x[i+1]-x[i]),g=(vo-y[j])/(y[j+1]-y[j]);
        const double a=d.current_ma[i*ny+j],b=d.current_ma[i*ny+j+1];
        const double c=d.current_ma[(i+1)*ny+j],e=d.current_ma[(i+1)*ny+j+1];
        return {(1-f)*((1-g)*a+g*b)+f*((1-g)*c+g*e),
            ((1-g)*(c-a)+g*(e-b))/(x[i+1]-x[i]),
            ((1-f)*(b-a)+f*(e-c))/(y[j+1]-y[j])};
    }
    static double value(const Source& s,double t) {
        size_t k=std::upper_bound(s.time.begin(),s.time.end(),t)-s.time.begin();
        k=std::min(std::max(k,size_t(1)),s.time.size()-1)-1;
        return s.voltage[k]+(s.voltage[k+1]-s.voltage[k])*
            (t-s.time[k])/(s.time[k+1]-s.time[k]);
    }
    static Rc::Result solve(size_t n,const std::vector<Rc::Resistor>& resistors,
        const std::vector<Rc::Capacitor>& capacitors,const std::vector<Source>& sources,
        const std::vector<Stage>& stages,std::vector<double> initial,
        double begin,double end,double max_dt,size_t max_steps=100000) {
        if(!n || n>64 || stages.size()>16 || initial.size()!=n ||
            !std::isfinite(begin) || !std::isfinite(end) || !(end>begin) ||
            !std::isfinite(max_dt) || !(max_dt>0))
            throw std::runtime_error("Invalid connected CCSN dimensions/time (64 nodes, 16 stages)");
        for(double v:initial)if(!std::isfinite(v))throw std::runtime_error("Invalid connected CCSN initial voltage");
        const size_t budget=std::min(max_steps,size_t(8000000/n));
        std::vector<double> c(n*n,0.),g(n*n,0.),corners{begin,end};
        struct Refinement { double time,dt; bool enter; };
        std::vector<Refinement> refinements;
        auto stamp=[&](auto& a,size_t i,size_t j,double v) {
            if(i>=n || (j!=SIZE_MAX && j>=n) || !std::isfinite(v) || v<0 || i==j)
                throw std::runtime_error("Invalid connected CCSN passive element");
            a[i*n+i]+=v;
            if(j!=SIZE_MAX){a[j*n+j]+=v;a[i*n+j]-=v;a[j*n+i]-=v;}
        };
        for(const auto& r:resistors) {
            if(!(r.ohms>0))throw std::runtime_error("Invalid connected CCSN resistance");
            stamp(g,r.a,r.b,1000./r.ohms);
        }
        for(const auto& a:capacitors)stamp(c,a.a,a.b,a.pf);
        std::vector<const Source*> ideal(n,nullptr);
        std::vector<bool> driven(n,false),output(n,false);
        size_t samples=0;
        for(const auto& s:sources) {
            if(s.node>=n || driven[s.node] || s.time.size()<2 || s.time.size()!=s.voltage.size() ||
                !std::isfinite(s.ohms) || s.ohms<0 || s.time.size()>8000000-samples)
                throw std::runtime_error("Invalid connected CCSN source");
            samples+=s.time.size();driven[s.node]=true;
            for(size_t k=0;k<s.time.size();++k) {
                if(!std::isfinite(s.time[k]) || !std::isfinite(s.voltage[k]) ||
                    (k && !(s.time[k]>s.time[k-1])))
                    throw std::runtime_error("Invalid connected CCSN source waveform");
                if(s.time[k]>begin && s.time[k]<end)corners.push_back(s.time[k]);
                if(k) {
                    // A corner alone is insufficient: BE can otherwise take
                    // one step across a short edge and suppress its peak.
                    // Match the ramp resolution of CoupledRcSolver, including
                    // four edge lengths of recovery. Use knot times alone so
                    // active and paired quiet sources keep identical grids.
                    const double duration=s.time[k]-s.time[k-1],dt=duration/64.;
                    if(!(dt>0))throw std::runtime_error("Connected CCSN source interval too small");
                    const double a=std::max(begin,s.time[k-1]);
                    const double b=std::min(end,s.time[k]+4.*duration);
                    if(dt<max_dt && b>a) {
                        refinements.push_back({a,dt,true});refinements.push_back({b,dt,false});
                        corners.push_back(a);corners.push_back(b);
                    }
                }
            }
            if(s.time.front()>begin || s.time.back()<end)
                throw std::runtime_error("Connected CCSN source window incomplete");
            if(s.ohms==0) {
                ideal[s.node]=&s;
                if(std::fabs(initial[s.node]-value(s,begin))>1e-12)
                    throw std::runtime_error("Connected CCSN initial boundary conflict");
            } else stamp(g,s.node,SIZE_MAX,1000./s.ohms);
        }
        std::vector<double> state,reference_output;
        std::vector<OutputCharge> output_charge;
        for(const auto& s:stages) {
            const auto& d=s.table;
            if(s.input>=n || s.output>=n || s.input==s.output || driven[s.output] || output[s.output] ||
                !std::isfinite(s.input_pf) || s.input_pf<0 || !std::isfinite(d.output_pf) || d.output_pf<0 ||
                !std::isfinite(d.miller_pf) || d.miller_pf<0 || !std::isfinite(d.tau_ns) || d.tau_ns<0)
                throw std::runtime_error("Invalid connected CCSN stage/overlapping output");
            output[s.output]=true;
            output_charge.emplace_back(s.output_cap_profile);
            for(const auto* axis:{&d.input_voltage,&d.output_voltage}) {
                if(axis->size()<2)throw std::runtime_error("Connected CCSN axis too small");
                for(size_t k=0;k<axis->size();++k)
                    if(!std::isfinite((*axis)[k]) || (k && !((*axis)[k]>(*axis)[k-1])))
                        throw std::runtime_error("Invalid connected CCSN axis");
            }
            for(double a:d.current_ma)if(!std::isfinite(a))throw std::runtime_error("Invalid connected CCSN DC current");
            state.push_back(current(d,initial[s.input],initial[s.output]).value);
            reference_output.push_back(initial[s.output]);
            stamp(c,s.input,s.output,d.miller_pf);
            stamp(c,s.input,SIZE_MAX,s.input_pf);stamp(c,s.output,SIZE_MAX,d.output_pf);
        }
        std::sort(corners.begin(),corners.end());
        corners.erase(std::unique(corners.begin(),corners.end()),corners.end());
        std::sort(refinements.begin(),refinements.end(),[](const auto& a,const auto& b){return a.time<b.time;});
        std::multiset<double> active_resolution;
        size_t refinement=0;
        Rc::Result result{{begin},{std::move(initial)}};
        std::vector<double> v(n),residual(n),jac(n*n),delta(n),candidate(n),test(n);
        auto norm=[](const auto& a){double z=0.;for(double x:a)z=std::max(z,std::fabs(x));return z;};
        size_t count=0;
        for(size_t segment=1;segment<corners.size();++segment) {
            const double start=corners[segment-1];
            while(refinement<refinements.size() && refinements[refinement].time<=start) {
                const auto& event=refinements[refinement++];
                if(event.enter)active_resolution.insert(event.dt);
                else active_resolution.erase(active_resolution.find(event.dt));
            }
            const double resolution=active_resolution.empty()?max_dt:std::min(max_dt,*active_resolution.begin());
            const double duration=corners[segment]-start,requested=std::max(1.,std::ceil(duration/resolution));
            if(!std::isfinite(requested) || requested>budget-count)
                throw std::runtime_error("Connected CCSN step/memory budget exceeded");
            const size_t steps=size_t(requested);count+=steps;
            const double dt=duration/steps;
            for(size_t step=1;step<=steps;++step) {
                const double t=step==steps?corners[segment]:corners[segment-1]+step*dt;
                const auto& old=result.voltage.back();v=old;
                for(size_t i=0;i<n;++i)if(ideal[i])v[i]=value(*ideal[i],t);
                auto evaluate=[&](const auto& x,auto& f,std::vector<double>* matrix) {
                    for(const auto& s:stages)
                        if(x[s.input]<s.table.input_voltage.front() || x[s.input]>s.table.input_voltage.back() ||
                            x[s.output]<s.table.output_voltage.front() || x[s.output]>s.table.output_voltage.back())return false;
                    if(matrix)matrix->assign(n*n,0.);
                    for(size_t i=0;i<n;++i) {
                        // Form charge increments directly: subtracting two
                        // large C*v/dt products loses the small net current.
                        long double charge_current=0.;
                        for(size_t j=0;j<n;++j) {
                            const double a=g[i*n+j]+c[i*n+j]/dt;
                            charge_current+=static_cast<long double>(c[i*n+j])*(x[j]-old[j])/dt;
                            if(matrix)(*matrix)[i*n+j]=a;
                        }
                        f[i]=static_cast<double>(charge_current);
                    }
                    // Stamp each branch current once with opposite signs.
                    // Dense G*v cancellation otherwise introduces a false
                    // common-mode current for nearly shorted SPEF nodes.
                    for(const auto& r:resistors) {
                        const double branch=(1000./r.ohms)*(x[r.a]-(r.b==SIZE_MAX?0.:x[r.b]));
                        f[r.a]+=branch;if(r.b!=SIZE_MAX)f[r.b]-=branch;
                    }
                    for(const auto& s:sources)if(s.ohms>0)
                        f[s.node]+=(1000./s.ohms)*(x[s.node]-value(s,t));
                    for(size_t k=0;k<stages.size();++k) {
                        const auto& s=stages[k];const auto z=current(s.table,x[s.input],x[s.output]);
                        const double alpha=dt/(dt+s.table.tau_ns);
                        double output_current=(1-alpha)*state[k]+alpha*z.value;
                        double input_derivative=alpha*z.input_derivative;
                        double output_derivative=alpha*z.output_derivative;
                        if(!s.table.lag_output_feedback && s.table.tau_ns>0) {
                            const auto ref=current(s.table,x[s.input],reference_output[k]);
                            output_current=z.value+(1-alpha)*(state[k]-ref.value);
                            input_derivative=z.input_derivative-(1-alpha)*ref.input_derivative;
                            output_derivative=z.output_derivative;
                        }
                        f[s.output]-=output_current;
                        if(!s.output_cap_profile.empty()) {
                            const auto q=output_charge[k].at(x[s.output]);
                            f[s.output]+=(q.first-output_charge[k].at(old[s.output]).first)/dt;
                            if(matrix)(*matrix)[s.output*n+s.output]+=q.second/dt;
                        }
                        if(matrix) {
                            (*matrix)[s.output*n+s.input]-=input_derivative;
                            (*matrix)[s.output*n+s.output]-=output_derivative;
                        }
                    }
                    for(size_t i=0;i<n;++i)if(ideal[i]) {
                        f[i]=x[i]-value(*ideal[i],t);
                        if(matrix){for(size_t j=0;j<n;++j)(*matrix)[i*n+j]=i==j?1.:0.;}
                    }
                    for(double x:f)if(!std::isfinite(x))return false;
                    return true;
                };
                bool converged=false;
                for(size_t iteration=0;iteration<40;++iteration) {
                    if(!evaluate(v,residual,&jac))throw std::runtime_error("Connected CCSN trial outside voltage domain");
                    const double before=norm(residual);
                    if(before<=1e-11){converged=true;break;}
                    delta=residual;for(auto& z:delta)z=-z;
                    // Unsymmetric controlled-source Jacobian: partial-pivot LU.
                    for(size_t j=0;j<n;++j) {
                        size_t pivot=j;
                        for(size_t i=j+1;i<n;++i)if(std::fabs(jac[i*n+j])>std::fabs(jac[pivot*n+j]))pivot=i;
                        if(!std::isfinite(jac[pivot*n+j]) || std::fabs(jac[pivot*n+j])<1e-18)
                            throw std::runtime_error("Singular connected CCSN Jacobian");
                        if(pivot!=j){for(size_t k=j;k<n;++k)std::swap(jac[j*n+k],jac[pivot*n+k]);std::swap(delta[j],delta[pivot]);}
                        for(size_t i=j+1;i<n;++i) {
                            const double f=jac[i*n+j]/jac[j*n+j];
                            for(size_t k=j+1;k<n;++k)jac[i*n+k]-=f*jac[j*n+k];
                            delta[i]-=f*delta[j];
                        }
                    }
                    for(size_t i=n;i-- >0;) {
                        for(size_t j=i+1;j<n;++j)delta[i]-=jac[i*n+j]*delta[j];
                        delta[i]/=jac[i*n+i];
                    }
                    // These rows already satisfy their exact Dirichlet
                    // constraint. Pivoting a stiff network must not perturb
                    // the prescribed input by a roundoff-sized LU correction.
                    for(size_t i=0;i<n;++i)if(ideal[i])delta[i]=0.;
                    // Near a short, no representable voltage correction may
                    // reduce the remaining branch-current rounding error.
                    // Accept only a machine-scale correction AND a bounded
                    // rowwise backward error; do not relax physical currents
                    // with a global relative tolerance or alter the RC net.
                    if(norm(delta)<=32*std::numeric_limits<double>::epsilon()*std::max(1.,norm(v))) {
                        bool roundoff_only=true;
                        for(size_t i=0;i<n && roundoff_only;++i) {
                            long double scale=0.;
                            if(!ideal[i])for(size_t j=0;j<n;++j)
                                scale+=(std::fabs(g[i*n+j])+std::fabs(c[i*n+j]/dt))*
                                    std::max(std::fabs(v[j]),std::fabs(old[j]));
                            const long double bound=1e-11L+8*std::numeric_limits<double>::epsilon()*scale;
                            roundoff_only=std::fabs(residual[i])<=bound;
                        }
                        if(roundoff_only){converged=true;break;}
                    }
                    bool accepted=false;
                    for(double damping=1.;damping>=1./1048576.;damping*=.5) {
                        for(size_t i=0;i<n;++i)candidate[i]=v[i]+damping*delta[i];
                        if(evaluate(candidate,test,nullptr) && norm(test)<before) {v=candidate;accepted=true;break;}
                    }
                    if(!accepted)throw std::runtime_error("Connected CCSN Newton line search failed");
                }
                if(!converged)throw std::runtime_error("Connected CCSN Newton iteration budget exceeded");
                for(size_t k=0;k<stages.size();++k) {
                    const auto& s=stages[k];const double alpha=dt/(dt+s.table.tau_ns);
                    state[k]=(1-alpha)*state[k]+alpha*current(s.table,v[s.input],
                        s.table.lag_output_feedback?v[s.output]:reference_output[k]).value;
                }
                result.time.push_back(t);result.voltage.push_back(v);
            }
        }
        return result;
    }
};
} // namespace te
