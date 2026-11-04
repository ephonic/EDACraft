#pragma once
#include "sdf.hpp"
#include "time.hpp"
#include <array>

namespace dsim {
// Numeric path annotation after arc identity/condition matching. This is not a
// timing-check accumulator: negative path results are clamped after each update.
// The model supplies explicit initial delays and its own unit/precision.
class SdfPathDelays {
    TimeScale model_;
    std::array<uint64_t,12> quanta_{};
    bool explicit_x_=false;
    bool partial_zero_readback_=false;
public:
    // Delay order: 01,10,0Z,Z1,1Z,Z0,0X,X1,1X,X0,XZ,ZX.
    // Model and SDF lists accept exactly 1,2,3,6 or 12 values.
    SdfPathDelays(TimeScale model,const std::vector<std::string>& initial);
    TimeScale model_time() const {return model_;}
    const std::array<uint64_t,12>& model_quanta() const {return quanta_;}
    // Raw selected corners, not global-tick previews. A missing value inherits.
    // Returns the number of stored transition slots whose result was clamped.
    // All failures leave the complete old table unchanged.
    // An increment after partial ABSOLUTE with zero slots is rejected: VCS
    // readback differs from ordinary arithmetic there and remains unresolved.
    // Mixed DEVICE/IOPATH annotations may require an ABSOLUTE maximum against
    // the current path. Merge basic slots before deriving X transitions;
    // INCREMENT continues to read and modify the effective stored values.
    size_t apply(SdfEntry::Mode mode,const std::vector<std::optional<std::string>>& selected,uint64_t sdf_unit_fs,
                 bool absolute_maximum=false);
    std::array<uint64_t,12> ticks(uint64_t global_precision_fs) const;
    // Logic codes follow V::bit: 0,1,X=2,Z=3. Equal codes have no transition.
    static int transition(int from,int to);
    uint64_t delay(int from,int to,uint64_t global_precision_fs) const;
};
}
