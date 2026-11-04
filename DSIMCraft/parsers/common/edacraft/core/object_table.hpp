#ifndef EDACRAFT_CORE_OBJECT_TABLE_HPP
#define EDACRAFT_CORE_OBJECT_TABLE_HPP

#include <array>
#include <bitset>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <new>
#include <type_traits>
#include <utility>
#include <vector>

namespace edacraft::core {

inline constexpr size_t OBJECT_TABLE_BLOCK_SIZE = 4096;

template<typename T>
class ObjectTable {
public:
    static constexpr uint32_t NULL_ID = UINT32_MAX;

    ObjectTable() = default;
    ~ObjectTable() = default;

    ObjectTable(const ObjectTable&) = delete;
    ObjectTable& operator=(const ObjectTable&) = delete;
    ObjectTable(ObjectTable&&) noexcept = default;
    ObjectTable& operator=(ObjectTable&&) noexcept = default;

    uint32_t alloc() {
        if (!free_list_.empty()) {
            uint32_t id = free_list_.back();
            free_list_.pop_back();
            auto& slot = at(id);
            if constexpr (std::is_trivially_destructible_v<T>) {
                slot = T{};
            } else {
                new (&slot) T{};
            }
            return id;
        }
        uint32_t id = static_cast<uint32_t>(size_);
        ++size_;
        ensure_block(id);
        auto& obj = at(id);
        obj = T{};
        return id;
    }

    template<typename... Args>
    uint32_t emplace(Args&&... args) {
        if (!free_list_.empty()) {
            uint32_t id = free_list_.back();
            free_list_.pop_back();
            auto& slot = at(id);
            if constexpr (std::is_trivially_destructible_v<T>) {
                slot = T{std::forward<Args>(args)...};
            } else {
                new (&slot) T{std::forward<Args>(args)...};
            }
            return id;
        }
        uint32_t id = static_cast<uint32_t>(size_);
        ++size_;
        ensure_block(id);
        auto& obj = at(id);
        obj = T{std::forward<Args>(args)...};
        return id;
    }

    void free(uint32_t id) {
        if (id >= size_) return;
        uint32_t blk = id / OBJECT_TABLE_BLOCK_SIZE;
        uint32_t off = id % OBJECT_TABLE_BLOCK_SIZE;
        if (blk < blocks_.size() && blocks_[blk] && blocks_[blk]->alive.test(off)) {
            if constexpr (!std::is_trivially_destructible_v<T>) {
                blocks_[blk]->data[off].~T();
            }
            blocks_[blk]->alive.reset(off);
            free_list_.push_back(id);
        }
    }

    T& operator[](uint32_t id) { return at(id); }
    const T& operator[](uint32_t id) const { return at(id); }

    T* try_get(uint32_t id) {
        if (id >= size_) return nullptr;
        uint32_t blk = id / OBJECT_TABLE_BLOCK_SIZE;
        uint32_t off = id % OBJECT_TABLE_BLOCK_SIZE;
        if (blk >= blocks_.size() || !blocks_[blk] || !blocks_[blk]->alive.test(off)) {
            return nullptr;
        }
        return &blocks_[blk]->data[off];
    }

    const T* try_get(uint32_t id) const {
        if (id >= size_) return nullptr;
        uint32_t blk = id / OBJECT_TABLE_BLOCK_SIZE;
        uint32_t off = id % OBJECT_TABLE_BLOCK_SIZE;
        if (blk >= blocks_.size() || !blocks_[blk] || !blocks_[blk]->alive.test(off)) {
            return nullptr;
        }
        return &blocks_[blk]->data[off];
    }

    size_t size() const { return size_; }

    void reserve(size_t count) {
        size_t needed = (count + OBJECT_TABLE_BLOCK_SIZE - 1) / OBJECT_TABLE_BLOCK_SIZE;
        while (blocks_.size() < needed) {
            blocks_.push_back(std::make_unique<Block>());
        }
    }

    size_t capacity() const { return blocks_.size() * OBJECT_TABLE_BLOCK_SIZE; }

private:
    struct Block {
        std::array<T, OBJECT_TABLE_BLOCK_SIZE> data;
        std::bitset<OBJECT_TABLE_BLOCK_SIZE> alive;
    };

    T& at(uint32_t id) {
        uint32_t blk = id / OBJECT_TABLE_BLOCK_SIZE;
        uint32_t off = id % OBJECT_TABLE_BLOCK_SIZE;
        return blocks_[blk]->data[off];
    }

    const T& at(uint32_t id) const {
        uint32_t blk = id / OBJECT_TABLE_BLOCK_SIZE;
        uint32_t off = id % OBJECT_TABLE_BLOCK_SIZE;
        return blocks_[blk]->data[off];
    }

    void ensure_block(uint32_t id) {
        uint32_t blk = id / OBJECT_TABLE_BLOCK_SIZE;
        while (blocks_.size() <= blk) {
            blocks_.push_back(std::make_unique<Block>());
        }
    }

    std::vector<std::unique_ptr<Block>> blocks_;
    std::vector<uint32_t> free_list_;
    size_t size_ = 0;
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_OBJECT_TABLE_HPP
