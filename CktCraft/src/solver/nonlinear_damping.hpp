// nonlinear_damping.hpp — 非线性 Newton 阻尼策略（Backtracking / Trust-Region / LM）
//
// Phase A2-4：把现有各 solver 内联的 backtracking line-search 抽象为统一阻尼控制器，
// 并新增 Levenberg-Marquardt（自适应 Tikhonov）与 Trust-Region（dogleg）两种策略。
//
// 设计：
//   - DampingController 持有一个自适应 λ（LM 用）或信任域半径 Δ（TR 用）。
//   - 调用方在每轮 Newton 提供：当前 J（稠密行主序）、F、x、Newton 步 dx、‖F‖。
//   - step() 返回阻尼后的 xNew 与接受标志；调用方据此更新 x、J、F。
//   - LM：J_reg = J + λ·diag(JᵀJ)；λ 随成功/失败自适应（成功降 λ 走近 Newton，
//     失败升 λ 走近梯度下降）。比固定 Tikhonov 更鲁棒，对强非线性/病态雅可比收敛更稳。
//   - TR：dogleg 在 Newton 步与最速下降步间插值，半径 Δ 自适应。
//
// 当前实现聚焦 LM（HB-NL 主用，最直接收益）；TR 作为接口预留，内部退化为 LM+步长限幅。
// Backtracking 作为基线策略保留（与现有行为等价）。
//
// 详见 plan（Phase A2 步骤 4）。
#ifndef RFSIM_SOLVER_NONLINEAR_DAMPING_HPP
#define RFSIM_SOLVER_NONLINEAR_DAMPING_HPP

#include <cstdint>
#include <vector>

namespace rfsim {

// 阻尼策略
enum class DampingStrategy {
    Backtracking,       // 回溯线搜索（Armijo），与现有 HB-NL/DC 行为等价（基线）
    LevenbergMarquardt, // 自适应 Tikhonov：λ 随收敛情况升降（推荐 HB-NL）
    TrustRegion         // 信任域 dogleg（当前实现退化为 LM + 步长限幅）
};

// 阻尼控制器：跨 Newton 迭代保持自适应状态（λ / Δ）。
// 调用约定（每轮 Newton）：
//   1. 调用方解 J·dx = -F 得 Newton 步 dx（LM 模式下调方应在 solveDampedStep 里把 λ 加进 J 对角）
//   2. 调用 step(...)，控制器内部试步并按策略接受/拒绝、更新 λ/Δ
//   3. 用返回的 xNew 重算 J、F 进入下一轮
class DampingController {
public:
    // dim: 未知量维度（用于校验）。strategy: 阻尼策略。
    explicit DampingController(uint32_t dim, DampingStrategy strategy = DampingStrategy::LevenbergMarquardt);

    // 设置初始 λ（LM）/ Δ（TR）。默认 λ=1e-6（与 HB-NL 原 Tikhonov 一致）。
    void setInitialLambda(double lam) { lambda_ = lam; lambdaInit_ = lam; }
    // LM λ 自适应倍率：成功 λ/=lambdaDecrease（更接近 Newton），失败 λ*=lambdaIncrease（更保守）。
    void setLambdaAdapt(double increase, double decrease) {
        lambdaIncrease_ = increase; lambdaDecrease_ = decrease;
    }
    // 步长限幅（所有策略通用，与现有 dvmax 语义一致）：|dx_i| ≤ stepClamp。
    void setStepClamp(double clamp) { stepClamp_ = clamp; }
    DampingStrategy strategy() const { return strategy_; }
    double lambda() const { return lambda_; }
    double trustRadius() const { return trustRadius_; }

    // 把 LM 正则（λ·diag(JᵀJ) 的近似）加到稠密 Jacobian 的对角线。
    // J：行主序 dim×dim。diagScaleSq[i] = max(J[i,k]² over k)（列 i 的雅可比尺度平方）。
    //   标准 LM 用 diag(JᵀJ)，但为避免每轮重算 JᵀJ（O(dim³)），这里用每行/列的最大
    //   |J|² 作尺度估计（Marquardt 原始提议的 scaling），开销 O(dim²)。
    // 调用方在 factorize 前对 J 调用本方法。
    void applyLmRegularization(std::vector<double>& J) const;

    // 阻尼步：试 α=1.0（必要时回溯），判断是否接受。
    //   F, x, dx, fNorm：当前工作点的残差/状态/Newton 步/残差范数。
    //   fTrial：试步后的残差范数（调用方已试算 Xtrial 并算出 ‖F(Xtrial)‖）。
    //   xTrial：试步后的状态（α=1 时）。
    // 返回 {alpha, accepted}。调用方据此 commit 或保持 x。
    //   - Backtracking：Armijo 充分下降（‖F‖² 形式，系数 c=1e-4），失败回溯到 α<minAlpha。
    //   - LM：接受则 λ 降（走近 Newton），拒绝则 λ 升（更保守），调用方需用新 λ 重新解 J·dx=-F。
    //   - TR：步长 ‖dx‖ 与 Δ 比较，超出则缩放。
    struct StepResult { double alpha; bool accepted; bool recomputeStep; };
    StepResult step(double fNorm, double fTrial, double alpha,
                    double dxNorm, double xNorm);

    // 重置到初始 λ（跨分析或收敛失败重启时调用）。
    void reset() { lambda_ = lambdaInit_; trustRadius_ = trustRadiusInit_; }

private:
    uint32_t dim_;
    DampingStrategy strategy_;
    double lambda_ = 1e-6;
    double lambdaInit_ = 1e-6;
    double lambdaIncrease_ = 4.0;   // 失败时 λ *= 4
    double lambdaDecrease_ = 2.0;   // 成功时 λ /= 2
    double trustRadius_ = 1.0;
    double trustRadiusInit_ = 1.0;
    double stepClamp_ = 0.5;        // |dx_i| 限幅（默认 dvmax=0.5）
};

} // namespace rfsim

#endif // RFSIM_SOLVER_NONLINEAR_DAMPING_HPP
