#ifndef EDACRAFT_CORE_STRING_POOL_HPP
#define EDACRAFT_CORE_STRING_POOL_HPP

#include <cstddef>
#include <cstdint>
#include <deque>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>

namespace edacraft::core {

class StringPool {
public:
    StringPool() = default;

    StringPool(const StringPool& other) : strings_(other.strings_) {
        rebuild_index();
    }

    StringPool& operator=(const StringPool& other) {
        if (this == &other) return *this;
        strings_ = other.strings_;
        rebuild_index();
        return *this;
    }

    StringPool(StringPool&&) noexcept = default;
    StringPool& operator=(StringPool&&) noexcept = default;

    uint32_t intern(std::string_view s) const {
        auto it = index_.find(s);
        if (it != index_.end()) {
            return it->second;
        }
        uint32_t id = static_cast<uint32_t>(strings_.size());
        strings_.emplace_back(s);
        index_.emplace(std::string_view{strings_.back()}, id);
        return id;
    }

    std::string_view view(uint32_t id) const {
        if (id >= strings_.size()) return {};
        return strings_[id];
    }

    std::optional<uint32_t> find(std::string_view s) const {
        auto it = index_.find(s);
        if (it == index_.end()) return std::nullopt;
        return it->second;
    }

    size_t memory_usage() const {
        size_t total = 0;
        for (const auto& s : strings_) total += s.capacity() + sizeof(std::string);
        return total;
    }

    size_t size() const { return strings_.size(); }

    void clear() {
        index_.clear();
        strings_.clear();
    }

private:
    void rebuild_index() {
        index_.clear();
        index_.reserve(strings_.size());
        uint32_t id = 0;
        for (const auto& string : strings_) {
            index_.emplace(std::string_view{string}, id++);
        }
    }

    // deque keeps the character storage of SSO strings stable as new names
    // are appended, so the index can reference the canonical string instead
    // of owning a second copy.
    mutable std::deque<std::string> strings_;
    mutable std::unordered_map<std::string_view, uint32_t> index_;
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_STRING_POOL_HPP
