#pragma once
#include "math_types.h"
#include <string>
#include <vector>

namespace tcad {
// One actual solver invocation. Samples never cross solver/retry boundaries.
// Gummel: completed outer updates before any final undamped audit/polish.
// Newton: base-state equation residuals before line search, excluding trials.
struct NonlinearSolveHistory {
    std::string solver;
    bool converged = false;
    real_t final_poisson_residual = -TCAD_CONST(1.0); // Gummel post-polish audit, if computed
    std::vector<std::vector<real_t>> samples;
};

// Diagnostics survive physical rollback. Only retained trials contribute dwell.
struct TransientTrialHistory {
    std::string role;
    std::string solver = "newton";
    real_t start_time = TCAD_CONST(0.0), end_time = TCAD_CONST(0.0), step_dt = TCAD_CONST(0.0);
    bool solver_called = false, converged = false, retained = false;
    bool exception = false;
    std::vector<std::vector<real_t>> samples;
};

struct TransientAttemptHistory {
    real_t start_time = TCAD_CONST(0.0), end_time = TCAD_CONST(0.0), step_dt = TCAD_CONST(0.0);
    size_t retry_index = 0;
    bool error_control = false, accepted = false;
    bool polarization_control = false, electrical_control = false;
    bool error_estimate_available = false;
    real_t polarization_error_ratio = -TCAD_CONST(1.0), electrical_error_ratio = -TCAD_CONST(1.0);
    real_t exported_polarization_error_ratio = -TCAD_CONST(1.0), exported_electrical_error_ratio = -TCAD_CONST(1.0);
    std::string status = "pending", stopping_reason;
    std::vector<TransientTrialHistory> trials;
};
}
