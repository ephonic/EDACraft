#include "edacraft/core/logic_view.hpp"

#include <algorithm>

namespace edacraft::core {

void LogicView::clear() {
    nodes_.clear();
    edges_.clear();
    node_index_.clear();
    edge_index_.clear();
    incoming_.clear();
    outgoing_.clear();
}

void LogicView::add_node(LogicNode node) {
    if (node.id == 0) return;
    auto existing = node_index_.find(node.id);
    if (existing != node_index_.end()) {
        nodes_[existing->second] = std::move(node);
        return;
    }
    size_t idx = nodes_.size();
    node_index_[node.id] = idx;
    nodes_.push_back(std::move(node));
}

void LogicView::add_edge(LogicEdge edge) {
    if (edge.id == 0 || edge.src_node_id == 0 || edge.dst_node_id == 0) return;
    auto existing = edge_index_.find(edge.id);
    if (existing != edge_index_.end()) {
        size_t idx = existing->second;
        const auto& old = edges_[idx];
        auto remove_index = [idx](auto& indices) {
            indices.erase(std::remove(indices.begin(), indices.end(), idx), indices.end());
        };
        if (auto it = outgoing_.find(old.src_node_id); it != outgoing_.end()) {
            remove_index(it->second);
        }
        if (auto it = incoming_.find(old.dst_node_id); it != incoming_.end()) {
            remove_index(it->second);
        }
        edges_[idx] = std::move(edge);
        outgoing_[edges_[idx].src_node_id].push_back(idx);
        incoming_[edges_[idx].dst_node_id].push_back(idx);
        return;
    }
    size_t idx = edges_.size();
    edge_index_[edge.id] = idx;
    edges_.push_back(std::move(edge));
    outgoing_[edges_.back().src_node_id].push_back(idx);
    incoming_[edges_.back().dst_node_id].push_back(idx);
}

const LogicNode* LogicView::find_node(uint64_t node_id) const {
    auto it = node_index_.find(node_id);
    if (it == node_index_.end()) return nullptr;
    if (it->second >= nodes_.size()) return nullptr;
    return &nodes_[it->second];
}

const LogicEdge* LogicView::find_edge(uint64_t edge_id) const {
    auto it = edge_index_.find(edge_id);
    if (it == edge_index_.end()) return nullptr;
    if (it->second >= edges_.size()) return nullptr;
    return &edges_[it->second];
}

std::vector<const LogicEdge*> LogicView::incoming_edges(uint64_t node_id) const {
    std::vector<const LogicEdge*> result;
    auto it = incoming_.find(node_id);
    if (it == incoming_.end()) return result;
    result.reserve(it->second.size());
    for (size_t idx : it->second) {
        if (idx < edges_.size()) result.push_back(&edges_[idx]);
    }
    return result;
}

std::vector<const LogicEdge*> LogicView::outgoing_edges(uint64_t node_id) const {
    std::vector<const LogicEdge*> result;
    auto it = outgoing_.find(node_id);
    if (it == outgoing_.end()) return result;
    result.reserve(it->second.size());
    for (size_t idx : it->second) {
        if (idx < edges_.size()) result.push_back(&edges_[idx]);
    }
    return result;
}

} // namespace edacraft::core
