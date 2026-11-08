#pragma once

#include <cstdint>
#include <iosfwd>
#include <string>

namespace edacraft::core {
class LibertyDB;
class StringPool;
}

namespace te {

// ────────────────────────────────────────────────────────────
// Structured binary serializer / deserializer for LibertyDB
// ────────────────────────────────────────────────────────────
//
// File format: .ftlib (flat binary) or .ftlib.gz (gzip compressed)
//
//   Header (64 bytes)
//   String Pool
//   Library Directory
//   Cell Index (sorted by name for binary search)
//   Cell Data (packed: header → pins → arcs → pvt → tables)
//
// See liberty_binary.cc for detailed layout.
// ────────────────────────────────────────────────────────────

// Serialize LibertyDB + StringPool to an ostream.
// If compress=true, the output is gzip-wrapped.
// Returns false on I/O error.
bool save_liberty_binary(const edacraft::core::LibertyDB& db,
                         const edacraft::core::StringPool& pool,
                         std::ostream& out,
                         bool compress = false);

// Deserialize from file path. Auto-detects gzip by magic bytes
// or by .gz / .ftlib.gz extension.
// Returns false on I/O error, corruption, or version mismatch.
bool load_liberty_binary(const std::string& filepath,
                         edacraft::core::LibertyDB& db,
                         edacraft::core::StringPool& pool);

} // namespace te
