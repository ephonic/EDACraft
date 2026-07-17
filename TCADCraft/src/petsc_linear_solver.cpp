#ifdef TCAD_USE_PETSC

#include "petsc_linear_solver.h"
#include <iostream>
#include <stdexcept>
#include <vector>

namespace tcad {

static bool petsc_global_initialized = false;

void PetscLinearSolver::initialize(int argc, char** argv) {
    if (!petsc_global_initialized) {
        PetscInitialize(&argc, &argv, nullptr, nullptr);
        petsc_global_initialized = true;
    }
}

void PetscLinearSolver::finalize() {
    if (petsc_global_initialized) {
        PetscFinalize();
        petsc_global_initialized = false;
    }
}

bool PetscLinearSolver::is_initialized() {
    PetscBool flag;
    PetscInitialized(&flag);
    return flag == PETSC_TRUE;
}

PetscLinearSolver::PetscLinearSolver(const SolverOptions& opt) : opt_(opt) {
    if (!is_initialized()) {
        initialize();
        initialized_here_ = true;
    }
}

PetscLinearSolver::~PetscLinearSolver() {
    // We don't finalize PETSc here because it may be shared across instances
}

Mat PetscLinearSolver::create_matrix(const SparseMatrix& A) {
    const PetscInt n = static_cast<PetscInt>(A.rows());
    const PetscInt nnz = static_cast<PetscInt>(A.nnz());
    
    // Convert indices from size_t to PetscInt (safe copy)
    std::vector<PetscInt> row_ptr(A.row_offsets().begin(), A.row_offsets().end());
    std::vector<PetscInt> col_idx(A.col_indices().begin(), A.col_indices().end());
    
    // Convert values from real_t to PetscScalar
    std::vector<PetscScalar> vals(nnz);
    for (PetscInt i = 0; i < nnz; ++i) {
        vals[i] = static_cast<PetscScalar>(A.vals()[i]);
    }
    
    Mat mat;
    MatCreateSeqAIJWithArrays(PETSC_COMM_SELF, n, n,
                               row_ptr.data(), col_idx.data(), vals.data(), &mat);
    MatSetOption(mat, MAT_NO_OFF_PROC_ENTRIES, PETSC_TRUE);
    MatSetOption(mat, MAT_KEEP_NONZERO_PATTERN, PETSC_TRUE);
    return mat;
}

Vec PetscLinearSolver::create_vec(const Vector& v) {
    const PetscInt n = static_cast<PetscInt>(v.size());
    std::vector<PetscScalar> data(n);
    for (PetscInt i = 0; i < n; ++i) {
        data[i] = static_cast<PetscScalar>(v[i]);
    }
    Vec vec;
    VecCreateSeqWithArray(PETSC_COMM_SELF, 1, n, data.data(), &vec);
    return vec;
}

void PetscLinearSolver::copy_vec(Vec src, Vector& dst) {
    const PetscScalar* array;
    VecGetArrayRead(src, &array);
    for (size_t i = 0; i < dst.size(); ++i) {
        dst[i] = static_cast<real_t>(array[i]);
    }
    VecRestoreArrayRead(src, &array);
}

void PetscLinearSolver::set_ksp_type(KSP ksp) {
    switch (opt_.type) {
        case SolverType::CG:
            KSPSetType(ksp, KSPCG);
            break;
        case SolverType::GMRES:
            KSPSetType(ksp, KSPGMRES);
            KSPGMRESSetRestart(ksp, static_cast<PetscInt>(opt_.restart));
            break;
        case SolverType::BICGSTAB:
        case SolverType::BICGSTAB_ILU0:
        default:
            KSPSetType(ksp, KSPBCGS);
            break;
    }
}

void PetscLinearSolver::set_pc_type(PC pc) {
    switch (opt_.prec) {
        case PreconditionerType::NONE:
            PCSetType(pc, PCNONE);
            break;
        case PreconditionerType::DIAGONAL:
            PCSetType(pc, PCJACOBI);
            break;
        case PreconditionerType::IC0:
            PCSetType(pc, PCICC);  // Incomplete Cholesky (for SPD)
            break;
        case PreconditionerType::ILU0:
        default:
            #if defined(PETSC_HAVE_HYPRE)
                // Use HYPRE BoomerAMG for 3D problems if available
                PCSetType(pc, PCHYPRE);
                PCHYPRESetType(pc, "boomeramg");
            #else
                PCSetType(pc, PCILU);
                PCFactorSetLevels(pc, 0);
            #endif
            break;
    }
}

size_t PetscLinearSolver::solve(const SparseMatrix& A, const Vector& b, Vector& x) {
    const PetscInt n = static_cast<PetscInt>(A.rows());
    if (b.size() != static_cast<size_t>(n) || x.size() != static_cast<size_t>(n)) {
        throw std::invalid_argument("Size mismatch in PetscLinearSolver::solve");
    }

    // Create PETSc objects from tcad data
    Mat mat = create_matrix(A);
    
    // For rhs and initial guess, we need persistent arrays until Vec is destroyed
    std::vector<PetscScalar> b_data(n), x_data(n);
    for (PetscInt i = 0; i < n; ++i) {
        b_data[i] = static_cast<PetscScalar>(b[i]);
        x_data[i] = static_cast<PetscScalar>(x[i]);
    }
    
    Vec rhs, sol;
    VecCreateSeqWithArray(PETSC_COMM_SELF, 1, n, b_data.data(), &rhs);
    VecCreateSeqWithArray(PETSC_COMM_SELF, 1, n, x_data.data(), &sol);

    // Create KSP solver
    KSP ksp;
    KSPCreate(PETSC_COMM_SELF, &ksp);
    KSPSetOperators(ksp, mat, mat);
    set_ksp_type(ksp);
    
    PC pc;
    KSPGetPC(ksp, &pc);
    set_pc_type(pc);
    
    KSPSetTolerances(ksp, static_cast<PetscReal>(opt_.tol),
                     PETSC_DEFAULT, PETSC_DEFAULT,
                     static_cast<PetscInt>(opt_.max_iter));
    KSPSetFromOptions(ksp);  // Allow command-line overrides
    
    // Solve
    KSPSolve(ksp, rhs, sol);
    
    // Check convergence
    KSPConvergedReason reason;
    KSPGetConvergedReason(ksp, &reason);
    PetscInt iter;
    KSPGetIterationNumber(ksp, &iter);
    
    if (reason < 0 && opt_.verbose) {
        std::cerr << "PETSc KSP did not converge, reason: " << reason << std::endl;
    }
    
    // Copy solution back
    copy_vec(sol, x);
    
    // Cleanup
    KSPDestroy(&ksp);
    VecDestroy(&rhs);
    VecDestroy(&sol);
    MatDestroy(&mat);
    
    if (reason < 0) {
        throw std::runtime_error("PETSc KSP solver failed to converge");
    }
    return static_cast<size_t>(iter);
}

} // namespace tcad

#endif // TCAD_USE_PETSC
