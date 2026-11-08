#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace te {

class TimingGraph;

// ────────────────────────────────────────────────────────────
// MmapStore: persistent timing results via memory-mapped file
// ────────────────────────────────────────────────────────────
//
// File layout (little-endian):
//   Header (64 bytes):
//     [0..7]   magic = "TESTATE\0"
//     [8..11]  version = 1
//     [12..15] vertex_count
//     [16..23] generation
//     [24..63] reserved (zero)
//
//   Data (contiguous float arrays):
//     arrivals[vertex_count * 4]
//     slews[vertex_count * 4]
//     requireds[vertex_count * 4]
//     pred_max[vertex_count * 4] (uint32_t, per mm_rf)
//     pred_min[vertex_count * 4] (uint32_t, per mm_rf)
//
// The store is read/write through mmap.  On save, data is
// memcpy'd into the mapped region and msync'd.  On load,
// the region is mapped read-only and copied into the graph.
// ────────────────────────────────────────────────────────────

class MmapStore {
public:
    static constexpr uint32_t VERSION = 1;
    static constexpr char MAGIC[8] = {'T', 'E', 'S', 'T', 'A', 'T', 'E', '\0'};
    static constexpr size_t HEADER_SIZE = 64;

    // Save timing results from graph to file (creates or overwrites).
    static bool save(const TimingGraph& graph, const std::string& filepath);

    // Load timing results from file into graph.
    // Returns false if file is missing, corrupted, or version mismatch.
    static bool load(TimingGraph& graph, const std::string& filepath);

private:
    struct Header {
        char magic[8];
        uint32_t version;
        uint32_t vertex_count;
        uint64_t generation;
        char reserved[40];
    };
    static_assert(sizeof(Header) == 64, "Header must be 64 bytes");
};

} // namespace te
