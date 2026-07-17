// linear_solver_factory.cpp — 线性求解器工厂实现
//
// Phase A1 步骤 2/3：自动选择 + 统一构造入口。
// 选择策略详见 linear_solver_factory.hpp 注释。
//
// 升级（用户需求）：大矩阵（dim > kEmpiricalThreshold，默认 10万）触发经验基准——
// 对候选求解器各跑 N 次 factorize+solve，选最快的。小矩阵用静态规则（默认 KLU）。
#include "linear_solver_factory.hpp"
#include "lu_solver.hpp"
#include "iterative_solver.hpp"
#include "solver_benchmark.hpp"  // 经验选择（大矩阵）

#ifdef RFSIM_USE_KLU
#include "klu_solver.hpp"
#endif
#ifdef RFSIM_USE_UMFPACK
#include "umfpack_solver.hpp"
#endif

#include <cctype>
#include <cstring>

namespace rfsim {

namespace {

// Auto 选择的小矩阵阈值。dim < 此值且矩阵稠密时优先 DenseLu。
// 电路 MNA 即使小也通常稀疏，但极小电路（<64 节点）稠密 LU 常数因子更优。
constexpr uint32_t kDenseDimThreshold = 64;

// 判断矩阵是否"稠密"：nnz/dim² 超过此比例视为稠密。
constexpr double kDenseRatio = 0.30;

} // namespace

SolverMethod parseSolverMethod(const std::string& name, std::string* err) {
    // 小写比较
    auto eq = [&](const char* kw) {
        if (name.size() != std::strlen(kw)) return false;
        for (size_t i = 0; i < name.size(); ++i) {
            if (std::tolower(static_cast<unsigned char>(name[i])) !=
                std::tolower(static_cast<unsigned char>(kw[i])))
                return false;
        }
        return true;
    };
    if (name.empty() || eq("auto")) return SolverMethod::Auto;
    if (eq("klu"))      return SolverMethod::Klu;
    if (eq("umfpack") || eq("umf")) return SolverMethod::Umfpack;
    if (eq("dense") || eq("dense-lu") || eq("lu")) return SolverMethod::DenseLu;
    if (eq("bicgstab") || eq("iterative") || eq("iter")) return SolverMethod::BiCgStab;
    if (err) *err = "unknown solver method '" + name + "' (expected: auto/klu/umfpack/dense/bicgstab)";
    return SolverMethod::Auto;
}

const char* solverMethodName(SolverMethod m) {
    switch (m) {
        case SolverMethod::Auto:    return "auto";
        case SolverMethod::Klu:     return "klu";
        case SolverMethod::Umfpack: return "umfpack";
        case SolverMethod::DenseLu: return "dense-lu";
        case SolverMethod::BiCgStab:return "bicgstab";
    }
    return "auto";
}

SolverHints hintsFromMatrix(const SparseMatrix& A) {
    SolverHints h;
    h.dim = A.dim();
    // nnz 从 finalize 后的 rowPtr 末值取；未 finalize 时为 0。
    const auto& rp = A.rowPtr();
    if (!rp.empty()) h.nnz = rp.back();
    return h;
}

std::unique_ptr<LinearSolver> makeLinearSolver(SolverMethod method,
                                               const SolverHints& hints) {
    // 升级（用户需求）：大矩阵（dim > kEmpiricalThreshold）且 Auto 时，先尝试经验基准选择。
    // 经验选择会跑候选求解器各 N 次 factorize+solve，选最快的，结果按矩阵指纹缓存。
    // 小矩阵或非 Auto 方法跳过经验选择，走静态规则。
    if (method == SolverMethod::Auto && hints.dim > kEmpiricalThreshold) {
        // hints 只有 dim/nnz，经验选择需要 SparseMatrix —— 调用方应在有大矩阵时
        // 直接用 selectEmpirically(A, hints)。这里 hints 无矩阵引用，故经验选择
        // 通过 makeAutoSolver(A) 路径触发（见下方重载）。此处保留静态规则。
        // （makeLinearSolver(method, hints) 主要服务于已知方法/小矩阵场景。）
    }

    // Auto 策略：决定实际用哪个子类。
    SolverMethod actual = method;
    if (method == SolverMethod::Auto) {
        const uint32_t dim = hints.dim;
        const uint32_t nnz = hints.nnz;
        // 稠密度估计（dim=0 时按稀疏处理，走 KLU 兜底）
        double density = (dim > 0) ? static_cast<double>(nnz) /
                                     (static_cast<double>(dim) * dim)
                                   : 0.0;
        bool smallDense = (dim > 0 && dim < kDenseDimThreshold && density > kDenseRatio);
#ifdef RFSIM_USE_KLU
        actual = smallDense ? SolverMethod::DenseLu : SolverMethod::Klu;
#else
        // 无 KLU 编译：Auto 始终回退 DenseLu。
        actual = SolverMethod::DenseLu;
#endif
    }

    switch (actual) {
        case SolverMethod::Klu: {
#ifdef RFSIM_USE_KLU
            return std::make_unique<KluSolver>();
#else
            // 显式请求 KLU 但未编译：回退 DenseLu（调用方应在 verbose 提示）。
            return std::make_unique<LuSolver>();
#endif
        }
        case SolverMethod::Umfpack: {
#ifdef RFSIM_USE_UMFPACK
            return std::make_unique<UmfpackSolver>();
#else
            return std::make_unique<LuSolver>();
#endif
        }
        case SolverMethod::DenseLu:
            return std::make_unique<LuSolver>();
        case SolverMethod::BiCgStab:
            // 迭代求解器始终可用（iterative_solver.cpp 同库编译）。
            return std::make_unique<BiCgStabSolver>();
        case SolverMethod::Auto:
            // 理论不可达（上面已解析 Auto），防御性回退。
            return std::make_unique<LuSolver>();
    }
    return std::make_unique<LuSolver>();
}

// 升级：makeAutoSolver(A) 对大矩阵触发经验基准选择。
std::unique_ptr<LinearSolver> makeAutoSolver(const SparseMatrix& A) {
    // 大矩阵（dim > 阈值）：经验基准选最快求解器。
    if (EmpiricalSolverSelector::enabledForDim(A.dim())) {
        auto empiric = EmpiricalSolverSelector::instance().select(A, hintsFromMatrix(A));
        if (empiric) return empiric;
        // 经验选择失败（如所有候选都奇异）→ 落到静态规则
    }
    return makeLinearSolver(SolverMethod::Auto, hintsFromMatrix(A));
}

} // namespace rfsim
