// Bounded attempts must preserve caller state when a graph/pivot is unsuitable.
#include "linear_solver.h"
#include <iostream>
#include <stdexcept>
#ifdef __linux__
#include <sys/resource.h>
#endif
using namespace tcad;
static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
int main() {
    try {
#ifdef __linux__
        // An 8192-square binary128 matrix alone needs 1 GiB. These calls must
        // complete under 128 MiB, including the graph and band workspaces.
        struct rlimit limit{128u*1024u*1024u,128u*1024u*1024u};
        require(setrlimit(RLIMIT_AS,&limit)==0,"cannot install memory limit");
#endif
        LinearSolver solver;
        const size_t n=8192;
        Vector sentinel{TCAD_CONST(17.0),TCAD_CONST(-9.0)};
        for (bool pivot : {false,true}) {
            SparseMatrix matrix(n);
            // Species ordering obscures a chain or disconnected 2x2 blocks.
            auto index=[&](size_t i){return (i%2)*(n/2)+i/2;};
            Vector expected(n);
            for(size_t i=0;i<n;++i) {
                const size_t row=index(i);
                expected[row]=TCAD_CONST(1.0)+real_t(i%19)/TCAD_CONST(23.0);
                if(pivot) matrix.add_entry(row,index(i^1),TCAD_CONST(2.0));
                else {
                    matrix.add_entry(row,row,TCAD_CONST(4.0));
                    if(i)matrix.add_entry(row,index(i-1),TCAD_CONST(-1.0));
                    if(i+1<n)matrix.add_entry(row,index(i+1),TCAD_CONST(-0.5));
                }
            }
            matrix.finalize();const Vector rhs=matrix.apply(expected);Vector actual=sentinel;
            require(solver.try_banded_direct(matrix,rhs,actual),"bounded known solution rejected");
            const Vector applied=matrix.apply(actual);
            for(size_t i=0;i<n;++i) {
                require(abs_q(actual[i]-expected[i])<TCAD_CONST(1e-26),"bounded solution inaccurate");
                require(abs_q(applied[i]-rhs[i])<TCAD_CONST(1e-26),"original equations failed");
            }
            std::cout<<"bounded known solution n="<<n<<" pivot="<<pivot<<" passed\n";
        }
        for (bool star : {false,true}) {
            SparseMatrix matrix(n);
            if(star) for(size_t i=0;i<n;++i) {
                matrix.add_entry(i,i,TCAD_CONST(4.0));
                if(i) {matrix.add_entry(0,i,TCAD_CONST(1.0));matrix.add_entry(i,0,TCAD_CONST(1.0));}
            }
            matrix.finalize();Vector actual=sentinel;
            require(!solver.try_banded_direct(matrix,Vector(n,TCAD_CONST(1.0)),actual),"unsuitable matrix accepted");
            require(actual==sentinel,"failed bounded attempt changed caller solution");
            std::cout<<"bounded refusal n="<<n<<" star="<<star<<" preserved state\n";
        }
        for(size_t size : {size_t(0),size_t(8)}) {
            SparseMatrix matrix(size);for(size_t i=0;i<size;++i)matrix.add_entry(i,i,TCAD_CONST(1.0));matrix.finalize();
            Vector actual=sentinel;
            require(!solver.try_banded_direct(matrix,Vector(size,TCAD_CONST(1.0)),actual),"tiny graph should retain normal backend");
            require(actual==sentinel,"tiny graph refusal changed solution");
        }
        SparseMatrix matrix(3);matrix.finalize();Vector actual=sentinel;bool rejected=false;
        try {solver.try_banded_direct(matrix,Vector(2,TCAD_CONST(1.0)),actual);}
        catch(const std::invalid_argument&){rejected=true;}
        require(rejected && actual==sentinel,"dimension error not transactional");
        std::cout<<"tiny graphs and dimension rejection preserved state; memory limit 128 MiB\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
