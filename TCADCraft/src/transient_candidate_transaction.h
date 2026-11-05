#pragma once
#include "math_types.h"
#include <array>
#include <map>
#include <vector>

namespace tcad { namespace detail {
// Internal candidate boundary, separate from solve_transient's whole-call
// exception contract. Construct before mutation; commit only after the ledger
// and returned history are ready. Construction may throw without changing the
// live state. Restoration must also work with a persistently failing allocator.
template<class Result>
class TransientCandidateTransaction {
public:
    using State = std::array<std::vector<real_t>*, 10>;
    TransientCandidateTransaction(State live, std::map<size_t, real_t>& contacts,
        std::vector<Result>& history, real_t* clock = nullptr)
        : live_(live), contacts_(contacts), history_(history), clock_(clock),
          entered_contacts_(contacts), entered_size_(history.size()),
          entered_time_(clock ? *clock : TCAD_CONST(0.0)) {
        for (size_t i = 0; i < live_.size(); ++i) entered_[i] = *live_[i];
    }
    TransientCandidateTransaction(const TransientCandidateTransaction&) = delete;
    TransientCandidateTransaction& operator=(const TransientCandidateTransaction&) = delete;
    ~TransientCandidateTransaction() noexcept { restore(); }
    void restore() noexcept {
        if (!active_) return;
        for (size_t i = 0; i < live_.size(); ++i) live_[i]->swap(entered_[i]);
        contacts_.swap(entered_contacts_);
        // Only provisional appends are allowed while a candidate is active.
        while (history_.size() > entered_size_) history_.pop_back();
        if (clock_) *clock_ = entered_time_;
        active_ = false;
    }
    void commit() noexcept { active_ = false; }
private:
    State live_;
    std::array<std::vector<real_t>, 10> entered_;
    std::map<size_t, real_t>& contacts_;
    std::vector<Result>& history_;
    real_t* clock_;
    std::map<size_t, real_t> entered_contacts_;
    size_t entered_size_;
    real_t entered_time_;
    bool active_ = true;
};
}}
