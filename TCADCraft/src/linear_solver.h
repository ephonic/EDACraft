#pragma once

#include "sparse_matrix.h"
#include "direct_solver.h"
#include "ilu_preconditioner.h"
#include "ic_preconditioner.h"
#include <functional>

#ifdef TCAD_USE_PETSC
#include <petsc.h>
#include <petscksp.h>
#endif



namespace tcad {

enum class SolverType {
    BICGSTAB,
    BICGSTAB_ILU0,
    GMRES,
    CG,
    JACOBI,
    GAUSS_SEIDEL,
    DENSE_DIRECT,  // Fallback for n < 2000, guarantees convergence
    IR_BICGSTAB,   // Iterative refinement: double BiCGStab + float128 residual
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
    // 1e-16: quad-justified but far cheaper than 1e-25 (BiCGStab iteration
    // count scales with log(1/tol); 1e-25 made 2D/3D sweeps impractically slow).
    real_t tol = 1e-16Q;
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
    size_t solve_ir_bicgstab(const SparseMatrix& A, const Vector& b, Vector& x);
#ifdef TCAD_USE_PETSC
    size_t solve_petsc(const SparseMatrix& A, const Vector& b, Vector& x);
    // PETSc reuse cache: keep Mat/KSP/Vecs across calls when the problem size
    // is unchanged (fixed mesh -> constant sparsity pattern -> SuperLU reuses
    // the symbolic factorization, only numeric refactor each call).  Cuts the
    // per-Gummel-iteration PETSc setup overhead (~50ms x 44 iters x 3 solves).
    Mat petsc_A_ = nullptr;
    KSP petsc_ksp_ = nullptr;
    Vec petsc_b_ = nullptr, petsc_x_ = nullptr;
    PetscInt petsc_n_ = -1;
    void petsc_free();
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
