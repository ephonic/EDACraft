// graph.h — 轻量无向图 + 连通分量（替代 Boost Graph）
//
// amor 原代码依赖 Boost Graph 的 adjacency_list + connected_components。
// 这里用邻接表 + BFS 实现同款功能，消除 Boost 依赖。
#ifndef RFSIM_MOR_GRAPH_H
#define RFSIM_MOR_GRAPH_H

#include <vector>
#include <cstdint>

namespace rfsim::mor {

class Graph {
public:
    Graph() = default;
    explicit Graph(int n) : adj_(n) {}

    void resize(int n) { adj_.assign(n, {}); }
    int numVertices() const { return static_cast<int>(adj_.size()); }

    void addEdge(int u, int v) {
        if (u < 0 || v < 0) return;
        if (u >= (int)adj_.size()) adj_.resize(u + 1);
        if (v >= (int)adj_.size()) adj_.resize(v + 1);
        adj_[u].push_back(v);
        adj_[v].push_back(u);
    }

    // 连通分量：返回分量数，label[i] = 节点 i 的分量编号（0-based）
    int connectedComponents(std::vector<int>& label) const {
        int n = static_cast<int>(adj_.size());
        label.assign(n, -1);
        int comp = 0;
        for (int i = 0; i < n; ++i) {
            if (label[i] != -1) continue;
            // BFS
            std::vector<int> queue;
            queue.push_back(i);
            label[i] = comp;
            size_t head = 0;
            while (head < queue.size()) {
                int u = queue[head++];
                for (int v : adj_[u]) {
                    if (label[v] == -1) {
                        label[v] = comp;
                        queue.push_back(v);
                    }
                }
            }
            ++comp;
        }
        return comp;
    }

private:
    std::vector<std::vector<int>> adj_;
};

} // namespace rfsim::mor

#endif // RFSIM_MOR_GRAPH_H
