#include "liberty_binary.hh"

#include <algorithm>
#include <cctype>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

#include "edacraft/core/liberty_db.hpp"
#include "liberty_compress.hh"
#include "liberty_input_format.hh"
#include "parser/liberty_parser.hh"
#include "time_engine/liberty_io.hh"
#include "time_engine/types.hh"

namespace te {
namespace ec = edacraft::core;

namespace {

// ────────────────────────────────────────────────────────────
// Endianness check
// ────────────────────────────────────────────────────────────
inline bool is_little_endian() {
    uint16_t x = 1;
    return *reinterpret_cast<const uint8_t*>(&x) == 1;
}

// ────────────────────────────────────────────────────────────
// Binary buffer writer
// ────────────────────────────────────────────────────────────
class BufWriter {
    std::vector<uint8_t> data_;
public:
    template<typename T>
    void write(const T& val) {
        static_assert(std::is_trivially_copyable_v<T>, "T must be trivially copyable");
        size_t pos = data_.size();
        data_.resize(pos + sizeof(T));
        std::memcpy(data_.data() + pos, &val, sizeof(T));
    }

    void write_bytes(const uint8_t* src, size_t len) {
        size_t pos = data_.size();
        data_.resize(pos + len);
        std::memcpy(data_.data() + pos, src, len);
    }

    void write_floats(const float* src, size_t count) {
        write_bytes(reinterpret_cast<const uint8_t*>(src), count * sizeof(float));
    }

    size_t size() const { return data_.size(); }
    uint8_t* data() { return data_.data(); }
    const uint8_t* data() const { return data_.data(); }
    std::vector<uint8_t> release() { return std::move(data_); }
};

// ────────────────────────────────────────────────────────────
// Binary buffer reader
// ────────────────────────────────────────────────────────────
class BufReader {
    const uint8_t* data_;
    size_t size_;
    size_t pos_ = 0;
public:
    BufReader(const uint8_t* data, size_t size) : data_(data), size_(size) {}

    template<typename T>
    T read() {
        static_assert(std::is_trivially_copyable_v<T>, "T must be trivially copyable");
        if (pos_ + sizeof(T) > size_) throw std::runtime_error("liberty_binary: read past end");
        T val;
        std::memcpy(&val, data_ + pos_, sizeof(T));
        pos_ += sizeof(T);
        return val;
    }

    void read_bytes(uint8_t* dst, size_t len) {
        if (pos_ + len > size_) throw std::runtime_error("liberty_binary: read past end");
        std::memcpy(dst, data_ + pos_, len);
        pos_ += len;
    }

    void read_floats(float* dst, size_t count) {
        read_bytes(reinterpret_cast<uint8_t*>(dst), count * sizeof(float));
    }

    size_t tell() const { return pos_; }
    void seek(size_t pos) { pos_ = pos; }
    size_t remaining() const { return size_ - pos_; }
};

// ────────────────────────────────────────────────────────────
// File format structs (little-endian, packed by memcpy)
// ────────────────────────────────────────────────────────────
static_assert(sizeof(float) == 4, "float must be 4 bytes");

#pragma pack(push, 1)

struct FtlHeader {
    char magic[8];
    uint32_t version;
    uint32_t flags;
    uint64_t uncompressed_size;
    uint64_t string_pool_offset;
    uint64_t string_pool_size;
    uint32_t num_libraries;
    uint64_t library_dir_offset;
    uint32_t num_cells_total;
    uint64_t cell_index_offset;
};
static_assert(sizeof(FtlHeader) == 64, "FtlHeader must be 64 bytes");

constexpr char FTL_MAGIC[8] = {'F', 'T', 'L', 'I', 'B', '\0', '\0', '\0'};
// v6 adds SI power-unit scales and Liberty internal_power tables.  v7 retains
// conditional pin receiver groups; v8 retains timing-arc receiver tables;
// v9 retains timing-arc CCSN first-stage Miller capacitance and makes optional
// CSM corner-vector lengths explicit.
// v17 requires regeneration: older parsers omitted CCS retaining currents
// even though the existing arc payload can serialize them. Their absence
// cannot be distinguished from a library with no retaining characterization.
// Version 10 preserves recovery/removal types that older parsers lost.
// v12 appends conditional leakage groups; power tables now use canonical axes.
// v18 retains complete pin/arc CCSN stages and their referenced templates.
// v17 caches silently discarded these data and must be regenerated.
constexpr uint32_t FTL_VERSION = 18;
constexpr uint32_t FTL_FLAG_COMPRESSED = 1;

struct FtlLibraryEntry {
    uint32_t name_id;
    float time_unit;
    float cap_unit;
    float res_unit;
    float volt_unit;
    float curr_unit;
    float leak_power_unit;
    float slew_lower;
    float slew_upper;
    float input_thresh_rise;
    float input_thresh_fall;
    float output_thresh_rise;
    float output_thresh_fall;
    float slew_derate;
    uint32_t cell_start_idx;
    uint32_t cell_count;
    float default_max_transition;    // v3+
    float default_max_capacitance;   // v3+
    float default_max_fanout;        // v3+
};

struct FtlLibraryPowerExt {
    float time_unit_seconds;
    float capacitance_unit_farads;
    float voltage_unit_volts;
    float leakage_power_unit_watts;
};

struct FtlCellIndexEntry {
    uint32_t name_id;      // original StringId (remapped on read)
    uint64_t cell_offset;  // offset to FtlCellHeader in file
};

struct FtlCellHeader {
    uint32_t name_id;
    float area;
    uint32_t num_pins;
    uint32_t num_arcs;
    uint32_t num_pvt_points;
};

// Extended cell header for version 2+ (written after FtlCellHeader)
struct FtlCellExtHeader {
    uint32_t function_id;       // StringId
    uint32_t footprint_id;      // StringId
    float cell_leakage_power;
    uint8_t dont_use;
    uint32_t ff_clocked_on;     // StringId
    uint32_t ff_next_state;     // StringId
    uint32_t ff_clear;          // StringId
    uint32_t ff_preset;         // StringId
    uint32_t ff_enable;         // StringId
    float max_capacitance;      // v3+
    float max_transition;       // v3+
    float max_fanout;           // v3+
    uint32_t clock_gating_integrated_cell; // v5, StringId
    uint32_t ff_state; // v5, primary state variable declared by ff(...)
};

struct FtlPinHeader {
    uint32_t name_id;
    float capacitance;
    uint8_t is_clock;
    uint8_t direction;
    uint32_t num_arc_ids;
    float miller_cap_rise;
    float miller_cap_fall;
    uint32_t related_pg_pin;
};

// Extended pin header for version 2+ (written after FtlPinHeader)
struct FtlPinExtHeader {
    uint32_t function_id;   // StringId
    uint32_t clear_id;      // StringId
    uint32_t preset_id;     // StringId
    uint32_t enable_id;     // StringId
    uint8_t clock_gate_flags; // v5: clock, enable, test, output
};

struct FtlPinPowerHeader {
    uint32_t num_internal_power;
};

struct FtlInternalPowerHeader {
    uint32_t related_pin;
    uint32_t related_pg_pin;
    uint32_t when_id;
};

struct FtlReceiverCapacitanceHeader {
    uint32_t num_groups;
};

struct FtlReceiverCapacitanceGroupHeader {
    uint32_t when_id;
};

struct FtlArcHeader {
    uint32_t from_pin;
    uint32_t to_pin;
    uint8_t sense;
    uint8_t type;
    uint32_t related_pin;
};

struct FtlArcExtHeader {
    uint32_t when_id;
};

struct FtlArcMillerExt {
    float miller_cap_rise;
    float miller_cap_fall;
};

#pragma pack(pop)

// ────────────────────────────────────────────────────────────
// Helpers for NLDM / CSM serialization
// ────────────────────────────────────────────────────────────

// v18 stores CCSN syntax trees outside the string pool, so embedded numeric
// arrays retain their original precision and are independent of ID remapping.
static void write_ccsn_string(BufWriter& w, const std::string& value) {
    w.write<uint32_t>(static_cast<uint32_t>(value.size()));
    if (!value.empty()) w.write_bytes(reinterpret_cast<const uint8_t*>(value.data()), value.size());
}
static std::string read_ccsn_string(BufReader& r) {
    const auto count = r.read<uint32_t>();
    if (count > r.remaining()) throw std::runtime_error("liberty_binary: invalid CCSN string length");
    std::string value(count, '\0');
    if (count) r.read_bytes(reinterpret_cast<uint8_t*>(&value[0]), count);
    return value;
}
static void write_ccsn_nodes(BufWriter& w, const std::vector<ec::LibertyCcsnNode>& nodes,
                              unsigned depth = 0) {
    if (depth > 64) throw std::runtime_error("liberty_binary: excessive CCSN nesting");
    w.write<uint32_t>(static_cast<uint32_t>(nodes.size()));
    for (const auto& node : nodes) {
        write_ccsn_string(w, node.name);
        w.write<uint8_t>(static_cast<uint8_t>(node.kind));
        w.write<uint32_t>(static_cast<uint32_t>(node.arguments.size()));
        for (const auto& atom : node.arguments) {
            write_ccsn_string(w, atom.text);
            w.write<uint8_t>(atom.quoted ? 1 : 0);
        }
        write_ccsn_nodes(w, node.children, depth + 1);
    }
}
static void read_ccsn_nodes(BufReader& r, std::vector<ec::LibertyCcsnNode>& nodes,
                             unsigned depth = 0) {
    if (depth > 64) throw std::runtime_error("liberty_binary: excessive CCSN nesting");
    const auto count = r.read<uint32_t>();
    // Every node needs at least a name length, kind, atom count and child count.
    if (count > r.remaining()/13) throw std::runtime_error("liberty_binary: invalid CCSN node count");
    nodes.resize(count);
    for (auto& node : nodes) {
        node.name = read_ccsn_string(r);
        const auto kind = r.read<uint8_t>();
        if (kind > static_cast<uint8_t>(ec::LibertyCcsnNode::Kind::Group))
            throw std::runtime_error("liberty_binary: invalid CCSN node kind");
        node.kind = static_cast<ec::LibertyCcsnNode::Kind>(kind);
        const auto atoms = r.read<uint32_t>();
        if (atoms > r.remaining()/5) throw std::runtime_error("liberty_binary: invalid CCSN atom count");
        node.arguments.resize(atoms);
        for (auto& atom : node.arguments) {
            atom.text = read_ccsn_string(r);
            const auto quoted = r.read<uint8_t>();
            if (quoted > 1) throw std::runtime_error("liberty_binary: invalid CCSN quote flag");
            atom.quoted = quoted != 0;
        }
        read_ccsn_nodes(r, node.children, depth + 1);
    }
}

template <typename NldmTableT>
static void write_nldm(BufWriter& w, const NldmTableT& tbl) {
    w.write<uint32_t>(static_cast<uint32_t>(tbl.rows));
    w.write<uint32_t>(static_cast<uint32_t>(tbl.cols));
    w.write<uint32_t>(static_cast<uint32_t>(tbl.axis1.size()));
    w.write<uint32_t>(static_cast<uint32_t>(tbl.axis2.size()));
    w.write<uint32_t>(static_cast<uint32_t>(tbl.values.size()));
    if (!tbl.axis1.empty()) w.write_floats(tbl.axis1.data(), tbl.axis1.size());
    if (!tbl.axis2.empty()) w.write_floats(tbl.axis2.data(), tbl.axis2.size());
    if (!tbl.values.empty()) w.write_floats(tbl.values.data(), tbl.values.size());
}

static void read_nldm(BufReader& r, ec::NldmTable& tbl) {
    tbl.rows = r.read<uint32_t>();
    tbl.cols = r.read<uint32_t>();
    uint32_t axis1_size = r.read<uint32_t>();
    uint32_t axis2_size = r.read<uint32_t>();
    uint32_t values_size = r.read<uint32_t>();
    if (axis1_size > 0) {
        tbl.axis1.resize(axis1_size);
        r.read_floats(tbl.axis1.data(), axis1_size);
    }
    if (axis2_size > 0) {
        tbl.axis2.resize(axis2_size);
        r.read_floats(tbl.axis2.data(), axis2_size);
    }
    if (values_size > 0) {
        tbl.values.resize(values_size);
        r.read_floats(tbl.values.data(), values_size);
    }
}

template <typename CsmTableT>
static void write_csm(BufWriter& w, const CsmTableT& tbl) {
    w.write<uint32_t>(tbl.nslew);
    w.write<uint32_t>(tbl.ncap);
    if (tbl.nslew == 0 || tbl.ncap == 0) return;

    w.write_floats(tbl.input_slews.data(), tbl.input_slews.size());
    w.write_floats(tbl.load_caps.data(), tbl.load_caps.size());

    size_t nw = static_cast<size_t>(tbl.nslew) * tbl.ncap;
    for (size_t i = 0; i < nw; ++i) {
        const auto& wf = tbl.waveforms[i];
        w.write<uint32_t>(static_cast<uint32_t>(wf.time_points.size()));
        w.write<float>(wf.reference_time);
        if (!wf.time_points.empty()) {
            w.write_floats(wf.time_points.data(), wf.time_points.size());
            w.write_floats(wf.current.data(), wf.current.size());
        }
    }

    // v9 stores the optional corner vectors with explicit lengths. Earlier
    // writers implicitly assumed both vectors always contained nslew*ncap
    // entries, although Liberty files are allowed to omit them. That made a
    // following CSM table unreadable when either vector was empty.
    w.write<uint32_t>(static_cast<uint32_t>(tbl.corner_delays.size()));
    if (!tbl.corner_delays.empty()) {
        w.write_floats(tbl.corner_delays.data(), tbl.corner_delays.size());
    }
    w.write<uint32_t>(static_cast<uint32_t>(tbl.corner_slews.size()));
    if (!tbl.corner_slews.empty()) {
        w.write_floats(tbl.corner_slews.data(), tbl.corner_slews.size());
    }
}

static void read_csm(BufReader& r,
                     ec::CsmOutputCurrentTable& tbl,
                     bool has_explicit_corner_sizes) {
    tbl.nslew = r.read<uint32_t>();
    tbl.ncap = r.read<uint32_t>();
    if (tbl.nslew == 0 || tbl.ncap == 0) return;

    tbl.input_slews.resize(tbl.nslew);
    tbl.load_caps.resize(tbl.ncap);
    r.read_floats(tbl.input_slews.data(), tbl.nslew);
    r.read_floats(tbl.load_caps.data(), tbl.ncap);

    size_t nw = static_cast<size_t>(tbl.nslew) * tbl.ncap;
    tbl.waveforms.resize(nw);
    for (size_t i = 0; i < nw; ++i) {
        auto& wf = tbl.waveforms[i];
        uint32_t ntp = r.read<uint32_t>();
        wf.reference_time = r.read<float>();
        if (ntp > 0) {
            wf.time_points.resize(ntp);
            wf.current.resize(ntp);
            r.read_floats(wf.time_points.data(), ntp);
            r.read_floats(wf.current.data(), ntp);
        }
    }

    const size_t delay_count = has_explicit_corner_sizes
        ? r.read<uint32_t>() : nw;
    tbl.corner_delays.resize(delay_count);
    if (delay_count != 0) {
        r.read_floats(tbl.corner_delays.data(), delay_count);
    }
    const size_t slew_count = has_explicit_corner_sizes
        ? r.read<uint32_t>() : nw;
    tbl.corner_slews.resize(slew_count);
    if (slew_count != 0) {
        r.read_floats(tbl.corner_slews.data(), slew_count);
    }
}

// ────────────────────────────────────────────────────────────
// String pool serialization
// ────────────────────────────────────────────────────────────

template <typename PoolT>
static void write_string_pool(BufWriter& w, const PoolT& pool) {
    uint32_t count = static_cast<uint32_t>(pool.size());
    w.write<uint32_t>(count);

    // Build offsets and data
    std::vector<uint32_t> offsets;
    offsets.reserve(count);
    std::vector<char> data;
    data.reserve(count * 32); // rough guess

    for (uint32_t i = 0; i < count; ++i) {
        offsets.push_back(static_cast<uint32_t>(data.size()));
        std::string_view sv = pool.view(i);
        data.insert(data.end(), sv.begin(), sv.end());
        data.push_back('\0');
    }

    for (uint32_t off : offsets) w.write(off);
    w.write_bytes(reinterpret_cast<const uint8_t*>(data.data()), data.size());
}

static std::vector<uint32_t> read_string_pool(BufReader& r, ec::StringPool& pool) {
    uint32_t count = r.read<uint32_t>();
    std::vector<uint32_t> remap;
    if (count == 0) return remap;

    std::vector<uint32_t> offsets(count);
    for (uint32_t i = 0; i < count; ++i) {
        offsets[i] = r.read<uint32_t>();
    }

    size_t data_start = r.tell();
    remap.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        r.seek(data_start + offsets[i]);
        std::string s;
        while (true) {
            char c = r.read<char>();
            if (c == '\0') break;
            s.push_back(c);
        }
        uint32_t new_id = pool.intern(s);
        remap.push_back(new_id);
    }
    return remap;
}

inline uint32_t remap_id(uint32_t old_id, const std::vector<uint32_t>& remap) {
    if (old_id == UINT32_MAX) return UINT32_MAX;
    if (old_id >= remap.size()) return UINT32_MAX;
    return remap[old_id];
}

template <typename DbT, typename PoolT>
bool save_liberty_binary_impl(const DbT& db,
                              const PoolT& pool,
                              std::ostream& out,
                              bool compress) {
    if (!is_little_endian()) {
        std::cerr << "liberty_binary: big-endian platforms not supported\n";
        return false;
    }

    BufWriter w;

    // Reserve space for header (patched later)
    size_t header_pos = w.size();
    for (int i = 0; i < 64; ++i) w.write<uint8_t>(0);

    // ── String Pool ──
    uint64_t sp_offset = w.size();
    write_string_pool(w, pool);
    uint64_t sp_size = w.size() - sp_offset;

    // ── Library Directory ──
    uint64_t lib_dir_offset = w.size();
    uint32_t num_libs = static_cast<uint32_t>(db.library_count());
    w.write<uint32_t>(num_libs);

    struct CellRange { uint32_t start; uint32_t count; };
    std::vector<CellRange> lib_cell_ranges;
    lib_cell_ranges.reserve(num_libs);

    uint32_t total_cells = 0;
    for (uint32_t li = 0; li < num_libs; ++li) {
        const auto& lib = db.library(li);
        uint32_t cell_count = static_cast<uint32_t>(lib.cells.size());
        lib_cell_ranges.push_back({total_cells, cell_count});
        total_cells += cell_count;

        FtlLibraryEntry le{};
        le.name_id = lib.name;
        le.time_unit = lib.units.time;
        le.cap_unit = lib.units.capacitance;
        le.res_unit = lib.units.resistance;
        le.volt_unit = lib.units.voltage;
        le.curr_unit = lib.units.current;
        le.leak_power_unit = lib.units.leakage_power;
        le.slew_lower = lib.units.slew_lower;
        le.slew_upper = lib.units.slew_upper;
        le.input_thresh_rise = lib.units.input_threshold_rise;
        le.input_thresh_fall = lib.units.input_threshold_fall;
        le.output_thresh_rise = lib.units.output_threshold_rise;
        le.output_thresh_fall = lib.units.output_threshold_fall;
        le.slew_derate = lib.units.slew_derate;
        le.cell_start_idx = lib_cell_ranges.back().start;
        le.cell_count = cell_count;
        le.default_max_transition = lib.default_max_transition;
        le.default_max_capacitance = lib.default_max_capacitance;
        le.default_max_fanout = lib.default_max_fanout;
        w.write(le);
        FtlLibraryPowerExt power_ext{};
        power_ext.time_unit_seconds = lib.units.time_unit_seconds;
        power_ext.capacitance_unit_farads = lib.units.capacitance_unit_farads;
        power_ext.voltage_unit_volts = lib.units.voltage_unit_volts;
        power_ext.leakage_power_unit_watts =
            lib.units.leakage_power_unit_watts;
        w.write(power_ext);
    }

    // ── Cell Data + Index ──
    // We write all cell data first, collecting offsets,
    // then write the index at the end.
    std::vector<FtlCellIndexEntry> cell_index;
    cell_index.reserve(total_cells);

    for (uint32_t li = 0; li < num_libs; ++li) {
        const auto& lib = db.library(li);
        uint32_t ncells = static_cast<uint32_t>(lib.cells.size());
        for (uint32_t ci = 0; ci < ncells; ++ci) {
            const auto& cell = lib.cells[ci];
            FtlCellIndexEntry cie{};
            cie.name_id = 0; // unused in linear-scan approach
            cie.cell_offset = w.size();
            cell_index.push_back(cie);

            // Cell header
            FtlCellHeader ch{};
            ch.name_id = cell.name;
            ch.area = cell.area;
            ch.num_pins = static_cast<uint32_t>(cell.pins.size());
            ch.num_arcs = static_cast<uint32_t>(cell.arcs.size());
            ch.num_pvt_points = static_cast<uint32_t>(cell.pvt_points.size());
            w.write(ch);

            // Extended cell header (v2+)
            FtlCellExtHeader ceh{};
            ceh.function_id = cell.function;
            ceh.footprint_id = cell.footprint;
            ceh.cell_leakage_power = cell.cell_leakage_power;
            ceh.dont_use = cell.dont_use ? 1 : 0;
            ceh.ff_clocked_on = cell.ff_clocked_on;
            ceh.ff_next_state = cell.ff_next_state;
            ceh.ff_clear = cell.ff_clear;
            ceh.ff_preset = cell.ff_preset;
            ceh.ff_enable = cell.ff_enable;
            ceh.max_capacitance = cell.max_capacitance;
            ceh.max_transition = cell.max_transition;
            ceh.max_fanout = cell.max_fanout;
            ceh.clock_gating_integrated_cell = cell.clock_gating_integrated_cell;
            ceh.ff_state = cell.ff_state;
            w.write(ceh);

            // Pins
            for (const auto& pin : cell.pins) {
                FtlPinHeader ph{};
                ph.name_id = pin.name;
                ph.capacitance = pin.capacitance;
                ph.is_clock = pin.is_clock ? 1 : 0;
                ph.direction = static_cast<uint8_t>(pin.direction);
                ph.num_arc_ids = static_cast<uint32_t>(pin.arc_ids.size());
                ph.miller_cap_rise = pin.miller_cap_rise;
                ph.miller_cap_fall = pin.miller_cap_fall;
                ph.related_pg_pin = pin.related_pg_pin;
                w.write(ph);

                // Extended pin header (v2+)
                FtlPinExtHeader peh{};
                peh.function_id = pin.function;
                peh.clear_id = pin.clear;
                peh.preset_id = pin.preset;
                peh.enable_id = pin.enable;
                peh.clock_gate_flags = (pin.clock_gate_clock_pin ? 1 : 0) |
                    (pin.clock_gate_enable_pin ? 2 : 0) |
                    (pin.clock_gate_test_pin ? 4 : 0) |
                    (pin.clock_gate_out_pin ? 8 : 0);
                w.write(peh);

                if (!pin.arc_ids.empty()) {
                    w.write_bytes(reinterpret_cast<const uint8_t*>(pin.arc_ids.data()),
                                  pin.arc_ids.size() * sizeof(uint32_t));
                }
                write_nldm(w, pin.receiver_capacitance1_rise);
                write_nldm(w, pin.receiver_capacitance1_fall);
                write_nldm(w, pin.receiver_capacitance2_rise);
                write_nldm(w, pin.receiver_capacitance2_fall);
                FtlReceiverCapacitanceHeader rch{};
                rch.num_groups =
                    static_cast<uint32_t>(pin.receiver_capacitance.size());
                w.write(rch);
                for (const auto& receiver : pin.receiver_capacitance) {
                    FtlReceiverCapacitanceGroupHeader rcgh{};
                    rcgh.when_id = receiver.when;
                    w.write(rcgh);
                    write_nldm(w, receiver.receiver_capacitance1_rise);
                    write_nldm(w, receiver.receiver_capacitance1_fall);
                    write_nldm(w, receiver.receiver_capacitance2_rise);
                    write_nldm(w, receiver.receiver_capacitance2_fall);
                }
                FtlPinPowerHeader pph{};
                pph.num_internal_power =
                    static_cast<uint32_t>(pin.internal_power.size());
                w.write(pph);
                for (const auto& power : pin.internal_power) {
                    FtlInternalPowerHeader iph{};
                    iph.related_pin = power.related_pin;
                    iph.related_pg_pin = power.related_pg_pin;
                    iph.when_id = power.when;
                    w.write(iph);
                    write_nldm(w, power.rise_power);
                    write_nldm(w, power.fall_power);
                }
            }

            // Arcs
            for (const auto& arc : cell.arcs) {
                FtlArcHeader ah{};
                ah.from_pin = arc.from_pin;
                ah.to_pin = arc.to_pin;
                ah.sense = static_cast<uint8_t>(arc.sense);
                ah.type = static_cast<uint8_t>(arc.type);
                ah.related_pin = arc.related_pin;
                w.write(ah);
                FtlArcExtHeader aeh{};
                aeh.when_id = arc.when;
                w.write(aeh);
                FtlArcMillerExt ameh{};
                ameh.miller_cap_rise = arc.miller_cap_rise;
                ameh.miller_cap_fall = arc.miller_cap_fall;
                w.write(ameh);

                write_nldm(w, arc.rise_delay);
                write_nldm(w, arc.fall_delay);
                write_nldm(w, arc.rise_output_slew);
                write_nldm(w, arc.fall_output_slew);
                write_nldm(w, arc.rise_constraint);
                write_nldm(w, arc.fall_constraint);
                write_nldm(w, arc.receiver_capacitance1_rise);
                write_nldm(w, arc.receiver_capacitance1_fall);
                write_nldm(w, arc.receiver_capacitance2_rise);
                write_nldm(w, arc.receiver_capacitance2_fall);
                write_csm(w, arc.csm_output_current_rise);
                write_csm(w, arc.csm_output_current_fall);
            }

            // PVT points
            for (const auto& pvt : cell.pvt_points) {
                w.write<float>(pvt.process);
                w.write<float>(pvt.voltage);
                w.write<float>(pvt.temperature);
            }
        }
    }

    // Cell index is kept in library order (global_idx -> cell_offset).
    // No sorting needed since cell_offset increases monotonically.
    // Cell index entries already have correct cell_offset from construction.
    // name_id is unused in current linear-scan approach.
    for (auto& cie : cell_index) {
        (void)cie;
    }

    // Write cell index
    uint64_t cell_index_offset = w.size();
    w.write<uint32_t>(static_cast<uint32_t>(cell_index.size()));
    for (const auto& cie : cell_index) {
        w.write(cie);
    }

    // v11 appends electrical metadata after the index. Earlier cell layouts
    // stay readable, and legacy caches use the historical unit-load default.
    for (uint32_t li = 0; li < num_libs; ++li) {
        const auto& lib = db.library(li);
        w.write<float>(lib.default_fanout_load);
        for (uint32_t ci = 0; ci < lib.cells.size(); ++ci)
            for (const auto& pin : lib.cells[ci].pins) w.write<float>(pin.fanout_load);
    }

    // ── Patch header ──
    for (uint32_t li = 0; li < num_libs; ++li) {
        const auto& lib = db.library(li);
        w.write<uint32_t>(lib.power_metadata_complete ? 1 : 0);
        for (uint32_t ci = 0; ci < lib.cells.size(); ++ci) {
            const auto& groups = lib.cells[ci].leakage_power;
            w.write<uint32_t>(uint32_t(groups.size()));
            for (const auto& group : groups) {
                w.write<float>(group.value);
                w.write<uint32_t>(group.when);
                w.write<uint32_t>(group.related_pg_pin);
            }
        }
    }
    // v13 retains per-pin electrical rules, independently of historical
    // cell-wide aggregates. Append metadata to keep older timing layouts readable.
    for (uint32_t li=0;li<num_libs;++li) {
        const auto& lib=db.library(li);
        w.write<uint32_t>(lib.electrical_metadata_complete ? 1 : 0);
        for (uint32_t ci=0;ci<lib.cells.size();++ci) for (const auto& pin:lib.cells[ci].pins) {
            w.write<float>(pin.max_transition);
            w.write<float>(pin.max_capacitance);
            w.write<float>(pin.max_fanout);
        }
    }
    // v14 preserves declaration provenance; table contents alone cannot
    // distinguish an absent edge from a declared but malformed table.
    for (uint32_t li=0;li<num_libs;++li) {
        const auto& lib=db.library(li);
        for (uint32_t ci=0;ci<lib.cells.size();++ci)
            for (const auto& arc:lib.cells[ci].arcs)
                w.write<uint32_t>(arc.constraint_transition_mask);
    }
    // v15 preserves both FF state variables without changing older layouts.
    for (uint32_t li=0;li<num_libs;++li) {
        const auto& lib=db.library(li);
        w.write<uint32_t>(lib.sequential_metadata_complete ? 1 : 0);
        for (uint32_t ci=0;ci<lib.cells.size();++ci)
            w.write<uint32_t>(lib.cells[ci].ff_state_neg);
    }
    // v16 retains static rise/fall pin capacitance and its early/late bounds.
    for (uint32_t li=0;li<num_libs;++li) {
        const auto& lib=db.library(li);
        for (uint32_t ci=0;ci<lib.cells.size();++ci) for (const auto& pin:lib.cells[ci].pins) {
            w.write<float>(pin.rise_capacitance); w.write<float>(pin.fall_capacitance);
            w.write<float>(pin.rise_capacitance_lower); w.write<float>(pin.rise_capacitance_upper);
            w.write<float>(pin.fall_capacitance_lower); w.write<float>(pin.fall_capacitance_upper);
        }
    }
    // CCSN model data: ownership follows the existing pin/arc ordering.
    for (uint32_t li=0; li<num_libs; ++li) {
        const auto& lib = db.library(li);
        write_ccsn_nodes(w, lib.ccsn_templates);
        for (uint32_t ci=0; ci<lib.cells.size(); ++ci) {
            for (const auto& pin : lib.cells[ci].pins) write_ccsn_nodes(w, pin.ccsn_stages);
            for (const auto& arc : lib.cells[ci].arcs) write_ccsn_nodes(w, arc.ccsn_stages);
        }
    }
    FtlHeader h{};
    std::memcpy(h.magic, FTL_MAGIC, 8);
    h.version = FTL_VERSION;
    h.flags = compress ? FTL_FLAG_COMPRESSED : 0;
    h.uncompressed_size = w.size();
    h.string_pool_offset = sp_offset;
    h.string_pool_size = sp_size;
    h.num_libraries = num_libs;
    h.library_dir_offset = lib_dir_offset;
    h.num_cells_total = total_cells;
    h.cell_index_offset = cell_index_offset;

    std::memcpy(w.data() + header_pos, &h, sizeof(h));

    // ── Write / compress ──
    if (compress) {
        try {
            auto compressed = compress_gzip(w.data(), w.size());
            out.write(reinterpret_cast<const char*>(compressed.data()), compressed.size());
        } catch (const std::exception& e) {
            std::cerr << "liberty_binary: compression failed: " << e.what() << "\n";
            return false;
        }
    } else {
        out.write(reinterpret_cast<const char*>(w.data()), w.size());
    }

    return out.good();
}

} // anonymous namespace

// ────────────────────────────────────────────────────────────
// Public API: save
// ────────────────────────────────────────────────────────────

bool save_liberty_binary(const ec::LibertyDB& db,
                         const ec::StringPool& pool,
                         std::ostream& out,
                         bool compress) {
    return save_liberty_binary_impl(db, pool, out, compress);
}

// ────────────────────────────────────────────────────────────
// Public API: load
// ────────────────────────────────────────────────────────────

bool load_liberty_binary(const std::string& filepath,
                         ec::LibertyDB& db,
                         ec::StringPool& pool) {
    if (!is_little_endian()) {
        std::cerr << "liberty_binary: big-endian platforms not supported\n";
        return false;
    }

    // Read entire file
    std::ifstream file(filepath, std::ios::binary | std::ios::ate);
    if (!file) {
        std::cerr << "liberty_binary: cannot open " << filepath << "\n";
        return false;
    }
    auto file_size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> raw(file_size);
    file.read(reinterpret_cast<char*>(raw.data()), file_size);
    if (!file) {
        std::cerr << "liberty_binary: failed to read " << filepath << "\n";
        return false;
    }

    // Detect gzip
    std::vector<uint8_t> buf;
    if (is_gzip_data(raw.data(), raw.size())) {
        try {
            buf = decompress_gzip(raw.data(), raw.size());
        } catch (const std::exception& e) {
            std::cerr << "liberty_binary: decompression failed: " << e.what() << "\n";
            return false;
        }
    } else {
        buf = std::move(raw);
    }

    if (buf.size() < sizeof(FtlHeader)) {
        std::cerr << "liberty_binary: file too small\n";
        return false;
    }

    BufReader r(buf.data(), buf.size());
    FtlHeader h = r.read<FtlHeader>();

    if (std::memcmp(h.magic, FTL_MAGIC, 8) != 0) {
        std::cerr << "liberty_binary: bad magic\n";
        return false;
    }
    if (h.version != FTL_VERSION) {
        std::cerr << "liberty_binary: unsupported version " << h.version << "\n";
        return false;
    }
    bool v2_or_later = true;
    bool v3_or_later = true;
    bool v4_or_later = true;
    const bool v6_or_later = h.version >= 6;
    const bool v7_or_later = h.version >= 7;
    const bool v8_or_later = h.version >= 8;
    const bool v9_or_later = h.version >= 9;

    // ── String Pool ──
    r.seek(static_cast<size_t>(h.string_pool_offset));
    std::vector<uint32_t> id_remap = read_string_pool(r, pool);

    // ── Library Directory ──
    r.seek(static_cast<size_t>(h.library_dir_offset));
    uint32_t num_libs = r.read<uint32_t>();

    struct LibInfo {
        FtlLibraryEntry entry;
        uint32_t library_index;
    };
    std::vector<LibInfo> libs;
    libs.reserve(num_libs);

    for (uint32_t i = 0; i < num_libs; ++i) {
        FtlLibraryEntry le = r.read<FtlLibraryEntry>();
        FtlLibraryPowerExt power_ext{};
        if (v6_or_later) power_ext = r.read<FtlLibraryPowerExt>();
        const auto library_index = static_cast<uint32_t>(db.library_count());
        auto& lib = db.create_library();
        lib.name = remap_id(le.name_id, id_remap);
        lib.units.time = le.time_unit;
        lib.units.capacitance = le.cap_unit;
        lib.units.resistance = le.res_unit;
        lib.units.voltage = le.volt_unit;
        lib.units.current = le.curr_unit;
        lib.units.leakage_power = le.leak_power_unit;
        lib.units.slew_lower = le.slew_lower;
        lib.units.slew_upper = le.slew_upper;
        lib.units.input_threshold_rise = le.input_thresh_rise;
        lib.units.input_threshold_fall = le.input_thresh_fall;
        lib.units.output_threshold_rise = le.output_thresh_rise;
        lib.units.output_threshold_fall = le.output_thresh_fall;
        lib.units.slew_derate = le.slew_derate;
        if (v6_or_later) {
            lib.units.time_unit_seconds = power_ext.time_unit_seconds;
            lib.units.capacitance_unit_farads =
                power_ext.capacitance_unit_farads;
            lib.units.voltage_unit_volts = power_ext.voltage_unit_volts;
            lib.units.leakage_power_unit_watts =
                power_ext.leakage_power_unit_watts;
        }
        if (v3_or_later) {
            lib.default_max_transition = le.default_max_transition;
            lib.default_max_capacitance = le.default_max_capacitance;
            lib.default_max_fanout = le.default_max_fanout;
        }
        // create_library can relocate the DB's library vector. Retain an
        // index rather than a pointer into an earlier vector allocation.
        libs.push_back({le, library_index});
    }

    // ── Cell Index (read but we don't strictly need it for linear load) ──
    r.seek(static_cast<size_t>(h.cell_index_offset));
    uint32_t index_count = r.read<uint32_t>();
    std::vector<FtlCellIndexEntry> cell_index;
    cell_index.reserve(index_count);
    for (uint32_t i = 0; i < index_count; ++i) {
        cell_index.push_back(r.read<FtlCellIndexEntry>());
    }

    // Build a name -> cell_offset map for fast lookup (optional optimization)
    // For now, linear scan is fine. We'll build the map from cell_index entries.
    // But cell_index contains offsets, not name_ids. We need to know which
    // cell each offset refers to. We'll just read cells sequentially.

    // ── Read cells sequentially ──
    for (uint32_t li = 0; li < num_libs; ++li) {
        const auto& le = libs[li].entry;
        auto& lib = db.library(libs[li].library_index);

        for (uint32_t ci = 0; ci < le.cell_count; ++ci) {
            // Find the offset for this cell from cell_index
            uint32_t global_idx = le.cell_start_idx + ci;
            if (global_idx >= cell_index.size()) {
                std::cerr << "liberty_binary: cell index out of range\n";
                return false;
            }
            r.seek(static_cast<size_t>(cell_index[global_idx].cell_offset));

            FtlCellHeader ch = r.read<FtlCellHeader>();
            ec::LibertyCellHandle cell_id{lib.cells.emplace(remap_id(ch.name_id, id_remap))};
            auto& cell = lib.cells[cell_id.id];
            cell.area = ch.area;
            cell.pvt_points.resize(ch.num_pvt_points);

            // Extended cell header (v2+)
            if (v2_or_later) {
                FtlCellExtHeader ceh = r.read<FtlCellExtHeader>();
                cell.function = remap_id(ceh.function_id, id_remap);
                cell.footprint = remap_id(ceh.footprint_id, id_remap);
                cell.cell_leakage_power = ceh.cell_leakage_power;
                cell.dont_use = (ceh.dont_use != 0);
                cell.ff_clocked_on = remap_id(ceh.ff_clocked_on, id_remap);
                cell.ff_next_state = remap_id(ceh.ff_next_state, id_remap);
                cell.ff_clear = remap_id(ceh.ff_clear, id_remap);
                cell.ff_preset = remap_id(ceh.ff_preset, id_remap);
                cell.ff_enable = remap_id(ceh.ff_enable, id_remap);
                cell.clock_gating_integrated_cell =
                    remap_id(ceh.clock_gating_integrated_cell, id_remap);
                cell.ff_state = remap_id(ceh.ff_state, id_remap);
                if (v3_or_later) {
                    cell.max_capacitance = ceh.max_capacitance;
                    cell.max_transition = ceh.max_transition;
                    cell.max_fanout = ceh.max_fanout;
                }
            }

            // Pins
            cell.pins.resize(ch.num_pins);
            for (uint32_t pi = 0; pi < ch.num_pins; ++pi) {
                FtlPinHeader ph = r.read<FtlPinHeader>();
                auto& pin = cell.pins[pi];
                pin.name = remap_id(ph.name_id, id_remap);
                pin.capacitance = ph.capacitance;
                pin.is_clock = (ph.is_clock != 0);
                pin.direction = static_cast<ec::PortDirection>(ph.direction);
                pin.miller_cap_rise = ph.miller_cap_rise;
                pin.miller_cap_fall = ph.miller_cap_fall;
                pin.related_pg_pin = remap_id(ph.related_pg_pin, id_remap);

                // Extended pin header (v2+)
                if (v2_or_later) {
                    FtlPinExtHeader peh = r.read<FtlPinExtHeader>();
                    pin.function = remap_id(peh.function_id, id_remap);
                    pin.clear = remap_id(peh.clear_id, id_remap);
                    pin.preset = remap_id(peh.preset_id, id_remap);
                    pin.enable = remap_id(peh.enable_id, id_remap);
                    pin.clock_gate_clock_pin = (peh.clock_gate_flags & 1) != 0;
                    pin.clock_gate_enable_pin = (peh.clock_gate_flags & 2) != 0;
                    pin.clock_gate_test_pin = (peh.clock_gate_flags & 4) != 0;
                    pin.clock_gate_out_pin = (peh.clock_gate_flags & 8) != 0;
                }

                if (ph.num_arc_ids > 0) {
                    pin.arc_ids.resize(ph.num_arc_ids);
                    r.read_bytes(reinterpret_cast<uint8_t*>(pin.arc_ids.data()),
                                 ph.num_arc_ids * sizeof(uint32_t));
                }
                read_nldm(r, pin.receiver_capacitance1_rise);
                read_nldm(r, pin.receiver_capacitance1_fall);
                read_nldm(r, pin.receiver_capacitance2_rise);
                read_nldm(r, pin.receiver_capacitance2_fall);
                if (v7_or_later) {
                    const auto rch = r.read<FtlReceiverCapacitanceHeader>();
                    pin.receiver_capacitance.resize(rch.num_groups);
                    for (auto& receiver : pin.receiver_capacitance) {
                        const auto rcgh =
                            r.read<FtlReceiverCapacitanceGroupHeader>();
                        receiver.when = remap_id(rcgh.when_id, id_remap);
                        read_nldm(r, receiver.receiver_capacitance1_rise);
                        read_nldm(r, receiver.receiver_capacitance1_fall);
                        read_nldm(r, receiver.receiver_capacitance2_rise);
                        read_nldm(r, receiver.receiver_capacitance2_fall);
                    }
                }
                if (v6_or_later) {
                    const auto pph = r.read<FtlPinPowerHeader>();
                    pin.internal_power.resize(pph.num_internal_power);
                    for (auto& power : pin.internal_power) {
                        const auto iph = r.read<FtlInternalPowerHeader>();
                        power.related_pin = remap_id(iph.related_pin, id_remap);
                        power.related_pg_pin =
                            remap_id(iph.related_pg_pin, id_remap);
                        power.when = remap_id(iph.when_id, id_remap);
                        read_nldm(r, power.rise_power);
                        read_nldm(r, power.fall_power);
                    }
                }
            }

            // Arcs
            cell.arcs.resize(ch.num_arcs);
            for (uint32_t ai = 0; ai < ch.num_arcs; ++ai) {
                FtlArcHeader ah = r.read<FtlArcHeader>();
                auto& arc = cell.arcs[ai];
                arc.from_pin = remap_id(ah.from_pin, id_remap);
                arc.to_pin = remap_id(ah.to_pin, id_remap);
                arc.sense = static_cast<ec::LibertyTimingSense>(ah.sense);
                arc.type = static_cast<ec::LibertyTimingType>(ah.type);
                arc.related_pin = remap_id(ah.related_pin, id_remap);
                if (v4_or_later) {
                    FtlArcExtHeader aeh = r.read<FtlArcExtHeader>();
                    arc.when = remap_id(aeh.when_id, id_remap);
                }
                if (v9_or_later) {
                    const FtlArcMillerExt ameh = r.read<FtlArcMillerExt>();
                    arc.miller_cap_rise = ameh.miller_cap_rise;
                    arc.miller_cap_fall = ameh.miller_cap_fall;
                }

                read_nldm(r, arc.rise_delay);
                read_nldm(r, arc.fall_delay);
                read_nldm(r, arc.rise_output_slew);
                read_nldm(r, arc.fall_output_slew);
                read_nldm(r, arc.rise_constraint);
                read_nldm(r, arc.fall_constraint);
                // Old writers collapsed unrecognized check types to combinational.
                // Preserve load compatibility, but never propagate a constraint
                // table as a delay arc or pretend its exact check type is known.
                if (h.version < 10 && arc.type == ec::LibertyTimingType::Combinational &&
                    (arc.rise_constraint.rows || arc.fall_constraint.rows))
                    arc.type = ec::LibertyTimingType::Unknown;
                if (v8_or_later) {
                    read_nldm(r, arc.receiver_capacitance1_rise);
                    read_nldm(r, arc.receiver_capacitance1_fall);
                    read_nldm(r, arc.receiver_capacitance2_rise);
                    read_nldm(r, arc.receiver_capacitance2_fall);
                }
                read_csm(r, arc.csm_output_current_rise, v9_or_later);
                read_csm(r, arc.csm_output_current_fall, v9_or_later);
            }

            // PVT points
            if (ch.num_pvt_points > 0) {
                r.read_bytes(reinterpret_cast<uint8_t*>(cell.pvt_points.data()),
                             ch.num_pvt_points * sizeof(ec::PvtPoint));
            }
        }
    }

    if (h.version >= 11) {
        r.seek(static_cast<size_t>(h.cell_index_offset) + sizeof(uint32_t) +
               cell_index.size() * sizeof(FtlCellIndexEntry));
        for (auto& info : libs) {
            auto& lib = db.library(info.library_index);
            lib.default_fanout_load = r.read<float>();
            for (uint32_t ci = 0; ci < lib.cells.size(); ++ci)
                for (auto& pin : lib.cells[ci].pins) pin.fanout_load = r.read<float>();
        }
    }
    if (h.version >= 12) {
        for (auto& info : libs) {
        auto& lib=db.library(info.library_index);
        lib.power_metadata_complete=r.read<uint32_t>()!=0;
        for (uint32_t ci=0;ci<lib.cells.size();++ci) {
            auto& groups=lib.cells[ci].leakage_power;
            const auto count=r.read<uint32_t>();
            if (count>1000000) return false;
            groups.resize(count);
            for (auto& group : groups) {
                group.value=r.read<float>();
                group.when=r.read<uint32_t>();
                group.related_pg_pin=r.read<uint32_t>();
            }
        }
        }
    }
    if (h.version<12) for (auto& info : libs) db.library(info.library_index).power_metadata_complete=false;
    if (h.version>=13) {
        for (auto& info:libs) {
            auto& lib=db.library(info.library_index);
            lib.electrical_metadata_complete=r.read<uint32_t>()!=0;
            for (uint32_t ci=0;ci<lib.cells.size();++ci) for (auto& pin:lib.cells[ci].pins) {
                pin.max_transition=r.read<float>();
                pin.max_capacitance=r.read<float>();
                pin.max_fanout=r.read<float>();
            }
        }
    } else for (auto& info:libs) db.library(info.library_index).electrical_metadata_complete=false;
    if (h.version>=14) {
        for (auto& info:libs) {
            auto& lib=db.library(info.library_index);
            for (uint32_t ci=0;ci<lib.cells.size();++ci) for (auto& arc:lib.cells[ci].arcs) {
                const auto mask=r.read<uint32_t>();
                if (mask>3) return false;
                arc.constraint_transition_mask=static_cast<uint8_t>(mask);
            }
        }
    } // Older formats retain mask=0 and conservatively require both edges.
    for (auto& info:libs) {
        auto& lib=db.library(info.library_index);
        lib.sequential_metadata_complete=h.version>=15 && r.read<uint32_t>()!=0;
        if (h.version>=15) for (uint32_t ci=0;ci<lib.cells.size();++ci)
            lib.cells[ci].ff_state_neg=remap_id(r.read<uint32_t>(),id_remap);
    }
    if (h.version>=16) for (auto& info:libs) {
        auto& lib=db.library(info.library_index);
        for (uint32_t ci=0;ci<lib.cells.size();++ci) for (auto& pin:lib.cells[ci].pins) {
            pin.rise_capacitance=r.read<float>(); pin.fall_capacitance=r.read<float>();
            pin.rise_capacitance_lower=r.read<float>(); pin.rise_capacitance_upper=r.read<float>();
            pin.fall_capacitance_lower=r.read<float>(); pin.fall_capacitance_upper=r.read<float>();
        }
    }
    for (auto& info : libs) {
        auto& lib = db.library(info.library_index);
        read_ccsn_nodes(r, lib.ccsn_templates);
        for (uint32_t ci=0; ci<lib.cells.size(); ++ci) {
            for (auto& pin : lib.cells[ci].pins) read_ccsn_nodes(r, pin.ccsn_stages);
            for (auto& arc : lib.cells[ci].arcs) read_ccsn_nodes(r, arc.ccsn_stages);
        }
    }
    return true;
}

bool save_core_liberty_binary(const ec::LibertyDB& db,
                              const ec::StringPool& pool,
                              std::ostream& out,
                              bool compress) {
    return save_liberty_binary(db, pool, out, compress);
}

bool load_core_liberty_binary(const std::string& filepath,
                              ec::LibertyDB& db,
                              ec::StringPool& pool) {
    return load_liberty_binary(filepath, db, pool);
}

bool read_core_liberty_file(const std::string& filepath,
                            ec::LibertyDB& db,
                            ec::StringPool& pool) {
    detail::reject_experimental_db_input(filepath);
    auto ext = std::filesystem::path(filepath).extension();
    bool is_binary = (ext == ".ftlib" || filepath.find(".ftlib.gz") != std::string::npos);
    // A rejected binary is not Liberty text (in particular, an old cache must
    // not report success with an empty library after a schema upgrade).
    if (is_binary) return load_core_liberty_binary(filepath, db, pool);

    std::ifstream infile(filepath);
    if (!infile) return false;
    std::ostringstream ss;
    ss << infile.rdbuf();
    std::string content = ss.str();
    parser::LibertyParser parser(content);
    parser.parse(db, pool);
    return true;
}

} // namespace te
