#ifndef EDACRAFT_CORE_LOGIC_VIEW_HPP
#define EDACRAFT_CORE_LOGIC_VIEW_HPP

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace edacraft::core {

enum class LogicDialect : uint8_t {
    Invalid = 0,
    Word = 1,
    Gate = 2,
    Bit = 3,
    Macro = 4,
    Sequential = 5,
};

struct LogicBitRange {
    uint16_t offset = 0;
    uint16_t width = 1;
};

struct LogicNodeCost {
    float area = 0.0f;
    float delay = 0.0f;
    float power = 0.0f;
    float slack = 0.0f;
    float slew = 0.0f;
};

struct LogicNode {
    uint64_t id = 0;
    LogicDialect dialect = LogicDialect::Invalid;
    uint16_t node_type = 0;
    uint16_t bit_width = 1;
    std::string name;
    uint64_t parent_node_id = 0;
    uint64_t internal_root_id = 0;
    std::string hierarchy_path;
    std::string module_type_name;
    LogicNodeCost cost;
    std::string mapped_cell_name;
    std::string mapped_instance_name;
    std::string mapped_output_pin;
    bool mapped_output_inverted = false;
    bool skip_rtl_cell = false;
};

struct LogicEdge {
    uint64_t id = 0;
    uint64_t src_node_id = 0;
    uint64_t dst_node_id = 0;
    LogicBitRange src_range;
    LogicBitRange dst_range;
    bool complement = false;
};

class LogicView {
public:
    void clear();

    void add_node(LogicNode node);
    void add_edge(LogicEdge edge);

    const LogicNode* find_node(uint64_t node_id) const;
    const LogicEdge* find_edge(uint64_t edge_id) const;

    const std::vector<LogicNode>& nodes() const { return nodes_; }
    const std::vector<LogicEdge>& edges() const { return edges_; }
    size_t node_count() const { return nodes_.size(); }
    size_t edge_count() const { return edges_.size(); }

    std::vector<const LogicEdge*> incoming_edges(uint64_t node_id) const;
    std::vector<const LogicEdge*> outgoing_edges(uint64_t node_id) const;

private:
    std::vector<LogicNode> nodes_;
    std::vector<LogicEdge> edges_;
    std::unordered_map<uint64_t, size_t> node_index_;
    std::unordered_map<uint64_t, size_t> edge_index_;
    std::unordered_map<uint64_t, std::vector<size_t>> incoming_;
    std::unordered_map<uint64_t, std::vector<size_t>> outgoing_;
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_LOGIC_VIEW_HPP
