#pragma once
#include <cstdint>
#include <string>
#include <string_view>
#include <memory>
#include <vector>
#include "time.hpp"

namespace dsim {
struct GateTimingData;
struct GateSource;
// Owned structural IR. No RTL parser nodes or Network pointers survive binding.
struct GatePort {
    std::string name,direction;
    int high=0,low=0;
    bool packed=false;
    std::vector<int> nets; // declaration order, most significant first
};
struct GateModel {
    struct Pin { std::string name; bool output=false; std::string expression; bool inout=false,internal=false; };
    std::string name;
    size_t copy_width=0; // one atomic continuous assignment / port adapter
    int sequential_kind=0; // 1 ff, 2 latch
    bool output_reads_inputs=false;
    std::string control,next,clear,preset;
    char conflict1='X',conflict2='X';
    std::vector<Pin> pins;
    std::vector<int> wait_inputs; // only actual control/output dependencies for storage
};
struct GateInstance { uint32_t model,first; };
struct GateTimingNames {
    struct Pin {std::string name,direction;int net;};
    struct Scope {uint32_t name;std::string type;std::vector<Pin> pins;TimeScale time;};
    std::vector<char> bytes;
    std::vector<uint32_t> instance_names,sorted_instances;
    std::vector<Scope> scopes;
    uint32_t append(const std::vector<std::string>& path);
    std::string_view key(uint32_t offset) const;
    void finalize();
    int find_instance(const std::vector<std::string>& path) const;
    static std::string encode(const std::vector<std::string>& path);
};
struct GateOptions {
    bool wave_names=false,timing_names=false,timing_only=false;
    std::shared_ptr<GateSource> source; // prepared text is transferred once to the network parser
};
struct GateDesign {
    std::string top;
    TimeScale top_time;
    uint64_t structural_precision_fs=0;
    std::string preprocessing_report="{}";
    std::string partitioning_report;
    bool batch_enabled=false;
    bool parallel_enabled=false;
    bool scalar_timing_enabled=false;
    bool sdf_jobs_enabled=false;
    bool path_dictionary_enabled=false;
    bool fold_zero_inputs=false;
    std::vector<GatePort> ports;
    std::vector<GateModel> models;
    std::vector<GateInstance> instances;
    std::vector<int> pin_nets;
    std::vector<int8_t> constants; // -1 ordinary net; 0,1,X=2,Z=3
    std::vector<std::string> wave_names; // optional; empty without --wave-support
    bool wave_enabled=false;
    bool timing_only=false;
    std::shared_ptr<GateTimingNames> timing_names;
    std::shared_ptr<GateTimingData> timing;
    size_t network_nets=0,network_pins=0,network_instances=0;
    double parse_seconds=0,bind_seconds=0;
    static std::string rtl_identifier(const std::string& name);
    std::string stub() const;
    std::string cpp(uint64_t precision_fs=0,bool parallel_wave=true) const;
    std::string report() const;
};
GateDesign parse_gate(const std::string& file,const std::string& top,const std::vector<std::string>& libraries,GateOptions options={});
}
