#pragma once

#include <cstdint>
#include <vector>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"
#include "sdc/resolved_constraints.hh"

namespace te {

class TimingGraph;
class Network;
class ArrivalPropagator;

// ────────────────────────────────────────────────────────────
// Required Time Propagator: backward propagation from endpoints
// ────────────────────────────────────────────────────────────
//
// Propagates required times backwards through the timing graph:
// 1. Initialize endpoints with required = clock_period (from SDC)
// 2. Process vertices in reverse topological order (level by level, descending)
// 3. For each vertex:
//    a. For each fanout edge, compute edge delay
//    b. required = min(required, required_of_fanout - edge_delay)

class RequiredPropagator {
public:
    RequiredPropagator(
        TimingGraph& graph,
        const Network& network,
        const edacraft::core::LibertyDB& liberty,
        const ResolvedConstraintSet* sdc, ArrivalPropagator* arrival = nullptr,
        bool exhaustive = false, size_t path_limit = 1000000
    ) : graph_(graph), network_(network), liberty_(liberty), sdc_(sdc), arrival_(arrival),
        exhaustive_(exhaustive), path_limit_(path_limit) {}

    void propagate_all();
    void propagate_dirty();

private:
    TimingGraph& graph_;
    const Network& network_;
    const edacraft::core::LibertyDB& liberty_;
    const ResolvedConstraintSet* sdc_;
    ArrivalPropagator* arrival_;
    bool exhaustive_;
    size_t path_limit_;
    void propagate_launch_labels();
};

} // namespace te
