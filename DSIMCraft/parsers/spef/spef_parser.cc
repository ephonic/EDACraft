#include "spef_parser.hh"

#include <cctype>
#include <cstdlib>
#include <cmath>
#include <algorithm>

#include <string>
#include <string_view>
#include <vector>
#include <unordered_map>

#include "parasitics/timing_parasitics.hh"

namespace te {

namespace {
std::string decode_spef_name(std::string_view name) {
    std::string result;
    result.reserve(name.size());
    for(size_t i=0;i<name.size();++i) {
        if(name[i]=='\\' && i+1<name.size()) ++i;
        result.push_back(name[i]);
    }
    return result;
}
}

SpefParser::SpefParser(std::string_view input)
    : input_(input) {}

SpefParser::Line SpefParser::next_line() {
    while (pos_ < input_.size()) {
        size_t start = pos_;
        size_t end = input_.find('\n', start);
        if (end == std::string_view::npos) end = input_.size();
        line_num_++;

        std::string_view line = input_.substr(start, end - start);
        size_t cs = 0;
        while (cs < line.size() && std::isspace(static_cast<unsigned char>(line[cs]))) cs++;

        if (cs >= line.size()) {
            pos_ = end + (end < input_.size() ? 1 : 0);
            continue;
        }

        pos_ = end + (end < input_.size() ? 1 : 0);
        return {line, line_num_};
    }
    return {"", line_num_};
}

bool SpefParser::parse(TimingParasiticDB& db, SpefNameResolver& resolver) {
    if (input_.empty()) {
        error_ = "Empty SPEF input";
        return false;
    }
    enum class DnetSection { None, Conn, Cap, Res };
    DnetSection section = DnetSection::None;
    FullRcNetwork current_rc;
    NetId current_net = NULL_NET;
    std::unordered_map<std::string, uint32_t> node_map;
    uint32_t next_node_id = 0;
    std::unordered_map<std::string, std::string> name_map; // *N -> actual_name
    bool in_name_map = false;
    float r_scale = 1.0f;   // to ohm
    float c_scale = 1.0f;   // to farad
    float t_scale = 1.0f;   // to ns
    char delimiter = ':';
    bool includes_pin_caps = false;
    // Some extractors emit zero-capacitance aggregate bus D_NET records
    // (e.g. bus[39:0]) even though the gate netlist contains only bit nets.
    // Keep those records isolated and ignore their empty body; real bit-net
    // records are still required to resolve successfully.
    bool skip_unresolved_bus_dnet = false;

    // Helper to get or create node ID
    auto get_node_id = [&](const std::string& name) -> uint32_t {
        auto it = node_map.find(name);
        if (it != node_map.end()) return it->second;
        uint32_t id = next_node_id++;
        node_map[name] = id;
        if (valid(current_net)) db.register_node(name, current_net, id);
        return id;
    };

    while (pos_ < input_.size()) {
        auto line = next_line();
        if (line.text.empty()) break;

        size_t cs = 0;
        while (cs < line.text.size() && std::isspace(static_cast<unsigned char>(line.text[cs]))) cs++;
        if (cs >= line.text.size()) continue;

        // Helper to resolve a name via name_map
        auto resolve_name = [&](const std::string& name) -> std::string {
            auto it = name_map.find(name);
            if (it != name_map.end()) return decode_spef_name(it->second);
            // SPEF abbreviates the instance/net prefix, not the whole
            // node name: *85:I is the I pin of NAME_MAP entry *85.
            size_t split=std::string::npos;
            for(size_t i=0;i<name.size();++i) {
                if(name[i]=='\\' && i+1<name.size()) { ++i; continue; }
                if(name[i]==delimiter) { split=i; break; }
            }
            if (split != std::string::npos) {
                it = name_map.find(name.substr(0, split));
                if (it != name_map.end()) return decode_spef_name(it->second + name.substr(split));
            }
            return decode_spef_name(name);
        };

        if (line.text[cs] != '*') {
            if (skip_unresolved_bus_dnet) continue;
            if (section == DnetSection::Conn) {
                // Parse CONN line: *I pin_name direction  or  *P port_name direction
                auto tokens = tokenize(line.text.substr(cs));
                if (tokens.size() >= 2) {
                    std::string conn_type(tokens[0]);
                    std::string pin_name = resolve_name(std::string(tokens[1]));
                    std::string dir = (tokens.size() >= 3) ? std::string(tokens[2]) : "I";

                    PinId pin = NULL_PIN;
                    if (conn_type == "*I" || conn_type == "I") {
                        pin = resolver.resolve_pin(pin_name);
                    } else if (conn_type == "*P" || conn_type == "P") {
                        pin = resolver.resolve_pin(pin_name);
                    }

                    uint32_t nid = get_node_id(pin_name);
                    // Ensure node exists in RC network
                    if (nid >= current_rc.nodes.size()) {
                        current_rc.nodes.resize(nid + 1);
                    }
                    current_rc.nodes[nid].id = nid;
                    current_rc.nodes[nid].pin = pin;

                    // Instance output pins (*I ... O) drive the net.
                    // Input ports (*P ... I) also drive the net (external source).
                    // Output ports (*P ... O) are loads.
                    bool is_driver = false;
                    if ((conn_type == "*I" || conn_type == "I") &&
                        (dir == "O" || dir == "*O")) {
                        is_driver = true;
                    } else if ((conn_type == "*P" || conn_type == "P") &&
                               (dir == "I" || dir == "*I")) {
                        is_driver = true;
                    }
                    if (is_driver) {
                        current_rc.driver_node_id = nid;
                    }
                }
            } else if (section == DnetSection::Cap) {
                // Parse ground CAP (id node cap) or coupling CAP
                // (id node1 node2 cap).  The parasitic DB stores coupling
                // values in pF, matching the timing loading API; normalize
                // the SPEF native unit here instead of treating a coupling
                // entry as another ground capacitor on node2.
                auto tokens = tokenize(line.text.substr(cs));
                if (tokens.size() >= 3) {
                    float cap_val = std::strtof(std::string(tokens.back()).c_str(), nullptr);
                    const bool coupling = tokens.size() >= 4;
                    std::string node_name = resolve_name(std::string(
                        tokens[tokens.size() - (coupling ? 3 : 2)]));

                    uint32_t nid = get_node_id(node_name);
                    if (nid >= current_rc.nodes.size()) {
                        current_rc.nodes.resize(nid + 1);
                    }
                    current_rc.nodes[nid].id = nid;
                    if (coupling) {
                        const std::string other_name = resolve_name(std::string(tokens[tokens.size() - 2]));
                        const NetId other_net = resolver.resolve_node_net(other_name);
                        if (valid(other_net) && valid(current_net) && other_net != current_net) {
                            db.add_node_coupling(node_name, other_name, current_net, other_net,
                                static_cast<uint32_t>(std::strtoul(std::string(tokens[0]).c_str(),nullptr,10)),
                                cap_val * c_scale / 1.0e-12f);
                        } else if (valid(other_net) && other_net == current_net) {
                            const auto other_node=get_node_id(other_name);
                            if (other_node>=current_rc.nodes.size()) current_rc.nodes.resize(other_node+1);
                            current_rc.nodes[other_node].id=other_node;
                            current_rc.capacitors.push_back({static_cast<uint32_t>(current_rc.capacitors.size()),
                                nid,other_node,cap_val});
                        }
                    } else {
                        ParasiticCapacitor cap;
                        cap.id = static_cast<uint32_t>(current_rc.capacitors.size());
                        cap.node1 = nid;
                        cap.node2 = UINT32_MAX;
                        cap.capacitance = cap_val;
                        current_rc.nodes[nid].gnd_cap += cap_val;
                        current_rc.capacitors.push_back(cap);
                    }
                }
            } else if (section == DnetSection::Res) {
                // Parse RES line: id node1_name node2_name res_value
                auto tokens = tokenize(line.text.substr(cs));
                if (tokens.size() >= 4) {
                    std::string n1_name = resolve_name(std::string(tokens[tokens.size() - 3]));
                    std::string n2_name = resolve_name(std::string(tokens[tokens.size() - 2]));
                    float res_val = std::strtof(std::string(tokens.back()).c_str(), nullptr);

                    uint32_t n1 = get_node_id(n1_name);
                    uint32_t n2 = get_node_id(n2_name);
                    if (n1 >= current_rc.nodes.size()) current_rc.nodes.resize(n1 + 1);
                    if (n2 >= current_rc.nodes.size()) current_rc.nodes.resize(n2 + 1);
                    current_rc.nodes[n1].id = n1;
                    current_rc.nodes[n2].id = n2;

                    ParasiticResistor res;
                    res.id = static_cast<uint32_t>(current_rc.resistors.size());
                    res.node1 = n1;
                    res.node2 = n2;
                    res.resistance = res_val;
                    current_rc.resistors.push_back(res);
                }
            }
            continue;
        }

        size_t kw_end = cs + 1;
        while (kw_end < line.text.size() && !std::isspace(static_cast<unsigned char>(line.text[kw_end])) && line.text[kw_end] != '(')
            kw_end++;
        std::string_view keyword = line.text.substr(cs + 1, kw_end - cs - 1);

        if (skip_unresolved_bus_dnet && keyword != "D_NET" &&
            keyword != "END" && keyword != "NAME_MAP") {
            continue;
        }

        // If in NAME_MAP section and this isn't a known keyword, treat as name mapping entry
        if (in_name_map) {
            bool is_known_kw = (keyword == "END" || keyword == "D_NET" || keyword == "CONN" ||
                                keyword == "CAP" || keyword == "RES" || keyword == "NAME_MAP" ||
                                keyword == "PORT" || keyword == "DEFINE_PORTS" ||
                                keyword == "DESIGN" || keyword == "DATE" || keyword == "VENDOR" ||
                                keyword == "DIVIDER" || keyword == "DELIMITER" || keyword == "BUSDEL" ||
                                keyword == "D_SCALE" || keyword == "R_SCALE" || keyword == "C_SCALE" ||
                                keyword == "R_NET" || keyword == "C_NET" || keyword == "PORTS");
            if (!is_known_kw) {
                // NAME_MAP entry: *N actual_name  (keyword here is "N" like "1", "2", etc)
                auto tokens = tokenize(line.text.substr(cs));
                if (!tokens.empty() && tokens[0].size() > 1 && tokens[0][0] == '*') {
                    std::string key(tokens[0]);
                    std::string actual_name;
                    if (tokens.size() >= 2) {
                        actual_name = std::string(tokens[1]);
                    }
                    name_map[key] = actual_name;
                }
                continue;
            }
        }

        if (keyword == "END") {
            // Finalize current D_NET and continue parsing (not end of file)
            if (valid(current_net) && section != DnetSection::None) {
                db.set_network(current_net, std::move(current_rc));
            }
            section = DnetSection::None;
            current_net = NULL_NET;
            skip_unresolved_bus_dnet = false;
            continue;
        } else if (keyword == "DESIGN_FLOW") {
            includes_pin_caps = line.text.find("PIN_CAP INCLUDED") != std::string_view::npos;
        } else if (keyword == "DELIMITER") {
            auto tokens = tokenize(line.text.substr(kw_end));
            if (!tokens.empty() && !tokens[0].empty()) delimiter = tokens[0][0];
        } else if (keyword == "T_UNIT") {
            // Parse time unit: e.g., "1 NS"
            auto tokens = tokenize(line.text.substr(kw_end));
            if (tokens.size() >= 2) {
                float val = std::strtof(std::string(tokens[0]).c_str(), nullptr);
                std::string unit(tokens[1]);
                if (unit == "NS" || unit == "ns") t_scale = val;
                else if (unit == "PS" || unit == "ps") t_scale = val * 1e-3f;
                else if (unit == "US" || unit == "us") t_scale = val * 1e3f;
            }
        } else if (keyword == "R_UNIT") {
            auto tokens = tokenize(line.text.substr(kw_end));
            if (tokens.size() >= 2) {
                float val = std::strtof(std::string(tokens[0]).c_str(), nullptr);
                std::string unit(tokens[1]);
                if (unit == "OHM" || unit == "ohm") r_scale = val;
                else if (unit == "KOHM" || unit == "kohm") r_scale = val * 1e3f;
            }
        } else if (keyword == "C_UNIT") {
            auto tokens = tokenize(line.text.substr(kw_end));
            if (tokens.size() >= 2) {
                float val = std::strtof(std::string(tokens[0]).c_str(), nullptr);
                std::string unit(tokens[1]);
                if (unit == "FF" || unit == "ff") c_scale = val * 1e-15f;
                else if (unit == "PF" || unit == "pf") c_scale = val * 1e-12f;
            }
        } else if (keyword == "UNIT") {
            // IEEE 1481-1998 format: *UNIT 1 CAPACITANCE FF
            auto tokens = tokenize(line.text.substr(kw_end));
            if (tokens.size() >= 3) {
                float val = std::strtof(std::string(tokens[0]).c_str(), nullptr);
                std::string type(tokens[1]);
                std::string unit(tokens[2]);
                if (type == "TIME" || type == "time") {
                    if (unit == "NS" || unit == "ns") t_scale = val;
                    else if (unit == "PS" || unit == "ps") t_scale = val * 1e-3f;
                    else if (unit == "US" || unit == "us") t_scale = val * 1e3f;
                } else if (type == "RESISTANCE" || type == "resistance") {
                    if (unit == "OHM" || unit == "ohm") r_scale = val;
                    else if (unit == "KOHM" || unit == "kohm") r_scale = val * 1e3f;
                } else if (type == "CAPACITANCE" || type == "capacitance") {
                    if (unit == "FF" || unit == "ff") c_scale = val * 1e-15f;
                    else if (unit == "PF" || unit == "pf") c_scale = val * 1e-12f;
                }
            }
        } else if (keyword == "I" || keyword == "P" || keyword == "*I" || keyword == "*P") {
            // CONN line inside D_NET: *I pin_name direction or *P port_name direction
            if (section == DnetSection::Conn) {
                auto tokens = tokenize(line.text.substr(cs));
                if (tokens.size() >= 2) {
                    std::string conn_type(tokens[0]);
                    std::string pin_name = resolve_name(std::string(tokens[1]));
                    std::string dir = (tokens.size() >= 3) ? std::string(tokens[2]) : "I";

                    PinId pin = resolver.resolve_pin(pin_name);
                    if (!valid(pin)) {
                        error_ = "Unresolved SPEF connection '" + pin_name +
                            "' at line " + std::to_string(line.line_num);
                        return false;
                    }
                    uint32_t nid = get_node_id(pin_name);
                    if (nid >= current_rc.nodes.size()) {
                        current_rc.nodes.resize(nid + 1);
                    }
                    current_rc.nodes[nid].id = nid;
                    current_rc.nodes[nid].pin = pin;

                    // Instance output pins (*I ... O) drive the net.
                    // Input ports (*P ... I) also drive the net (external source).
                    // Output ports (*P ... O) are loads.
                    bool is_driver = false;
                    if ((conn_type == "*I" || conn_type == "I") &&
                        (dir == "O" || dir == "*O")) {
                        is_driver = true;
                    } else if ((conn_type == "*P" || conn_type == "P") &&
                               (dir == "I" || dir == "*I")) {
                        is_driver = true;
                    }
                    if (is_driver) {
                        current_rc.driver_node_id = nid;
                    }
                }
            }
        } else if (keyword == "D_NET") {
            in_name_map = false;
            // Finalize previous D_NET
            if (valid(current_net) && section != DnetSection::None) {
                db.set_network(current_net, std::move(current_rc));
            }
            section = DnetSection::Conn;
            current_rc = {};
            node_map.clear();
            next_node_id = 0;
            current_net = parse_dnet_name(line.text.substr(kw_end), resolver, name_map);
            if (!valid(current_net)) {
                std::string dnet_name;
                auto dnet_tokens = tokenize(line.text.substr(kw_end));
                if (!dnet_tokens.empty()) dnet_name = decode_spef_name(dnet_tokens.front());
                const bool aggregate_bus = dnet_name.find('[') != std::string::npos &&
                    dnet_name.find(':') != std::string::npos &&
                    dnet_name.find(']') != std::string::npos;
                const float aggregate_cap = dnet_tokens.size() > 1
                    ? std::strtof(std::string(dnet_tokens[1]).c_str(), nullptr) : 1.0f;
                if (aggregate_bus && std::fabs(aggregate_cap) < 1.0e-30f) {
                    skip_unresolved_bus_dnet = true;
                    section = DnetSection::Conn;
                    current_net = NULL_NET;
                    continue;
                }
                error_ = "Failed to resolve D_NET at line " + std::to_string(line.line_num);
                return false;
            }
            skip_unresolved_bus_dnet = false;
            current_rc.net = current_net;
            db.set_includes_pin_caps(current_net, includes_pin_caps);
            current_rc.driver_node_id = UINT32_MAX;
            current_rc.res_scale = r_scale;
            current_rc.cap_scale = c_scale;
            current_rc.time_scale = t_scale;
            // (debug print removed)
        } else if (keyword == "CONN") {
            section = DnetSection::Conn;
        } else if (keyword == "CAP") {
            section = DnetSection::Cap;
        } else if (keyword == "RES") {
            section = DnetSection::Res;
        } else if (keyword == "NAME_MAP") {
            in_name_map = true;
            section = DnetSection::None;
            if (valid(current_net)) {
                db.set_network(current_net, std::move(current_rc));
                current_net = NULL_NET;
            }
        } else if (keyword == "PORT" || keyword == "DEFINE_PORTS" ||
                   keyword == "DESIGN" || keyword == "DATE" || keyword == "VENDOR" ||
                   keyword == "DIVIDER" || keyword == "DELIMITER" || keyword == "BUSDEL" ||
                   keyword == "D_SCALE" || keyword == "R_SCALE" || keyword == "C_SCALE" ||
                   keyword == "R_NET" || keyword == "C_NET" ||
                   keyword == "PORTS") {
            in_name_map = false;
            if (section != DnetSection::None && keyword != "D_NET") {
                // These sections end the current D_NET
                if (valid(current_net)) {
                    db.set_network(current_net, std::move(current_rc));
                }
                section = DnetSection::None;
                current_net = NULL_NET;
            }
        }
    }

    // Finalize last D_NET
    if (valid(current_net) && section != DnetSection::None) {
        db.set_network(current_net, std::move(current_rc));
    }
    // Debug: print driver info for net "out"
    // (already handled by arrival propagator debug)

    return error_.empty();
}

NetId SpefParser::parse_dnet_name(std::string_view line, SpefNameResolver& resolver,
                                     const std::unordered_map<std::string, std::string>& name_map) {
    size_t ns = line.find_first_not_of(" \t(");
    if (ns == std::string_view::npos) return NULL_NET;
    size_t ne = line.find_first_of(" \t(", ns);
    std::string_view net_name = (ne == std::string_view::npos) ? line.substr(ns) : line.substr(ns, ne - ns);
    std::string resolved(net_name);
    auto it = name_map.find(resolved);
    if (it != name_map.end()) resolved = it->second;
    return resolver.resolve_net(decode_spef_name(resolved));
}

std::vector<std::string_view> SpefParser::tokenize(std::string_view line) {
    std::vector<std::string_view> tokens;
    size_t p = 0;
    while (p < line.size()) {
        size_t ts = line.find_first_not_of(" \t\r\n", p);
        if (ts == std::string_view::npos) break;
        size_t te = line.find_first_of(" \t\r\n", ts);
        tokens.push_back(line.substr(ts, te == std::string_view::npos ? std::string_view::npos : te - ts));
        p = (te == std::string_view::npos) ? line.size() : te;
    }
    return tokens;
}

} // namespace te
