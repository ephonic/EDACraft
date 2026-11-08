#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>
#include <unordered_map>

#include "time_engine/types.hh"
#include "parasitics/timing_parasitics.hh"

namespace te {

// Resolves SPEF string names to internal IDs.
class SpefNameResolver {
public:
    virtual ~SpefNameResolver() = default;
    virtual NetId resolve_net(std::string_view name) = 0;
    virtual PinId resolve_pin(std::string_view name) = 0;
    // Resolve a SPEF CAP node to its owning net.  A node may be a net name,
    // an instance pin, or a top-level port.  The default preserves the old
    // resolver contract for clients that only know direct net names.
    virtual NetId resolve_node_net(std::string_view name) {
        return resolve_net(name);
    }
};

// Hand-written state machine parser for SPEF format.
class SpefParser {
public:
    explicit SpefParser(std::string_view input);

    bool parse(TimingParasiticDB& db, SpefNameResolver& resolver);
    std::string_view last_error() const { return error_; }

private:
    struct Line {
        std::string_view text;
        int line_num;
    };

    Line next_line();
    NetId parse_dnet_name(std::string_view line, SpefNameResolver& resolver,
                          const std::unordered_map<std::string, std::string>& name_map);
    std::vector<std::string_view> tokenize(std::string_view line);

    std::string_view input_;
    size_t pos_ = 0;
    int line_num_ = 0;
    std::string error_;
};

} // namespace te
