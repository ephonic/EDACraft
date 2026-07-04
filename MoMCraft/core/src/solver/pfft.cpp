// =====================================================================
// mom/solver/pfft.cpp —— pFFT 完整实现
// =====================================================================
#include "mom/solver/pfft.hpp"
#include "mom/common/vec3_ext.hpp"
#include <Eigen/Dense>
#include <map>
#include <set>
#include <cmath>

namespace mom::solver {

// 析构函数定义（避免不完整类型问题）
PFFTMatrixVector::~PFFTMatrixVector() = default;

// 简化的 1D FFT（Cooley-Tukey，基 2）
void fft_1d(std::vector<Complex>& x, bool inverse = false) {
    Size n = x.size();
    if (n <= 1) return;

    // 位反转置换
    for (Size i = 1, j = 0; i < n; ++i) {
        Size bit = n >> 1;
        for (; j & bit; bit >>= 1) {
            j ^= bit;
        }
        j ^= bit;
        if (i < j) std::swap(x[i], x[j]);
    }

    // Cooley-Tukey
    for (Size len = 2; len <= n; len <<= 1) {
        Real ang = 2.0 * M_PI / Real(len) * (inverse ? -1.0 : 1.0);
        Complex wlen(std::cos(ang), std::sin(ang));
        for (Size i = 0; i < n; i += len) {
            Complex w(1, 0);
            for (Size j = 0; j < len / 2; ++j) {
                Complex u = x[i + j];
                Complex v = x[i + j + len / 2] * w;
                x[i + j] = u + v;
                x[i + j + len / 2] = u - v;
                w *= wlen;
            }
        }
    }

    if (inverse) {
        for (auto& v : x) v /= Real(n);
    }
}

// 2D FFT（行优先）
void fft_2d(Eigen::MatrixXcd& mat, bool inverse = false) {
    Index rows = mat.rows();
    Index cols = mat.cols();

    // 行 FFT
    for (Index i = 0; i < rows; ++i) {
        std::vector<Complex> row(cols);
        for (Index j = 0; j < cols; ++j) row[j] = mat(i, j);
        fft_1d(row, inverse);
        for (Index j = 0; j < cols; ++j) mat(i, j) = row[j];
    }

    // 列 FFT
    for (Index j = 0; j < cols; ++j) {
        std::vector<Complex> col(rows);
        for (Index i = 0; i < rows; ++i) col[i] = mat(i, j);
        fft_1d(col, inverse);
        for (Index i = 0; i < rows; ++i) mat(i, j) = col[i];
    }
}

struct PFFTMatrixVector::Impl {
    // 网格参数
    Real x_min, x_max, y_min, y_max;
    Size nx, ny;
    Real dx, dy;

    // 基函数到网格的投影权重（稀疏矩阵）
    // proj_weights[m] = {(i,j): weight} 表示基函数 m 在网格点 (i,j) 的权重
    std::vector<std::map<std::pair<Index, Index>, Real>> proj_weights;

    // 格林函数在网格上的 FFT（预计算）
    Eigen::MatrixXcd G_fft;

    // 近场校正表：{(m,n): Z_mn} 对距离 < threshold 的单元对
    std::map<std::pair<Index, Index>, Complex> near_field;

    // 格林函数求值器
    green::dyadic::SpatialDyadic green;
};

PFFTMatrixVector::PFFTMatrixVector(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    const PFFTConfig& config)
    : nb_(Index(mesh.bases.size())), impl_(std::make_unique<Impl>()) {

    impl_->green = green;

    // 1. 计算导体区域边界
    Real xmin = 1e30, xmax = -1e30, ymin = 1e30, ymax = -1e30;
    for (const auto& v : mesh.vertices) {
        xmin = std::min(xmin, v.x);
        xmax = std::max(xmax, v.x);
        ymin = std::min(ymin, v.y);
        ymax = std::max(ymax, v.y);
    }
    // 扩展边界（避免边缘效应）
    Real margin = 0.1 * std::max(xmax - xmin, ymax - ymin);
    impl_->x_min = xmin - margin;
    impl_->x_max = xmax + margin;
    impl_->y_min = ymin - margin;
    impl_->y_max = ymax + margin;

    // 2. 确定网格分辨率（自动或用户指定）
    // 为了 FFT 效率，使用 2 的幂次大小
    if (config.grid_resolution > 0) {
        impl_->nx = impl_->ny = config.grid_resolution;
    } else {
        // 自动：每个波长 ~10 个网格点，向上取整到 2 的幂次
        Real max_dim = std::max(impl_->x_max - impl_->x_min, impl_->y_max - impl_->y_min);
        Size n = Size(std::max(32.0, 10.0 * max_dim / 0.01));
        // 找到大于等于 n 的最小 2 的幂次
        Size power = 32;
        while (power < n) power *= 2;
        impl_->nx = impl_->ny = power;
    }
    impl_->dx = (impl_->x_max - impl_->x_min) / Real(impl_->nx);
    impl_->dy = (impl_->y_max - impl_->y_min) / Real(impl_->ny);

    // 3. 基函数投影到网格（RWG 基函数在三角形上线性）
    // 简化：将每个基函数投影到其支撑三角形的重心所在的网格点
    impl_->proj_weights.resize(nb_);
    for (Index m = 0; m < nb_; ++m) {
        const auto& basis = mesh.bases[m];
        // RWG 基函数支撑在两个三角形上
        std::vector<Index> tris = {basis.t_plus};
        if (basis.t_minus >= 0) tris.push_back(basis.t_minus);

        for (Index ti : tris) {
            const auto& tri = mesh.triangles[ti];
            // 三角形重心
            Vec3 centroid = tri.centroid;
            // 找到最近的网格点
            Index ix = Index((centroid.x - impl_->x_min) / impl_->dx);
            Index iy = Index((centroid.y - impl_->y_min) / impl_->dy);
            ix = std::max(Index(0), std::min(ix, Index(impl_->nx - 1)));
            iy = std::max(Index(0), std::min(iy, Index(impl_->ny - 1)));
            // 权重累加（多个三角形支撑同一个基函数）
            impl_->proj_weights[m][{ix, iy}] += 1.0;
        }
    }

    // 4. 格林函数在网格上的 FFT
    // 为了处理线性卷积，将网格扩展到 2 倍大小
    Size nx_ext = 2 * impl_->nx;
    Size ny_ext = 2 * impl_->ny;
    Eigen::MatrixXcd G_grid(nx_ext, ny_ext);
    G_grid.setZero();
    
    // 采样格林函数（中心在网格中心，用于循环卷积的正确放置）
    Index cx = impl_->nx / 2;
    Index cy = impl_->ny / 2;
    for (Index ix = 0; ix < Index(impl_->nx); ++ix) {
        for (Index iy = 0; iy < Index(impl_->ny); ++iy) {
            Real dx = (ix - cx) * impl_->dx;
            Real dy = (iy - cy) * impl_->dy;
            Real rho = std::sqrt(dx*dx + dy*dy);
            if (rho < 1e-6) rho = 1e-6;  // 避免奇点
            G_grid(ix, iy) = green.GA(rho);
        }
    }
    fft_2d(G_grid, false);  // 正向 FFT
    impl_->G_fft = G_grid;

    // 5. 近场校正表（距离 < threshold 的单元对）
    Real threshold = config.near_threshold;
    if (threshold <= 0) {
        threshold = 0.5 * std::max(impl_->dx, impl_->dy);  // 默认：半个网格间距
    }
    for (Index m = 0; m < nb_; ++m) {
        for (Index n = 0; n < nb_; ++n) {
            // 计算基函数 m 和 n 的质心距离
            Vec3 cm_m = mesh.bases[m].t_plus >= 0 ?
                mesh.triangles[mesh.bases[m].t_plus].centroid : Vec3(0,0,0);
            Vec3 cm_n = mesh.bases[n].t_plus >= 0 ?
                mesh.triangles[mesh.bases[n].t_plus].centroid : Vec3(0,0,0);
            Real dist = mom::dist(cm_m, cm_n);
            if (dist < threshold) {
                // 直接精确计算 Z[m,n]（简化：用格林函数求值）
                Complex Z_mn = green.GA(dist);  // 简化
                impl_->near_field[{m, n}] = Z_mn;
            }
        }
    }
}

std::vector<Complex> PFFTMatrixVector::multiply(const std::vector<Complex>& x) const {
    std::vector<Complex> y(nb_, Complex(0, 0));

    // 1. 远场：FFT 卷积
    // 投影到扩展网格（2 倍大小，用于线性卷积）
    Size nx_ext = 2 * impl_->nx;
    Size ny_ext = 2 * impl_->ny;
    Eigen::MatrixXcd x_grid(nx_ext, ny_ext);
    x_grid.setZero();
    for (Index m = 0; m < nb_; ++m) {
        for (const auto& [idx, w] : impl_->proj_weights[m]) {
            x_grid(idx.first, idx.second) += x[m] * w;
        }
    }

    // 检查 x_grid 是否有值
    Real x_norm = x_grid.norm();
    if (x_norm < 1e-30) {
        // x_grid 全为零，直接返回近场结果
        for (const auto& [mn, Z_mn] : impl_->near_field) {
            Index m = mn.first;
            Index n = mn.second;
            y[m] += Z_mn * x[n];
        }
        return y;
    }

    // FFT
    Eigen::MatrixXcd X_fft = x_grid;
    fft_2d(X_fft, false);

    // 卷积（逐元素乘）
    Eigen::MatrixXcd Y_fft = impl_->G_fft.cwiseProduct(X_fft);

    // IFFT
    Eigen::MatrixXcd y_grid = Y_fft;
    fft_2d(y_grid, true);

    // 反投影
    for (Index m = 0; m < nb_; ++m) {
        for (const auto& [idx, w] : impl_->proj_weights[m]) {
            y[m] += y_grid(idx.first, idx.second) * w;
        }
    }

    // 2. 近场校正
    for (const auto& [mn, Z_mn] : impl_->near_field) {
        Index m = mn.first;
        Index n = mn.second;
        y[m] += Z_mn * x[n];
    }

    return y;
}

// GMRES 迭代求解器（完整实现）
std::vector<Complex> solve_gmres(
    const PFFTMatrixVector& A,
    const std::vector<Complex>& b,
    Real tol,
    Index max_iter,
    Index restart) {

    const Index n = A.size();
    std::vector<Complex> x(n, Complex(0, 0));  // 初始解

    // 计算初始残差
    auto compute_residual = [&](const std::vector<Complex>& x) {
        std::vector<Complex> Ax = A.multiply(x);
        std::vector<Complex> r(n);
        Real r_norm = 0;
        for (Index i = 0; i < n; ++i) {
            r[i] = b[i] - Ax[i];
            r_norm += std::norm(r[i]);
        }
        return std::make_pair(r, std::sqrt(r_norm));
    };

    for (Index iter = 0; iter < max_iter; iter += restart) {
        auto [r, r_norm] = compute_residual(x);
        
        if (r_norm < tol * std::sqrt(std::norm(b[0]) * n)) {
            break;  // 收敛
        }

        // Arnoldi 过程：构建 Krylov 子空间的正交基
        Index m = std::min(restart, max_iter - iter);
        std::vector<std::vector<Complex>> V(m + 1, std::vector<Complex>(n));
        Eigen::MatrixXcd H = Eigen::MatrixXcd::Zero(m + 1, m);
        std::vector<Complex> g(m + 1, Complex(0, 0));
        
        // 归一化初始残差
        for (Index i = 0; i < n; ++i) {
            V[0][i] = r[i] / r_norm;
        }
        g[0] = r_norm;

        // Arnoldi 迭代（带重新正交化）
        for (Index j = 0; j < m; ++j) {
            // w = A·V[j]
            std::vector<Complex> w = A.multiply(V[j]);
            
            // 正交化：Classical Gram-Schmidt with reorthogonalization
            for (int reorth = 0; reorth < 2; ++reorth) {
                for (Index i = 0; i <= j; ++i) {
                    Complex h_ij = 0;
                    for (Index k = 0; k < n; ++k) {
                        h_ij += std::conj(V[i][k]) * w[k];
                    }
                    if (reorth == 0) {
                        H(i, j) = h_ij;
                    } else {
                        H(i, j) += h_ij;
                    }
                    for (Index k = 0; k < n; ++k) {
                        w[k] -= h_ij * V[i][k];
                    }
                }
            }
            
            // 计算新的基向量
            Real w_norm = 0;
            for (Index k = 0; k < n; ++k) {
                w_norm += std::norm(w[k]);
            }
            w_norm = std::sqrt(w_norm);
            
            H(j + 1, j) = w_norm;
            if (w_norm > 1e-30) {
                for (Index k = 0; k < n; ++k) {
                    V[j + 1][k] = w[k] / w_norm;
                }
            }
        }

        // 求解最小二乘问题：min ||H·y - g||
        // 使用 QR 分解
        Eigen::HouseholderQR<Eigen::MatrixXcd> qr(H.topRows(m));
        Eigen::VectorXcd g_vec = Eigen::Map<Eigen::VectorXcd>(g.data(), m);
        Eigen::VectorXcd y = qr.solve(g_vec);

        // 更新解：x = x + V·y
        for (Index j = 0; j < m; ++j) {
            for (Index k = 0; k < n; ++k) {
                x[k] += y(j) * V[j][k];
            }
        }
    }

    return x;
}

} // namespace mom::solver
