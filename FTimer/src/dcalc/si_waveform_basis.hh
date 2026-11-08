#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace te {
// Slews at the engine API are library-characterized ns. A physical voltage
// interval is characterized_slew * derate, not characterized_slew itself.
struct SiWaveformBasis {
    double lower=.2,upper=.8,derate=1.,threshold=.5;
    void validate() const {
        if (!(lower>0 && upper<1 && upper>lower && derate>0 &&
              threshold>0 && threshold<1) || !std::isfinite(derate))
            throw std::runtime_error("Invalid SI library thresholds/derate");
    }
    double ramp(double slew) const { validate();return slew*derate/(upper-lower); }
    double progress(bool rise) const { return rise?threshold:1.-threshold; }
    double resistance(double slew,double load_pf,bool rise) const {
        validate();
        const double span=rise?std::log((1.-lower)/(1.-upper)):std::log(upper/lower);
        return slew*derate*1000./(span*load_pf);
    }
    template<class Times,class Values>
    static double crossing(const Times& time,const Values& voltage,double target,bool rise) {
        for (size_t k=1;k<voltage.size();++k) {
            if (rise?(voltage[k-1]<target && voltage[k]>=target):
                     (voltage[k-1]>target && voltage[k]<=target))
                return double(time[k-1])+(target-voltage[k-1])/
                    (voltage[k]-voltage[k-1])*(double(time[k])-time[k-1]);
        }
        return NAN;
    }
    // Exact duration for the piecewise-linear reported segment, including a
    // segment which crosses both the positive and negative noise thresholds.
    static double width_fraction(double a,double b,double threshold) {
        auto above=[&](double x,double y) {
            if (x>threshold && y>threshold)return 1.;
            if (x<=threshold && y<=threshold)return 0.;
            const double fraction=(threshold-x)/(y-x);
            return x>threshold?fraction:1.-fraction;
        };
        return above(a,b)+above(-a,-b);
    }
};
} // namespace te
