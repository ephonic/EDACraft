// Entry rejection before changing Newton mask, history, or lagged DG state.
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include "math_types.h"
#include "poisson_solver.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include "statistics.h"
#define private public
#include "newton_solver.h"
#undef private
using namespace tcad;
namespace {
void check(bool b,const char* message){if(!b)throw std::runtime_error(message);}
std::string exact(real_t x){char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
void append(Vector& to,const Vector& from){to.push_back(static_cast<real_t>(from.size()));to.insert(to.end(),from.begin(),from.end());}
void chars(Vector& to,const std::vector<char>& from){to.push_back(static_cast<real_t>(from.size()));for(char v:from)to.push_back(static_cast<real_t>(v));}
Vector state(const NewtonSolver& s){Vector v{static_cast<real_t>(s.use_lagged_quantum_potential_)};
    chars(v,s.semi_mask_);append(v,s.lagged_Qn_);append(v,s.lagged_Qp_);append(v,s.residuals());
    v.push_back(static_cast<real_t>(s.nonlinear_samples().size()));for(const auto& sample:s.nonlinear_samples())append(v,sample);
    chars(v,s.inactive_n_);chars(v,s.inactive_p_);chars(v,s.fe_mask_);append(v,s.fe_polarization_);append(v,s.lk_previous_);append(v,s.lk_cached_phi_);
    return v;
}
Vector assembly(NewtonSolver s,const Vector& x){Vector f;s.assemble_residual(x,f);SparseMatrix j;s.assemble_jacobian(x,j);
    Vector v=f,dense(225,TCAD_CONST(0.0));for(size_t r=0;r<15;++r)for(size_t k=j.row_offsets()[r];k<j.row_offsets()[r+1];++k)dense[15*r+j.col_indices()[k]]+=j.vals()[k];
    v.insert(v.end(),dense.begin(),dense.end());for(auto q:v)check(isfinite_q(q),"Newton mask assembly nonfinite");return v;
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t fixtures=0,attempts=0,rejected=0,accepted=0,preserved=0,retries=0,refs=0,late_assembly=0,bypassed=0,late_solve=0,lost_history=0;
    size_t equilibrium=0,empty_classical=0,nonbinary=0,clear_restore=0;
    real_t max_equilibrium_phi=0,max_equilibrium_carrier=0;
    auto emit=[&](const char* kind,const Vector& v){std::cout<<"{\"case\":"<<++refs<<",\"kind\":\""<<kind<<"\",\"values\":[";
        for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true})for(bool logs:{false,true})for(int mode=0;mode<3;++mode)for(int kind=0;kind<4;++kind){
        Grid3D g{1,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
        Vector pos{0,TCAD_CONST(.7e-7),TCAD_CONST(1.8e-7),TCAD_CONST(3e-7),TCAD_CONST(4.5e-7)};
        if(axis==0){g.nx=5;if(graded)g.xx=pos;}if(axis==1){g.ny=5;if(graded)g.yx=pos;}if(axis==2){g.nz=5;if(graded)g.zx=pos;}
        NewtonOptions opt;opt.enable_quantum=mode!=0;opt.use_log_space=logs;opt.record_nonlinear_history=true;
        opt.linear_solver=SolverType::DENSE_DIRECT;opt.max_iter=4;opt.abs_tol=TCAD_CONST(1e-18);opt.tol=TCAD_CONST(1e-18);
        NewtonSolver s(g,opt);s.set_effective_dos(Vector(5,TCAD_CONST(1e19)),Vector(5,TCAD_CONST(1e19)));s.set_bandgap(Vector(5,TCAD_CONST(6.0)));
        std::vector<char> mask;if(kind==1)mask=std::vector<char>(5,0);if(kind==2)mask=std::vector<char>(5,1);if(kind==3)mask={0,-1,2,1,0};
        s.set_semiconductor_mask(mask);s.set_density_gradient_coefficients(0,0);
        s.set_phi_dirichlet({{0,0},{4,0}});s.set_electron_bc({{0,TCAD_CONST(2e19)},{4,TCAD_CONST(2e19)}});s.set_hole_bc({{0,TCAD_CONST(2e19)},{4,TCAD_CONST(2e19)}});
        Vector phi(5,0),n(5,TCAD_CONST(2e19)),p=n;
        check(s.solve(phi,n,p),"zero-coefficient public equilibrium failed");
        for(size_t i=0;i<5;++i){max_equilibrium_phi=std::max(max_equilibrium_phi,abs_q(phi[i]));
            max_equilibrium_carrier=std::max(max_equilibrium_carrier,std::max(abs_q(n[i]/TCAD_CONST(2e19)-TCAD_CONST(1.0)),abs_q(p[i]/TCAD_CONST(2e19)-TCAD_CONST(1.0))));}
        check(max_equilibrium_phi<TCAD_CONST(1e-25) && max_equilibrium_carrier<TCAD_CONST(1e-25),"public equilibrium changed physical state");
        check(!s.residuals().empty() && !s.nonlinear_samples().empty(),"public solve did not seed history");++equilibrium;
        Vector public_state=phi;public_state.insert(public_state.end(),n.begin(),n.end());public_state.insert(public_state.end(),p.begin(),p.end());append(public_state,s.residuals());
        for(const auto& sample:s.nonlinear_samples())append(public_state,sample);emit("public-zero-coefficient-equilibrium",public_state);
        s.set_density_gradient_coefficients(TCAD_CONST(4.885e-20),TCAD_CONST(3.432e-20));
        // Synthetic nonzero lagged values exercise the cached branch without
        // claiming a converged nonzero-Q device. Legal setters retain caches.
        s.use_lagged_quantum_potential_=mode==2;s.lagged_Qn_.assign(5,TCAD_CONST(.003));s.lagged_Qp_.assign(5,-TCAD_CONST(.004));
        Vector x(15);for(size_t i=0;i<5;++i){x[i]=TCAD_CONST(.02)*i;n[i]=TCAD_CONST(2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.08)*i*i);p[i]=TCAD_CONST(1.2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.11)*i*i);x[5+i]=logs?log_q(n[i]):n[i];x[10+i]=logs?log_q(p[i]):p[i];}
        const auto control=state(s),assembled=assembly(s,x);Vector reference=assembled;append(reference,control);emit("prescribed-residual-jacobian-cache",reference);
        for(size_t length:{size_t(1),size_t(2),size_t(4),size_t(6),size_t(10)})for(int pattern=0;pattern<2;++pattern){
            std::vector<char> bad(length,0);if(pattern)for(size_t i=0;i<length;++i)bad[i]=(i%3==0?0:i%2?-1:2);
            ++attempts;bool caught=false;try{s.set_semiconductor_mask(bad);}catch(const std::invalid_argument& e){check(std::string(e.what())=="Newton semiconductor mask size mismatch","wrong Newton mask diagnostic");caught=true;++rejected;}
            if(caught){check(state(s)==control,"rejected Newton mask changed persistent state");check(assembly(s,x)==assembled,"rejected Newton mask changed equations");++preserved;}
            else{
                ++accepted;check(observe && s.semi_mask_==bad,"malformed Newton mask accepted");
                bool late=false;try{assembly(s,x);}catch(const std::invalid_argument& e){check(std::string(e.what())=="DG semiconductor mask size mismatch","unexpected late assembly exception");late=true;}
                if(late)++late_assembly;else ++bypassed;check(late==(mode==1),"unexpected cached/disabled mask path");
                NewtonSolver probe=s;Vector a(5,0),b(5,TCAD_CONST(2e19)),c=b;late=false;
                try{check(probe.solve(a,b,c),"disabled-quantum parent retry failed");}catch(const std::invalid_argument& e){check(std::string(e.what())=="DG semiconductor mask size mismatch","unexpected late solve exception");late=true;}
                check(late==(mode!=0),"unexpected late solve classification");if(late){++late_solve;check(probe.residuals().empty() && probe.nonlinear_samples().empty(),"late solve did not reproduce lost history");++lost_history;}
            }
            check(observe || caught,"malformed Newton mask accepted");s.set_semiconductor_mask(mask);check(state(s)==control && assembly(s,x)==assembled,"Newton valid mask retry mismatch");++retries;
        }
        s.set_semiconductor_mask({});NewtonSolver classical=s;classical.opt_.enable_quantum=false;
        check(assembly(s,x)==assembly(classical,x),"empty Newton mask did not disable quantum equations");++empty_classical;
        check(s.lagged_Qn_==Vector(5,TCAD_CONST(.003)) && s.lagged_Qp_==Vector(5,-TCAD_CONST(.004)),"legal empty mask unexpectedly changed cache");
        Vector cleared=assembly(s,x);append(cleared,state(s));emit("empty-mask-classical-equations",cleared);
        s.set_semiconductor_mask(mask);check(state(s)==control && assembly(s,x)==assembled,"clear restore changed Newton equations/state");++clear_restore;
        if(kind==3){s.set_semiconductor_mask({0,1,1,1,0});check(assembly(s,x)==assembled,"nonbinary mask truth values changed equations");++nonbinary;}
        ++fixtures;
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":"<<fixtures<<",\"attempted\":"<<attempts<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<refs<<",\"public_zero_coefficient_equilibria\":"<<equilibrium<<",\"empty_classical_checks\":"<<empty_classical<<",\"nonbinary_checks\":"<<nonbinary<<",\"clear_restore_cases\":"<<clear_restore<<",\"late_assembly_exceptions\":"<<late_assembly<<",\"assembly_bypasses\":"<<bypassed<<",\"late_solve_exceptions\":"<<late_solve<<",\"lost_history_cases\":"<<lost_history<<",\"max_equilibrium_phi\":"<<static_cast<double>(max_equilibrium_phi)<<",\"max_equilibrium_carrier_relative\":"<<static_cast<double>(max_equilibrium_carrier)<<"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
