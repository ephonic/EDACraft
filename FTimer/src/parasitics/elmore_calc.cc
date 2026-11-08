#include "elmore_calc.hh"

#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <cmath>

namespace te {

ElmoreResult compute_elmore_delays(const FullRcNetwork& rc) {
    ElmoreResult result;
    if (rc.nodes.empty() || rc.driver_node_id == UINT32_MAX ||
        rc.driver_node_id >= rc.nodes.size()) return result;

    // Parallel resistors connect one child, not several copies of its
    // capacitance. Combine their conductance before the tree traversal.
    // Preserve a unique edge's original float resistance exactly.
    std::vector<ParasiticResistor> edges;
    std::vector<double> conductance;
    std::unordered_map<uint64_t,size_t> parallel;
    for(const auto& res:rc.resistors) {
        if(res.node1>=rc.nodes.size() || res.node2>=rc.nodes.size() || res.node1==res.node2) continue;
        const auto a=std::min(res.node1,res.node2),b=std::max(res.node1,res.node2);
        const uint64_t key=(uint64_t(a)<<32)|uint64_t(b);
        const auto inserted=parallel.emplace(key,edges.size());
        if(inserted.second) {
            edges.push_back(res);
            conductance.push_back(res.resistance>0.f?1./res.resistance:0.);
        } else {
            const size_t k=inserted.first->second;
            if(edges[k].resistance==0.f || res.resistance==0.f) edges[k].resistance=0.f;
            else {
                conductance[k]+=1./res.resistance;
                edges[k].resistance=float(1./conductance[k]);
            }
        }
    }
    // Build adjacency list: node_id → [(neighbor_id, resistance)]
    std::vector<std::vector<std::pair<uint32_t, float>>> adj(rc.nodes.size());
    for (const auto& res : edges) {
        if (res.node1 < rc.nodes.size() && res.node2 < rc.nodes.size()) {
            adj[res.node1].push_back({res.node2, res.resistance});
            adj[res.node2].push_back({res.node1, res.resistance});
        }
    }

    // BFS from driver to establish parent-child tree structure
    std::vector<int> parent(static_cast<int>(rc.nodes.size()), -1);
    std::vector<float> parent_res(static_cast<int>(rc.nodes.size()), 0.0f);
    std::queue<uint32_t> q;
    q.push(rc.driver_node_id);
    std::unordered_set<uint32_t> visited;
    visited.insert(rc.driver_node_id);

    while (!q.empty()) {
        uint32_t u = q.front(); q.pop();
        for (auto [v, r] : adj[u]) {
            if (visited.count(v)) continue;
            visited.insert(v);
            parent[v] = static_cast<int>(u);
            parent_res[v] = r;
            q.push(v);
        }
    }

    // Collect nodes in BFS order for pre-order traversal
    std::vector<uint32_t> bfs_order;
    bfs_order.reserve(rc.nodes.size());
    bfs_order.push_back(rc.driver_node_id);
    std::vector<uint8_t> in_bfs(rc.nodes.size(), 0);
    in_bfs[rc.driver_node_id] = 1;
    for (size_t i = 0; i < bfs_order.size(); ++i) {
        uint32_t u = bfs_order[i];
        for (auto [v, r] : adj[u]) {
            if (parent[v] == static_cast<int>(u) && !in_bfs[v]) {
                in_bfs[v] = 1;
                bfs_order.push_back(v);
            }
        }
    }

    // Unit conversion: R(ohm) * C(farad) = seconds → ps
    float rc_to_ps = rc.res_scale * rc.cap_scale / 1e-12f;

    // ────────────────────────────────────────────────────────────
    // Step 1: Compute subtree capacitance for each node (post-order)
    // ────────────────────────────────────────────────────────────
    std::vector<float> subtree_cap(rc.nodes.size(), 0.0f);
    float sum_r_c2 = 0.0f;
    for (auto it = bfs_order.rbegin(); it != bfs_order.rend(); ++it) {
        uint32_t u = *it;
        float cap = rc.nodes[u].gnd_cap;
        for (auto [v, r] : adj[u]) {
            if (parent[v] == static_cast<int>(u)) {
                cap += subtree_cap[v];
                // Driving-point admittance 2nd moment contribution:
                // Σ R_edge · C_subtree²
                sum_r_c2 += parent_res[v] * subtree_cap[v] * subtree_cap[v];
            }
        }
        subtree_cap[u] = cap;
    }
    result.total_load_cap = subtree_cap[rc.driver_node_id];
    result.sum_r_c2 = sum_r_c2;
    result.rc_to_ps = rc_to_ps;

    // ────────────────────────────────────────────────────────────
    // Step 2: Compute Elmore delay to each node (pre-order)
    // ────────────────────────────────────────────────────────────
    std::vector<float> delay(rc.nodes.size(), 0.0f);
    for (uint32_t u : bfs_order) {
        if (parent[u] >= 0) {
            delay[u] = delay[parent[u]] + parent_res[u] * subtree_cap[u] * rc_to_ps;
        }
    }

    // ────────────────────────────────────────────────────────────
    // Step 3: Compute load-delay (ldelay) for each node (post-order)
    // ldelay[u] = cap(u) * delay(u) + sum(ldelay[child])
    // ────────────────────────────────────────────────────────────
    std::vector<float> ldelay(rc.nodes.size(), 0.0f);
    for (auto it = bfs_order.rbegin(); it != bfs_order.rend(); ++it) {
        uint32_t u = *it;
        float val = rc.nodes[u].gnd_cap * delay[u];
        for (auto [v, r] : adj[u]) {
            if (parent[v] == static_cast<int>(u)) {
                val += ldelay[v];
            }
        }
        ldelay[u] = val;
    }

    // ────────────────────────────────────────────────────────────
    // Step 4: Compute beta and impulse for each node (pre-order)
    // beta[child] = beta[parent] + R(parent,child) * ldelay[child]
    // impulse[u]  = 2 * beta[u] - delay[u]^2
    // ────────────────────────────────────────────────────────────
    std::vector<float> beta(rc.nodes.size(), 0.0f);
    std::vector<float> impulse(rc.nodes.size(), 0.0f);
    for (uint32_t u : bfs_order) {
        if (parent[u] >= 0) {
            // parent_res is in raw units; convert to ps via rc_to_ps
            // ldelay is in (farad * ps), parent_res in ohms
            // beta needs units of ps²: R(ohm) * C(farad) * ps = ps * ps = ps²
            // Wait: parent_res[ohms] * ldelay[farad * ps] = (ohm * farad) * ps = seconds * ps
            // We need to convert seconds to ps: multiply by rc_to_ps
            // Actually: R(ohm) * C(farad) = seconds. So R * (C * ps) = seconds * ps.
            // To get ps²: multiply by rc_to_ps again.
            // Let's verify with OpenTimer's code:
            // delay = R * C_subtree (in seconds)
            // ldelay = sum(C_i * delay_i) (in farad * seconds)
            // beta = sum(R * ldelay) (in ohm * farad * seconds = seconds²)
            // impulse = 2*beta - delay² (in seconds²)
            // So everything is in seconds², and OpenTimer doesn't do extra conversion.
            // In our code, delay is already in ps. So:
            // ldelay = sum(C_i * delay_i_ps) is in farad * ps.
            // beta = sum(R_ohms * ldelay_farad_ps) = seconds * ps.
            // To get ps²: multiply by rc_to_ps (which is ps/second).
            beta[u] = beta[parent[u]] + parent_res[u] * ldelay[u] * rc_to_ps;
        }
        impulse[u] = 2.0f * beta[u] - delay[u] * delay[u];
        if (impulse[u] < 0.0f) impulse[u] = 0.0f; // numerical safety
    }

    // Map delays and impulses to load pins
    for (const auto& node : rc.nodes) {
        if (valid(node.pin) && node.id != rc.driver_node_id) {
            result.pin_delay[node.pin.id] = delay[node.id];
            result.pin_impulse[node.pin.id] = impulse[node.id];
        }
    }

    return result;
}

} // namespace te
