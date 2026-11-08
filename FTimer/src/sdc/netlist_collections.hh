#pragma once

#include "network/network.hh"
#include <algorithm>
#include <cctype>
#include <functional>
#include <optional>
#include <sstream>

namespace te {

inline bool sdc_collection_glob_match(std::string_view pattern,
                                      std::string_view value) {
    size_t p = 0, v = 0, star = std::string_view::npos, retry = 0;
    while (v < value.size()) {
        if (p < pattern.size() && pattern[p] == '?') { ++p; ++v; continue; }
        if (p < pattern.size() && pattern[p] == '*') {
            star = p++;
            retry = v;
            continue;
        }
        if (p < pattern.size() && pattern[p] == value[v]) { ++p; ++v; continue; }
        if (star != std::string_view::npos) {
            p = star + 1;
            v = ++retry;
            continue;
        }
        return false;
    }
    while (p < pattern.size() && pattern[p] == '*') ++p;
    return p == pattern.size();
}

// Resolve the common netlist-dependent SDC collections before the shared
// syntax parser runs. Internal top pins have the opposite direction to RTL
// ports, so all_inputs are drivers and all_outputs are loads.
inline std::string expand_netlist_collections(const std::string& text, const Network& network) {
    std::vector<std::string> inputs, outputs, ports;
    for (uint32_t id = 0; id < network.pin_count(); ++id) {
        const auto& pin = network.pin(PinId{id});
        if (valid(pin.instance) && network.cell_name(network.instance(pin.instance).cell) != "__top__") continue;
        const auto name = std::string(network.pin_name(PinId{id}));
        ports.push_back(name);
        if (pin.direction == PortDirection::Output || pin.direction == PortDirection::Inout) inputs.push_back(name);
        if (pin.direction == PortDirection::Input || pin.direction == PortDirection::Inout) outputs.push_back(name);
    }
    auto words = [](const std::string& s) {
        std::vector<std::string> out;
        size_t start = 0;
        int braces = 0, brackets = 0;
        bool quote = false;
        for (size_t i = 0; i <= s.size(); ++i) {
            char c = i < s.size() ? s[i] : ' ';
            if (!braces && c == '"') quote = !quote;
            if (!quote) {
                if (c == '{') ++braces;
                else if (c == '}') --braces;
                else if (!braces && c == '[') ++brackets;
                else if (!braces && c == ']') --brackets;
            }
            if (!braces && !brackets && !quote && std::isspace(static_cast<unsigned char>(c))) {
                if (i > start) out.push_back(s.substr(start, i-start));
                start = i+1;
            }
        }
        return out;
    };
    using Names = std::vector<std::string>;
    std::function<std::optional<Names>(std::string)> evaluate;
    evaluate = [&](std::string expr) -> std::optional<Names> {
        if (expr.empty()) return Names{};
        if (expr.front() == '{' || expr.front() == '"') {
            expr = expr.substr(1, expr.size()-2);
            return words(expr);
        }
        if (expr.front() != '[') return Names{expr};
        auto args = words(expr.substr(1, expr.size()-2));
        if (args.empty()) return std::nullopt;
        if (args[0] == "all_inputs" && args.size() == 1) return inputs;
        if (args[0] == "all_outputs" && args.size() == 1) return outputs;
        if (args[0] == "get_ports" && args.size() == 2) {
            auto patterns = evaluate(args[1]);
            if (!patterns) return std::nullopt;
            Names matched;
            for (const auto& p : ports) for (const auto& pattern : *patterns) {
                // Match exact scalar ports, bus aliases, and the ubiquitous *.
                if (sdc_collection_glob_match(pattern, p) ||
                    p.rfind(pattern + "[", 0) == 0) {
                    matched.push_back(p); break;
                }
            }
            return matched;
        }
        if (args[0] == "remove_from_collection" && args.size() == 3) {
            auto selected = evaluate(args[1]), excluded = evaluate(args[2]);
            if (!selected || !excluded) return std::nullopt;
            selected->erase(std::remove_if(selected->begin(), selected->end(), [&](const auto& p) {
                return std::find(excluded->begin(), excluded->end(), p) != excluded->end();
            }), selected->end());
            return selected;
        }
        return std::nullopt;
    };
    std::string result;
    for (size_t pos = 0; pos < text.size();) {
        if (text[pos] != '[') { result += text[pos++]; continue; }
        size_t end = pos + 1;
        int depth = 1, brace = 0;
        for (; end < text.size() && depth; ++end) {
            if (text[end] == '{') ++brace;
            else if (text[end] == '}') --brace;
            else if (!brace && text[end] == '[') ++depth;
            else if (!brace && text[end] == ']') --depth;
        }
        const auto expr = text.substr(pos, end-pos);
        // Leave get_ports/get_pins syntax and its existing matching semantics
        // alone. Only materialize all_* and remove_from_collection commands.
        auto names = (expr.rfind("[all_", 0) == 0 || expr.rfind("[remove_from_collection", 0) == 0)
            ? evaluate(expr) : std::nullopt;
        if (names) {
            result += "[get_ports {";
            for (const auto& p : *names) result += " " + p;
            result += " }]";
        } else result += expr;
        pos = end;
    }
    return result;
}

} // namespace te
