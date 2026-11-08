#pragma once

#include "edacraft/core/resolved_constraint_set.hpp"
#include "time_engine/types.hh"

namespace te {

using ResolvedClock = edacraft::core::BasicResolvedClock<PinId>;
using ResolvedClockGroup = edacraft::core::ResolvedClockGroup;
using ResolvedInputDelay = edacraft::core::BasicResolvedInputDelay<PinId, Transition>;
using ResolvedOutputDelay = edacraft::core::BasicResolvedOutputDelay<PinId, Transition>;
using ResolvedSetLoad = edacraft::core::BasicResolvedSetLoad<PinId>;
using ResolvedInputTransition = edacraft::core::BasicResolvedInputTransition<PinId>;
using ResolvedClockLatency = edacraft::core::BasicResolvedClockLatency<PinId>;
using ResolvedClockUncertainty = edacraft::core::BasicResolvedClockUncertainty<PinId>;
using CaseAnalysis = edacraft::core::BasicResolvedCaseAnalysis<PinId>;
using ResolvedMaxDelay = edacraft::core::BasicResolvedMaxDelay<PinId>;
using ResolvedMinDelay = edacraft::core::BasicResolvedMinDelay<PinId>;
using ResolvedMulticyclePath = edacraft::core::BasicResolvedMulticyclePath<PinId>;
using ResolvedDisableTiming = edacraft::core::BasicResolvedDisableTiming<PinId>;
using ResolvedFalsePath = edacraft::core::BasicResolvedFalsePath<PinId>;
using OcvDerate = edacraft::core::ResolvedOcvDerate;
using AocvPoint = edacraft::core::ResolvedAocvPoint;
using AocvTable = edacraft::core::ResolvedAocvTable;
using ResolvedConstraintSet = edacraft::core::BasicResolvedConstraintSet<PinId, Transition>;

} // namespace te
