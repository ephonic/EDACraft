#pragma once

#include "edacraft/core/liberty_db.hpp"
#include <algorithm>

namespace te {

// Evaluate each linear segment as slope*x + intercept. Algebraically
// equivalent weighted sums have different float residuals, which can select
// different branches in the finite-tolerance characterization solve.
inline float lookup_nldm(const edacraft::core::NldmTable& table,
                         float input_slew, float load_cap) {
    if (!table.rows || !table.cols) return 0.f;
    auto high_index=[](const std::vector<float>& axis,float value) {
        if (axis.size()<2) return size_t(0);
        const auto found=std::lower_bound(axis.begin(),axis.end(),value);
        return found==axis.end()?axis.size()-1:
            std::max(size_t(1),size_t(found-axis.begin()));
    };
    auto line=[](float a,float b,float low,float high,float value) {
        if (low==high) return a;
        const float slope=(b-a)/(high-low);
        // Preserve the float products even on compilers that contract a
        // multiply and subtraction into a single rounded operation.
        const volatile float low_product=low*slope;
        const volatile float scaled=value*slope;
        const float intercept=a-low_product;
        return intercept+scaled;
    };
    const size_t r1=high_index(table.axis1,input_slew);
    const size_t c1=high_index(table.axis2,load_cap);
    const size_t r0=r1?r1-1:0,c0=c1?c1-1:0;
    const float low_cap=table.axis2.empty()?0.f:table.axis2[c0];
    const float high_cap=table.axis2.empty()?0.f:table.axis2[c1];
    const float top=line(table.values[r0*table.cols+c0],
                         table.values[r0*table.cols+c1],low_cap,high_cap,load_cap);
    const float bottom=line(table.values[r1*table.cols+c0],
                            table.values[r1*table.cols+c1],low_cap,high_cap,load_cap);
    return line(top,bottom,table.axis1.empty()?0.f:table.axis1[r0],
                 table.axis1.empty()?0.f:table.axis1[r1],input_slew);
}

} // namespace te
