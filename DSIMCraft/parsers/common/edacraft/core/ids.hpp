#ifndef EDACRAFT_CORE_IDS_HPP
#define EDACRAFT_CORE_IDS_HPP

#include <cstdint>
#include <limits>

namespace edacraft::core {

// ─── Strongly-typed 32-bit handles ─────────────────────────────────
// These are the canonical handle types for the unified data model.
// Both fsyn and ftimer use these when interacting through edacraft_core.

struct NetHandle       { uint32_t id; };
struct PinHandle       { uint32_t id; };
struct InstanceHandle  { uint32_t id; };
struct CellHandle      { uint32_t id; };
struct ClockHandle     { uint32_t id; };
struct LibraryHandle   { uint32_t id; };
struct StringHandle    { uint32_t id; };

// Sentinel null handles
constexpr NetHandle       NULL_NET{UINT32_MAX};
constexpr PinHandle       NULL_PIN{UINT32_MAX};
constexpr InstanceHandle  NULL_INSTANCE{UINT32_MAX};
constexpr CellHandle      NULL_CELL{UINT32_MAX};
constexpr ClockHandle     NULL_CLOCK{UINT32_MAX};
constexpr LibraryHandle   NULL_LIBRARY{UINT32_MAX};
constexpr StringHandle    NULL_STRING{UINT32_MAX};

inline bool valid(NetHandle h)       { return h.id != UINT32_MAX; }
inline bool valid(PinHandle h)       { return h.id != UINT32_MAX; }
inline bool valid(InstanceHandle h)  { return h.id != UINT32_MAX; }
inline bool valid(CellHandle h)      { return h.id != UINT32_MAX; }
inline bool valid(ClockHandle h)     { return h.id != UINT32_MAX; }
inline bool valid(LibraryHandle h)   { return h.id != UINT32_MAX; }
inline bool valid(StringHandle h)    { return h.id != UINT32_MAX; }

inline bool operator==(NetHandle a, NetHandle b)       { return a.id == b.id; }
inline bool operator!=(NetHandle a, NetHandle b)       { return a.id != b.id; }
inline bool operator==(PinHandle a, PinHandle b)       { return a.id == b.id; }
inline bool operator!=(PinHandle a, PinHandle b)       { return a.id != b.id; }
inline bool operator==(InstanceHandle a, InstanceHandle b) { return a.id == b.id; }
inline bool operator!=(InstanceHandle a, InstanceHandle b) { return a.id != b.id; }
inline bool operator==(CellHandle a, CellHandle b)     { return a.id == b.id; }
inline bool operator!=(CellHandle a, CellHandle b)     { return a.id != b.id; }
inline bool operator==(ClockHandle a, ClockHandle b)   { return a.id == b.id; }
inline bool operator!=(ClockHandle a, ClockHandle b)   { return a.id != b.id; }

// ─── Port direction ─────────────────────────────────────────────────
enum class PortDirection : uint8_t {
    Input,
    Output,
    Inout,
    Internal,
};

// ─── Transition direction ───────────────────────────────────────────
enum class Transition : uint8_t { Rise = 0, Fall = 1 };

// ─── Min/Max analysis corner ────────────────────────────────────────
enum class MinMax : uint8_t { Min = 0, Max = 1 };

} // namespace edacraft::core

#endif // EDACRAFT_CORE_IDS_HPP
