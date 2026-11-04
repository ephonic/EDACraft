#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include "gate/gate_netlist_parser.hh"
#include "spef/spef_parser.hh"
#include "time_engine/liberty_io.hh"
#include "edacraft/core/liberty_db.hpp"

static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
static std::string read(const std::filesystem::path& path) {
    std::ifstream input(path);
    require(input.good(), "Cannot open fixture");
    return std::string(std::istreambuf_iterator<char>(input), {});
}
class Resolver final : public te::SpefNameResolver {
public:
    explicit Resolver(te::Network& network) : network_(network) {}
    te::NetId resolve_net(std::string_view name) override {
        return network_.find_net(name).value_or(te::NULL_NET);
    }
    te::PinId resolve_pin(std::string_view name) override {
        const auto split = name.find(':');
        const auto inst_name = split == std::string_view::npos ? std::string_view("top") : name.substr(0, split);
        const auto pin_name = split == std::string_view::npos ? name : name.substr(split + 1);
        const auto inst = network_.find_instance(inst_name);
        return inst ? network_.find_pin(*inst, pin_name).value_or(te::NULL_PIN) : te::NULL_PIN;
    }
    te::NetId resolve_node_net(std::string_view name) override {
        auto net = resolve_net(name);
        if (te::valid(net)) return net;
        auto pin = resolve_pin(name);
        return te::valid(pin) ? network_.pin(pin).net : te::NULL_NET;
    }
private:
    te::Network& network_;
};
int main(int argc, char** argv) try {
    require(argc == 3, "Usage: parser_bundle_smoke <source-dir> <output-dir>");
    const std::filesystem::path source(argv[1]), output(argv[2]);
    te::Network network;
    te::GateNetlistParser netlist(network);
    require(netlist.parse((source / "test/examples/tiny.v").string(), "top") == "top", "Wrong top");
    const auto net = network.find_net("a");
    require(net.has_value(), "Missing input net");
    Resolver resolver(network);
    te::TimingParasiticDB parasitics;
    const auto spef_text = read(source / "test/examples/tiny.spef");
    te::SpefParser spef(spef_text);
    if (!spef.parse(parasitics, resolver)) throw std::runtime_error(std::string(spef.last_error()));
    const auto* rc = parasitics.get_network(*net);
    require(rc && rc->resistors.size() == 1 && rc->nodes.size() == 2, "Wrong RC network");
    require(std::abs(rc->resistors[0].resistance - 10.0f) < 1e-6f, "Wrong resistance");
    require(std::abs(rc->cap_scale - 1e-12f) < 1e-18f, "Wrong SPEF capacitance scale");
    for (const char* fixture : {"seq_cell.lib", "csm_cell.lib"}) {
        edacraft::core::LibertyDB text_db;
        edacraft::core::StringPool text_pool;
        require(te::read_core_liberty_file((source / "test/liberty" / fixture).string(), text_db, text_pool), "Liberty parse failed");
        require(text_db.library_count() == 1 && text_db.library(0).cells.size() > 0, "Empty Liberty fixture");
        for (bool gzip : {false, true}) {
            auto path = output / (std::string(fixture) + (gzip ? ".ftlib.gz" : ".ftlib"));
            {
                std::ofstream binary(path, std::ios::binary);
                require(te::save_core_liberty_binary(text_db, text_pool, binary, gzip), "Binary save failed");
            }
            edacraft::core::LibertyDB binary_db;
            edacraft::core::StringPool binary_pool;
            require(te::read_core_liberty_file(path.string(), binary_db, binary_pool), "Binary load failed");
            require(binary_db.library_count() == text_db.library_count(), "Wrong library count");
            require(binary_db.library(0).cells.size() == text_db.library(0).cells.size(), "Wrong cell count");
            for (uint32_t i = 0; i < text_db.library(0).cells.size(); ++i) {
                const auto& before = text_db.library(0).cells[i];
                const auto& after = binary_db.library(0).cells[i];
                require(text_pool.view(before.name) == binary_pool.view(after.name), "Wrong cell name");
                require(before.pins.size() == after.pins.size() && before.arcs.size() == after.arcs.size(), "Wrong cell structure");
            }
            std::filesystem::remove(path);
        }
    }
    std::cout << "PASS: gate netlist, SPEF RC, Liberty and plain/gzip FTLib round trips\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
