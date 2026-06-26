// vector_fit.hpp — Vector Fitting 有理逼近算法
//
// 从频域数据（如 S 参数）拟合有理函数：
// H(s) = Σ_k (r_k / (s - p_k)) + d + s*e
//
// 其中 p_k 是极点，r_k 是留数，d 是常数项，e 是比例项

#ifndef RFSIM_SPARAM_VECTOR_FIT_HPP
#define RFSIM_SPARAM_VECTOR_FIT_HPP

#include <vector>
#include <complex>

namespace rfsim {

struct VFResult {
    std::vector<std::complex<double>> poles;      // 极点 p_k
    std::vector<std::complex<double>> residues;   // 留数 r_k
    std::complex<double> constant;                // 常数项 d
    std::complex<double> proportional;            // 比例项 e
    double rms_error;                             // 拟合误差
    bool converged;                               // 是否收敛
};

// Vector Fitting 主函数（两阶段: 极点重定位迭代 + 最终留数求解）
// freqs: 频率点 (Hz)
// H: 频域响应数据 H(jω)
// num_poles: 极点数量
// num_iters: 极点重定位最大迭代次数
// tol: 收敛容差(相邻两次迭代 rms_error 相对变化)
VFResult vectorFit(
    const std::vector<double>& freqs,
    const std::vector<std::complex<double>>& H,
    int num_poles = 10,
    int num_iters = 10,
    double tol = 1e-6
);

// 固定极点求解留数（用于 N×N Y 矩阵共享同一组极点的场景）
// 极点固定为 poles,直接最小二乘解 H(s) = Σ r_k/(s-p_k) + d + s*e
VFResult vectorFitFixedPoles(
    const std::vector<double>& freqs,
    const std::vector<std::complex<double>>& H,
    const std::vector<std::complex<double>>& poles
);

} // namespace rfsim

#endif // RFSIM_SPARAM_VECTOR_FIT_HPP
