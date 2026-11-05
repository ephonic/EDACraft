// Include the production TU to exercise its private continuity dispatcher.
// This keeps the dispatch test out of the public solver API. The static
// library supplies other dependencies without linking a second Gummel object.
#include "../../src/gummel_solver.cpp"
#include <sstream>
#include <stdexcept>
#include <string>
#ifdef __linux__
#include <sys/resource.h>
#endif
using namespace tcad;
struct Capture {
    std::ostringstream stream;
    std::streambuf* previous = std::cerr.rdbuf(stream.rdbuf());
    ~Capture() { std::cerr.rdbuf(previous); }
};
static void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
int main(int argc, char** argv) {
    if (argc != 2) return 1;
    try {
#ifdef __linux__
        struct rlimit limit{128u*1024u*1024u,128u*1024u*1024u};
        check(setrlimit(RLIMIT_AS,&limit)==0,"memory limit unavailable");
#endif
        const std::string mode=argv[1];
        const bool cached=mode=="cached" || mode=="refusal_recover" || mode=="refusal_fail";
        const bool refusal=mode=="refusal_recover" || mode=="refusal_fail";
        const bool small=mode=="dense_small" || mode=="explicit_dense" || mode=="threshold";
        check(cached || small || mode=="retry" || mode=="primary","unknown mode");
        const size_t count=mode=="threshold"?32:(small?17:4097);
        SparseMatrix matrix(count);
        Vector truth(count),rhs(count),initial(count,TCAD_CONST(2.0));
        for(size_t i=0;i<count;++i) truth[i]=refusal?TCAD_CONST(2.0):TCAD_CONST(2.0)+real_t(i%3)/10;
        // Form RHS independently of SparseMatrix::apply.
        for(size_t i=0;i<count;++i) {
            if(refusal && i==0) {rhs[i]=mode=="refusal_fail"?TCAD_CONST(1.0):TCAD_CONST(0.0);continue;}
            matrix.add_entry(i,i,TCAD_CONST(4.0));rhs[i]=4*truth[i];
            if(mode=="dense_small") {
                for(size_t j=0;j<count;++j) if(i!=j) {
                    matrix.add_entry(i,j,TCAD_CONST(.01));rhs[i]+=TCAD_CONST(.01)*truth[j];
                }
            } else if(!refusal) {
                if(i) {matrix.add_entry(i,i-1,-TCAD_CONST(1.0));rhs[i]-=truth[i-1];}
                if(i+1<count) {matrix.add_entry(i,i+1,-TCAD_CONST(1.0));rhs[i]-=truth[i+1];}
            }
        }
        matrix.finalize();
        SolverOptions options;options.type=mode=="explicit_dense"?SolverType::DENSE_DIRECT:SolverType::GMRES;
        options.prec=PreconditionerType::NONE;options.tol=TCAD_CONST(1e-18);
        options.max_iter=(mode=="retry" || mode=="refusal_fail" || mode=="dense_small")?0:100;
        options.restart=30;
        LinearSolver primary(options);bool use_banded=cached;Vector solution;
        Capture capture;
        const bool solved=solve_continuity_linear_system(matrix,rhs,initial,primary,options,"Test",use_banded,solution);
        const std::string log=capture.stream.str();
        check(log.find("bad_alloc")==std::string::npos,"automatic retry reached dense allocation");
        check(log.find("small dense retry failed")==std::string::npos,"small dense retry failed");
        if(refusal) {
            check(log.find("bounded band unavailable; resuming primary")!=std::string::npos,"cached refusal did not resume primary");
            check(!use_banded,"rejected band remained cached");
        }
        if(mode=="refusal_fail") check(!solved,"inconsistent equation was accepted");
        else {
            check(solved,"valid continuity equation was rejected");
            for(size_t i=0;i<count;++i)
                check(abs_q(solution[i]-truth[i])<TCAD_CONST(1e-10),"solution differs from prescribed populations");
            check(scaled_linear_residual(matrix,rhs,solution)<=TCAD_CONST(1e-8),"original equation audit failed");
            const bool expected_band=mode=="cached" || mode=="retry";
            check(use_banded==expected_band,"unexpected band cache state");
            if(mode=="cached")check(log.find("cached bounded band accepted")!=std::string::npos,"cached band path not exercised");
            if(mode=="retry")check(log.find("switched to bounded float128")!=std::string::npos,"band retry not exercised");
            if(mode=="primary")check(log.find("bounded band")==std::string::npos,"successful primary unexpectedly retried");
        }
        std::cout<<"{\"mode\":\""<<mode<<"\",\"nodes\":"<<count
                 <<",\"converged\":"<<(solved?"true":"false")
                 <<",\"band_cached\":"<<(use_banded?"true":"false")
                 <<",\"memory_limit_MiB\":128}\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
