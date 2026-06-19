// test_gmres.cpp - GMRES solver unit tests
#include "assembly/gmres.hpp"
#include <gtest/gtest.h>
#include <cmath>
#include <random>

using namespace rfsim;

namespace {

class DenseMatrixOp : public LinearOperator {
public:
    DenseMatrixOp(uint32_t n, const std::vector<double>& A)
        : n_(n), A_(A) {}
    uint32_t dim() const noexcept override { return n_; }
    void apply(const std::vector<double>& x, std::vector<double>& y) const override {
        y.assign(n_, 0.0);
        for (uint32_t i = 0; i < n_; ++i)
            for (uint32_t j = 0; j < n_; ++j)
                y[i] += A_[size_t(i) * n_ + j] * x[j];
    }
private:
    uint32_t n_;
    std::vector<double> A_;
};

class IdentityPrecond : public Preconditioner {
public:
    explicit IdentityPrecond(uint32_t n) : n_(n) {}
    uint32_t dim() const noexcept override { return n_; }
    void apply(const std::vector<double>& r, std::vector<double>& z) const override {
        z = r;
    }
private:
    uint32_t n_;
};

class DiagonalPrecond : public Preconditioner {
public:
    DiagonalPrecond(const std::vector<double>& invDiag) : invDiag_(invDiag) {}
    uint32_t dim() const noexcept override { return static_cast<uint32_t>(invDiag_.size()); }
    void apply(const std::vector<double>& r, std::vector<double>& z) const override {
        z.resize(invDiag_.size());
        for (size_t i = 0; i < invDiag_.size(); ++i) z[i] = invDiag_[i] * r[i];
    }
private:
    std::vector<double> invDiag_;
};

} // namespace

TEST(Gmres, Identity) {
    uint32_t n = 5;
    std::vector<double> A(n * n, 0.0);
    for (uint32_t i = 0; i < n; ++i) A[size_t(i) * n + i] = 1.0;
    DenseMatrixOp op(n, A);
    IdentityPrecond pc(n);
    std::vector<double> b(n, 1.0);
    std::vector<double> x(n, 0.0);
    auto r = solveGmres(op, &pc, b, x, GmresOptions{10, 100, 1e-10, 1e-12});
    EXPECT_TRUE(r.converged);
    for (uint32_t i = 0; i < n; ++i) EXPECT_NEAR(x[i], 1.0, 1e-9);
}

TEST(Gmres, RandomWellConditioned) {
    uint32_t n = 20;
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    std::vector<double> A(n * n, 0.0);
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) A[size_t(i) * n + j] = dist(rng);
        A[size_t(i) * n + i] += 10.0;  // 对角占优
    }
    DenseMatrixOp op(n, A);
    IdentityPrecond pc(n);
    std::vector<double> b(n);
    for (uint32_t i = 0; i < n; ++i) b[i] = dist(rng);
    std::vector<double> x(n, 0.0);
    auto r = solveGmres(op, &pc, b, x, GmresOptions{30, 1000, 1e-10, 1e-12});
    EXPECT_TRUE(r.converged);
    // 验证残差
    std::vector<double> Ax;
    op.apply(x, Ax);
    double res = 0;
    for (uint32_t i = 0; i < n; ++i) res += (Ax[i] - b[i]) * (Ax[i] - b[i]);
    EXPECT_LT(std::sqrt(res), 1e-8);
}

TEST(Gmres, DiagonalPreconditioner) {
    uint32_t n = 30;
    std::mt19937 rng(123);
    std::uniform_real_distribution<double> dist(-0.5, 0.5);
    std::vector<double> A(n * n, 0.0);
    std::vector<double> invDiag(n);
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) A[size_t(i) * n + j] = dist(rng);
        A[size_t(i) * n + i] = 1e3;  // 大幅缩放对角
        invDiag[i] = 1.0 / A[size_t(i) * n + i];
    }
    DenseMatrixOp op(n, A);
    DiagonalPrecond pc(invDiag);
    std::vector<double> b(n);
    for (uint32_t i = 0; i < n; ++i) b[i] = dist(rng);
    std::vector<double> x(n, 0.0);
    GmresOptions opts{20, 500, 1e-10, 1e-12};
    auto r = solveGmres(op, &pc, b, x, opts);
    EXPECT_TRUE(r.converged);
}
