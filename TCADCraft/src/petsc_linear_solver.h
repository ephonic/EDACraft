#pragma once

#ifdef TCAD_USE_PETSC

#include "sparse_matrix.h"
#include "linear_solver.h"
#include <petsc.h>
#include <string>

namespace tcad {

/**
 * PETSc-based linear solver wrapper.
 * 
 * Converts tcad::SparseMatrix (CSR) to PETSc Mat and solves with KSP.
 * Supports CG, BiCGStab, GMRES with AMG/ILU/Jacobi preconditioning.
 * 
 * Designed for 3D large-scale problems where native solvers struggle.
 */
class PetscLinearSolver {
public:
    explicit PetscLinearSolver(const SolverOptions& opt = {});
    ~PetscLinearSolver();

    // Solve A*x = b, returns number of KSP iterations
    size_t solve(const SparseMatrix& A, const Vector& b, Vector& x);

    // Static helper: initialize/finalize PETSc (call once per process)
    static void initialize(int argc = 0, char** argv = nullptr);
    static void finalize();
    static bool is_initialized();

private:
    SolverOptions opt_;
    bool initialized_here_ = false;

    void set_ksp_type(KSP ksp);
    void set_pc_type(PC pc);
    
    // Convert tcad CSR to PETSc SeqAIJ matrix (creates new Mat each call)
    Mat create_matrix(const SparseMatrix& A);
    Vec create_vec(const Vector& v);
    void copy_vec(Vec src, Vector& dst);
};

} // namespace tcad

#endif // TCAD_USE_PETSC
