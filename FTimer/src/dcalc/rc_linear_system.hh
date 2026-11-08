#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <utility>
#include <vector>

namespace te {

// Passive backward-Euler network. Trees use linear-time elimination; meshes
// retain every resistor and use Cholesky or a residual-checked sparse solve.
class RcLinearSystem {
public:
    struct Edge { uint32_t a, b; double g; };

    bool initialize(size_t n, uint32_t driver, const std::vector<Edge>& edges) {
        if (!n || driver >= n) return false;
        n_ = n; driver_ = driver; edges_ = edges;
        adjacency_.assign(n, {}); conductance_.assign(n, 0.);
        for (const auto& e : edges) {
            if (e.a >= n || e.b >= n || e.a == e.b || !(e.g > 0.) || !std::isfinite(e.g))
                return false;
            adjacency_[e.a].push_back({e.b, e.g});
            adjacency_[e.b].push_back({e.a, e.g});
            conductance_[e.a] += e.g; conductance_[e.b] += e.g;
        }
        parent_.assign(n, UINT32_MAX); parent_g_.assign(n, 0.);
        order_ = {driver}; parent_[driver] = driver;
        for (size_t k = 0; k < order_.size(); ++k)
            for (auto [v, g] : adjacency_[order_[k]]) {
                if (parent_[v] != UINT32_MAX) continue;
                parent_[v] = order_[k]; parent_g_[v] = g; order_.push_back(v);
            }
        tree_ = edges.size() == n - 1;
        return order_.size() == n; // Disconnected extractions remain invalid.
    }

    bool factor(const std::vector<double>& cd) {
        if (cd.size() != n_) return false;
        diagonal_ = conductance_;
        for (size_t i = 0; i < n_; ++i) {
            if (cd[i] < 0. || !std::isfinite(cd[i])) return false;
            diagonal_[i] += cd[i];
        }
        if (tree_) {
            reduced_ = diagonal_;
            for (size_t k = n_; k-- > 1;) {
                const auto u = order_[k];
                if (!(reduced_[u] > 0.)) return false;
                reduced_[parent_[u]] -= parent_g_[u] * parent_g_[u] / reduced_[u];
            }
            driver_diagonal = reduced_[driver_];
            return driver_diagonal > 0.;
        }
        cholesky_.clear();
        if (n_ <= 256) {
            cholesky_.assign(n_ * n_, 0.);
            for (size_t i = 0; i < n_; ++i) cholesky_[i*n_+i] = diagonal_[i];
            for (const auto& e : edges_) {
                cholesky_[e.a*n_+e.b] -= e.g; cholesky_[e.b*n_+e.a] -= e.g;
            }
            for (size_t i = 0; i < n_; ++i) for (size_t j = 0; j <= i; ++j) {
                double sum = cholesky_[i*n_+j];
                for (size_t k = 0; k < j; ++k) sum -= cholesky_[i*n_+k]*cholesky_[j*n_+k];
                if (i == j) {
                    if (!(sum > 0.)) return false;
                    cholesky_[i*n_+j] = std::sqrt(sum);
                } else cholesky_[i*n_+j] = sum/cholesky_[j*n_+j];
            }
        }
        std::vector<double> source(n_, 0.); source[driver_] = 1.;
        if (!solve(source, response_) || !(response_[driver_] > 0.)) return false;
        driver_diagonal = 1./response_[driver_];
        return std::isfinite(driver_diagonal);
    }

    bool reduce(const std::vector<double>& rhs) {
        if (tree_) {
            reduced_rhs_ = rhs;
            for (size_t k = n_; k-- > 1;) {
                const auto u = order_[k];
                reduced_rhs_[parent_[u]] += parent_g_[u]*reduced_rhs_[u]/reduced_[u];
            }
            driver_rhs = reduced_rhs_[driver_];
        } else {
            if (!solve(rhs, particular_)) return false;
            driver_rhs = particular_[driver_]*driver_diagonal;
        }
        return std::isfinite(driver_rhs);
    }

    void back_substitute(double driver_voltage, std::vector<double>& voltage) const {
        voltage.resize(n_); voltage[driver_] = driver_voltage;
        if (tree_) {
            for (size_t k = 1; k < n_; ++k) {
                const auto u = order_[k];
                voltage[u] = (reduced_rhs_[u]+parent_g_[u]*voltage[parent_[u]])/reduced_[u];
            }
        } else {
            const double current = (driver_voltage-particular_[driver_])*driver_diagonal;
            for (size_t i = 0; i < n_; ++i) voltage[i] = particular_[i]+response_[i]*current;
            voltage[driver_] = driver_voltage;
        }
    }

    double driver_diagonal = 0., driver_rhs = 0.;

private:
    void multiply(const std::vector<double>& x, std::vector<double>& y) const {
        y.resize(n_);
        for (size_t i = 0; i < n_; ++i) y[i] = diagonal_[i]*x[i];
        for (const auto& e : edges_) { y[e.a] -= e.g*x[e.b]; y[e.b] -= e.g*x[e.a]; }
    }
    static double dot(const std::vector<double>& a, const std::vector<double>& b) {
        return std::inner_product(a.begin(), a.end(), b.begin(), 0.);
    }
    bool solve(const std::vector<double>& b, std::vector<double>& x) const {
        x.assign(n_, 0.);
        if (!cholesky_.empty()) {
            for (size_t i = 0; i < n_; ++i) {
                double v = b[i];
                for (size_t j = 0; j < i; ++j) v -= cholesky_[i*n_+j]*x[j];
                x[i] = v/cholesky_[i*n_+i];
            }
            for (size_t i = n_; i-- > 0;) {
                double v = x[i];
                for (size_t j = i+1; j < n_; ++j) v -= cholesky_[j*n_+i]*x[j];
                x[i] = v/cholesky_[i*n_+i];
            }
            return true;
        }
        std::vector<double> r = b, z(n_), p(n_), ap(n_);
        const double norm = dot(b, b);
        if (norm == 0.) return true;
        for (size_t i = 0; i < n_; ++i) {
            if (!(diagonal_[i] > 0.)) return false;
            z[i] = r[i]/diagonal_[i];
        }
        p = z; double rz = dot(r, z);
        for (size_t k = 0; k < std::min<size_t>(4096, 2*n_+32); ++k) {
            multiply(p, ap); const double denom = dot(p, ap);
            if (!(denom > 0.)) return false;
            const double alpha = rz/denom;
            for (size_t i = 0; i < n_; ++i) { x[i] += alpha*p[i]; r[i] -= alpha*ap[i]; }
            if (dot(r, r) <= norm*1e-20) {
                multiply(x, ap);
                for (size_t i = 0; i < n_; ++i) ap[i] -= b[i];
                return dot(ap, ap) <= norm*1e-18;
            }
            for (size_t i = 0; i < n_; ++i) z[i] = r[i]/diagonal_[i];
            const double next = dot(r, z), beta = next/rz;
            for (size_t i = 0; i < n_; ++i) p[i] = z[i]+beta*p[i];
            rz = next;
        }
        return false;
    }
    size_t n_ = 0; uint32_t driver_ = 0; bool tree_ = false;
    std::vector<Edge> edges_;
    std::vector<std::vector<std::pair<uint32_t, double>>> adjacency_;
    std::vector<uint32_t> parent_, order_;
    std::vector<double> parent_g_, conductance_, diagonal_, reduced_, reduced_rhs_;
    std::vector<double> cholesky_, response_, particular_;
};

} // namespace te
