// Experimental CCS runtime, included inside rc_surface_dcalc.cc's anonymous
// namespace. See docs/primetime_ccs_adaptive_runtime_20261021.md for the open
// accuracy limits. Source construction uses Liberty data only.
//
// Startup conditioning preserves native charge, the 25-75 span and the 50%
// crossing. Its float segment arithmetic precedes double CCS compression.
// Solve in original load-column order; the columns need not be voltage sorted.
struct AdaptiveCcsTimeState {
    size_t column=0;
    double nearest_current=0.,nearest_cap=0.;

    // Column and nearest-source state survive rejected integration trials.
    // A crossing is interpolated directly; capacitance/voltage bounds apply
    // only when extrapolating a pair with no valid intersection.
    std::pair<double,double> solve(const std::vector<std::pair<double,double>>& points,
                                  const std::vector<double>& caps,double B,double gain,
                                  bool first_trial=false) {
        size_t count=points.size(),start=std::min(column,count-2),nearest=0;
        bool backtrack=start>0,retried_first_pair=false;
        const double lower=float(.1*caps.front()),upper=11.*caps.back();
        auto result=[&](double current){return std::make_pair(B+gain*current,current);};
        for(;;) {
            double best=std::numeric_limits<double>::infinity();
            bool restart=false;
            for(size_t j=start;j<count;++j) {
                const auto [v,I]=points[j];
                const double model=B+gain*I;
                if(v!=0. && I!=0. && model!=0. && std::fabs(v-model)<best) {
                    best=std::fabs(v-model);nearest=j;
                    nearest_current=I;nearest_cap=caps[j];
                }
                if(j==start) {
                    if(backtrack && j>0 && v!=0. && model>v) {
                        --start;restart=true;break;
                    }
                } else {
                    const auto [pv,pI]=points[j-1];
                    const double pm=B+gain*pI,dc=caps[j]-caps[j-1],dv=v-pv,dm=model-pm;
                    if(pv!=0. && v!=0. && (pv-pm)*(model-v)>=0. &&
                       std::fabs(dc*(dm-dv))>=1e-10) {
                        const double f=(pv-pm)/(dm-dv);
                        if(f>=0. && f<=1.) {
                            column=j-1;
                            return result(std::fabs(gain)>1e-10 ? (pv+f*dv-B)/gain : nearest_current);
                        }
                    }
                }
            }
            if(restart)continue;
            if(nearest<count-2 && !retried_first_pair) {
                if(nearest==0) {
                    start=0;count=2;retried_first_pair=true;backtrack=false;
                    continue;
                }
                column=start;
                return result(nearest_current);
            }
            const auto [v0,i0]=points[count-2];
            const auto [v1,i1]=points[count-1];
            const double m0=B+gain*i0,m1=B+gain*i1,c0=caps[count-2],c1=caps[count-1];
            const double den=m1-m0-v1+v0;
            double v=v1;
            if(float(den)!=0.f) {
                double cap=std::clamp(c0+(v0-m0)/den*(c1-c0),lower,upper);
                if(cap<0.)cap=std::max(c0,c1);
                if(float(c1)!=float(c0))v=v0+(cap-c0)/(c1-c0)*(v1-v0);
            }
            v=std::clamp(v,.5*std::min(v0,v1),2.*std::max(v0,v1));
            double current=0.;
            if(v>=1e-9) {
                current=std::fabs(gain)>1e-10 ? (v-B)/gain : nearest_current;
                if(current<=0.)current=nearest_current;
            }
            column=count-2;
            if(first_trial && retried_first_pair)current=nearest_current;
            return result(current);
        }
    }
};

struct AdaptiveCcsPulse {
    std::vector<double> t,i,v;
    double cap=0.,ref=0.,supply=1.;
    size_t native_count=0;
    bool initialize(const edacraft::core::CsmWaveform& w,double c,double vdd) {
        cap=c;ref=w.reference_time;supply=vdd;native_count=w.current.size();
        if(w.time_points.size()<2 || w.time_points.size()!=w.current.size() || !(cap>0.))return false;
        for(size_t j=0;j<w.current.size();++j) {t.push_back(w.time_points[j]);i.push_back(std::fabs(w.current[j])/vdd);}
        if(i.back()>*std::max_element(i.begin(),i.end())*.0001) {t.push_back(t.back()+.001*(t.back()-t[t.size()-2]));i.push_back(0.);}
        return integrate();
    }
    bool integrate() {
        v.assign(t.size(),0.);
        for(size_t j=1;j<t.size();++j) {
            if(!(t[j]>t[j-1]))return false;
            v[j]=v[j-1]+.5*(t[j]-t[j-1])*(i[j]+i[j-1])/cap;
        }
        return v.back()>.8 && std::isfinite(v.back());
    }
    std::pair<double,double> at_voltage(double x,double segment_voltage=std::numeric_limits<double>::quiet_NaN()) const {
        // A Jacobian perturbation stays in the source segment selected at
        // the unperturbed voltage, including when it crosses a sample knot.
        const double lookup=std::isfinite(segment_voltage)?segment_voltage:x;
        size_t j=1;while(j+1<v.size() && v[j]<lookup)++j;
        // The base and +1 mV Jacobian samples share one inverse branch.
        // If either charge radicand is nonpositive, use voltage-linear
        // interpolation for both; sqrt(max(0,q)) changes the source itself.
        if(std::isfinite(segment_voltage)) {
            if(lookup>=v.back())return {t.back()-ref,i.back()};
            const double slope=(i[j]-i[j-1])/(t[j]-t[j-1]);
            const double a=i[j-1]*i[j-1]+2*slope*(lookup-v[j-1])*cap;
            const double b=a+2*slope*.001*cap;
            if(a<=0. || b<=0.) {
                const double w=(x-v[j-1])/(v[j]-v[j-1]);
                return {t[j-1]+w*(t[j]-t[j-1])-ref,i[j-1]+w*(i[j]-i[j-1])};
            }
        }
        const double slope=(i[j]-i[j-1])/(t[j]-t[j-1]);
        const double q=(x-v[j-1])*cap,cur=std::sqrt(std::max(0.,i[j-1]*i[j-1]+2*slope*q));
        return {t[j-1]+2*q/std::max(1e-30,i[j-1]+cur)-ref,cur};
    }
    std::pair<double,double> at_time(double x) const {
        x+=ref;
        if(x<t.front())return {0.,0.};
        if(x>=t.back())return {v.back(),i.back()};
        size_t j=1;while(t[j]<x)++j;
        const double dt=x-t[j-1],s=(i[j]-i[j-1])/(t[j]-t[j-1]);
        return {v[j-1]+dt*(i[j-1]+.5*s*dt)/cap,i[j-1]+s*dt};
    }
    bool condition_startup() {
        // Library preprocessing works on the native float samples, before
        // appending the zero-current compression tail. Rounding each segment
        // product and each rescaled current is observable at runtime startup.
        const size_t n=native_count;
        if(n<2 || n>t.size() || !(supply>0.))return false;
        std::vector<float> currents(n);
        for(size_t j=0;j<n;++j)currents[j]=float(i[j]*supply);
        auto charge=[&]() {
            std::vector<double> volts(n,0.);
            for(size_t j=1;j<n;++j) {
                const float dt=float(t[j])-float(t[j-1]);
                const float sum=currents[j]+currents[j-1];
                volts[j]=volts[j-1]+std::fabs(float(dt*sum))*(.5/(cap*supply));
            }
            return volts;
        };
        auto crossing=[&](const auto& volts,double x) {
            size_t j=1;while(j+1<n && volts[j]<x)++j;
            return t[j-1]+double(float(float(t[j])-float(t[j-1])))*
                (x-volts[j-1])/(volts[j]-volts[j-1]);
        };
        const auto raw=charge();size_t last=0;
        while(last+1<n && raw[last+1]<.05)++last;
        bool changed=false;
        for(size_t j=last;j-->0;)if(currents[j]>currents[j+1]) {currents[j]=currents[j+1];changed=true;}
        if(!changed)return true;
        const double q=raw.back()/charge().back();
        for(auto& x:currents)x=float(double(x)*q);
        const auto conditioned=charge();
        const double scale=(crossing(raw,.75)-crossing(raw,.25))/
            (crossing(conditioned,.75)-crossing(conditioned,.25));
        const double before=crossing(raw,.5),after=crossing(conditioned,.5);
        if(!(scale>0.) || !std::isfinite(scale))return false;
        t.resize(n);i.resize(n);
        for(size_t j=0;j<n;++j) {
            t[j]=float(scale*(t[j]-after)+before);
            i[j]=float(double(currents[j])/scale)/supply;
        }
        if(i.back()>*std::max_element(i.begin(),i.end())*.0001) {
            t.push_back(t.back()+.001*(t.back()-t[t.size()-2]));i.push_back(0.);
        }
        return integrate();
    }
};
static bool adaptive_ccs_uses_cap_over_current(const std::vector<AdaptiveCcsPulse>& columns) {
    // Select on the retained load grid, after the nominal-load floor. With
    // at most one adjacent ratio below 2.5, the voltage-domain source uses
    // C/I interpolation. Applying it to dense grids changes ordinary paths.
    size_t close_pairs=0;
    for(size_t j=1;j<columns.size();++j)
        if(2.5*columns[j-1].cap>columns[j].cap)++close_pairs;
    return close_pairs<=1;
}

static double adaptive_ccs_voltage_current(double c0,double c1,double i0,double i1,
                                           double cap,bool cap_over_current,
                                           double zero_current=.0001) {
    double value=i0+(cap-c0)/(c1-c0)*(i1-i0);
    if(cap_over_current) {
        // At a fixed voltage C/I is the inverse voltage slope. Interpolate
        // that quantity before recovering the current at the inferred load.
        const double d0=c0/(float(i0)==0.f?zero_current:i0);
        const double d1=c1/(float(i1)==0.f?zero_current:i1);
        const double slope=(d1-d0)/(c1-c0);
        value=cap/(d1-c1*slope+cap*slope);
    }
    // The lower-then-upper ordering also applies to Jacobian probes that
    // extrapolate beyond a zero-current endpoint.
    return std::min(std::max(value,.5*std::min(i0,i1)),2.*std::max(i0,i1));
}

struct AdaptiveCcsCompact {
    double initial,peak,vp,tp;std::array<double,18> shape;
    bool initialize(AdaptiveCcsPulse p,bool negative) {
        if(!p.condition_startup())return false;
        size_t k=std::max_element(p.i.begin(),p.i.end())-p.i.begin();
        initial=p.i.front();peak=p.i[k];tp=float(p.t[k]-p.ref);
        // Preserve the precomputed charge coordinates while separating a
        // near-flat first sample from the peak. Compression interpolates the
        // adjusted current samples against those original coordinates.
        double rising_initial=initial;
        if(k>0 && rising_initial>.99*peak) {
            rising_initial*=.99;
            initial=float(rising_initial);
            p.i.front()=rising_initial;
        }
        const double full=p.v.back(),scale=std::fabs(1.-full)>.05*full?float(full):1.;
        vp=float((negative?full-p.v[k]:p.v[k])/full*scale);
        if(!(peak>initial && p.v[k]>0. && p.v[k]<full))return false;
        for(unsigned j=1;j<10;++j) {
            const double a=(p.at_voltage(p.v[k]*j/10.).second-rising_initial)/(peak-rising_initial);
            const double b=p.at_voltage(p.v[k]+(full-p.v[k])*j/10.).second/peak;
            // Decode integer shape bins with the native float scale, promoted
            // before multiplication. Rounding the product to float loses bits.
            // Conversion truncates toward zero after adding half a bin. A
            // negative shape sample can occur after the initial current dip.
            shape[j-1]=std::trunc(a*1000.+.5)*double(.001f);shape[j+8]=std::trunc(b*1000.+.5)*double(.001f);
            // Compression conditions the first two rising shape bins when
            // the initial current is below a quarter of the peak. Apply the
            // floor in integer bins, before slew interpolation and unpacking.
            // The native float bin scale makes these floors 24 and 49.
            if(j<=2 && .25*peak>std::fabs(initial)) {
                const double bin_scale=double(.001f);
                const double floor=std::trunc(.25*j/10./bin_scale)*bin_scale;
                shape[j-1]=std::max(shape[j-1],floor);
            }
        }
        return true;
    }
};
static std::optional<std::vector<AdaptiveCcsPulse>> adaptive_ccs_columns(
    const edacraft::core::CsmOutputCurrentTable& table,double slew,double vdd,
    double minimum_cap=0.) {
    if(table.input_slews.size()<2 || table.ncap!=table.load_caps.size() || table.ncap<2 ||
        table.waveforms.size()!=table.input_slews.size()*table.ncap)return std::nullopt;
    slew=std::clamp(slew,.2*table.input_slews.front(),1.1*table.input_slews.back());
    const bool negative=std::any_of(table.waveforms.front().current.begin(),table.waveforms.front().current.end(),[](float x){return x<0.;});
    float end=0.;
    for(size_t j=0;j<table.waveforms.size();++j) {
        AdaptiveCcsPulse p;
        if(!p.initialize(table.waveforms[j],table.load_caps[j%table.ncap],vdd))return std::nullopt;
        end=float(double(end)+p.v.back());
    }
    end/=float(table.waveforms.size());
    size_t hi=std::lower_bound(table.input_slews.begin(),table.input_slews.end(),slew)-table.input_slews.begin();
    hi=std::clamp(hi,size_t(1),table.input_slews.size()-1);size_t lo=table.input_slews[hi]!=slew?hi-1:hi;
    // The interpolation coordinate is stored at native float precision; the
    // weighted compact parameters themselves remain double until unpacked.
    const double w=lo==hi?0.:float((slew-table.input_slews[lo])/(table.input_slews[hi]-table.input_slews[lo]));
    std::vector<AdaptiveCcsPulse> out;
    // Keep the column bracketing 1% of the nominal network load and every
    // larger column. A fixed column count changes the startup root search.
    size_t first=0;
    const float floor_cap=float(minimum_cap);
    while(first+2<table.ncap && table.load_caps[first+1]<=floor_cap)++first;
    for(size_t ci=first;ci<table.ncap;++ci) {
        AdaptiveCcsCompact a,b;AdaptiveCcsPulse ra,rb;
        if(!ra.initialize(table.waveforms[lo*table.ncap+ci],table.load_caps[ci],vdd) ||
           !rb.initialize(table.waveforms[hi*table.ncap+ci],table.load_caps[ci],vdd) ||
           !a.initialize(ra,negative) || !b.initialize(rb,negative))return std::nullopt;
        const double ini=(1-w)*a.initial+w*b.initial,peak=(1-w)*a.peak+w*b.peak;
        const double packed=(1-w)*a.vp+w*b.vp,vp=std::clamp(negative?end-packed:packed,.005*end,.995*end);
        AdaptiveCcsPulse p;p.cap=table.load_caps[ci];p.t.resize(21);p.i.resize(21);p.v.resize(21);
        p.t[10]=(1-w)*a.tp+w*b.tp;
        for(unsigned j=0;j<=10;++j) {
            p.v[j]=vp*(1.-double(float(1.-j/10.)));
            // Unpacking takes the magnitude of the extrapolated first sample.
            // Interior amplitudes still interpolate using the signed initial.
            p.i[j]=j==0?std::fabs(a.initial+w*double(float(b.initial-a.initial))):j==10?peak:ini+((1-w)*(a.peak-a.initial)*a.shape[j-1]+w*(b.peak-b.initial)*b.shape[j-1]);
        }
        for(unsigned j=1;j<=10;++j) {
            p.v[10+j]=vp+(end-vp)*double(float(j/10.));
            // The tail interpolates normalized shape, then applies the
            // interpolated peak. The rising side above mixes amplitudes.
            // Bound interior tail amplitudes to 1% of that peak before
            // reconstructing time; slew extrapolation can make them negative.
            // The final zero-current endpoint remains separate.
            p.i[10+j]=j==10?0.:peak*std::max(.01,(1-w)*a.shape[j+8]+w*b.shape[j+8]);
        }
        // Form native I/V samples first, integrate forward with float time
        // accumulation, then translate the complete pulse to the peak time.
        // Integrating backward from the peak changes the startup samples.
        const double tpeak=p.t[10];
        for(auto& x:p.i)x=float(x);for(auto& x:p.v)x=float(x);
        p.t[0]=0.;
        for(size_t j=1;j<21;++j) {
            const float sum=float(p.i[j])+float(p.i[j-1]);
            if(sum<=0.)return std::nullopt;
            p.t[j]=float(p.t[j-1]+2*p.cap*(p.v[j]-p.v[j-1])/double(sum));
        }
        const double shift=tpeak-p.t[10];
        for(auto& x:p.t)x=float(x+shift);
        out.push_back(std::move(p));
    }
    return out;
}
using AdaptiveCcsRom = RcReducedModel;
static std::pair<double,double> adaptive_ccs_startup(const std::vector<AdaptiveCcsPulse>& columns,
                                                   const AdaptiveCcsRom& rom,double h,double epsilon) {
    // Bootstrap from the network's backward-Euler driving-point capacitance.
    // Use the same interpolated load for both the start time and current.
    double gain=0.;
    for(size_t j=0;j<rom.b.size();++j)gain+=rom.b[j]*rom.b[j]/(1./h+rom.eigen[j]);
    const double cap=h/gain;
    size_t hi=1;while(hi+1<columns.size() && columns[hi].cap<cap)++hi;
    const auto& lo=columns[hi-1];const auto& up=columns[hi];
    const double weight=std::clamp((cap-lo.cap)/(up.cap-lo.cap),0.,1.);
    return {std::max(lo.t.front()+weight*(up.t.front()-lo.t.front()),columns.front().t.front()+epsilon),
            lo.i.front()+weight*(up.i.front()-lo.i.front())};
}
static double adaptive_ccs_exact_si_unit(double unit) {
    if(!(unit>0.))return unit;
    const double decimal=std::pow(10.,std::round(std::log10(unit)));
    return unit==double(float(decimal))?decimal:unit;
}

// Source pruning follows the analysis envelope; the network's projection
// continues to use its independent fixed nominal reference.
static double adaptive_ccs_source_cap(const RcReceiverCapacitance& r) {
    return r.source_nominal>0.f?r.source_nominal:
        r.nominal>0.f?r.nominal:.5*(r.first+r.second);
}

static std::optional<RcWaveformResult> adaptive_ccs_lumped_receiver_seed(
    const edacraft::core::CsmOutputCurrentTable& table,const FullRcNetwork& rc,
    double slew,double vdd,float lower,float upper,float derate,double cap_unit,
    float load_threshold,const std::vector<RcReceiverCapacitance>& receivers,
    const RcSlewThresholds* windows) {
    if(rc.nodes.empty() || table.load_caps.size()<2 || !(cap_unit>0.) ||
       !(vdd>0.) || !(lower<upper) || !(derate>0.))return std::nullopt;
    const double scale=adaptive_ccs_exact_si_unit(rc.cap_scale)/adaptive_ccs_exact_si_unit(cap_unit);
    double cap=0.,nominal=0.;
    for(const auto& node:rc.nodes)cap+=node.gnd_cap*scale;
    nominal=cap;
    for(const auto& r:receivers) {
        const double loaded=std::max(r.first,r.second);
        cap+=(r.first-loaded)*scale;
        nominal+=(adaptive_ccs_source_cap(r)-loaded)*scale;
    }
    const auto columns=adaptive_ccs_columns(table,slew,vdd,.01*nominal);
    if(!columns || !(cap>0.))return std::nullopt;
    auto crossing=[&](double voltage,double load) {
        size_t hi=1;while(hi+1<columns->size() && (*columns)[hi].cap<load)++hi;
        const auto& a=(*columns)[hi-1];const auto& b=(*columns)[hi];
        const double w=(load-a.cap)/(b.cap-a.cap);
        return (1.-w)*a.at_voltage(voltage).first+w*b.at_voltage(voltage).first;
    };
    // A C1/C2 switch changes subsequent charge intervals. Re-evaluating an
    // absolute crossing at the new cap would discard the preceding history.
    std::vector<double> events;
    for(const auto& r:receivers)events.push_back(r.threshold);
    for(const auto& node:rc.nodes)if(node.id!=rc.driver_node_id && valid(node.pin)) {
        const auto w=rc_slew_window(node.id,lower,upper,derate,windows);
        events.insert(events.end(),{w.lower,rc_slew_middle(node.id,load_threshold,windows),w.upper});
    }
    std::sort(events.begin(),events.end());events.erase(std::unique(events.begin(),events.end()),events.end());
    std::unordered_map<double,double> times;
    double previous=0.,time=crossing(0.,cap);
    for(double voltage:events) {
        if(!(voltage>0.) || !std::isfinite(voltage))return std::nullopt;
        time+=crossing(voltage,cap)-crossing(previous,cap);
        if(!std::isfinite(time))return std::nullopt;
        times.emplace(voltage,time);previous=voltage;
        for(const auto& r:receivers)if(r.threshold==voltage)cap+=(r.second-r.first)*scale;
        if(!(cap>0.))return std::nullopt;
    }
    RcWaveformResult result;
    for(const auto& node:rc.nodes)if(node.id!=rc.driver_node_id && valid(node.pin)) {
        const auto w=rc_slew_window(node.id,lower,upper,derate,windows);
        const double middle=rc_slew_middle(node.id,load_threshold,windows);
        if(!(w.lower<middle && middle<w.upper && w.derate>0.))return std::nullopt;
        const double a=times.at(w.lower),b=times.at(middle),c=times.at(w.upper);
        if(!(a<b && b<c))return std::nullopt;
        result.receiver_slews[node.pin.id]={float((b-a)*(w.upper-w.lower)/(middle-w.lower)/w.derate),
            float((c-b)*(w.upper-w.lower)/(w.upper-middle)/w.derate)};
    }
    return result;
}

// The short-network runtime is a separate CCS solve. Its source crossings
// retain C1/C2 charge history, followed by the driver RC correction and the
// receiver's one-pole response. Integrating the extracted Pi instead selects
// a different model even when its numerical integration error is negligible.
static std::optional<RcWaveformResult> adaptive_ccs_short_star(
    const edacraft::core::CsmOutputCurrentTable& table,const FullRcNetwork& rc,
    double slew,double vdd,double lower,double upper,double derate,
    double cap_unit,double time_unit,double driver_threshold,double load_threshold,
    const std::vector<RcReceiverCapacitance>* receivers,
    const RcDelayThresholds* thresholds,const RcSlewThresholds* windows, bool* initial_short = nullptr) {
    // The balanced-star reduction uses total wire R/C and actual fanout.
    // Keep unsupported topology and receiver voltage windows distributed.
    if(!receivers || receivers->empty() || receivers->size()>9 ||
       rc.nodes.size()!=receivers->size()+1 ||
       rc.resistors.size()!=receivers->size() || rc.driver_node_id>=rc.nodes.size() ||
       (thresholds && !thresholds->empty()) || (windows && !windows->empty()))return std::nullopt;
    const auto& r=receivers->front();
    if(!(r.first>0.f && r.second>0.f) || !(lower<r.threshold && r.threshold<upper))return std::nullopt;
    std::vector<bool> seen(rc.nodes.size(),false);seen[rc.driver_node_id]=true;
    double resistance_sum=0.,loaded=0.,first_pins=0.,second_pins=0.,nominal_pins=0.,loaded_pins=0.;
    double branch_resistance=-1.,branch_wire=-1.;
    for(const auto& receiver:*receivers) {
        if(receiver.force_distributed || receiver.node>=rc.nodes.size() || seen[receiver.node] ||
           !valid(rc.nodes[receiver.node].pin) || !(receiver.first>0.f) ||
           !(receiver.second>0.f) || receiver.threshold!=r.threshold)return std::nullopt;
        seen[receiver.node]=true;
        const auto edge=std::find_if(rc.resistors.begin(),rc.resistors.end(),[&](const auto& e) {
            return (e.node1==rc.driver_node_id && e.node2==receiver.node) ||
                   (e.node2==rc.driver_node_id && e.node1==receiver.node);
        });
        if(edge==rc.resistors.end() || !(edge->resistance>0.f))return std::nullopt;
        const double wire=double(rc.nodes[receiver.node].gnd_cap)-std::max(receiver.first,receiver.second);
        // Loaded ground caps are floats. Removing unequal pin caps from
        // equal physical wire caps can leave a few rounding units of noise.
        const double wire_roundoff=4.*std::numeric_limits<float>::epsilon()*
            std::max({std::fabs(double(rc.nodes[receiver.node].gnd_cap)),
                      std::fabs(wire),std::fabs(branch_wire)});
        if(branch_resistance>=0. && (edge->resistance!=branch_resistance ||
           std::fabs(wire-branch_wire)>wire_roundoff))return std::nullopt;
        branch_resistance=edge->resistance;branch_wire=wire;
        resistance_sum+=edge->resistance;
        first_pins+=receiver.first;second_pins+=receiver.second;
        loaded_pins+=std::max(receiver.first,receiver.second);
        nominal_pins+=adaptive_ccs_source_cap(receiver);
    }
    cap_unit=adaptive_ccs_exact_si_unit(cap_unit);time_unit=adaptive_ccs_exact_si_unit(time_unit);
    const double scale=adaptive_ccs_exact_si_unit(rc.cap_scale)/cap_unit;
    for(const auto& node:rc.nodes)loaded+=node.gnd_cap;
    const float wire=float((loaded-loaded_pins)*scale);
    const double first=double(wire)+first_pins*scale,second=double(wire)+second_pins*scale;
    if(!(wire>0.f && first>0. && second>0.) ||
       std::min(first,second)<table.load_caps.front() ||
       std::max(first,second)>table.load_caps.back())return std::nullopt;
    const float resistance=float(resistance_sum*double(rc.res_scale)*cap_unit/time_unit);
    if(!(resistance>0.f))return std::nullopt;
    const float initial_total=wire+float(std::max(first_pins,second_pins)*scale);
    const double initial_fs=double(float(resistance*initial_total))*time_unit/1e-15;
    const double pf=cap_unit/1e-12;
    const double ratio=(double(float(std::max(first,second)))*pf+2e-5)/
        (double(wire)*pf+1e-5);
    if(!(initial_fs>=0.) || initial_fs>std::numeric_limits<int>::max())return std::nullopt;
    // The short-source model applies below a 4 ps charge-weighted boundary.
    // Multiple sinks retain the 20 ps prepass. Their final decision uses
    // the charge-distribution criterion below, including the actual fanout.
    if(receivers->size()==1 ? int(initial_fs)*ratio>=4000. :
       int(initial_fs)*ratio>=20000.)return std::nullopt;
    double nominal_rise=0.,nominal_fall=0.,admission_cap=0.,admission_slew=0.;
    bool nominal_rf=true;
    for(const auto& receiver:*receivers) {
        nominal_rf=nominal_rf && receiver.nominal_rise>0.f && receiver.nominal_fall>0.f;
        nominal_rise+=receiver.nominal_rise;nominal_fall+=receiver.nominal_fall;
        admission_cap+=receiver.admission_cap;
        admission_slew=std::max(admission_slew,double(receiver.admission_slew_ns));
    }
    if(!nominal_rf && receivers->size()>1 && initial_fs>=4000.)return std::nullopt;
    if(nominal_rf) {
        // Preserve the nominal admission decision across the receiver-load
        // update. A late rejection changes the solve, not its seed protocol.
        const float nominal_first=wire+float(nominal_rise*scale);
        const float nominal_second=wire+float(nominal_fall*scale);
        const float nominal_total=std::max(nominal_first,nominal_second);
        const double nominal_fs=double(float(resistance*nominal_total))*time_unit/1e-15;
        if(!std::isfinite(nominal_fs) || nominal_fs<0. ||
           nominal_fs>=double(std::numeric_limits<int>::max()))return std::nullopt;
        auto shape_at=[&](float cap) {return std::clamp((double(wire)/(receivers->size()+1.)+double(float(cap-wire))/receivers->size())/cap,.1,1.);};
        const double input_factor=std::max(1.,admission_slew>0. ? admission_slew : slew*time_unit/1e-9);
        auto admitted=[&](float first_cap,float second_cap) {
            const double weight=(double(std::max(first_cap,second_cap))*pf+2e-5)/(double(wire)*pf+1e-5);
            const double shape=std::max(shape_at(first_cap),shape_at(second_cap));
            const double criterion=shape*weight*input_factor*int(nominal_fs);
            return std::isfinite(criterion) && criterion>=0. && criterion<double(std::numeric_limits<int>::max()) && int(criterion)<2000;
        };
        const bool before=admitted(nominal_first,nominal_second);
        if(initial_short)*initial_short=before;
        if(!before || !admitted(std::max(float(first),float(wire+admission_cap*scale)),std::max(float(second),float(wire+admission_cap*scale))))return std::nullopt;
    }
    const float total_second=float(second);
    const double fanout=receivers->size();
    const double wire_rc=double(float(wire*resistance))/(fanout+1.);
    const double shape=std::clamp((wire_rc+double(float(total_second-wire))*resistance/fanout)/
        double(float(total_second*resistance)),.1,1.);
    const float beta=float(double(resistance)*first*float(shape));
    if(!(beta>0.f))return std::nullopt;
    const double nominal=double(wire)+nominal_pins*scale;
    const auto columns=adaptive_ccs_columns(table,slew,vdd,.01*nominal);
    if(!columns)return std::nullopt;
    auto crossing=[&](double voltage,double cap) {
        size_t hi=1;while(hi+1<columns->size() && (*columns)[hi].cap<cap)++hi;
        const auto& a=(*columns)[hi-1];const auto& b=(*columns)[hi];
        const double w=(cap-a.cap)/(b.cap-a.cap);
        return (1.-w)*a.at_voltage(voltage).first+w*b.at_voltage(voltage).first;
    };
    auto time=[&](double voltage) {
        return voltage<=r.threshold?crossing(voltage,first):
            crossing(r.threshold,first)+crossing(voltage,second)-crossing(r.threshold,second);
    };
    const double raw_delay=time(driver_threshold);
    const double raw_slew=(time(upper)-time(lower))/derate;
    const double window=std::log((1.-lower)/(1.-upper))/derate;
    const double corrected_slew=raw_slew-.3*beta*window;
    if(!(corrected_slew>0.) || !std::isfinite(raw_delay))return std::nullopt;
    RcWaveformResult result;result.time_voltage_surface=true;
    result.load_within_table=true;result.adaptive_integration=true;
    result.lumped_ccs_runtime=true;
    result.driver.delay=Delay{float(raw_delay+.3*beta*std::log(1.-driver_threshold))};
    result.driver.output_slew=Slew{float(corrected_slew)};
    result.driver.ceff=float(first);result.driver.source=DelayModelSource::Csm;
    DelayResult load;
    const float driver_slew=result.driver.output_slew.value;
    load.delay=Delay{float(-beta*std::log(1.-load_threshold))};
    load.output_slew=Slew{float(std::sqrt(double(float(driver_slew*driver_slew))+
        (beta*window)*(beta*window)))};
    load.ceff=float(first);load.source=DelayModelSource::Csm;
    for(const auto& receiver:*receivers)result.loads[rc.nodes[receiver.node].pin.id]=load;
    const double middle=load_threshold;
    for(const auto& receiver:*receivers)result.receiver_slews[rc.nodes[receiver.node].pin.id]={
        float((time(middle)-time(lower))*(upper-lower)/(middle-lower)/derate),
        float((time(upper)-time(middle))*(upper-lower)/(upper-middle)/derate)};
    return result;
}

static std::optional<RcWaveformResult> adaptive_ccs_surface(
    const edacraft::core::CsmOutputCurrentTable& table,const FullRcNetwork& rc,double slew,double vdd,
    double lower,double upper,double derate,double cap_unit,double time_unit,double driver_threshold,double load_threshold,
    const std::vector<RcReceiverCapacitance>* receivers,const RcDelayThresholds* thresholds,
    const RcSlewThresholds* slew_thresholds=nullptr,bool short_source_seed=false) {
    // Recover exact SI prefix factors from float unit metadata. Values in
    // the source tables and the extracted network remain unchanged.
    cap_unit=adaptive_ccs_exact_si_unit(cap_unit);time_unit=adaptive_ccs_exact_si_unit(time_unit);
    const double rc_cap_scale=adaptive_ccs_exact_si_unit(rc.cap_scale);
    const size_t n=rc.nodes.size();const uint32_t driver=rc.driver_node_id;
    std::vector<double> cap(n);std::vector<RcLinearSystem::Edge> edges;double total=0.;
    for(size_t j=0;j<n;++j){cap[j]=rc.nodes[j].gnd_cap*rc_cap_scale/cap_unit;total+=cap[j];}
    // The compressed source and passive-network integration also apply to
    // characterized loads. Falling back there changes the solver at an
    // arbitrary load boundary and loses several ps of slew on C906 U897.
    // Retain the lower coverage limit used by the surface fallback.
    if(total<table.load_caps.front())return std::nullopt;
    std::vector<double> nominal=cap;
    std::vector<unsigned> regional_receivers(n,0);
    if(receivers)for(const auto& r:*receivers)++regional_receivers[r.node];
    if(receivers)for(const auto& r:*receivers) {
        const double scale=rc_cap_scale/cap_unit,loaded=std::max(r.first,r.second);
        const double reference=std::isfinite(r.precise_nominal)?r.precise_nominal:r.nominal>0.f?r.nominal:.5*(r.first+r.second);
        // Exact ground recovery is available for an isolated regional load.
        // Aliased receivers or extra loads retain the additive reconstruction.
        if(std::isfinite(r.extracted_ground) && regional_receivers[r.node]==1 &&
           rc.nodes[r.node].gnd_cap==float(double(r.extracted_ground)+loaded)) {
            cap[r.node]=(double(r.extracted_ground)+r.first)*scale;
            nominal[r.node]=(double(r.extracted_ground)+reference)*scale;
        } else {
            cap[r.node]+=(r.first-loaded)*scale;
            nominal[r.node]+=(reference-loaded)*scale;
        }
    }
    for(const auto& r:rc.resistors){double resistance=double(float(double(r.resistance)*double(rc.res_scale)*1e-3))*(cap_unit/1e-12)/(time_unit/1e-9);if(!(resistance>0.))return std::nullopt;edges.push_back({r.node1,r.node2,1./resistance});}
    double nominal_total=0.;for(double c:nominal)nominal_total+=c;
    double source_total=nominal_total;
    if(receivers)for(const auto& r:*receivers)
        source_total+=(adaptive_ccs_source_cap(r)-
            (r.nominal>0.f?r.nominal:.5*(r.first+r.second)))*rc_cap_scale/cap_unit;
    // Bound the source table by the current receiver load envelope. The
    // fixed nominal network still defines the reduced voltage basis.
    double first_total=0.;for(double c:cap)first_total+=c;
    double second_total=first_total;
    if(receivers)for(const auto& r:*receivers)
        second_total+=(double(r.second)-r.first)*rc_cap_scale/cap_unit;
    const double minimum_source_total=std::min(first_total,second_total);
    auto source=adaptive_ccs_columns(table,slew,vdd,.01*minimum_source_total);if(!source)return std::nullopt;
    // A short-source initialization retains its two bracketing load columns
    // when the updated receiver load requires distributed integration.
    if(short_source_seed && source->size()>2) {
        size_t hi=1;while(hi+1<source->size() && (*source)[hi].cap<source_total)++hi;
        *source={(*source)[hi-1],(*source)[hi]};
    }
    const auto& cs=*source;
    const bool cap_over_current=adaptive_ccs_uses_cap_over_current(cs);
    const bool dynamic=receivers && !receivers->empty();
    AdaptiveCcsRom rom;
    if(dynamic) {
        // 100 ohm seed termination builds the fixed voltage Krylov space;
        // the integration network uses a 10 Gohm regularization instead.
        if(!rom.initialize_receivers(nominal,edges,driver,10.*(time_unit/1e-9)/(cap_unit/1e-12),
                                     1e-7*(time_unit/1e-9)/(cap_unit/1e-12),1e-13/time_unit,true) ||
           !rom.update_receivers_ql(cap,driver))return std::nullopt;
    } else if(!rom.initialize(cap,edges,driver))return std::nullopt;
    auto receiver_weights=[&]() {
        if(!dynamic)return;
        for(size_t j=0;j<rom.b.size();++j) {
            rom.weight[j]=std::fabs(rom.b[j]);
            for(size_t u=0;u<n;++u)if(valid(rc.nodes[u].pin))
                rom.weight[j]=std::max(rom.weight[j],std::fabs(rom.output[u][j]));
        }
    };
    receiver_weights();std::vector<bool> switched(dynamic?receivers->size():0,false);
    std::vector<size_t> output_nodes;
    for(size_t u=0;u<n;++u)if(u!=driver && valid(rc.nodes[u].pin))output_nodes.push_back(u);
    const double output_step_factor=output_nodes.size()>=8?double(float(.3)):1.;
    const size_t m=rom.b.size();const double root=std::sqrt(double(m)),ns=time_unit/1e-9;
    struct State {double t,v,norm,I;std::vector<double> x,out;size_t basis_epoch=0;};
    size_t basis_epoch=0;
    auto outputs=[&](const auto& x){std::vector<double> out(n,0.);for(size_t u=0;u<n;++u)for(size_t j=0;j<m;++j)out[u]+=rom.output[u][j]*x[j];return out;};
    // Above-table loads use the largest characterized source column. Its
    // pulse must permit at least twenty steps, with a 30 ps minimum ceiling.
    // Keep the pulse duration's native float subtraction: tiny changes to
    // accepted trials can select another branch of the crossed CCS columns.
    const double pulse_duration=double(float(float(cs.back().t.back())-float(cs.back().t.front())));
    const double max_step=std::max(.03/ns,pulse_duration/20.);
    double h=.0003/ns,pred=0.,modal_pred=0.,pn=0.;
    const auto startup=adaptive_ccs_startup(cs,rom,h,1e-6/ns);
    double t=startup.first;
    AdaptiveCcsTimeState time_state;
    std::vector<double> source_caps;for(const auto& c:cs)source_caps.push_back(c.cap);
    std::vector<State> history{{t-h,0.,0.,startup.second,std::vector<double>(m,0.),std::vector<double>(n,0.)}};
    std::optional<double> rail_conductance;
    bool trapezoidal=true;double minimum_step=.0001/ns;
    unsigned retries=0;std::vector<std::array<double,4>> times(n);
    for(auto& a:times)a.fill(std::numeric_limits<double>::quiet_NaN());
    auto current=[&](double v,double t,double reference_voltage){
        std::vector<std::pair<double,double>> a;for(const auto& c:cs)a.push_back(c.at_voltage(std::max(0.,v),std::max(0.,reference_voltage)));
        // Keep the same load pair as the base query while perturbing voltage.
        size_t hi=1;while(hi+1<a.size() &&
            (v==reference_voltage?a[hi].first:cs[hi].at_voltage(std::max(0.,reference_voltage),std::max(0.,reference_voltage)).first)<t)++hi;
        const auto x=a[hi-1],y=a[hi];double w=y.first==x.first?.5:(t-x.first)/(y.first-x.first);
        // The voltage-domain query obeys the same capacitance bounds as the
        // time-domain startup solve. Clip the inferred load before current:
        // clipping only the final current changes late threshold crossings.
        const double c0=cs[hi-1].cap,c1=cs[hi].cap;
        const double effective_cap=std::clamp(c0+w*(c1-c0),double(float(.1*cs.front().cap)),11.*cs.back().cap);
        // Native zero-current regularization is .0001 in pF/ns; convert it
        // with the source units, as for the passive-network integration.
        const double zero_current=.0001*(time_unit/1e-9)/(cap_unit/1e-12);
        return adaptive_ccs_voltage_current(c0,c1,x.second,y.second,effective_cap,cap_over_current,zero_current);
    };
    bool complete=false;unsigned voltage_restart_trials=0;
    auto predict_voltage=[&](unsigned trial) {
        // Startup trials hold the previous voltage even when three history
        // samples already exist. Extrapolating earlier changes the error
        // estimate, accepted step size and subsequent threshold crossings.
        if(trapezoidal && trial>2 && history.size()>=3) {
            const auto& a=history[history.size()-3];const auto& z=history[history.size()-2];const auto& c=history.back();
            const double w0=(t-z.t)*(t-c.t)/((a.t-z.t)*(a.t-c.t)),w1=(t-a.t)*(t-c.t)/((z.t-a.t)*(z.t-c.t)),w2=1-w0-w1;
            const double scalar_pred=w0*a.v+w1*z.v+w2*c.v;
            modal_pred=scalar_pred;
            if(a.basis_epoch!=basis_epoch || z.basis_epoch!=basis_epoch || c.basis_epoch!=basis_epoch) {
                modal_pred=0.;
                for(size_t j=0;j<m;++j)
                    modal_pred+=rom.b[j]*(w0*a.x[j]+w1*z.x[j]+w2*c.x[j]);
            }
            pred=std::min(1.,std::max(c.v,scalar_pred));pn=std::max(c.norm,w0*a.norm+w1*z.norm+w2*c.norm);
        } else {pred=modal_pred=history.back().v;pn=history.back().norm;}
        // Late voltage prediction holds the accepted scalar and modal state.
        // Keep the norm extrapolator active for truncation-error step control.
        if(history.back().v>.85)pred=modal_pred=history.back().v;
        if(voltage_restart_trials)pred=modal_pred=history.back().v;
    };

    for(unsigned k=0;k<8000;++k) {
        if(voltage_restart_trials)--voltage_restart_trials;
        const auto old=history.back();const double d=(trapezoidal?2.:1.)/h;std::vector<double> base(m),x(m);double gain=0.,B=0.;
        for(size_t j=0;j<m;++j){base[j]=((d-(trapezoidal?rom.eigen[j]:0.))*old.x[j]+(trapezoidal?rom.b[j]*old.I:0.))/(d+rom.eigen[j]);gain+=rom.b[j]*rom.b[j]/(d+rom.eigen[j]);B+=rom.b[j]*base[j];}
        double v,I,modal_I;
        // Once established, retain the accepted rail conductance, including
        // ringing past the rail or below the entry voltage.
        // The passive receiver network can still need later crossings.
        if(rail_conductance) {
            const double conductance=*rail_conductance;
            v=(B+gain*conductance)/(1.+gain*conductance);
            I=modal_I=conductance*(1.-v);
        } else if(old.v<=.3) {
            // Keep capacitance order. Sorting by voltage can connect unrelated
            // columns when the characterized waveforms cross, selecting a
            // different root and moving the reported crossing by hundreds of ps.
            std::vector<std::pair<double,double>> points;for(const auto& c:cs)points.push_back(c.at_time(t));
            const auto solution=time_state.solve(points,source_caps,B,gain,k==0);
            v=solution.first;I=modal_I=solution.second;
        } else {
            I=current(pred,t,pred);const double gradient=std::min(0.,(current(pred+.001,t,pred)-I)/.001);
            // The source queries the bounded scalar predictor, while the
            // implicit modal correction starts at the unbounded predictor.
            // They differ when the extrapolated voltage falls below old.v.
            // Preserve the source's separately corrected current for history.
            v=(B+gain*(I-gradient*modal_pred))/(1-gain*gradient);
            modal_I=I+gradient*(v-modal_pred);
            I+=gradient*(v-pred);
        }
        double norm=old.norm;
        for(size_t j=0;j<m;++j){x[j]=base[j]+rom.b[j]*modal_I/(d+rom.eigen[j]);norm+=std::fabs(x[j]-old.x[j])*rom.weight[j];}
        // A large driver-voltage jump has its own retry guard before
        // receiver switching and local truncation-error acceptance. PT allows
        // ten reductions here, even below the ordinary integration floor.
        if(k>2 && retries<10 && std::fabs(v-old.v)>.2) {
            ++retries;h*=.333;t=old.t+h;
            predict_voltage(k);continue;
        }
        const auto out=outputs(x);
        // Native CCS measures the first threshold crossing before the local
        // truncation-error controller. A subsequently rejected trial retains
        // that measurement, just as it retains source-column/switch state.
        // Measuring only accepted steps shifts U515's slew by 0.167 ps and
        // selects a different crossed-column branch at its downstream U519.
        complete=true;
        for(size_t u=0;u<n;++u) {
            double threshold=u==driver?driver_threshold:load_threshold;
            if(thresholds && u!=driver){auto it=thresholds->find(u);if(it!=thresholds->end())threshold=it->second;}
            const auto w=rc_slew_window(uint32_t(u),lower,upper,derate,slew_thresholds);
            const double middle=u==driver?driver_threshold:
                rc_slew_middle(uint32_t(u),float(load_threshold),slew_thresholds);
            const double targets[4]={w.lower,middle,w.upper,threshold};
            for(unsigned j=0;j<4;++j)if(!std::isfinite(times[u][j]) && old.out[u]<targets[j] && out[u]>=targets[j])times[u][j]=old.t+(t-old.t)*(targets[j]-old.out[u])/(out[u]-old.out[u]);
            if(u==driver || valid(rc.nodes[u].pin))for(double x:times[u])complete=complete && std::isfinite(x);
        }
        if(complete)break;
        bool changed=false,nonlinear_change=false;
        if(dynamic)for(size_t j=0;j<receivers->size();++j) {
            const auto& r=(*receivers)[j];
            if(!switched[j] && out[r.node]>=r.threshold) {
                switched[j]=true;changed=true;
                nonlinear_change|=r.first!=r.second;
                cap[r.node]+=(r.second-r.first)*rc_cap_scale/cap_unit;
            }
        }
        if(changed) {
            // Switch after the trial, preserving reduced voltage coordinates.
            // The norm is accumulated before changing its modal weights.
            if(!rom.update_receivers_ql(cap,driver,&x))return std::nullopt;
            receiver_weights();h*=.5;retries=2;
            if(nonlinear_change){voltage_restart_trials=2;++basis_epoch;}
        }
        // Sustained minimum-step error signals trapezoidal ringing. Switch
        // permanently to backward Euler, with its own floor and predictor.
        if(trapezoidal && k>3 && v>.1 && h<.0001001/ns && history.size()>=3 &&
           old.t-history[history.size()-2].t<.0001001/ns &&
           history[history.size()-2].t-history[history.size()-3].t<.0001001/ns &&
           std::max(std::fabs(v-pred)/(v+.05),std::fabs(norm-pn)/(norm+.05*root))>.03) {
            trapezoidal=false;minimum_step*=.2;
        }
        const bool reject=k>3 && retries<2 && v>.02 && h>.0001001/ns && std::max(std::fabs(v-pred)/(v+.05),std::fabs(norm-pn)/(norm+.05*root))>.03;
        if(reject){++retries;h*=.333;t=old.t+h;}
        else {
            const bool forcehalf=old.v<.02 && old.I>1.5*I;double hn;
            // The first trial establishes history before current-drop control.
            if(forcehalf && k>0)hn=.5*h;
            // PT keeps trials 0, 1 and 2 in startup growth. Applying the
            // curvature controller after trial 2 changes the CCS root path
            // on the original C906 U43 network (about 270 ps at the driver).
            else if(k<=2)hn=std::min(max_step,h*(std::fabs(v-old.v)<.02?1.5:1.));
            else {
                // Backward Euler uses 30% of the trapezoidal step ceiling.
                hn=std::min(h*1.5,(v>=.85?3.:1.)*(trapezoidal?1.:.3)*max_step);const double dt=t-old.t;
                if(dt>1e-6/ns) {
                    if(history.size()>=2){const auto& oo=history[history.size()-2];const double dt2=t-oo.t,cv=(norm-old.norm)/dt-(norm-oo.norm)/dt2;if(dt2>1e-6/ns && cv!=0.)hn=std::min(hn,.03*std::max(norm,.005)/std::fabs(cv));}
                    if(norm!=old.norm)hn=std::min(hn,.05*root/std::fabs(norm-old.norm)*dt);
                    if(v!=old.v)hn=std::min(hn,.05/std::fabs(v-old.v)*dt);
                    double dv=0.;size_t checked=0;
                    for(size_t u:output_nodes){dv=std::max(dv,std::fabs(out[u]-old.out[u]));if(++checked==12)break;}
                    if(dv>0.)hn=std::min(hn,output_step_factor*.05/dv*dt);
                }
                const double error=(trapezoidal?1.5:3.)*std::fabs(norm-pn);
                if(v>.85)hn=std::min(hn,(1.25-error/(norm*.03))*h);
                else if(norm>.02*root)hn=std::min(hn,(1.5-error/((norm+.05*root)*.03))*h);
                // A floor-selected step bypasses Euler damping.
                if(hn<.333*h)hn=.333*h;
                else if(!trapezoidal)hn*=v>=.85?.9:.8;
            }
            // A genuine C1/C2 change invalidates the voltage extrapolator.
            // Keep the accumulated norm history, reduce the first new-region
            // step, and hold the voltage predictor until a trial is accepted.
            if(nonlinear_change)hn*=.8;
            hn=std::max(minimum_step,hn);
            // An overshoot or zero-current state cannot establish a passive
            // rail tail. Keep querying the source until a valid state returns.
            if(!rail_conductance && v>.95 && v<1. && I>0.)
                rail_conductance=I/(1.-v);
            history.push_back({t,v,norm,I,x,out,basis_epoch});t+=hn;h=hn;retries=0;
            if(history.size()>3)history.erase(history.begin());
            if(!trapezoidal){pred=modal_pred=v;pn=norm;continue;}
        }
        predict_voltage(k);
        if(!std::isfinite(t) || t*ns>100.)break;
    }
    if(!complete)return std::nullopt;
    RcWaveformResult result;result.time_voltage_surface=true;
    result.load_within_table=total<=table.load_caps.back()*(1.+8*std::numeric_limits<float>::epsilon());
    result.adaptive_integration=true;
    result.driver.delay=Delay{float(times[driver][1])};result.driver.output_slew=Slew{float((times[driver][2]-times[driver][0])/derate)};result.driver.ceff=float(total);result.driver.source=DelayModelSource::Csm;
    for(size_t u=0;u<n;++u)if(u!=driver && valid(rc.nodes[u].pin)) {
        const auto w=rc_slew_window(uint32_t(u),lower,upper,derate,slew_thresholds);
        const double middle=rc_slew_middle(uint32_t(u),float(load_threshold),slew_thresholds);
        DelayResult load;load.delay=Delay{float(times[u][3]-times[driver][1])};load.output_slew=Slew{float((times[u][2]-times[u][0])/w.derate)};load.ceff=float(total);load.source=DelayModelSource::Csm;result.loads[rc.nodes[u].pin.id]=load;
        result.receiver_slews[rc.nodes[u].pin.id]={float((times[u][1]-times[u][0])*(w.upper-w.lower)/(middle-w.lower)/w.derate),float((times[u][2]-times[u][1])*(w.upper-w.lower)/(w.upper-middle)/w.derate)};
    }
    return result;
}
