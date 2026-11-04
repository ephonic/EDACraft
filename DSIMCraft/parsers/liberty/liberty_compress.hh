#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace te {

// ────────────────────────────────────────────────────────────
// zlib compression helpers for .ftlib binary format
// ────────────────────────────────────────────────────────────

// Compress raw data with gzip wrapper (RFC 1952).
// level: 0=store, 1=fast, 6=default, 9=best compression.
std::vector<uint8_t> compress_gzip(const uint8_t* data, size_t len, int level = 6);

// Decompress gzip-wrapped data. Returns empty vector on error.
std::vector<uint8_t> decompress_gzip(const uint8_t* data, size_t len);

// Check if buffer starts with gzip magic bytes (0x1f 0x8b).
bool is_gzip_data(const uint8_t* data, size_t len);

} // namespace te
