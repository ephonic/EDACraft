// nonlinear_damping.cpp — 非线性 Newton 阻尼控制器实现
//
// Phase A2-4。详见 nonlinear_damping.hpp。
#include "nonlinear_damping.hpp"

#include <algorithm>
#include <cmath>

namespace rfsim {

DampingController::DampingController(uint32_t dim, DampingStrategy strategy)
    : dim_(dim), strategy_(strategy) {}

void DampingController::applyLmRegularization(std::vector<double>& J) const {
    if (strategy_ != DampingStrategy::LevenbergMarquardt &&
        strategy_ != DampingStrategy::TrustRegion) return;
    if (lambda_ <= 0.0 || dim_ == 0) return;
    // Marquardt scaling：对角加 λ·max_k|J[i,k]|²（行 i 的雅可比尺度平方）。
    // 这是 diag(JᵀJ) 的廉价近似，避免 O(dim³) 的 JᵀJ 计算。
    for (uint32_t i = 0; i < dim_; ++i) {
        double scaleSq = 0.0;
        const size_t base = size_t(i) * dim_;
        for (uint32_t k = 0; k < dim_; ++k) {
            double v = J[base + k];
            double a = std::fabs(v);
            if (a > scaleSq) scaleSq = a;
        }
        // scaleSq 取最大 |J|（非平方，等效 λ 缩放——Marquardt 原始用 |J|_max 而非 |J|²_max
        // 作为尺度，数值更稳定）。对角加 λ·scaleSq。
        J[base + i] += lambda_ * (scaleSq > 0.0 ? scaleSq : 1.0);
    }
}

DampingController::StepResult DampingController::step(double fNorm, double fTrial,
                                                       double alpha, double dxNorm, double xNorm) {
    StepResult res{alpha, false, false};
    if (strategy_ == DampingStrategy::Backtracking) {
        // Armijo 充分下降（‖F‖² 形式，与 HB-NL 现有逻辑一致）
        const double armijoC = 1e-4;
        if (fTrial * fTrial <= fNorm * fNorm * (1.0 - 2.0 * armijoC * alpha) ||
            alpha < 1e-7) {
            res.accepted = (fTrial <= fNorm * (1.0 + 1e-10));
        }
        // Backtracking 不需要重算步（λ 不变）。
        return res;
    }

    if (strategy_ == DampingStrategy::LevenbergMarquardt) {
        // LM 接受准则：‖F(X+α·dx)‖ < ‖F(X)‖（简单下降；LM 经典判据）。
        // 试步用 α（调用方可能已按 stepClamp 缩放）。成功 → λ 降；失败 → λ 升，需重解。
        bool descent = (fTrial <= fNorm * (1.0 + 1e-12));
        if (descent) {
            res.accepted = true;
            // 成功：λ 减小（向纯 Newton 靠拢，加速收敛）
            lambda_ /= lambdaDecrease_;
            if (lambda_ < 1e-12) lambda_ = 1e-12;
        } else {
            // 失败：λ 增大（更保守，接近梯度下降），调用方需用新 λ 重解 J·dx=-F
            lambda_ *= lambdaIncrease_;
            if (lambda_ > 1e6) lambda_ = 1e6;
            res.accepted = false;
            res.recomputeStep = true;
        }
        return res;
    }

    // TrustRegion：dogleg 简化——步长 ‖dx‖ 与 Δ 比较，超出则缩放并标记重算。
    if (dxNorm > trustRadius_ && dxNorm > 0.0) {
        // 步长超出信任域：缩放接受（不重算），缩信任域
        res.alpha = alpha * (trustRadius_ / dxNorm);
        res.accepted = (fTrial <= fNorm * (1.0 + 1e-10));
        if (res.accepted) trustRadius_ = std::min(trustRadius_ * 1.5, xNorm + dxNorm);
        else trustRadius_ = std::max(trustRadius_ * 0.5, 1e-6);
    } else {
        res.accepted = (fTrial <= fNorm * (1.0 + 1e-10));
        if (res.accepted) trustRadius_ = std::min(trustRadius_ * 1.5, xNorm + dxNorm + 1.0);
    }
    return res;
}

} // namespace rfsim
