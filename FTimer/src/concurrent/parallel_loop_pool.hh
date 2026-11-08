#pragma once

#include <algorithm>
#include <condition_variable>
#include <cstddef>
#include <exception>
#include <functional>
#include <mutex>
#include <thread>
#include <utility>
#include <vector>

namespace te::detail {

inline bool& in_parallel_region() {
    static thread_local bool active = false;
    return active;
}

// Share workers across topology levels and both loop APIs. Independent
// callers use the current thread when the pool is busy. In particular, a
// callback can join a child thread that enters another loop without deadlock.
class ParallelLoopPool {
public:
    ~ParallelLoopPool() {
        {
            std::lock_guard<std::mutex> lock(state_mutex_);
            stopping_ = true;
        }
        ready_.notify_all();
        for (auto& worker : workers_) worker.join();
    }

    void run(size_t begin, size_t end, unsigned width,
             std::function<void(size_t, unsigned)> job) {
        std::unique_lock<std::mutex> dispatch(dispatch_mutex_, std::try_to_lock);
        if (!dispatch.owns_lock()) {
            ParallelRegion region;
            for (size_t i = begin; i < end; ++i) job(i, 0);
            return;
        }
        {
            std::lock_guard<std::mutex> lock(state_mutex_);
            workers_.reserve(width - 1);
            while (workers_.size() + 1 < width) {
                const unsigned id = static_cast<unsigned>(workers_.size()) + 1;
                workers_.emplace_back([this, id] { worker_loop(id); });
            }
            begin_ = begin;
            chunk_ = (end - begin) / width;
            extra_ = (end - begin) % width;
            width_ = width;
            pending_ = width - 1;
            exception_ = nullptr;
            job_ = std::move(job);
            ++generation_;
        }
        ready_.notify_all();
        execute(begin, begin + chunk_ + (extra_ != 0), 0);
        std::unique_lock<std::mutex> lock(state_mutex_);
        finished_.wait(lock, [this] { return pending_ == 0; });
        job_ = {};
        const auto exception = exception_;
        lock.unlock();
        if (exception) std::rethrow_exception(exception);
    }

private:
    struct ParallelRegion {
        bool previous = in_parallel_region();
        ParallelRegion() { in_parallel_region() = true; }
        ~ParallelRegion() { in_parallel_region() = previous; }
    };

    void execute(size_t begin, size_t end, unsigned id) {
        ParallelRegion region;
        try {
            for (size_t i = begin; i < end; ++i) job_(i, id);
        } catch (...) {
            std::lock_guard<std::mutex> lock(state_mutex_);
            if (!exception_) exception_ = std::current_exception();
        }
    }

    void worker_loop(unsigned id) {
        size_t observed_generation = 0;
        std::unique_lock<std::mutex> lock(state_mutex_);
        for (;;) {
            ready_.wait(lock, [&] {
                return stopping_ || generation_ != observed_generation;
            });
            if (stopping_) return;
            observed_generation = generation_;
            if (id >= width_) continue;
            const size_t first = begin_ + id * chunk_ + std::min<size_t>(id, extra_);
            const size_t last = first + chunk_ + (id < extra_);
            lock.unlock();
            execute(first, last, id);
            lock.lock();
            if (--pending_ == 0) finished_.notify_one();
        }
    }

    std::mutex dispatch_mutex_, state_mutex_;
    std::condition_variable ready_, finished_;
    std::vector<std::thread> workers_;
    std::function<void(size_t, unsigned)> job_;
    size_t begin_ = 0, chunk_ = 0, extra_ = 0, generation_ = 0;
    unsigned width_ = 0, pending_ = 0;
    bool stopping_ = false;
    std::exception_ptr exception_;
};

inline ParallelLoopPool& parallel_loop_pool() {
    static ParallelLoopPool pool;
    return pool;
}

} // namespace te::detail
