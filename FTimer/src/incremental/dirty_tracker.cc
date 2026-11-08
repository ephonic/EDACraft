#include "dirty_tracker.hh"

#include "graph/timing_graph.hh"
#include "network/network.hh"

namespace te {

DirtyTracker::DirtyTracker(TimingGraph& graph) : graph_(&graph) {}

void DirtyTracker::mark_pin(PinId pin) {
    mark_vertex(pin.id * 2);       // rise
    mark_vertex(pin.id * 2 + 1);   // fall
}

void DirtyTracker::mark_net(NetId net, const Network& network) {
    if (!valid(net)) return;
    const auto& net_data = network.net(net);
    if (valid(net_data.driver)) {
        mark_pin(net_data.driver);
    }
    for (auto load_pin : net_data.loads) {
        mark_pin(load_pin);
    }
}

void DirtyTracker::mark_vertex(uint32_t vid) {
    if (vid == UINT32_MAX) return;
    if (in_queue_.size() <= vid) {
        in_queue_.resize(static_cast<size_t>(vid) + 1, 0);
    }
    if (!in_queue_[vid]) {
        in_queue_[vid] = 1;
        queue_.push_back(vid);
    }
}

void DirtyTracker::flush() {
    for (uint32_t vid : queue_) {
        graph_->mark_dirty(vid);
    }
    queue_.clear();
    std::fill(in_queue_.begin(), in_queue_.end(), 0);
}

void DirtyTracker::clear() {
    queue_.clear();
    std::fill(in_queue_.begin(), in_queue_.end(), 0);
}

} // namespace te
