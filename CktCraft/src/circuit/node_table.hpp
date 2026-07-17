// node_table.hpp — 节点名 ↔ 内部索引映射
#ifndef RFSIM_CIRCUIT_NODE_TABLE_HPP
#define RFSIM_CIRCUIT_NODE_TABLE_HPP

#include "../rfsim.hpp"
#include <string>
#include <unordered_map>
#include <vector>

namespace rfsim {

// 节点表：节点名(小写) -> NodeId。地节点(GND/0/!)固定为 0。
class NodeTable {
public:
    NodeTable() {
        // 预注册地节点的各种别名
        intern("0");     // SPICE 数字地
        intern("gnd");
        intern("!");
        intern("ground");
    }

    // 取得或创建节点索引。"0"/"gnd"/"!" 等都映射到 0。
    NodeId intern(const std::string& name) {
        std::string low = lower(name);
        // 地节点别名
        if (isGround(low)) return 0;
        auto it = map_.find(low);
        if (it != map_.end()) return it->second;
        NodeId id = static_cast<NodeId>(names_.size() + 1); // 从 1 开始
        map_[low] = id;
        names_.push_back(low);
        return id;
    }

    // 查询（不创建）。不存在返回 0xFFFFFFFF
    [[nodiscard]] NodeId lookup(const std::string& name) const {
        std::string low = lower(name);
        if (isGround(low)) return 0;
        auto it = map_.find(low);
        return it != map_.end() ? it->second : 0xFFFFFFFFu;
    }

    [[nodiscard]] const std::string& nameOf(NodeId id) const {
        if (id == 0) { static const std::string g = "0"; return g; }
        return names_[id - 1];
    }

    // 非地节点数
    [[nodiscard]] size_t size() const noexcept { return names_.size(); }

private:
    std::unordered_map<std::string, NodeId> map_;
    std::vector<std::string> names_;

    static std::string lower(std::string s) {
        for (auto& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        return s;
    }
    static bool isGround(const std::string& low) {
        return low == "0" || low == "gnd" || low == "!" || low == "ground";
    }
};

} // namespace rfsim

#endif // RFSIM_CIRCUIT_NODE_TABLE_HPP
