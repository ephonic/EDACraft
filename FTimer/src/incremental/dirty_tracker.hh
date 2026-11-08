#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "time_engine/types.hh"

namespace te {

class TimingGraph;
class Network;

// ────────────────────────────────────────────────────────────
// DirtyTracker: manages incremental change notifications
// ────────────────────────────────────────────────────────────
//
// Bridges ECO-level changes (net cap changed, pin slew changed,
// Liberty cell updated, etc.) to graph-level dirty vertex marks.
//
// Usage:
//   1. Call mark_pin / mark_net / mark_vertex as changes occur.
//   2. Call flush() to apply all queued marks to TimingGraph.
//   3. Call clear() to discard queued marks without applying.
//
// The tracker de-duplicates vertices so a vertex is never marked
// dirty more than once in the same flush cycle.
// ────────────────────────────────────────────────────────────

class DirtyTracker {
public:
    DirtyTracker() = default;
    explicit DirtyTracker(TimingGraph& graph);

    // Bind to a graph (must be called before flush if default-constructed).
    void attach(TimingGraph& graph) { graph_ = &graph; }

    // Mark a pin's rise and fall vertices as dirty.
    void mark_pin(PinId pin);

    // Mark all pins on a net as dirty (driver + all loads).
    void mark_net(NetId net, const Network& network);

    // Mark a specific graph vertex as dirty.
    void mark_vertex(uint32_t vid);

    // Apply all queued dirty marks to the graph.  The owning timing update
    // increments the graph generation after propagation completes.
    void flush();

    // Clear internal queue without applying.
    void clear();

    // Number of queued dirty vertices (before flush).
    size_t queue_size() const { return queue_.size(); }

    const std::vector<uint32_t>& queued_vertices() const { return queue_; }

    // True if no changes are queued.
    bool empty() const { return queue_.empty(); }

private:
    TimingGraph* graph_ = nullptr;
    std::vector<uint32_t> queue_;
    std::vector<uint8_t> in_queue_;
};

} // namespace te
