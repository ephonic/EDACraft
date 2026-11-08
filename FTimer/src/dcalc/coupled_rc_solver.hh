#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

namespace te {

// Full nodal C dv/dt + Gv = i. Capacitors between nodes retain their
// off-diagonal entries; replacing coupling with grounded caps cannot solve noise.
// Units: ns, pF, ohm, volts. Drivers are explicit Thevenin PWL sources.
class CoupledRcSolver {
public:
    struct Resistor { size_t a, b; double ohms; };
    struct Capacitor { size_t a, b; double pf; }; // b==SIZE_MAX means ground
    // ohms==0 is an exact prescribed voltage boundary, not a small R.
    struct Driver { size_t node; double ohms, initial, final, center, ramp; };
    // One characterized quiet output stage. Current is injected into the
    // physical node, in mA; a passive restoring table is nonincreasing.
    // Replaces a quiet Thevenin driver at this node, when present, keeping
    // its event grid. This is not a full dynamic CCSN gate model.
    struct StaticDriver {
        size_t node;
        std::vector<double> voltage, current_ma;
        // Optional passive PWL output charge (pC) on the same voltage grid.
        // Kept separate from the physical RC capacitance matrix.
        std::vector<double> output_charge_pc;
    };
    // Explicit characterized source law I(t,V)=injection_ma(t)-g(t)*V.
    // Both tables are PWL in time; nonnegative g is passive output feedback.
    // The caller supplies an isolated-reference-consistent source law. This
    // primitive does not extract CCSN parameters or select a timing arc.
    struct NortonSource {
        size_t node;
        std::vector<double> time, injection_ma, conductance_ma_per_v;
    };
    // Experimental single CCB with a prescribed input (not a coupled receiver).
    // Idc is bilinear, input-major, in mA. tau=0 is the instantaneous law;
    // tau>0 relaxes only the input excitation at the initial output reference:
    // tau*dJ/dt=Idc(Vin,Vref)-J; Iout=J+Idc(Vin,Vout)-Idc(Vin,Vref).
    // Output recovery feedback is instantaneous. The previous whole-current
    // relaxation remains an explicit diagnostic option, not a vendor model.
    // Miller current
    // is stamped as Cm*dVin/dt and Cm on the output diagonal. Cout excludes
    // external RC, receiver capacitance and Cm. No voltage extrapolation.
    struct DynamicStage {
        size_t node;
        std::vector<double> input_voltage, output_voltage, current_ma;
        std::vector<double> time, input_v;
        double miller_pf=0., output_pf=0., tau_ns=0.;
        bool lag_output_feedback=false; // legacy tau*dJ/dt=Idc(Vin,Vout)-J
    };
    static double stage_input(const DynamicStage& d, double t) {
        if (d.time.size()<2 || d.time.size()!=d.input_v.size() ||
            t<d.time.front() || t>d.time.back())
            throw std::runtime_error("SI stage input outside prescribed time domain");
        size_t k=std::upper_bound(d.time.begin(),d.time.end(),t)-d.time.begin();
        k=std::min(std::max(k,size_t(1)),d.time.size()-1)-1;
        const double f=(t-d.time[k])/(d.time[k+1]-d.time[k]);
        return d.input_v[k]+f*(d.input_v[k+1]-d.input_v[k]);
    }
    static std::vector<double> stage_slice(const DynamicStage& d, double vi) {
        const auto& x=d.input_voltage; const auto& y=d.output_voltage;
        if (x.size()<2 || y.size()<2 || x.size()>8000000/y.size() ||
            d.current_ma.size()!=x.size()*y.size() || !std::isfinite(vi) ||
            vi<x.front() || vi>x.back())
            throw std::runtime_error("Invalid SI stage table/domain");
        for (const auto* axis:{&x,&y}) for(size_t k=0;k<axis->size();++k)
            if (!std::isfinite((*axis)[k]) || (k && !((*axis)[k]>(*axis)[k-1])))
                throw std::runtime_error("Invalid SI stage voltage axis");
        size_t i=std::upper_bound(x.begin(),x.end(),vi)-x.begin();
        i=std::min(std::max(i,size_t(1)),x.size()-1)-1;
        const double f=(vi-x[i])/(x[i+1]-x[i]);
        std::vector<double> out(y.size());
        for(size_t j=0;j<y.size();++j) {
            out[j]=d.current_ma[i*y.size()+j]+f*(d.current_ma[(i+1)*y.size()+j]-d.current_ma[i*y.size()+j]);
            if (!std::isfinite(out[j]) || (j && out[j]>out[j-1]))
                throw std::runtime_error("SI stage requires passive output feedback at prescribed input");
        }
        return out;
    }
    struct Result { std::vector<double> time; std::vector<std::vector<double>> voltage; };

    // A caller may share this plan between active and paired quiet solves.
    // It changes sampling only, never the PWL source or circuit equations.
    struct TimeGrid {
        struct Window { double begin,end,step; };
        std::vector<double> corners;
        std::vector<Window> windows;
    };
    static TimeGrid source_grid(const std::vector<NortonSource>& sources,
                               const DynamicStage* stage=nullptr) {
        TimeGrid grid;
        auto add=[&](const auto& time,const std::vector<const std::vector<double>*>& axes) {
            if(time.size()<2)throw std::runtime_error("Invalid SI source grid dimensions");
            std::vector<double> ranges;
            for(const auto* axis:axes) {
                const auto& a=*axis;
                if(a.size()!=time.size())throw std::runtime_error("Invalid SI source grid dimensions");
                for(double v:a)if(!std::isfinite(v))throw std::runtime_error("Invalid SI source grid value");
                const auto mm=std::minmax_element(a.begin(),a.end());
                ranges.push_back(*mm.second-*mm.first);
                if(!std::isfinite(ranges.back()))throw std::runtime_error("SI source grid range overflow");
            }
            for(size_t k=0;k<time.size();++k) {
                if(!std::isfinite(time[k]) || (k && !(time[k]>time[k-1])))
                    throw std::runtime_error("Invalid SI source grid time");
                grid.corners.push_back(time[k]);
                if(!k)continue;
                double fraction=0.;
                for(size_t j=0;j<axes.size();++j)if(ranges[j]>0)
                    fraction=std::max(fraction,std::fabs((*axes[j])[k]-(*axes[j])[k-1])/ranges[j]);
                if(!(fraction>0))continue;
                // Resolve a full excursion by at least128 steps. Existing
                // dense samples stay mandatory, without multiplying each
                // small increment by64. Recovery retains the same scale.
                const double edge=(time[k]-time[k-1])/fraction,step=edge/128.;
                if(!std::isfinite(step))continue; // no tighter constraint
                if(!(step>0))throw std::runtime_error("SI source grid interval too small");
                double end=std::min(time.back(),time[k]+4.*edge);
                grid.windows.push_back({time[k-1],end,step});
                // A distributed RC peak can occur much later than the
                // input edge. Relax recovery resolution geometrically,
                // rather than jumping straight back to max_dt after4 edges.
                // This retains128 samples per growing time scale without
                // imposing the shortest input step over the full horizon.
                double span=4.*edge,recovery_step=step;
                while(end<time.back()) {
                    span*=2.;recovery_step*=2.;
                    const double next=std::min(time.back(),end+span);
                    if(!(next>end) || !std::isfinite(recovery_step))break;
                    grid.windows.push_back({end,next,recovery_step});end=next;
                }
            }
        };
        for(const auto& s:sources)add(s.time,{&s.injection_ma,&s.conductance_ma_per_v});
        if(stage)add(stage->time,{&stage->input_v});
        return grid;
    }

    static Result solve(size_t n, const std::vector<Resistor>& resistors,
        const std::vector<Capacitor>& capacitors, const std::vector<Driver>& drivers,
        std::vector<double> initial, double begin, double end, double max_dt,
        size_t max_steps = 100000, const StaticDriver* quiet = nullptr,
        const std::vector<NortonSource>& sources = {}, const DynamicStage* stage = nullptr,
        const TimeGrid* shared_grid = nullptr) {
        if (!n || n > 512 || initial.size() != n || !(max_dt > 0) || !(end > begin) ||
            !std::isfinite(begin) || !std::isfinite(end) || !std::isfinite(max_dt))
            throw std::runtime_error("Invalid coupled RC dimensions/time range (limit: 512 nodes)");
        StaticDriver stage_quiet;
        double stage_state=0., stage_reference_output=0.;
        if (stage) {
            const auto& d=*stage;
            if (quiet || d.node>=n || d.time.size()<2 || d.time.size()!=d.input_v.size() ||
                d.time.size()>8000000 || !std::isfinite(d.miller_pf) || d.miller_pf<0 ||
                !std::isfinite(d.output_pf) || d.output_pf<0 ||
                !std::isfinite(d.tau_ns) || d.tau_ns<0)
                throw std::runtime_error("Invalid SI experimental stage dimensions/parameters");
            for(size_t k=0;k<d.time.size();++k) {
                if (!std::isfinite(d.time[k]) || !std::isfinite(d.input_v[k]) ||
                    (k && !(d.time[k]>d.time[k-1])))
                    throw std::runtime_error("Invalid SI stage prescribed input");
                stage_slice(d,d.input_v[k]);
            }
            for(double value:d.current_ma) if (!std::isfinite(value))
                throw std::runtime_error("Invalid SI stage DC current");
            stage_quiet={d.node,d.output_voltage,stage_slice(d,stage_input(d,begin)),{}};
            quiet=&stage_quiet;
            const auto& x=quiet->voltage; const auto& y=quiet->current_ma;
            if (initial[d.node]<x.front() || initial[d.node]>x.back())
                throw std::runtime_error("SI stage initial output outside characterized range");
            size_t k=std::upper_bound(x.begin(),x.end(),initial[d.node])-x.begin();
            k=std::min(std::max(k,size_t(1)),x.size()-1)-1;
            stage_state=y[k]+(y[k+1]-y[k])*(initial[d.node]-x[k])/(x[k+1]-x[k]);
            stage_reference_output=initial[d.node];
            stage_input(d,end);
        }
        const double requested_steps = std::ceil((end-begin)/max_dt);
        if (!(requested_steps > 0) || requested_steps > max_steps || requested_steps > 8000000/n)
            throw std::runtime_error("SI waveform step/memory budget exceeded");
        for (double value : initial) if (!std::isfinite(value)) throw std::runtime_error("Invalid SI initial voltage");
        std::vector<bool> source_node(n,false);
        size_t source_samples=0;
        for (const auto& source:sources) {
            const size_t m=source.time.size();
            if (source.node>=n || source_node[source.node] || m<2 ||
                m!=source.injection_ma.size() || m!=source.conductance_ma_per_v.size() ||
                m>8000000-source_samples)
                throw std::runtime_error("Invalid SI Norton source dimensions/budget");
            source_samples+=m;source_node[source.node]=true;
            for (size_t k=0;k<m;++k)
                if (!std::isfinite(source.time[k]) || !std::isfinite(source.injection_ma[k]) ||
                    !std::isfinite(source.conductance_ma_per_v[k]) || source.conductance_ma_per_v[k]<0 ||
                    (k && !(source.time[k]>source.time[k-1])))
                    throw std::runtime_error("SI Norton source must be finite, ordered and passive");
            if (source.time.front()>begin || source.time.back()<end)
                throw std::runtime_error("SI Norton source does not cover solve interval");
            if (quiet && source.node==quiet->node)
                throw std::runtime_error("SI Norton source overlaps static driver");
        }
        std::vector<double> quiet_charge, quiet_current;
        double quiet_reference_cap=0., quiet_reference_g=0.;
        if (quiet) {
            const auto& q=*quiet;
            if (q.node>=n || q.voltage.size()<2 || q.voltage.size()!=q.current_ma.size())
                throw std::runtime_error("Invalid SI static I-V dimensions");
            if (!q.output_charge_pc.empty() && q.output_charge_pc.size()!=q.voltage.size())
                throw std::runtime_error("Invalid SI output charge dimensions");
            quiet_charge.resize(q.voltage.size(),0.);
            for (size_t k=0;k<q.voltage.size();++k) {
                if (!std::isfinite(q.voltage[k]) || !std::isfinite(q.current_ma[k]) ||
                    (k && (!(q.voltage[k]>q.voltage[k-1]) || q.current_ma[k]>q.current_ma[k-1])))
                    throw std::runtime_error("SI static I-V must be finite, ordered and passive");
                if (!q.output_charge_pc.empty()) {
                    if (!std::isfinite(q.output_charge_pc[k]) ||
                        (k && q.output_charge_pc[k]<q.output_charge_pc[k-1]))
                        throw std::runtime_error("SI output charge must be finite and nondecreasing");
                    quiet_charge[k]=q.output_charge_pc[k]-q.output_charge_pc.front();
                    if (!std::isfinite(quiet_charge[k]))
                        throw std::runtime_error("Invalid SI output charge range");
                }
            }
            // A restoring I-V law also anchors the physical node. Keep half
            // its minimum conductance in G, and compensate the residual
            // source exactly. Without this split, an otherwise well-posed
            // output with no external C (or with a flat Q interval) fails
            // before the nonlinear driver is included in the Schur solve.
            double minimum_g=std::numeric_limits<double>::infinity();
            for (size_t k=1;k<q.voltage.size();++k) {
                const double conductance=(q.current_ma[k-1]-q.current_ma[k])/
                    (q.voltage[k]-q.voltage[k-1]);
                if (!std::isfinite(conductance)) throw std::runtime_error("Invalid SI restoring conductance");
                minimum_g=std::min(minimum_g,conductance);
            }
            quiet_reference_g=stage?0.:.5*minimum_g;
            quiet_current=q.current_ma;
            for (size_t k=0;k<q.voltage.size();++k) {
                quiet_current[k]+=quiet_reference_g*q.voltage[k];
                if (!std::isfinite(quiet_current[k])) throw std::runtime_error("Invalid SI residual current");
            }
            if (!q.output_charge_pc.empty()) {
                double minimum_cap=std::numeric_limits<double>::infinity();
                for (size_t k=1;k<q.voltage.size();++k) {
                    const double cap=(quiet_charge[k]-quiet_charge[k-1])/
                        (q.voltage[k]-q.voltage[k-1]);
                    if (!std::isfinite(cap)) throw std::runtime_error("Invalid SI output capacitance");
                    minimum_cap=std::min(minimum_cap,cap);
                }
                // Put half the minimum differential capacitance in C. This
                // makes a charge-only output node solvable even without an
                // external capacitor. Retain the other half in Q so its
                // residual stays passive despite floating-point rounding.
                quiet_reference_cap=.5*minimum_cap;
                for (size_t k=0;k<q.voltage.size();++k)
                    quiet_charge[k]-=quiet_reference_cap*(q.voltage[k]-q.voltage.front());
            }
            if (initial[q.node]<q.voltage.front() || initial[q.node]>q.voltage.back())
                throw std::runtime_error("SI static I-V initial voltage outside characterized range");
            size_t replaced=0;
            for (const auto& d:drivers) if (d.node==q.node) {
                if (d.ohms==0 || d.initial!=d.final || ++replaced>1)
                    throw std::runtime_error("SI static I-V overlaps a switching or duplicate driver");
            }
        }
        std::vector<double> c(n*n,0), g(n*n,0);
        auto stamp = [&](std::vector<double>& m, size_t a, size_t b, double value) {
            if (a >= n || (b != SIZE_MAX && b >= n) || !std::isfinite(value) || value < 0)
                throw std::runtime_error("Invalid coupled RC element");
            m[a*n+a] += value;
            if (b != SIZE_MAX) { m[b*n+b] += value; m[a*n+b] -= value; m[b*n+a] -= value; }
        };
        for (const auto& r : resistors) {
            if (!(r.ohms > 0)) throw std::runtime_error("Nonpositive SI resistor");
            stamp(g,r.a,r.b,1000./r.ohms);
        }
        for (const auto& cap : capacitors) stamp(c,cap.a,cap.b,cap.pf);
        if (stage) stamp(c,stage->node,SIZE_MAX,stage->miller_pf+stage->output_pf);
        if (quiet_reference_cap>0) stamp(c,quiet->node,SIZE_MAX,quiet_reference_cap);
        if (quiet_reference_g>0) stamp(g,quiet->node,SIZE_MAX,quiet_reference_g);
        auto source_voltage=[](const Driver& d,double t) {
            const double f=d.ramp>0?std::clamp((t-d.center)/d.ramp+.5,0.,1.):(t>d.center?1.:0.);
            return d.initial+(d.final-d.initial)*f;
        };
        std::vector<const Driver*> ideal(n,nullptr);
        for (const auto& d : drivers) {
            if (d.ohms < 0 || !std::isfinite(d.ohms) || d.node >= n || d.ramp < 0 ||
                !std::isfinite(d.ramp) || !std::isfinite(d.center) ||
                !std::isfinite(d.initial) || !std::isfinite(d.final))
                throw std::runtime_error("Invalid SI driver");
            if (source_node[d.node]) throw std::runtime_error("SI Norton source overlaps another driver");
            if (d.ohms==0) {
                if (ideal[d.node]) throw std::runtime_error("Duplicate SI ideal voltage boundary");
                ideal[d.node]=&d;
                const double v=source_voltage(d,begin);
                if (std::fabs(initial[d.node]-v)>32*std::numeric_limits<double>::epsilon()*
                    std::max({1.,std::fabs(v),std::fabs(initial[d.node])}))
                    throw std::runtime_error("SI initial voltage conflicts with ideal boundary");
            } else if (!quiet || d.node!=quiet->node) stamp(g,d.node,SIZE_MAX,1000./d.ohms);
        }
        for (const auto& d:drivers) if (d.ohms>0 && ideal[d.node])
            throw std::runtime_error("SI ideal voltage boundary overlaps another driver");
        // An unloaded, capacitance-free resistor leaf draws exactly zero
        // current, so its voltage equals its neighbour's at every solved
        // time. Eliminate these algebraic leaves before factorization. Keeping
        // tiny observer resistors in G otherwise loses the much smaller driver
        // conductance and can move even a constant high-rail baseline.
        std::vector<bool> retained(n,true), protected_node(n,false);
        for (const auto& d:drivers) protected_node[d.node]=true;
        for (const auto& source:sources) protected_node[source.node]=true;
        if (quiet) protected_node[quiet->node]=true;
        for (const auto& r:resistors) if (r.b==SIZE_MAX) protected_node[r.a]=true;
        std::vector<size_t> degree(n,0), parent(n,SIZE_MAX);
        for (size_t i=0;i<n;++i) for (size_t j=0;j<n;++j)
            if (i!=j && g[i*n+j]<0) ++degree[i];
        bool removed=true;
        while (removed) {
            removed=false;
            for (size_t i=0;i<n;++i) {
                if (!retained[i] || protected_node[i] || c[i*n+i]!=0 || degree[i]!=1) continue;
                size_t neighbour=0;
                while (neighbour<n && (!retained[neighbour] || i==neighbour || g[i*n+neighbour]>=0)) ++neighbour;
                if (neighbour==n) throw std::runtime_error("Invalid SI leaf adjacency");
                parent[i]=neighbour;retained[i]=false;--degree[neighbour];removed=true;
            }
        }
        const auto reduced_n=size_t(std::count(retained.begin(),retained.end(),true));
        if (reduced_n<n) {
            std::vector<size_t> index(n,SIZE_MAX), root(n);
            std::vector<double> reduced_initial;
            for (size_t i=0;i<n;++i) if (retained[i]) {index[i]=reduced_initial.size();reduced_initial.push_back(initial[i]);}
            for (size_t i=0;i<n;++i) {
                root[i]=i;
                while (parent[root[i]]!=SIZE_MAX) root[i]=parent[root[i]];
            }
            std::vector<Resistor> rr;
            std::vector<Capacitor> cc;
            std::vector<Driver> dd;
            std::vector<NortonSource> ss;
            for (const auto& r:resistors) if (retained[r.a] && (r.b==SIZE_MAX || retained[r.b]))
                rr.push_back({index[r.a],r.b==SIZE_MAX?SIZE_MAX:index[r.b],r.ohms});
            for (const auto& cap:capacitors) if (retained[cap.a] && (cap.b==SIZE_MAX || retained[cap.b]))
                cc.push_back({index[cap.a],cap.b==SIZE_MAX?SIZE_MAX:index[cap.b],cap.pf});
            for (auto d:drivers) {d.node=index[d.node];dd.push_back(d);}
            for (auto source:sources) {source.node=index[source.node];ss.push_back(std::move(source));}
            StaticDriver reduced_quiet;
            if (quiet) {reduced_quiet=*quiet;reduced_quiet.node=index[quiet->node];}
            DynamicStage reduced_stage;
            if(stage) {reduced_stage=*stage;reduced_stage.node=index[stage->node];}
            auto result=solve(reduced_n,rr,cc,dd,std::move(reduced_initial),begin,end,max_dt,
                std::min(max_steps,size_t(8000000/n)),quiet && !stage?&reduced_quiet:nullptr,ss,stage?&reduced_stage:nullptr,shared_grid);
            for (size_t k=0;k<result.voltage.size();++k) {
                if (!k) {result.voltage[k]=initial;continue;}
                auto compact=std::move(result.voltage[k]);result.voltage[k].resize(n);
                for (size_t i=0;i<n;++i) result.voltage[k][i]=compact[index[root[i]]];
            }
            return result;
        }
        // End a step at every PWL corner. Otherwise a transition shorter
        // than max_dt can start and finish between samples, losing its peak.
        // Resolve each ramp by at least 64 intervals; max_dt remains an
        // upper bound, and all additional samples count against the SAME
        // step/memory limits. Quiet sources retain corners too, so active
        // and baseline solves have exactly the same time grid.
        std::vector<double> corners{begin,end};
        for (const auto& d : drivers) {
            for (double t : {d.center-d.ramp*.5,d.center+d.ramp*.5})
                if (t>begin && t<end) corners.push_back(t);
            // A finite aggressor impedance can move the victim peak just
            // past the source edge. Retain fine samples during recovery too.
            const double tail=d.center+d.ramp*4.5;
            if (d.ramp>0 && d.ramp<64*max_dt && tail>begin && tail<end) corners.push_back(tail);
        }
        for (const auto& source:sources) for (double t:source.time)
            if (t>begin && t<end) corners.push_back(t);
        if(stage) for(double t:stage->time) if(t>begin && t<end) corners.push_back(t);
        const auto automatic_grid=shared_grid?TimeGrid{}:source_grid(sources,stage);
        const auto& grid=shared_grid?*shared_grid:automatic_grid;
        struct Event { double time,step; bool enter; };
        std::vector<Event> events;
        for(double t:grid.corners) {
            if(!std::isfinite(t))throw std::runtime_error("Invalid SI shared grid corner");
            if(t>begin && t<end)corners.push_back(t);
        }
        for(const auto& w:grid.windows) {
            if(!std::isfinite(w.begin) || !std::isfinite(w.end) || !std::isfinite(w.step) ||
                !(w.end>w.begin) || !(w.step>0))throw std::runtime_error("Invalid SI shared grid window");
            const double a=std::max(begin,w.begin),b=std::min(end,w.end);
            if(b>a && w.step<max_dt) {
                corners.push_back(a);corners.push_back(b);
                events.push_back({a,w.step,true});events.push_back({b,w.step,false});
            }
        }
        std::sort(events.begin(),events.end(),[](const auto& a,const auto& b){return a.time<b.time;});
        std::multiset<double> source_resolution;size_t event=0;
        std::sort(corners.begin(),corners.end());
        corners.erase(std::unique(corners.begin(),corners.end()),corners.end());
        struct Segment { double begin,end,dt; size_t steps; };
        std::vector<Segment> segments;
        size_t steps=0;
        const size_t limit=std::min(max_steps,size_t(8000000/n));
        for (size_t k=1;k<corners.size();++k) {
            const double a=corners[k-1],b=corners[k];
            if (b-a <= 16*std::numeric_limits<double>::epsilon()*
                    std::max({std::fabs(a),std::fabs(b),end-begin})) continue;
            double resolution=max_dt;
            while(event<events.size() && events[event].time<=a) {
                const auto& e=events[event++];
                if(e.enter)source_resolution.insert(e.step);
                else source_resolution.erase(source_resolution.find(e.step));
            }
            if(!source_resolution.empty())resolution=std::min(resolution,*source_resolution.begin());
            for (const auto& d : drivers)
                if (d.ramp>0 && a<d.center+d.ramp*4.5 && b>d.center-d.ramp*.5)
                    resolution=std::min(resolution,d.ramp/64.);
            const double count=std::ceil((b-a)/resolution);
            if (!std::isfinite(count) || count>limit-steps)
                throw std::runtime_error("SI waveform step/memory budget exceeded");
            const auto m=size_t(count);
            segments.push_back({a,b,(b-a)/m,m});steps+=m;
        }
        Result result;
        result.time.reserve(steps+1); result.voltage.reserve(steps+1);
        result.time.push_back(begin); result.voltage.push_back(std::move(initial));
        std::vector<double> rhs(n), next(n),l(n*n),response(n),transformed;
        auto substitute=[&](std::vector<double>& values) {
            for (size_t i=0;i<n;++i) {
                for (size_t j=0;j<i;++j) values[i]-=l[i*n+j]*values[j];
                values[i]/=l[i*n+i];
            }
            for (size_t i=n;i-- >0;) {
                for (size_t j=i+1;j<n;++j) values[i]-=l[j*n+i]*values[j];
                values[i]/=l[i*n+i];
            }
        };
        auto source_at=[](const NortonSource& source,double t) {
            size_t k=std::upper_bound(source.time.begin(),source.time.end(),t)-source.time.begin();
            k=std::min(std::max(k,size_t(1)),source.time.size()-1)-1;
            const double f=(t-source.time[k])/(source.time[k+1]-source.time[k]);
            return std::pair<double,double>{
                source.injection_ma[k]+f*(source.injection_ma[k+1]-source.injection_ma[k]),
                source.conductance_ma_per_v[k]+f*(source.conductance_ma_per_v[k+1]-source.conductance_ma_per_v[k])};
        };
        std::vector<double> source_g(n,0.);
        for (const auto& segment : segments) {
          const double dt=segment.dt;
          auto factor=[&](double t) {
          for (const auto& source:sources) source_g[source.node]=source_at(source,t).second;
          std::fill(l.begin(),l.end(),0);
          for (size_t i=0;i<n;++i) for (size_t j=0;j<=i;++j) {
            double value=g[i*n+j]+c[i*n+j]/dt;
            if (i==j) value+=source_g[i];
            // Symmetric Dirichlet elimination keeps the free-node matrix
            // positive definite. The removed C/G columns enter the RHS
            // below; retaining old C*v is essential to stamp C*dV/dt.
            if (ideal[i] || ideal[j]) value=i==j?1.:0.;
            for (size_t k=0;k<j;++k) value-=l[i*n+k]*l[j*n+k];
            if (i==j) {
                if (!(value>0) || !std::isfinite(value)) throw std::runtime_error("Singular SI network");
                l[i*n+j]=std::sqrt(value);
            } else l[i*n+j]=value/l[j*n+j];
          }
          if (quiet) {
              // Schur reduction with injected I(x)-(Q(x)-Q(previous))/dt.
              // h=(G+C/dt)^-1[q,q]>0, nonincreasing I and nondecreasing
              // Q make x-h I(x)+h Q(x)/dt strictly increasing. Invert PWL
              // charge itself, rather than C(x)*(x-previous). No
              // Newton damping, rail clamp, or fitted equivalent R.
              std::fill(response.begin(),response.end(),0.);
              response[quiet->node]=1.; substitute(response);
              const double h=response[quiet->node];
              if (!(h>0) || !std::isfinite(h)) throw std::runtime_error("Invalid SI static I-V response");
              transformed.resize(quiet->voltage.size());
              for(size_t k=0;k<transformed.size();++k) {
                  transformed[k]=quiet->voltage[k]-h*quiet_current[k]+h*quiet_charge[k]/dt;
                  if (!std::isfinite(transformed[k]) || (k && !(transformed[k]>transformed[k-1])))
                      throw std::runtime_error("Invalid SI static I-V inverse");
              }
          }
          };
          // Preserve the original once-per-segment factorization for ordinary
          // drivers. A characterized time-varying g changes the matrix and its
          // static-I-V Schur response at each sample, not just the RHS.
          if (sources.empty() && !stage) factor(segment.begin);
          for (size_t step=1;step<=segment.steps;++step) {
            const double t=step==segment.steps ? segment.end : segment.begin+step*dt;
            double stage_miller_current=0., stage_next_state=0.;
            if(stage) {
                const auto dc=stage_slice(*stage,stage_input(*stage,t));
                const double alpha=dt/(stage->tau_ns+dt);
                stage_miller_current=stage->miller_pf*(stage_input(*stage,t)-
                    stage_input(*stage,result.time.back()))/dt;
                if(!stage->lag_output_feedback && stage->tau_ns>0) {
                    const auto& x=stage->output_voltage;
                    size_t j=std::upper_bound(x.begin(),x.end(),stage_reference_output)-x.begin();
                    j=std::min(std::max(j,size_t(1)),x.size()-1)-1;
                    const double reference=dc[j]+(dc[j+1]-dc[j])*
                        (stage_reference_output-x[j])/(x[j+1]-x[j]);
                    stage_next_state=(1.-alpha)*stage_state+alpha*reference;
                    for(size_t k=0;k<dc.size();++k)
                        quiet_current[k]=dc[k]+(stage_next_state-reference)+stage_miller_current;
                } else for(size_t k=0;k<dc.size();++k)
                    quiet_current[k]=(1.-alpha)*stage_state+alpha*dc[k]+stage_miller_current;
            }
            if (!sources.empty() || stage) factor(t);
            const auto& previous = result.voltage.back();
            std::fill(rhs.begin(),rhs.end(),0);
            for (size_t i=0;i<n;++i) for (size_t j=0;j<n;++j) rhs[i] += c[i*n+j]*previous[j]/dt;
            for (const auto& d : drivers) {
                if (d.ohms==0 || (quiet && d.node==quiet->node)) continue;
                const double fraction = d.ramp > 0 ? std::clamp((t-d.center)/d.ramp+.5,0.,1.) : (t > d.center ? 1. : 0.);
                rhs[d.node] += (d.initial+(d.final-d.initial)*fraction)*1000./d.ohms;
            }
            for (const auto& source:sources) rhs[source.node]+=source_at(source,t).first;
            for(size_t j=0;j<n;++j) if(ideal[j]) {
                const double v=source_voltage(*ideal[j],t);
                for(size_t i=0;i<n;++i) if(!ideal[i])
                    rhs[i]-=(g[i*n+j]+c[i*n+j]/dt)*v;
                rhs[j]=v;
            }
            for (size_t i=0;i<n;++i) {
                double value=rhs[i]; for (size_t j=0;j<i;++j) value-=l[i*n+j]*next[j];
                next[i]=value/l[i*n+i];
            }
            for (size_t i=n;i-- >0;) {
                double value=next[i]; for (size_t j=i+1;j<n;++j) value-=l[j*n+i]*next[j];
                next[i]=value/l[i*n+i];
                if (!std::isfinite(next[i])) throw std::runtime_error("Non-finite SI waveform");
            }
            if (quiet) {
                auto previous_k=std::upper_bound(quiet->voltage.begin(),quiet->voltage.end(),
                    previous[quiet->node])-quiet->voltage.begin();
                previous_k=std::min(std::max(previous_k,decltype(previous_k)(1)),
                    decltype(previous_k)(quiet->voltage.size()-1))-1;
                const double previous_charge=quiet_charge[previous_k]+
                    (quiet_charge[previous_k+1]-quiet_charge[previous_k])*
                    (previous[quiet->node]-quiet->voltage[previous_k])/
                    (quiet->voltage[previous_k+1]-quiet->voltage[previous_k]);
                const double h=response[quiet->node];
                const double u=next[quiet->node]+h*previous_charge/dt;
                if (u<transformed.front() || u>transformed.back())
                    throw std::runtime_error("SI static I-V voltage outside characterized range");
                size_t k=std::upper_bound(transformed.begin(),transformed.end(),u)-transformed.begin();
                k=std::min(std::max(k,size_t(1)),transformed.size()-1)-1;
                const double slope=(quiet_current[k+1]-quiet_current[k])/
                    (quiet->voltage[k+1]-quiet->voltage[k]);
                const double cap=(quiet_charge[k+1]-quiet_charge[k])/
                    (quiet->voltage[k+1]-quiet->voltage[k]);
                const double intercept=quiet_current[k]-slope*quiet->voltage[k]-
                    (quiet_charge[k]-cap*quiet->voltage[k])/dt;
                const double x=(u+h*intercept)/(1-h*slope+h*cap/dt);
                const double current=quiet_current[k]+slope*(x-quiet->voltage[k])-
                    (quiet_charge[k]+cap*(x-quiet->voltage[k])-previous_charge)/dt;
                for(size_t i=0;i<n;++i) {
                    next[i]+=response[i]*current;
                    if (!std::isfinite(next[i])) throw std::runtime_error("Non-finite SI static I-V waveform");
                }
            }
            if(stage) {
                const auto& x=quiet->voltage;
                size_t k=std::upper_bound(x.begin(),x.end(),next[stage->node])-x.begin();
                k=std::min(std::max(k,size_t(1)),x.size()-1)-1;
                if(!stage->lag_output_feedback && stage->tau_ns>0)stage_state=stage_next_state;
                else stage_state=quiet_current[k]+(quiet_current[k+1]-quiet_current[k])*
                    (next[stage->node]-x[k])/(x[k+1]-x[k])-stage_miller_current;
            }
            result.time.push_back(t); result.voltage.push_back(next);
          }
        }
        return result;
    }
};
} // namespace te
