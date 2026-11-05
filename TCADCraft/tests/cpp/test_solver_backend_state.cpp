// Backend selection and optional PETSc resources must preserve known equations.
#include "linear_solver.h"
#include <iostream>
#include <stdexcept>
using namespace tcad;
static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
#ifdef TCAD_USE_PETSC
static SparseMatrix matrix(int kind) {
    SparseMatrix a(3);
    for (size_t i=0; i<3; ++i) {
        a.add_entry(i,i,TCAD_CONST(4.0)+kind);
        if (kind==1) a.add_entry(i,(i+1)%3,TCAD_CONST(0.5));
        else if (kind==2) a.add_entry(i,(i+2)%3,TCAD_CONST(-0.25));
    }
    a.finalize();return a;
}
static void solve(LinearSolver& solver, int kind) {
    auto a=matrix(kind);Vector truth{TCAD_CONST(1.5),TCAD_CONST(-2.5),TCAD_CONST(0.25)};
    Vector b=a.apply(truth),x(3,TCAD_CONST(0.0));solver.solve(a,b,x);
    auto ax=a.apply(x);
    for(size_t i=0;i<3;++i) {
        require(abs_q(x[i]-truth[i])<TCAD_CONST(1e-12),"PETSc solution changed across cache use");
        require(abs_q(ax[i]-b[i])<TCAD_CONST(1e-11),"PETSc original equation residual failed");
    }
}
#endif
int main() {
    try {
        for(int bad : {-1,9,2147483647}) {
            bool rejected=false;
            try { LinearSolver::validate_solver_type(bad); }
            catch(const std::invalid_argument&) { rejected=true; }
            require(rejected,"invalid backend accepted");
        }
        for(int valid=0;valid<8;++valid) LinearSolver::validate_solver_type(valid);
#ifdef TCAD_USE_PETSC
        LinearSolver::validate_solver_type(8);
        SolverOptions options;options.type=SolverType::PETSC;options.tol=TCAD_CONST(1e-12);
        LinearSolver original(options);solve(original,0);solve(original,1);solve(original,1);solve(original,2);
        { LinearSolver copied(original);solve(copied,1); }
        solve(original,2);
        LinearSolver assigned(options);solve(assigned,0);assigned=original;solve(assigned,1);
        assigned=assigned;solve(assigned,2);solve(original,1);
        std::cout << "PETSc enabled: changed/same CSR patterns, owned copy, assignment, self-assignment passed\n";
#else
        bool unavailable=false;
        try { LinearSolver::validate_solver_type(8); }
        catch(const std::runtime_error& error) { unavailable=std::string(error.what()).find("PETSc backend unavailable")!=std::string::npos; }
        require(unavailable,"uncompiled PETSc was not rejected");
        std::cout << "portable backend: invalid and uncompiled selections rejected\n";
#endif
    } catch(const std::exception& error) { std::cerr << error.what() << '\n';return 1; }
}
