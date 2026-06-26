#pragma once

#include "sparse_matrix.h"
#include "direct_solver.h"
#include "ilu_preconditioner.h"
#include "ic_preconditioner.h"
#include <functional>



namespace tcad {

enum class SolverType {
    BICGSTAB,
    BICGSTAB_ILU0,
    GMRES,
    CG,
    JACOBI,
    GAUSS_SEIDEL,
    DENSE_DIRECT,  // Fallback for n < 2000, guarantees convergence
    PETSC          // External PETSc solver (CG/GMRES/AMG/ILU)
};

enum class PreconditionerType {
    NONE,
    DIAGONAL,
    ILU0,
    IC0
};

struct SolverOptions {
    SolverType type = SolverType::BICGSTAB_ILU0;
    size_t max_iter = 10000;
    real_t tol = 1e-25Q; // Adjusted: 1e-25 for quad, 1e-12 for double fallback
    size_t restart = 30; // For GMRES
    bool verbose = false;
    PreconditionerType prec = PreconditionerType::ILU0;
};

class LinearSolver {
public:
    explicit LinearSolver(const SolverOptions& opt = {});
    ~LinearSolver();

    // Solve A*x = b, returns number of iterations, throws on failure
    size_t solve(const SparseMatrix& A, const Vector& b, Vector& x);

    static SolverOptions default_poisson_options();
    static SolverOptions default_continuity_options();

private:
    SolverOptions opt_;

    size_t bicgstab(const SparseMatrix& A, const Vector& b, Vector& x);
    size_t gmres(const SparseMatrix& A, const Vector& b, Vector& x);
    size_t cg(const SparseMatrix& A, const Vector& b, Vector& x);
    size_t jacobi(const SparseMatrix& A, const Vector& b, Vector& x);
    size_t gauss_seidel(const SparseMatrix& A, const Vector& b, Vector& x);
    size_t dense_direct(const SparseMatrix& A, const Vector& b, Vector& x);
#ifdef TCAD_USE_PETSC
    size_t solve_petsc(const SparseMatrix& A, const Vector& b, Vector& x);
#endif
};

// Preconditioner interface (simplified diagonal preconditioner)
class DiagonalPreconditioner {
public:
    void setup(const SparseMatrix& A);
    Vector apply(const Vector& r) const;
private:
    Vector inv_diag_;
};

} // namespace tcad
