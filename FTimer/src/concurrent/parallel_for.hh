#pragma once

#include <cstddef>
#include <exception>
#include <mutex>
#include <thread>
#include <vector>
#include <algorithm>
#include <atomic>
#include "parallel_loop_pool.hh"

namespace te {

// Global thread-count override for parallel_for.
// 0 means "use hardware_concurrency()".
inline std::atomic<int>& parallel_thread_count() {
    static std::atomic<int> count{0};
    return count;
}

inline unsigned get_num_threads() {
    int cfg = parallel_thread_count().load();
    if (cfg > 0) return static_cast<unsigned>(cfg);
    unsigned hc = std::thread::hardware_concurrency();
    return hc ? hc : 4;
}

// Simple parallel-for over a range [begin, end).
// Falls back to serial execution for small ranges.
// Propagates exceptions from worker threads to the caller.
// Parallel-for with thread-id passed to the worker function.
// fn signature: void(size_t index, unsigned thread_id)
// Propagates exceptions from worker threads to the caller.
template <typename Func>
inline void parallel_for_with_id(size_t begin, size_t end, Func&& fn) {
    size_t n = end > begin ? end - begin : 0;
    if (n == 0) return;

    // Keep at least 64 items per participant, not per whole loop. Avoid
    // launching host-sized thread batches for narrow topology levels.
    const unsigned num_threads = static_cast<unsigned>(std::min<size_t>(
        get_num_threads(), std::max<size_t>(1, n / 64)));
    if (num_threads == 1 || detail::in_parallel_region()) {
        for (size_t i = begin; i < end; ++i) {
            fn(i, 0);
        }
        return;
    }

    detail::parallel_loop_pool().run(begin, end, num_threads,
        [&](size_t i, unsigned id) { fn(i, id); });
}

template <typename Func>
inline void parallel_for(size_t begin, size_t end, Func&& fn) {
    parallel_for_with_id(begin, end, [&](size_t i, unsigned) { fn(i); });
}

} // namespace te
