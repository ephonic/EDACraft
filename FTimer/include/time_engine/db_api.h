// Native API imported and adapted from /home/yangfan/c906/t12/db_api.h.
// Original SHA256: 16fa88540d345d1e7a73c889ae602b042ac3e7576380bd77caa6a5abc5035479
// Experimental diagnostics: extracted records and ownership hints are not a
// complete timing model. See docs/native_db_reader.md for the current boundary.
// Uses zlib directly, without external tools, licenses or companion files.
#pragma once
#include <cstddef>
#include <iosfwd>
#include <cstdint>
#include <string>
#include <vector>
#include "edacraft/core/liberty_db.hpp"
#include "edacraft/core/string_pool.hpp"

namespace edacraft::core::native {

struct DbInfo {
    uint64_t file_size = 0;
    uint32_t stream_count = 0;
    uint64_t compressed_bytes = 0;
    uint64_t uncompressed_bytes = 0;
    uint32_t complete_stream_count = 0;
    uint32_t partial_stream_count = 0;
    size_t directory_cells = 0;
    std::vector<std::string> cell_names;
    size_t dictionary_entries = 0; // diagnostic subset, not dictionary completeness
    std::string library_name;
};

// CRC-valid structural ROOT inventory. Partial payload streams are accounted
// separately; recovering their bytes does not establish their integrity.
bool probe_synopsys_db(const std::string& path, DbInfo& info,
                       std::string* error = nullptr);
bool parse_root_cell_names(const std::string& root, std::vector<std::string>& names,
                           std::string* error = nullptr);

struct NldmTable {
    std::string kind; // named table kind or "unknown" for compact records
    std::string tmpl;
    std::vector<float> axis1, axis2, values;
};
bool extract_nldm_tables(const std::string& path, std::vector<NldmTable>& out,
                         std::string* error = nullptr);
bool parse_stream_tables(const std::string& stream_plain, std::vector<NldmTable>& out);

struct CcsVector {
    float slew = 0.0f, cap = 0.0f, ref_time = 0.0f;
    std::vector<float> times, currents;
};
struct CcsVectorDoc {
    std::string group; // may be unknown/ambiguous in shared carriers
    std::string cell; // diagnostic ownership hint only
    std::vector<std::string> owners;
    std::vector<CcsVector> vectors;
    size_t stream_offset = 0;
};
bool extract_ccs_vectors(const std::string& path, std::vector<CcsVectorDoc>& out,
                         std::string* error = nullptr);
bool parse_stream_ccs(const std::string& stream_plain, size_t stream_offset,
                      const std::string& group, std::vector<CcsVectorDoc>& out);

struct CellObject {
    std::string name, footprint;
    float area = 0.0f;
    size_t stream_offset = 0;
};
bool extract_cell_objects(const std::string& path, std::vector<CellObject>& out,
                          std::string* error = nullptr);

struct CellLink {
    std::string cell;
    size_t cell_object_stream = SIZE_MAX;
    std::vector<size_t> carrier_streams, carrier_pages;
};
bool extract_cell_links(const std::string& path, std::vector<CellLink>& out,
                        std::string* error = nullptr);
// Carrier sharing does not resolve individual arc ownership.
void attribute_ccs_by_cell(const std::vector<CellLink>& links,
                           std::vector<CcsVectorDoc>& docs);

struct PinObject {
    std::string name;
    float capacitance = -1.0f, rise_capacitance = -1.0f, fall_capacitance = -1.0f;
    float max_capacitance = -1.0f, min_capacitance = -1.0f;
    std::string function, power_down_function;
    int direction = -1;
};
struct PortsDoc {
    std::string cell; // diagnostic ownership hint only
    std::vector<PinObject> pins;
    size_t stream_offset = 0;
};
bool extract_ports(const std::string& path, std::vector<PortsDoc>& out,
                   std::string* error = nullptr);

struct ArcObject {
    std::string when, sdf_cond;
    int owner_pin_index = -1, related_pins_index = -1;
};
struct ArcDoc {
    std::vector<ArcObject> arcs;
    size_t stream_offset = 0;
};
bool extract_arcs(const std::string& path, std::vector<ArcDoc>& out,
                  std::string* error = nullptr);

// Loads the checked sequential-object profile, including indexed NLDM/CCS
// arcs and FF state. Fragmented/reused carriers and unsupported semantics are
// rejected with a diagnostic; the heuristic extraction APIs are not used.
// Leaves both destination objects unchanged on failure. Never publishes the
// imported prototype's cell-only skeleton as a successfully loaded LibertyDB.
bool read_synopsys_db_native(const std::string& path, LibertyDB& db,
                             StringPool& pool, std::string* error = nullptr);

} // namespace edacraft::core::native

// Isolated experimental library only: link time_engine_db_experimental.
// Neither these exports nor the native reader are linked into the main flow.
namespace edacraft::core::dbio {
// Emits the retained timing/power model. Unsupported or malformed data fails
// with an error; it is never silently dropped. Source-only metadata is not kept.
bool write_liberty_text(const LibertyDB& db, const StringPool& pool,
                        std::ostream& out, std::string* error = nullptr);
bool write_liberty_file(const LibertyDB& db, const StringPool& pool,
                        const std::string& path, std::string* error = nullptr);
}
