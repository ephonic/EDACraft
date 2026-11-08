#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>
#include <vector>

namespace te {

inline double rc_driver_current_at(const std::vector<std::pair<double,double>>& curve,
                                   double voltage) {
    const auto it=std::upper_bound(curve.begin(),curve.end(),
        std::make_pair(voltage,std::numeric_limits<double>::infinity()));
    if(it==curve.begin()) return it->second;
    if(it==curve.end()) return curve.back().second;
    const auto lo=*(it-1),hi=*it;
    return lo.second+(hi.second-lo.second)*(voltage-lo.first)/(hi.first-lo.first);
}

// Scale the history up to its boundary, then join the mature source there.
// Interpolate before scaling: a sample beyond the boundary belongs to the
// unscaled tail and must not dilute the history's boundary current.
inline void splice_rc_driver_curve(std::vector<std::pair<double,double>>& history,
                                    const std::vector<std::pair<double,double>>& tail,
                                    double boundary,double gain) {
    const double before=rc_driver_current_at(history,boundary)*gain;
    const double after=rc_driver_current_at(tail,boundary);
    history.erase(std::lower_bound(history.begin(),history.end(),
        std::make_pair(boundary,-std::numeric_limits<double>::infinity())),history.end());
    for(auto& point:history) point.second*=gain;
    history.push_back({boundary,before});
    history.push_back({boundary,after});
    for(const auto& point:tail) if(point.first>boundary) history.push_back(point);
}

// Solve the reduced passive network's KCL equation against a piecewise
// linear source. Equal-voltage points describe a downward current jump:
// the boundary can hold its voltage while supplying any intervening current.
inline double solve_rc_driver_curve(double diagonal, double rhs,
                                    const std::vector<std::pair<double,double>>& curve) {
    for(size_t j=1;j<curve.size();++j) {
        const auto lo=curve[j-1],hi=curve[j];
        if(hi.first==lo.first) {
            const double required=diagonal*lo.first-rhs;
            if(lo.second>=required && required>=hi.second)
                return std::clamp(lo.first,0.,1.);
            continue;
        }
        if(hi.first-lo.first<1e-8) continue;
        const double slope=(hi.second-lo.second)/(hi.first-lo.first);
        const double denominator=diagonal-slope;
        if(denominator<=0.) continue;
        const double voltage=(rhs+lo.second-slope*lo.first)/denominator;
        if(voltage>=lo.first-1e-8 && voltage<=hi.first+1e-8)
            return std::clamp(voltage,0.,1.);
    }
    return std::numeric_limits<double>::quiet_NaN();
}

} // namespace te
