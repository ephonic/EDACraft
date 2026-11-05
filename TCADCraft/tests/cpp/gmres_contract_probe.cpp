#include "linear_solver.h"
#include <iostream>
#include <algorithm>
#include <string>
using namespace tcad;
int main(int argc,char**argv){
    if(argc!=3)return 2;
    std::string mode=argv[1];size_t budget=std::stoul(argv[2]);
    size_t n=mode=="restart"?9:2;
    SparseMatrix A(n);Vector truth(n,TCAD_CONST(0.5)),x(n,TCAD_CONST(0.0));
    if(mode=="happy" || mode=="zero"){
        A.add_entry(0,0,TCAD_CONST(1.0));A.add_entry(0,1,TCAD_CONST(1.0));
        A.add_entry(1,0,TCAD_CONST(-1.0));A.add_entry(1,1,TCAD_CONST(1.0));
    }else if(mode=="singular"){
        A.add_entry(0,0,TCAD_CONST(0.0));A.add_entry(1,1,TCAD_CONST(0.0));
    }else{
        for(size_t i=0;i<n;++i){A.add_entry(i,i,TCAD_CONST(4.0));
            if(i)A.add_entry(i,i-1,TCAD_CONST(-1.0));
            if(i+1<n)A.add_entry(i,i+1,TCAD_CONST(-0.5));}
    }
    A.finalize();Vector rhs=A.apply(truth);
    if(mode=="singular")rhs.assign(n,TCAD_CONST(1.0));
    if(mode=="warm")x=truth;
    Vector before=x;
    SolverOptions o;o.type=SolverType::GMRES;o.prec=PreconditionerType::DIAGONAL;
    o.restart=mode=="restart"?3:30;o.max_iter=budget;o.tol=TCAD_CONST(1e-26);
    size_t steps=LinearSolver(o).solve(A,rhs,x);Vector applied=A.apply(x);
    real_t error=0,residual=0,rhsnorm=0,change=0;bool finite=true;
    for(size_t i=0;i<n;++i){error=std::max(error,abs_q(x[i]-truth[i]));
        residual=std::max(residual,abs_q(applied[i]-rhs[i]));rhsnorm=std::max(rhsnorm,abs_q(rhs[i]));
        change=std::max(change,abs_q(x[i]-before[i]));finite=finite&&isfinite_q(x[i]);}
    std::cout<<"{\"steps\":"<<steps<<",\"budget\":"<<budget<<",\"mantissa_bits\":"<<real_mantissa_bits()
      <<",\"error\":"<<double(error)<<",\"residual\":"<<double(residual/std::max(rhsnorm,TCAD_CONST(1e-300)))
      <<",\"change\":"<<double(change)<<",\"finite\":"<<(finite?"true":"false")<<"}\n";
}
