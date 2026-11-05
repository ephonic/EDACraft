#include "linear_solver.h"
#include <iostream>
#include <algorithm>
#include <string>
using namespace tcad;
int main(int argc,char**argv){
    if(argc!=4)return 2;
    const std::string mode=argv[1];
    real_t amplitude=strtoflt128(argv[2],nullptr);
    if(!isfinite_q(amplitude)||amplitude<=0)return 3;
    const size_t n=mode=="restart"?9:2;
    SparseMatrix A(n);Vector truth(n,amplitude/TCAD_CONST(2.0)),x(n,TCAD_CONST(0.0));
    if(n==2){
        A.add_entry(0,0,TCAD_CONST(1.0));A.add_entry(0,1,TCAD_CONST(1.0));
        A.add_entry(1,0,TCAD_CONST(-1.0));A.add_entry(1,1,TCAD_CONST(1.0));
    }else{
        for(size_t i=0;i<n;++i){A.add_entry(i,i,TCAD_CONST(4.0));
            if(i)A.add_entry(i,i-1,TCAD_CONST(-1.0));
            if(i+1<n)A.add_entry(i,i+1,TCAD_CONST(-0.5));}
    }
    A.finalize();Vector rhs=A.apply(truth);
    if(mode=="homogeneous"){x=truth;truth.assign(n,TCAD_CONST(0.0));rhs.assign(n,TCAD_CONST(0.0));}
    if(mode=="warm")x=truth;
    SolverOptions o;o.type=SolverType::GMRES;
    o.prec=std::string(argv[3])=="ilu"?PreconditionerType::ILU0:PreconditionerType::DIAGONAL;
    o.restart=n==9?3:30;o.max_iter=n==9?120:2;o.tol=TCAD_CONST(1e-26);
    const size_t steps=LinearSolver(o).solve(A,rhs,x);Vector applied=A.apply(x);
    real_t error=0,residual=0;bool finite=true;
    for(size_t i=0;i<n;++i){
        if(!isfinite_q(x[i])||!isfinite_q(applied[i]))finite=false;
        error=std::max(error,abs_q((x[i]-truth[i])/amplitude));
        residual=std::max(residual,abs_q((applied[i]-rhs[i])/amplitude));
    }
    std::cout<<"{\"steps\":"<<steps<<",\"budget\":"<<o.max_iter<<",\"mantissa_bits\":"<<real_mantissa_bits()
        <<",\"scaled_error\":"<<double(error)<<",\"scaled_residual\":"<<double(residual)
        <<",\"finite\":"<<(finite?"true":"false")<<"}\n";
}
