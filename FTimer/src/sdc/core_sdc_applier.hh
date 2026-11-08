#pragma once

#include "edacraft/core/constraint_db.hpp"
#include "time_engine/types.hh"
#include "sdc/resolved_constraints.hh"

#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace te {

using PinResolver = std::function<std::optional<PinId>(const std::string&)>;
using PinListResolver = std::function<std::vector<PinId>(const std::string&)>;
using StringInterner = std::function<uint32_t(const std::string&)>;

uint32_t apply_core_sdc(
    const edacraft::core::ConstraintDB& constraints,
    ResolvedConstraintSet& sdc_ctx,
    const PinResolver& pin_resolver,
    const StringInterner& string_interner,
    bool verbose = false);

uint32_t apply_core_sdc(
    const edacraft::core::ConstraintDB& constraints,
    ResolvedConstraintSet& sdc_ctx,
    const PinListResolver& pin_resolver,
    const StringInterner& string_interner,
    bool verbose = false);

std::vector<PinId> resolve_sdc_pin_list(
    const std::vector<std::string>& names,
    const PinResolver& pin_resolver);

std::vector<PinId> resolve_sdc_pin_list(
    const std::vector<std::string>& names,
    const PinListResolver& pin_resolver);

} // namespace te
