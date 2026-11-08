#include "mmap_store.hh"

#include <cstring>
#include <fcntl.h>
#ifdef _WIN32
#include <windows.h>
#include <io.h>
#include <sys/stat.h>
#else
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

#include <cerrno>
#include <iostream>

#include "graph/timing_graph.hh"

namespace te {

#ifdef _WIN32
namespace {
constexpr int kMapFailed = -1;

void* portable_mmap(void*, size_t length, int prot, int, int fd, long long) {
    HANDLE file = reinterpret_cast<HANDLE>(_get_osfhandle(fd));
    if (file == INVALID_HANDLE_VALUE) return reinterpret_cast<void*>(kMapFailed);
    DWORD protect = (prot & 2) ? PAGE_READWRITE : PAGE_READONLY;
    DWORD access = (prot & 2) ? FILE_MAP_WRITE : FILE_MAP_READ;
    HANDLE mapping = CreateFileMappingA(file, nullptr, protect,
                                        static_cast<DWORD>(length >> 32),
                                        static_cast<DWORD>(length), nullptr);
    if (!mapping) return reinterpret_cast<void*>(kMapFailed);
    void* view = MapViewOfFile(mapping, access, 0, 0, length);
    CloseHandle(mapping);
    return view ? view : reinterpret_cast<void*>(kMapFailed);
}

int portable_munmap(void* addr, size_t) {
    return UnmapViewOfFile(addr) ? 0 : -1;
}

int portable_msync(void* addr, size_t length, int) {
    return FlushViewOfFile(addr, length) ? 0 : -1;
}

int portable_ftruncate(int fd, long long length) {
    return _chsize_s(fd, static_cast<__int64>(length));
}
} // namespace
#define mmap te::portable_mmap
#define munmap te::portable_munmap
#define msync te::portable_msync
#define ftruncate te::portable_ftruncate
#define MAP_FAILED reinterpret_cast<void*>(kMapFailed)
#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_SHARED 1
#define MAP_PRIVATE 2
#define MS_SYNC 0
#endif

// ────────────────────────────────────────────────────────────
// Save: map file, write header + data, sync, unmap
// ────────────────────────────────────────────────────────────
bool MmapStore::save(const TimingGraph& graph, const std::string& filepath) {
    uint32_t vcount = graph.vertex_count();
    if (vcount == 0) return false;

    size_t data_floats = static_cast<size_t>(vcount) * 4 * 3; // arr + slew + req
    size_t data_uints  = static_cast<size_t>(vcount) * 4 * 2; // pred_max + pred_min (per mm_rf)
    size_t data_size   = data_floats * sizeof(float) + data_uints * sizeof(uint32_t);
    size_t file_size   = HEADER_SIZE + data_size;

    int fd = ::open(filepath.c_str(), O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return false;

    // Extend file to required size
    if (::ftruncate(fd, static_cast<off_t>(file_size)) != 0) {
        ::close(fd);
        return false;
    }

    void* addr = ::mmap(nullptr, file_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (addr == MAP_FAILED) {
        ::close(fd);
        return false;
    }
    ::close(fd); // fd can be closed after mmap

    // Write header
    Header hdr{};
    std::memcpy(hdr.magic, MAGIC, 8);
    hdr.version      = VERSION;
    hdr.vertex_count = vcount;
    hdr.generation   = graph.generation();
    std::memcpy(addr, &hdr, sizeof(hdr));

    // Write data
    char* ptr = static_cast<char*>(addr) + HEADER_SIZE;

    // arrivals
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                float val = graph.arrival(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf)).value;
                std::memcpy(ptr, &val, sizeof(float));
                ptr += sizeof(float);
            }
        }
    }
    // slews
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                float val = graph.slew(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf)).value;
                std::memcpy(ptr, &val, sizeof(float));
                ptr += sizeof(float);
            }
        }
    }
    // requireds
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                float val = graph.required(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf)).value;
                std::memcpy(ptr, &val, sizeof(float));
                ptr += sizeof(float);
            }
        }
    }
    // pred_max (per mm_rf)
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                uint32_t val = graph.pred_max(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf));
                std::memcpy(ptr, &val, sizeof(uint32_t));
                ptr += sizeof(uint32_t);
            }
        }
    }
    // pred_min (per mm_rf)
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                uint32_t val = graph.pred_min(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf));
                std::memcpy(ptr, &val, sizeof(uint32_t));
                ptr += sizeof(uint32_t);
            }
        }
    }

    ::msync(addr, file_size, MS_SYNC);
    ::munmap(addr, file_size);
    return true;
}

// ────────────────────────────────────────────────────────────
// Load: map file read-only, validate header, copy into graph
// ────────────────────────────────────────────────────────────
bool MmapStore::load(TimingGraph& graph, const std::string& filepath) {
    int fd = ::open(filepath.c_str(), O_RDONLY);
    if (fd < 0) return false;

    struct stat st;
    if (::fstat(fd, &st) != 0) {
        ::close(fd);
        return false;
    }
    size_t file_size = static_cast<size_t>(st.st_size);
    if (file_size < HEADER_SIZE) {
        ::close(fd);
        return false;
    }

    void* addr = ::mmap(nullptr, file_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (addr == MAP_FAILED) {
        ::close(fd);
        return false;
    }
    ::close(fd);

    // Validate header
    Header hdr;
    std::memcpy(&hdr, addr, sizeof(hdr));
    if (std::memcmp(hdr.magic, MAGIC, 8) != 0 || hdr.version != VERSION) {
        ::munmap(addr, file_size);
        return false;
    }

    uint32_t vcount = hdr.vertex_count;
    size_t expected = HEADER_SIZE
        + static_cast<size_t>(vcount) * 4 * 3 * sizeof(float)
        + static_cast<size_t>(vcount) * 4 * 2 * sizeof(uint32_t); // pred_max+pred_min per mm_rf
    if (file_size < expected) {
        ::munmap(addr, file_size);
        return false;
    }

    if (graph.vertex_count() != vcount) {
        // Graph structure mismatch; caller should rebuild graph first
        ::munmap(addr, file_size);
        return false;
    }

    const char* ptr = static_cast<const char*>(addr) + HEADER_SIZE;

    // arrivals
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                float val;
                std::memcpy(&val, ptr, sizeof(float));
                graph.set_arrival(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf), Delay{val});
                ptr += sizeof(float);
            }
        }
    }
    // slews
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                float val;
                std::memcpy(&val, ptr, sizeof(float));
                graph.set_slew(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf), Slew{val});
                ptr += sizeof(float);
            }
        }
    }
    // requireds
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                float val;
                std::memcpy(&val, ptr, sizeof(float));
                graph.set_required(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf), Required{val});
                ptr += sizeof(float);
            }
        }
    }
    // pred_max (per mm_rf)
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                uint32_t val;
                std::memcpy(&val, ptr, sizeof(uint32_t));
                graph.set_pred_max(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf), val);
                ptr += sizeof(uint32_t);
            }
        }
    }
    // pred_min (per mm_rf)
    for (uint32_t vid = 0; vid < vcount; ++vid) {
        for (int mm = 0; mm < 2; ++mm) {
            for (int rf = 0; rf < 2; ++rf) {
                uint32_t val;
                std::memcpy(&val, ptr, sizeof(uint32_t));
                graph.set_pred_min(vid, static_cast<MinMax>(mm), static_cast<Transition>(rf), val);
                ptr += sizeof(uint32_t);
            }
        }
    }

    ::munmap(addr, file_size);
    return true;
}

} // namespace te
