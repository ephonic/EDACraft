// Native Synopsys DB reader, adapted from /home/yangfan/c906/t12/db_api.h.
// Provenance and scope: docs/parser-origin/db-api/README.md, docs/liberty-db.md.
// No vendor tool, environment setup, shell command or license is used.
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "edacraft/core/liberty_db.hpp"
#include "edacraft/core/string_pool.hpp"

namespace edacraft::core {
namespace dbio {
enum class LibraryFileFormat { Unknown, LibertyText, SynopsysDb };
LibraryFileFormat detect_library_file(const std::string& path);
// Strict entry: never accept incomplete DB cell/pin/arc graphs for simulation.
// On failure both output objects are unchanged.
bool read_library_file(const std::string& path, LibertyDB& db, StringPool& pool,
                       std::string* error = nullptr);
}
namespace native {

struct DbInfo {
    uint64_t file_size = 0;
    uint32_t stream_count = 0;        // gzip streams found
    uint64_t compressed_bytes = 0;    // sum of compressed sizes
    uint64_t uncompressed_bytes = 0;  // sum of decoded sizes
    size_t dictionary_entries = 0;    // interned strings in stream #0
    std::string library_name;         // "#<lib>" entry from the dictionary
};

// Container-level probe: header check + gzip stream walk + dictionary
// decode.  No Synopsys tool required.
bool probe_synopsys_db(const std::string& path, DbInfo& info,
                       std::string* error = nullptr);

struct NldmTable {
    std::string kind;       // cell_rise | cell_fall | rise_transition | fall_transition
                            // | rise_power | fall_power | receiver_capacitance*_*
                            // | "unknown" (compact record, no inline name)
    std::string tmpl;       // e.g. delay_template_8x8 (when present)
    std::vector<float> axis1;
    std::vector<float> axis2;
    std::vector<float> values;  // row-major, values[r*axis2.size()+c]
};

// Extract every table record found in the object streams (named and
// compact forms).  Cell/arc attribution requires the object linkage,
// so tables are returned in file order; use extract_cell_objects for
// the cell inventory.
bool extract_nldm_tables(const std::string& path,
                         std::vector<NldmTable>& out,
                         std::string* error = nullptr);

// One CCS output_current waveform vector: the sample coordinates are
// carried by the record itself (input slew, load cap, reference time,
// time base and sampled output current).
struct CcsVector {
    float slew = 0.0f;
    float cap = 0.0f;
    float ref_time = 0.0f;
    std::vector<float> times;
    std::vector<float> currents;
};

// Extract every CCS output_current vector record ("vector" objects in
// output_current_rise/fall streams, verbose and compact forms).
// rise/fall tagging is filled in when the enclosing stream names its
// object; see the CcsVectorDoc::group field.
struct CcsVectorDoc {
    std::string group;          // "output_current_rise" | "output_current_fall" | ""
    std::string cell;           // attributed cell (attribute_ccs_by_cell)
    std::vector<std::string> owners;  // all cells sharing this carrier
    std::vector<CcsVector> vectors;
    size_t stream_offset = 0;   // file offset of the containing stream
};
bool extract_ccs_vectors(const std::string& path,
                         std::vector<CcsVectorDoc>& out,
                         std::string* error = nullptr);

// Library cell inventory from the per-cell object streams: name, area,
// footprint.  (Order follows the ROOT stream's cell directory.)
struct CellObject {
    std::string name;
    std::string footprint;
    float area = 0.0f;
    size_t stream_offset = 0;
};
bool extract_cell_objects(const std::string& path,
                          std::vector<CellObject>& out,
                          std::string* error = nullptr);

// Advanced: parse one already-decompressed object stream (the payload
// of a single gzip block).  Useful for tooling that manages stream
// decompression itself.
bool parse_stream_tables(const std::string& stream_plain,
                         std::vector<NldmTable>& out);
bool parse_stream_ccs(const std::string& stream_plain, size_t stream_offset,
                      const std::string& group,
                      std::vector<CcsVectorDoc>& out);

// ── Object graph (cell-level attribution) ─────────────────────────────
// The ROOT stream's cell directory maps every cell to its data:
//   <len><NAME> <cellid varint> then records
//   <tag 0x10..0x18> <cellid> <page LE u16/u24> 00 00
// where page*0x100 is a file offset INSIDE the owning stream:
//   tag 0x11/0x14 -> the cell-object stream (name/area/footprint;
//                    resolved for all 1125 directory cells)
//   tag 0x15..0x18 -> heavy-data carriers (1083 cells; carriers are
//                    shared between cells and pack several objects).
// Status: the link layer is decoded and extract_cell_links resolves
// page pointers to stream offsets (tags 15-18 resolve mostly to
// ccs-current carriers, some to ccsn/constraint/nldm streams; ~40% of
// the pointers land in fragment-continuation zones that carry no
// stream start).  attribute_ccs_by_cell attaches owner cells to
// extracted vector documents.  Section-level verification shows the
// cell's data starts at the page pointer (decompress counting input
// bytes to the pointer; the output position lands on a record
// boundary), but multiple cells' sections interleave inside shared
// carriers — exact section end needs the next page mark of a
// DIFFERENT cell plus the pin-object streams (arc from/to/sense) for
// the full LibertyDB graph.
struct CellLink {
    std::string cell;
    size_t cell_object_stream = SIZE_MAX;   // stream file offset
    std::vector<size_t> carrier_streams;    // deduped stream offsets
    std::vector<size_t> carrier_pages;      // raw page pointers (tags 15-18)
};

// Parse the ROOT directory and resolve the page pointers against the
// gzip stream inventory.  Returns one CellLink per directory cell.
bool extract_cell_links(const std::string& path,
                        std::vector<CellLink>& out,
                        std::string* error = nullptr);

// Attach attribution to extracted CCS vector documents: every doc whose
// stream_offset is listed in a CellLink gets the cell name recorded.
// (docs are matched by stream_offset, so run extract_ccs_vectors first.)
void attribute_ccs_by_cell(const std::vector<CellLink>& links,
                           std::vector<CcsVectorDoc>& docs);

// ── Pin objects ("ports" streams) ─────────────────────────────────────
// FINAL STRUCTURE (validated): ports streams are PER-PIN (1085 for the
// 1085 SDBD cells' pin sets; each carries one pin's electricals + the
// cell's pg-pin section).  Pin electricals are bit-exact vs SDBD:
//  - names:     "<len><NAME [A-Z0-9]>" followed by slot marker "81 40"
//  - first-pin verbose: "<idx> 03 <id> <len>'capacitance' <BE f32>"
//  - later compact:     "03 <f32> 04 <f32> ... 09 <f32>" (7 caps)
//  - outputs: max/min_capacitance via verbose tokens
// Cell grouping: pin streams share the parent cell's varint id (the
// cb9c93ae0b-family ids in ROOT records); ROOT tag 13 pages point at
// the cell's first pin stream.
struct PinObject {
    std::string name;
    float capacitance = -1.0f;
    float rise_capacitance = -1.0f;
    float fall_capacitance = -1.0f;
    float max_capacitance = -1.0f;
    float min_capacitance = -1.0f;
    std::string function;
    std::string power_down_function;
    int direction = -1;
};
struct PortsDoc {
    std::string cell;      // attribution via ROOT (partial; grouping by
                           // parent id is the finishing step)
    std::vector<PinObject> pins;
    size_t stream_offset = 0;
};

// Extract every ports stream (1085 docs, pin names + electricals
// validated bit-exact against the lc_shell dump).
bool extract_ports(const std::string& path,
                   std::vector<PortsDoc>& out,
                   std::string* error = nullptr);

// ── Arc objects ("timing" streams) ────────────────────────────────────
// One timing stream holds arc records with inline when/sdf_cond:
//   kind "08 06 timing"; per arc:
//     "<tag> 08 <len>'sdf_cond' <cond text>"
//     "<tag> 04 <len>'when' <cond text>"
//     owner_pin_index / related_pins_index (small ints)
//     table slots (cell_rise..receiver_cap2_fall)
struct ArcObject {
    std::string when;
    std::string sdf_cond;
    int owner_pin_index = -1;
    int related_pins_index = -1;
};
struct ArcDoc {
    std::vector<ArcObject> arcs;
    size_t stream_offset = 0;
};

// Extract every timing-arc stream and parse the per-arc records.
bool extract_arcs(const std::string& path,
                  std::vector<ArcDoc>& out,
                  std::string* error = nullptr);

// ── Strict simulation model entry ─────────────────────────────────────
// Full graph assembly is not yet implemented by the supplied decoder.
// Returns false with a diagnostic, preserving db/pool. Use read_synopsys_db
// below to obtain recovered objects with explicit incomplete coverage.
bool read_synopsys_db_native(const std::string& path,
                             LibertyDB& db,
                             StringPool& pool,
                             std::string* error = nullptr);

// Recovered records are kept outside LibertyDB until their exact graph
// ownership is known. They must not be used as attributed simulation models.
struct DbDocument {
    DbInfo info;
    std::vector<CellObject> cells;
    std::vector<NldmTable> tables;
    std::vector<CcsVectorDoc> ccs;
    std::vector<PortsDoc> ports;
    std::vector<ArcDoc> timing;
    size_t partial_streams = 0;
    bool simulation_model_complete = false;
};
// Reads the container and decodes each recovered stream once. Success means
// object extraction succeeded, NOT that a complete LibertyDB can be assembled.
// Failed reads leave document unchanged. No calls to external executables.
bool read_synopsys_db(const std::string& path, DbDocument& document,
                      std::string* error = nullptr);
// JSON coverage/inventory, with explicit model completeness and limitations.
std::string db_document_json(const DbDocument& document);

} // namespace native
} // namespace edacraft::core

