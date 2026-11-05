#include "linear_solver.h"
#include <algorithm>
#include <iostream>
#include <string>
using namespace tcad;
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string mode(argv[1]);
    const size_t n = mode == "dense" ? 64 : 768;
    SparseMatrix a(n);
    Vector truth(n), row_scale(n), unit(n);
    const bool scaled = mode == "species" || mode == "disconnected";
    auto index = [&](size_t i) { return scaled ? (i % 3) * (n / 3) + i / 3 : i; };
    for (size_t i = 0; i < n; ++i) {
        const size_t k = index(i);
        unit[k] = scaled ? pow_q(TCAD_CONST(10.0), real_t(int(i % 7) - 3) * 8) : TCAD_CONST(1.0);
        row_scale[k] = scaled ? pow_q(TCAD_CONST(10.0), real_t(int(i % 9) - 4) * 30) : TCAD_CONST(1.0);
        truth[k] = unit[k] * (TCAD_CONST(1.0) + real_t(i % 19) / 23);
    }
    auto add = [&](size_t i, size_t j, real_t value) {
        a.add_entry(index(i), index(j), row_scale[index(i)] * value / unit[index(j)]);
    };
    for (size_t i = 0; i < n; ++i) {
        if (mode == "dense") {
            add(i, i, TCAD_CONST(100.0));
            for (size_t j = 0; j < n; ++j)
                if (i != j) add(i, j, real_t(int((i * 13 + j * 17) % 11) - 5) / 128);
        } else if (mode == "pivot" || mode == "disconnected") {
            add(i, i ^ 1, TCAD_CONST(2.0));
            if (mode == "pivot") {
                if (i > 1) add(i, i - 2, TCAD_CONST(0.125));
                if (i + 2 < n) add(i, i + 2, TCAD_CONST(-0.125));
            }
        } else {
            add(i, i, mode == "asymmetric" && i == 0 ? TCAD_CONST(0.0) : TCAD_CONST(4.0));
            if (i) add(i, i - 1, TCAD_CONST(-1.0));
            if (i + 1 < n) add(i, i + 1, TCAD_CONST(-0.5));
            if (mode == "asymmetric" && i > 2) add(i, i - 3, TCAD_CONST(0.125));
            if (mode == "species" && i + 17 < n) add(i, i + 17, TCAD_CONST(0.0625));
        }
    }
    a.finalize();
    const Vector b = a.apply(truth);
    Vector x(n, TCAD_CONST(0.0));
    SolverOptions options; options.type = SolverType::DENSE_DIRECT;
    LinearSolver(options).solve(a, b, x);
    const Vector ax = a.apply(x);
    real_t solution = TCAD_CONST(0.0), backward = TCAD_CONST(0.0);
    for (size_t i = 0; i < n; ++i) {
        solution = std::max(solution, abs_q(x[i] - truth[i]) / abs_q(truth[i]));
        real_t scale = abs_q(b[i]);
        for (size_t e = a.row_offsets()[i]; e < a.row_offsets()[i+1]; ++e)
            scale += abs_q(a.vals()[e] * x[a.col_indices()[e]]);
        backward = std::max(backward, abs_q(ax[i] - b[i]) / std::max(scale, TCAD_CONST(1e-300)));
    }
    std::cout << "{\"mantissa_bits\":" << real_mantissa_bits()
              << ",\"solution_relative\":" << double(solution)
              << ",\"backward_relative\":" << double(backward) << "}\n";
    return real_mantissa_bits() == 113 && solution < TCAD_CONST(1e-26) &&
           backward < TCAD_CONST(1e-28) ? 0 : 1;
}
