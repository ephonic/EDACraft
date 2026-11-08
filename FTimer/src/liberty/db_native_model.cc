#include "db_native_model.hh"
#include "../parser/liberty_parser.hh"
#include <zlib.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <type_traits>
#include <utility>
#include <vector>

namespace edacraft::core::native::detail {
namespace {
[[noreturn]] void fail(const std::string& s) { throw std::runtime_error(s); }
void require(bool ok, const std::string& s) { if (!ok) fail(s); }

struct Cursor {
    const std::string& bytes;
    size_t pos = 0;
    std::map<uint32_t, std::string> symbols{{0, ""}};
    void need(size_t n) const {
        require(pos <= bytes.size() && n <= bytes.size() - pos,
                "truncated object at byte " + std::to_string(pos));
    }
    int64_t integer() {
        uint32_t result = 0;
        unsigned shift = 0; bool negative = false;
        for (unsigned k = 0; k < 5; ++k) {
            need(1); const auto b = static_cast<unsigned char>(bytes[pos++]);
            require(k != 4 || b < 32, "overflowed object integer");
            // The second byte carries the sign in bit 6. Its six data bits
            // shift all later groups by one relative to unsigned LEB128.
            if (k == 1) negative = (b & 64) != 0;
            result |= uint32_t(b & (k == 1 ? 63 : 127)) << shift;
            shift += k == 1 ? 6 : 7;
            if (!(b & 128)) return negative ? -int64_t(result) : int64_t(result);
        }
        fail("unterminated object integer");
    }
    std::string string() {
        const auto id = integer();
        auto it = symbols.find(id);
        if (it != symbols.end()) return it->second;
        require(id == symbols.size(), "nonsequential interned-string definition");
        const auto len = integer(); need(len);
        auto s = bytes.substr(pos, len); pos += len;
        require(s.find('\0') == std::string::npos, "NUL in object string");
        symbols.emplace(id, s); return s;
    }
    float real() {
        need(4); uint32_t b = 0;
        for (int k = 0; k < 4; ++k) b = (b << 8) | static_cast<unsigned char>(bytes[pos++]);
        float value; std::memcpy(&value, &b, 4);
        require(std::isfinite(value), "nonfinite object float"); return value;
    }
    void finish() {
        // The object serializer appends one checksum word in addition to the
        // enclosing gzip CRC. Its algorithm is not inferred from a byte scan.
        integer(); require(pos == bytes.size(), "unparsed object trailer");
    }
};

struct Part {
    std::string name;
    int64_t owner = 0, size = 0;
    std::map<std::string, std::string> properties;
    std::vector<Part> children;
    size_t offset = 0;
};
Part directory(Cursor& c, size_t depth, size_t& count) {
    require(depth < 64 && ++count < 1000000, "directory limits exceeded");
    Part p; p.name = c.string(); require(!p.name.empty(), "empty directory entry");
    p.owner = c.integer(); p.size = c.integer();
    require(p.owner >= 0 && (p.size == -1 || p.size > 0), "invalid directory owner/size");
    while (true) {
        c.need(1); if (c.bytes[c.pos] == 0) { ++c.pos; break; }
        auto key = c.string(); auto value = c.string();
        require(p.properties.emplace(key, value).second, "duplicate directory property");
    }
    while (true) {
        c.need(1); if (c.bytes[c.pos] == 0) { ++c.pos; break; }
        p.children.push_back(directory(c, depth + 1, count));
    }
    return p;
}

bool inflate_member(const std::string& file, size_t offset, std::string& out, size_t& used) {
    z_stream z{}; if (inflateInit2(&z, 31) != Z_OK) fail("cannot initialize gzip reader");
    struct End { z_stream* z; ~End() { inflateEnd(z); } } end{&z};
    out.clear(); unsigned char buf[65536]; size_t pos = offset;
    while (pos < file.size()) {
        const size_t n = std::min<size_t>(file.size() - pos, 1u << 20);
        z.next_in = reinterpret_cast<Bytef*>(const_cast<char*>(file.data() + pos));
        z.avail_in = static_cast<uInt>(n);
        do {
            const auto before = z.avail_in;
            z.next_out = buf; z.avail_out = sizeof(buf);
            const int rc = inflate(&z, Z_NO_FLUSH);
            const size_t produced = sizeof(buf) - z.avail_out;
            require(out.size() + produced <= (256u << 20), "gzip object exceeds 256 MiB limit");
            out.append(reinterpret_cast<char*>(buf), produced);
            if (rc == Z_STREAM_END) { used = pos + n - z.avail_in - offset; return true; }
            if (rc != Z_OK && rc != Z_BUF_ERROR) return false;
            if (!produced && before == z.avail_in) return false;
        } while (z.avail_in || z.avail_out == 0);
        pos += n;
    }
    return false;
}

struct Value {
    uint32_t type = 0;
    double number = 0;
    std::string text;
};
struct Object {
    uint32_t id = 0, type = 0;
    std::string name;
    std::map<std::string, Value> attrs;
    std::map<std::string, std::vector<uint32_t>> refs;
};
struct Schema {
    std::vector<std::pair<uint32_t, std::string>> fields;
    std::vector<std::string> refs;
    std::map<uint32_t, std::pair<uint32_t, std::string>> attrs;
    std::map<uint32_t, std::string> pointers;
};
struct Graph {
    std::shared_ptr<const std::string> storage;
    Cursor c;
    std::map<uint32_t, Schema> schemas;
    std::map<uint32_t, Object> objects;
    explicit Graph(std::string data) : storage(std::make_shared<const std::string>(std::move(data))), c{*storage} {
        // Serializer preamble observed in both the 2016 and 2024 writers.
        // Other preambles require an explicit decoder, not offset guessing.
        static const unsigned char prefix[] = {1,1,1,9,8,3,0x36,0x20,0xb8,1,8};
        c.need(sizeof(prefix));
        require(std::memcmp(c.bytes.data(), prefix, sizeof(prefix)) == 0,
                "unsupported native object serializer preamble");
        c.pos = sizeof(prefix);
        require(read_object(0) == 1, "missing root object"); c.finish();
    }
    Value value(uint32_t t) {
        Value v; v.type = t;
        if (t <= 2) v.number = c.integer();
        else if (t == 3) v.number = c.real();
        else if (t == 5) v.text = c.string();
        else if (t == 7) {
            auto n = c.integer(); require(n >= 0,"negative byte-array length"); c.need(n); v.text = c.bytes.substr(c.pos, n); c.pos += n;
        } else fail("unsupported scalar type " + std::to_string(t));
        return v;
    }
    std::vector<uint32_t> references(size_t depth) {
        std::vector<uint32_t> result;
        while (auto id = read_object(depth + 1)) result.push_back(id);
        return result;
    }
    uint32_t read_object(size_t depth) {
        require(depth < 256, "object recursion limit exceeded");
        const auto id = c.integer(); if (!id || objects.count(id)) return id;
        require(id == objects.size() + 1 && objects.size() < 1000000,
                "invalid object definition ID");
        const auto type = c.integer();
        if (!schemas.count(type)) {
            auto& s = schemas[type];
            auto n = c.integer(); require(n >= 0 && n < 4096, "invalid field count");
            while (n--) { auto t = c.integer(); auto name = c.string(); s.fields.emplace_back(t, name); }
            n = c.integer(); require(n >= 0 && n < 4096, "invalid reference field count");
            while (n--) s.refs.push_back(c.string());
        }
        auto& s = schemas.at(type);
        Object o; o.id = id; o.type = type; o.name = c.string();
        auto& obj = objects.emplace(id, std::move(o)).first->second;
        for (const auto& f : s.fields) obj.attrs.emplace(f.second, value(f.first));
        for (const auto& name : s.refs) obj.refs.emplace(name, references(depth));
        while (auto attr = c.integer()) {
            if (attr < 0) {
                const auto key = uint32_t(-attr);
                if (!s.pointers.count(key)) s.pointers.emplace(key, c.string());
                const auto name = s.pointers.at(key);
                require(!obj.refs.count(name), "duplicate object reference field " + name);
                obj.refs.emplace(name, references(depth));
            } else {
                if (!s.attrs.count(attr)) { auto t = c.integer(); auto name = c.string(); s.attrs.emplace(attr, std::make_pair(t, name)); }
                const auto& f = s.attrs.at(attr);
                require(!obj.attrs.count(f.second), "duplicate object attribute " + f.second);
                obj.attrs.emplace(f.second, value(f.first));
            }
        }
        return id;
    }
    std::vector<const Object*> edge(const std::string& name) const {
        std::vector<const Object*> result;
        for (const auto& [id, o] : objects) {
            auto it = o.refs.find(name);
            if (it != o.refs.end()) for (auto i : it->second) result.push_back(&objects.at(i));
        }
        return result;
    }
};

const Value* attr(const Object& o, const std::string& name) {
    auto it = o.attrs.find(name); return it == o.attrs.end() ? nullptr : &it->second;
}
std::string text(const Object& o, const std::string& name, const std::string& fallback = "") {
    const auto v = attr(o, name); if (!v) return fallback;
    require(v->type == 5, "expected string attribute " + name); return v->text;
}
double number(const Object& o, const std::string& name, double fallback = 0) {
    const auto v = attr(o, name); if (!v) return fallback;
    require(v->type <= 3, "expected numeric attribute " + name); return v->number;
}
std::vector<double> array(const Object& o, const std::string& name) {
    const auto v = attr(o, name); require(v && v->type == 7, "missing array " + name);
    Cursor r{v->text}; const auto type = r.integer(), count = r.integer();
    require(count >= 0 && count < 10000000 && (type == 2 || type == 3), "unsupported array " + name);
    std::vector<double> result; result.reserve(count);
    for (uint32_t i = 0; i < count; ++i) result.push_back(type == 3 ? r.real() : double(r.integer()));
    require(r.pos == v->text.size(), "array size mismatch " + name);
    if (attr(o, name + "_size")) require(number(o, name + "_size") == count, "array count mismatch " + name);
    return result;
}
std::string quote(const std::string& s) {
    std::string out = "\"";
    for (unsigned char c : s) {
        require(c >= 32 && c != 127, "control character in semantic string");
        if (c == '"' || c == '\\') out += '\\';
        out += char(c);
    }
    return out + '"';
}
std::string real(double v) {
    std::ostringstream s; s << std::setprecision(std::numeric_limits<float>::max_digits10) << v; return s.str();
}
std::string numbers(const std::vector<double>& v) {
    std::string s; for (auto n : v) { if (!s.empty()) s += ','; s += real(n); } return quote(s);
}
void scalars(std::ostream& s, const Object& o, std::initializer_list<const char*> names) {
    for (const auto name : names) if (const auto v = attr(o, name)) {
        require(v->type <= 3 || v->type == 5, "unsupported semantic attribute " + std::string(name));
        s << name << ':' << (v->type == 5 ? quote(v->text) : v->type == 0 ? (v->number ? "true" : "false") : real(v->number)) << ';';
    }
}
const Part* child(const Part& p, const std::string& name) {
    const Part* result = nullptr;
    for (const auto& c : p.children) if (c.name == name) { require(!result, "duplicate part " + name); result = &c; }
    return result;
}
std::string decode_part(const std::string& file, const Part& p) {
    std::string out; size_t used = 0;
    require(inflate_member(file, p.offset, out, used) && used == p.size,
            "invalid compressed part " + p.name); return out;
}

struct Template {
    std::vector<double> x, y;
};
using Templates = std::map<std::string, Template>;
void emit_template(std::ostream& out, const std::string& kind, const Object& o, Templates& ts) {
    Template t;
    out << kind << '(' << quote(o.name) << "){";
    for (const char* n : {"variable_1", "variable_2", "variable_3"}) if (attr(o,n)) {
        const auto v = text(o,n);
        require(!v.empty() && std::all_of(v.begin(),v.end(),[](unsigned char c) {
            return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_';
        }), "unsupported template variable");
        out << n << ':' << v << ';';
    }
    if (attr(o, "index_1")) { t.x = array(o, "index_1"); out << "index_1(" << numbers(t.x) << ");"; }
    if (attr(o, "index_2")) { t.y = array(o, "index_2"); out << "index_2(" << numbers(t.y) << ");"; }
    require(ts.emplace(kind + ':' + o.name, t).second, "duplicate template " + o.name);
    out << '}';
}

void table(std::ostream& out, const Graph& g, const Object& o, const std::string& kind,
           const Templates& templates, const std::string& family, size_t depth = 0) {
    require(depth < 8, "nested timing table limit exceeded");
    const auto tmpl = text(o, "template");
    const auto found = templates.find(family + ':' + tmpl);
    require(tmpl.empty() || found != templates.end(), "unresolved table template " + tmpl);
    out << kind << '(' << (tmpl.empty() ? "" : quote(tmpl)) << "){";
    scalars(out, o, {"reference_time"});
    for (const char* n : {"index_1", "index_2", "index_3"}) if (attr(o, n)) out << n << '(' << numbers(array(o, n)) << ");";
    if (attr(o, "values")) {
        const auto v = array(o, "values");
        size_t rows = 1, cols = 1;
        if (kind == "vector") {
            require(array(o, "index_1").size() == 1 && array(o, "index_2").size() == 1,
                    "CCS vector requires scalar slew and load");
            require(array(o, "index_3").size() == v.size(), "CCS time/current size mismatch");
            cols = v.size();
        } else {
            auto x = attr(o, "index_1") ? array(o, "index_1") : found != templates.end() ? found->second.x : std::vector<double>{};
            auto y = attr(o, "index_2") ? array(o, "index_2") : found != templates.end() ? found->second.y : std::vector<double>{};
            rows = std::max<size_t>(1, x.size()); cols = std::max<size_t>(1, y.size());
        }
        require(rows && cols && rows <= v.size() && rows * cols == v.size(), "table shape mismatch " + kind);
        out << "values(";
        for (size_t row = 0; row < rows; ++row) {
            if (row) out << ',';
            out << numbers(std::vector<double>(v.begin() + row * cols, v.begin() + (row + 1) * cols));
        }
        out << ");";
    }
    for (const auto& [name, ids] : o.refs) {
        require(name == "vector", "unsupported table reference " + name);
        for (auto id : ids) table(out, g, g.objects.at(id), name, templates, family, depth + 1);
    }
    out << '}';
}

// These are format enum values, verified with independent compiled fixtures.
const char* timing_type(unsigned n) {
    switch (n) {
        case 0: return "combinational";
        case 4: return "hold_rising"; case 5: return "hold_falling";
        case 6: return "setup_rising"; case 7: return "setup_falling";
        case 8: return "rising_edge"; case 9: return "falling_edge";
        default: fail("unsupported timing_type enum " + std::to_string(n));
    }
}

struct CellParts {
    std::string name;
    std::map<std::string, Graph> graphs;
    explicit CellParts(const std::string& file, const Part& p) : name(p.name) {
        static const std::set<std::string> supported = {
            "cell_content", "pin_content", "timing_content", "function", "generic_netlist",
            "nldm_timing", "nlpm_power", "ccs_timing"
        };
        for (const auto& part : p.children) {
            require(supported.count(part.name) && part.children.empty(), "unsupported cell part " + part.name);
            auto bytes = decode_part(file, part);
            graphs.emplace(part.name, Graph(std::move(bytes)));
        }
    }
    const Graph& get(const std::string& n) const {
        const auto it = graphs.find(n); require(it != graphs.end(), "missing cell part " + n); return it->second;
    }
};

void emit_cell(std::ostream& out, const CellParts& cell, const Templates& templates,
               const Graph& skeleton, const Object& skeleton_cell) {
    const auto& cg = cell.get("cell_content");
    const Object* co = nullptr;
    for (const auto& [id, o] : cg.objects) if (o.type == 18 && o.name == cell.name) { require(!co, "ambiguous cell object"); co = &o; }
    require(co, "cell object/name mismatch " + cell.name);
    require(number(*co,"area") == number(skeleton_cell,"area"), "skeleton/cell area mismatch");
    require(cg.edge("leakage_power").empty(), "conditional leakage groups require a native decoder");
    out << "cell(" << quote(cell.name) << "){";
    scalars(out, *co, {"area", "cell_footprint", "cell_leakage_power", "dont_use", "don_t_use",
                      "max_capacitance", "max_transition", "max_fanout", "clock_gating_integrated_cell"});
    const auto& pg = cell.get("pin_content");
    for (const auto name : {"receiver_capacitance", "pg_pin", "ccsn_first_stage", "ccsn_last_stage"})
        require(pg.edge(name).empty(), "unsupported pin semantic group " + std::string(name));
    auto pins = pg.edge("ports");
    require(!pins.empty(), "cell has no pins " + cell.name);
    const auto skpins = skeleton_cell.refs.find("ports");
    require(skpins != skeleton_cell.refs.end() && skpins->second.size() == pins.size(), "skeleton pin count mismatch");
    for (size_t i=0;i<pins.size();++i) {
        const auto& original = skeleton.objects.at(skpins->second[i]);
        require(original.name == pins[i]->name && number(original,"direction") == number(*pins[i],"direction") &&
                number(original,"capacitance") == number(*pins[i],"capacitance") &&
                text(original,"function") == text(*pins[i],"function"), "skeleton/pin ownership mismatch " + cell.name);
    }
    std::set<std::string> pin_names;
    for (const auto p : pins) require(pin_names.insert(p->name).second, "duplicate pin " + p->name);
    auto arcs_it = cell.graphs.find("timing_content");
    std::vector<const Object*> arcs;
    if (arcs_it != cell.graphs.end()) arcs = arcs_it->second.edge("timing");
    std::vector<std::vector<std::string>> arc_tables(arcs.size());
    for (const auto& family : {"nldm_timing", "ccs_timing"}) {
        auto it = cell.graphs.find(family); if (it == cell.graphs.end()) continue;
        for (const auto& [id,obj] : it->second.objects)
            if (obj.type == 48 && attr(obj,"values") && obj.name != "vector")
                require(attr(obj,"owner_timing_index"), "unowned timing table " + obj.name);
        for (const auto& [id, obj] : it->second.objects) if (attr(obj, "owner_timing_index")) {
            const auto index = number(obj, "owner_timing_index");
            require(index >= 0 && index < arcs.size() && index == std::floor(index), "invalid timing owner index");
            require(obj.type == 48 && !obj.name.empty(), "unnamed timing table");
            static const std::set<std::string> kinds = {
                "cell_rise", "cell_fall", "rise_transition", "fall_transition", "rise_constraint", "fall_constraint",
                "receiver_capacitance1_rise", "receiver_capacitance1_fall", "receiver_capacitance2_rise", "receiver_capacitance2_fall",
                "output_current_rise", "output_current_fall"
            };
            require(kinds.count(obj.name), "unsupported timing table " + obj.name);
            std::ostringstream s; const bool ccs = obj.name.find("output_current_") == 0;
            table(s, it->second, obj, obj.name, templates, ccs ? "output_current_template" : "lu_table_template");
            arc_tables[size_t(index)].push_back(s.str());
        }
    }
    auto fg = cell.graphs.find("function");
    const auto seq = fg == cell.graphs.end() ? std::vector<const Object*>{} : fg->second.edge("seq_model");
    const bool is_ff = number(*co, "is_a_flip_flop") != 0;
    require(!number(*co, "is_a_latch"), "latch model is not supported by this native profile");
    require(seq.size() == size_t(is_ff), "sequential-state model mismatch");
    if (is_ff) {
        const auto& q = *seq[0];
        require(!text(q, "clocked_on").empty() && !text(q, "next_state").empty(), "incomplete FF state");
        out << "ff(" << quote(q.name) << ',' << quote(text(q, "second_variable_name")) << "){";
        scalars(out, q, {"clocked_on", "next_state", "clear", "preset", "clear_preset_var1", "clear_preset_var2"});
        out << '}';
    }
    std::vector<std::vector<std::string>> powers(pins.size());
    auto pow_it = cell.graphs.find("nlpm_power");
    if (pow_it != cell.graphs.end()) for (auto po : pow_it->second.edge("internal_power")) {
        const auto owner = number(*po, "owner_pin_index", -1);
        require(owner >= 0 && owner < pins.size() && owner == std::floor(owner), "invalid power owner index");
        std::ostringstream s; s << "internal_power(){";
        scalars(s, *po, {"when"});
        auto rel = po->refs.find("related_pins");
        if (rel != po->refs.end() && !rel->second.empty()) {
            std::string names;
            for (auto id : rel->second) { if (!names.empty()) names += ' '; names += pow_it->second.objects.at(id).name; }
            s << "related_pin:" << quote(names) << ';';
        }
        for (const auto kind : {"rise_power", "fall_power"}) {
            auto it = po->refs.find(kind);
            if (it != po->refs.end()) for (auto id : it->second)
                table(s, pow_it->second, pow_it->second.objects.at(id), kind, templates, "power_lut_template");
        }
        s << '}'; powers[size_t(owner)].push_back(s.str());
    }
    for (size_t i = 0; i < pins.size(); ++i) {
        const auto& p = *pins[i]; const auto direction = number(p, "direction", -1);
        require(direction >= 1 && direction <= 3, "unsupported pin direction");
        out << "pin(" << quote(p.name) << "){direction:" << (direction == 1 ? "input" : direction == 2 ? "output" : "inout") << ';';
        scalars(out, p, {"capacitance", "rise_capacitance", "fall_capacitance", "max_transition", "max_capacitance", "max_fanout",
                         "function", "clock", "fanout_load", "related_power_pin", "related_ground_pin",
                         "clock_gate_clock_pin", "clock_gate_enable_pin", "clock_gate_test_pin", "clock_gate_out_pin"});
        for (const auto& power : powers[i]) out << power;
        for (size_t ai = 0; ai < arcs.size(); ++ai) if (number(*arcs[ai], "owner_pin_index", -1) == i) {
            const auto& a = *arcs[ai]; auto related = array(a, "related_pins_index");
            require(!related.empty(), "timing arc without related pins");
            std::string names;
            for (auto ri : related) {
                require(ri >= 0 && ri < pins.size() && ri == std::floor(ri), "invalid related pin index");
                if (!names.empty()) names += ' '; names += pins[size_t(ri)]->name;
            }
            const auto sense = number(a, "timing_sense", 3);
            require(sense >= 0 && sense <= 3, "unknown timing sense");
            out << "timing(){related_pin:" << quote(names) << ";timing_type:" << timing_type(unsigned(number(a, "timing_type"))) << ';';
            if (sense < 3) out << "timing_sense:" << (sense == 0 ? "positive_unate" : sense == 1 ? "negative_unate" : "non_unate") << ';';
            scalars(out, a, {"when", "sdf_cond"});
            require(!arc_tables[ai].empty(), "timing arc without decoded tables");
            for (const auto& t : arc_tables[ai]) out << t;
            out << '}';
        }
        out << '}';
    }
    for (auto a : arcs) require(number(*a, "owner_pin_index", -1) >= 0 && number(*a, "owner_pin_index") < pins.size(), "invalid arc owner pin");
    out << '}';
}

std::string semantic_model(const std::string& file, const Part& root) {
    const auto li = child(root, "library_content"); require(li, "missing library metadata");
    auto bytes = decode_part(file, *li); Graph lg(bytes);
    const auto libs = lg.edge("contents"); require(libs.size() == 1 && libs[0]->type == 20, "unsupported library object");
    const auto& lib = *libs[0];
    require(text(lib,"default_wire_load").empty() && text(lib,"default_wire_load_selection").empty() &&
            lg.edge("wire_load").empty() && lg.edge("wire_load_selection").empty(),
            "wire-load metadata requires a native decoder");
    const auto name = root.properties.find("db library name");
    require(name != root.properties.end() && name->second == lib.name, "library name mismatch");
    const auto sk = child(root,"skeleton"); require(sk,"missing skeleton part");
    auto skbytes = decode_part(file,*sk); Graph skeleton(std::move(skbytes));
    std::map<std::string,const Object*> skcells;
    for (auto o : skeleton.edge("designs")) {
        require(o->type == 18 && skcells.emplace(o->name,o).second, "invalid skeleton cell directory");
    }
    std::ostringstream out; out << "library(" << quote(lib.name) << "){";
    require(number(lib, "time_scale") == 1, "unsupported time scale enum");
    const auto tu = text(lib, "time_unit_name");
    require(tu == "ns" || tu == "ps" || tu == "fs" || tu == "us", "unsupported time unit " + tu);
    out << "time_unit:" << quote("1" + tu) << ';';
    const auto cap = number(lib, "capacitive_load_units", -1);
    require(cap > 0, "missing capacitive load units"); out << "capacitive_load_unit(" << real(cap / 1000) << ",pf);";
    for (const auto& unit : {std::make_pair("voltage_unit", 3), std::make_pair("current_unit", 3),
                            std::make_pair("leakage_power_unit", 13), std::make_pair("pulling_resistance_unit", 1)}) {
        if (!attr(lib,unit.first)) continue;
        require(number(lib,unit.first) == unit.second, "unsupported unit enum " + std::string(unit.first));
        out << unit.first << ':' << quote(std::string(unit.first) == "voltage_unit" ? "1V" :
            std::string(unit.first) == "current_unit" ? "1mA" : std::string(unit.first) == "leakage_power_unit" ? "1nW" : "1kohm") << ';';
    }
    scalars(out, lib, {"nom_voltage", "nom_temperature", "nom_process", "delay_model",
        "input_threshold_pct_rise", "input_threshold_pct_fall", "output_threshold_pct_rise", "output_threshold_pct_fall",
        "slew_lower_threshold_pct_rise", "slew_lower_threshold_pct_fall", "slew_upper_threshold_pct_rise", "slew_upper_threshold_pct_fall",
        "slew_derate_from_library", "default_max_transition", "default_max_capacitance", "default_max_fanout", "default_fanout_load"});
    Templates templates;
    static const std::map<std::string, std::string> template_parts = {
        {"nldm_timing_template", "lu_table_template"}, {"nlpm_power_template", "power_lut_template"},
        {"ccs_timing_template", "output_current_template"}
    };
    for (const auto& [part_name, kind] : template_parts) if (const auto part = child(root, part_name)) {
        auto data = decode_part(file, *part); Graph g(data);
        for (auto o : g.edge(kind)) emit_template(out, kind, *o, templates);
    }
    size_t cell_count = 0;
    for (const auto& p : root.children) {
        if (child(p, "cell_content")) {
            require(skcells.count(p.name), "cell absent from skeleton " + p.name);
            emit_cell(out, CellParts(file, p), templates, skeleton, *skcells.at(p.name)); ++cell_count;
        }
        else require(p.name == "skeleton" || p.name == "library_content" || template_parts.count(p.name), "unsupported library part " + p.name);
    }
    require(cell_count && cell_count == skcells.size(), "skeleton/directory cell count mismatch"); out << '}'; return out.str();
}

bool empty_view(const std::string& file, const std::pair<size_t, size_t>& stream) {
    if (stream.second > 256) return false;
    std::string bytes; size_t used = 0;
    require(inflate_member(file, stream.first, bytes, used) && used == stream.second, "invalid empty-view candidate");
    Graph g(std::move(bytes));
    if (g.objects.size() != 1) return false;
    const auto& o = g.objects.at(1);
    if (o.type != 3 || !o.name.empty()) return false;
    for (const auto& [name,v] : o.attrs) if (v.type != 5 || !v.text.empty() ||
        (name != "version" && name != "hdlc_version" && name != "taint_license")) return false;
    for (const auto& [name,ids] : o.refs) if (!ids.empty() || (name != "contents" && name != "view_contents")) return false;
    return true;
}
void bind_parts(const std::string& file, Part& p, const std::vector<std::pair<size_t, size_t>>& streams,
                size_t& index, int64_t owner) {
    require(p.owner == owner, "external directory owner not supported");
    // A signed -1 identifies a directory-only node.
    if (p.size != -1) {
        // The writer emits empty auxiliary views which have no ROOT entry.
        // Only a fully decoded empty root may be omitted, never an arbitrary
        // short stream or one classified by matching printable strings.
        while (index < streams.size() && streams[index].second != p.size && empty_view(file, streams[index])) ++index;
        require(index < streams.size() && streams[index].second == p.size,
                "unsupported fragmented/reused object layout at part " + p.name);
        p.offset = streams[index++].first;
    }
    for (auto& c : p.children) bind_parts(file, c, streams, index, owner);
}
} // namespace

bool read_model(const std::string& path, LibertyDB& db, StringPool& pool, std::string* error) {
    try {
        std::ifstream input(path, std::ios::binary | std::ios::ate);
        require(bool(input), "cannot open " + path);
        const auto size = input.tellg(); require(size >= 16 && size < (std::streamoff(1) << 32), "unsupported .db file size");
        std::string data(size_t(size), '\0'); input.seekg(0);
        require(bool(input.read(data.data(), std::streamsize(data.size()))), "short .db read");
        static const unsigned char magic[] = {3,0x17,0x10,0x63,0,0x40,0xff,3};
        require(std::memcmp(data.data(), magic, sizeof(magic)) == 0, "not a Synopsys .db (bad magic)");
        std::vector<std::pair<size_t, size_t>> streams;
        std::string root_bytes, plain; size_t pos = 0, root_offset = 0;
        const std::string gzip("\x1f\x8b\x08", 3);
        while ((pos = data.find(gzip, pos)) != std::string::npos) {
            size_t used = 0;
            require(inflate_member(data, pos, plain, used), "incomplete/fragmented gzip object at " + std::to_string(pos));
            if (plain.find(std::string(1, 15) + "db library name") < 128) {
                require(root_bytes.empty(), "multiple ROOT objects"); root_bytes = plain; root_offset = pos;
            } else streams.emplace_back(pos, used);
            pos += used;
        }
        require(!root_bytes.empty(), "no supported CRC-valid ROOT object");
        Cursor rc{root_bytes}; size_t nodes = 0; auto root = directory(rc, 0, nodes); rc.finish();
        require(root.name == "." && root.size == -1 && !streams.empty(), "unsupported directory root");
        // This profile deliberately requires a complete sequential record
        // sequence and validates every recorded compressed length.
        require(root_offset > streams.back().first, "nonterminal directory unsupported by model profile");
        size_t index = 0; bind_parts(data, root, streams, index, root.owner);
        while (index < streams.size() && empty_view(data, streams[index])) ++index;
        require(index == streams.size(), "unreferenced compressed objects");
        const auto model = semantic_model(data, root);
        // Decode first, then parse a new library and a private pool. No mutation on
        // unsupported metadata, bad ownership, checksum or parser errors.
        LibertyDB next_db; auto next_pool = pool;
        te::parser::LibertyParser parser(model);
        parser.parse(next_db, next_pool);
        require(next_db.library_count() == 1, "native model did not create one library");
        static_assert(std::is_nothrow_move_assignable<LibertyLibrary>::value);
        static_assert(std::is_nothrow_move_assignable<StringPool>::value);
        db.create_library() = std::move(next_db.library(0));
        pool = std::move(next_pool); if (error) error->clear(); return true;
    } catch (const std::exception& e) {
        if (error) *error = std::string("native .db model incomplete/unsupported: ") + e.what();
        return false;
    }
}
} // namespace edacraft::core::native::detail
