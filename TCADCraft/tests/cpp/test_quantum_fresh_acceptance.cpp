// Manufactured fixed-Q states expose the damped-refresh stopping defect.
// They are gate counterexamples, not claims of converged physical devices.
#include <bits/stdc++.h>
#define private public
#include "newton_solver.h"
#undef private
#include "newton_quantum_acceptance.h"
using namespace tcad;
using V = std::vector<real_t>;
static void require(bool b,const char* message) { if(!b)throw std::runtime_error(message); }
static real_t B(real_t v) { return abs_q(v)<TCAD_CONST(1e-25)?TCAD_CONST(1.0)-v/TCAD_CONST(2.0):v/expm1_q(v); }
static bool gate(const V& f,const V& scale,real_t abs_tol,real_t tol) {
    real_t blocks[3]={0,0,0},norm=0;
    for(size_t i=0;i<f.size();++i){blocks[i/5]+=f[i]*f[i];norm=std::max(norm,abs_q(f[i]*scale[i]));}
    return (sqrt_q(blocks[0])<abs_tol&&sqrt_q(blocks[1])<abs_tol&&sqrt_q(blocks[2])<abs_tol)||norm<tol;
}
static V independent_q(const V& density,const V& pos,real_t coefficient,real_t vt) {
    V q(5,0);
    for(size_t i=1;i<4;++i) {
        const real_t u=sqrt_q(density[i]);
        const real_t lap=TCAD_CONST(2.0)/(pos[i+1]-pos[i-1])*
            ((sqrt_q(density[i+1])-u)/(pos[i+1]-pos[i])-(u-sqrt_q(density[i-1]))/(pos[i]-pos[i-1]));
        q[i]=std::max(-TCAD_CONST(4.0)*vt,std::min(TCAD_CONST(4.0)*vt,coefficient*lap/u));
    }
    return q;
}
static V currents(const NewtonSolver& s,const V& x,const V& c,const V& q,const V& pos,bool hole) {
    V j(4);const auto& mu=hole?s.mu_p_:s.mu_n_;
    const real_t sign=hole?-TCAD_CONST(1.0):TCAD_CONST(1.0);
    for(size_t i=0;i<4;++i) {
        const real_t d=pos[i+1]-pos[i],vl=x[i]+sign*q[i],vr=x[i+1]+sign*q[i+1];
        real_t m=TCAD_CONST(2.0)*mu[i]*mu[i+1]/(mu[i]+mu[i+1]+TCAD_CONST(1e-30));
        if(s.opt_.hfs_enabled) {
            real_t force=abs_q(vr-vl)/d;
            if(s.opt_.hfs_driving==0)force=abs_q(vr-vl-sign*s.VT_*log_q(c[i+1]/c[i]))/d;
            const real_t vs=hole?s.opt_.hfs_vsat_p:s.opt_.hfs_vsat_n;
            const real_t beta=hole?s.opt_.hfs_beta_p:s.opt_.hfs_beta_n;
            const real_t r=m*force/vs;
            if(r>TCAD_CONST(1e-12))m/=pow_q(TCAD_CONST(1.0)+pow_q(r,beta),TCAD_CONST(1.0)/beta);
        }
        const real_t v=(vr-vl)/s.VT_;
        j[i]=QE*m*s.VT_/d*(hole?c[i]*B(v)-c[i+1]*B(-v):c[i+1]*B(v)-c[i]*B(-v));
    }
    return j;
}
int main() {
    size_t cases=0,rows=0,kcl_alone_insufficient=0,controls=0,restores=0,active_ii_rows=0;
    real_t smallest_physical_norm=TCAD_CONST(1e100),largest_mixed_norm=0;
    try {
        for(int axis:{0,1,2})for(bool graded:{false,true})for(bool logs:{false,true})
        for(int hfs:{0,1,2})for(bool ii:{false,true})for(bool biased:{false,true}) {
            Grid3D g{5,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};
            if(axis==1){g.nx=1;g.ny=5;}if(axis==2){g.nx=1;g.nz=5;}
            V pos={0,TCAD_CONST(1e-8),TCAD_CONST(2e-8),TCAD_CONST(3e-8),TCAD_CONST(4e-8)};
            if(graded){pos={0,TCAD_CONST(1e-8),TCAD_CONST(2.5e-8),TCAD_CONST(4e-8),TCAD_CONST(6e-8)};if(axis==0)g.xx=pos;if(axis==1)g.yx=pos;if(axis==2)g.zx=pos;}
            NewtonOptions opt;opt.enable_quantum=true;opt.use_log_space=logs;opt.tol=TCAD_CONST(1e-8);opt.abs_tol=TCAD_CONST(1e-20);
            opt.hfs_enabled=hfs>0;opt.hfs_driving=hfs==1?1:0;
            opt.hfs_vsat_n=opt.hfs_vsat_p=TCAD_CONST(5e4);opt.hfs_beta_n=opt.hfs_beta_p=TCAD_CONST(2.0);
            opt.enable_ii=ii;opt.ii_A_n=opt.ii_A_p=TCAD_CONST(1e6);opt.ii_B_n=opt.ii_B_p=TCAD_CONST(1e5);
            NewtonSolver s(g,opt);s.set_semiconductor_mask(std::vector<char>(5,1));
            s.set_mobility(V(5,TCAD_CONST(.1)),V(5,TCAD_CONST(.1)));
            s.set_effective_dos(V(5,TCAD_CONST(1e20)),V(5,TCAD_CONST(1e20)));s.set_bandgap(V(5,TCAD_CONST(6.0)));
            s.dg_bn_=s.dg_bp_=TCAD_CONST(4.885e-20);
            V x(15),c(5),target_n(5),target_p(5);std::map<size_t,real_t> phi_bc;
            for(size_t i=0;i<5;++i) {
                c[i]=TCAD_CONST(2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.15)*i*(4-i));
                x[i]=biased?TCAD_CONST(.16)*(pos[i]/pos.back())*(TCAD_CONST(1.0)-pos[i]/pos.back()):TCAD_CONST(0.0);phi_bc[i]=x[i];
                x[5+i]=x[10+i]=logs?log_q(c[i]):c[i];
                target_n[i]=s.VT_*log_q(c[i]/TCAD_CONST(2e19))-x[i];
                target_p[i]=s.VT_*log_q(c[i]/TCAD_CONST(2e19))+x[i];
            }
            s.set_phi_dirichlet(phi_bc);s.set_electron_bc({{0,c[0]},{4,c[4]}});s.set_hole_bc({{0,c[0]},{4,c[4]}});
            const V q=independent_q(c,pos,s.dg_bn_,s.VT_);
            // Invert the production 0.2 mixing formula: one real refresh lands
            // on the manufactured zero-current transport state at this x.
            s.lagged_Qn_.resize(5);s.lagged_Qp_.resize(5);
            for(size_t i=0;i<5;++i){s.lagged_Qn_[i]=(target_n[i]-TCAD_CONST(.2)*q[i])/TCAD_CONST(.8);s.lagged_Qp_[i]=(target_p[i]-TCAD_CONST(.2)*q[i])/TCAD_CONST(.8);}
            s.refresh_lagged_quantum_potential(x);s.use_lagged_quantum_potential_=true;
            for(size_t i=0;i<5;++i)require(abs_q(s.lagged_Qn_[i]-target_n[i])<TCAD_CONST(1e-28)&&abs_q(s.lagged_Qp_[i]-target_p[i])<TCAD_CONST(1e-28),"refresh did not construct target Q");
            const V saved_n=s.lagged_Qn_,saved_p=s.lagged_Qp_,saved_x=x;
            V mixed;s.assemble_residual(x,mixed);SparseMatrix jac;s.assemble_jacobian(x,jac);
            V scale(15,TCAD_CONST(1.0)),measurement(15,TCAD_CONST(1.0));
            const auto& rp=jac.row_offsets();const auto& values=jac.vals();
            for(size_t i=0;i<15;++i){real_t mx=0;for(size_t k=rp[i];k<rp[i+1];++k)mx=std::max(mx,abs_q(values[k]));if(mx>EPSILON)scale[i]=TCAD_CONST(1.0)/mx;largest_mixed_norm=std::max(largest_mixed_norm,abs_q(mixed[i]*scale[i]));}
            require(gate(mixed,scale,opt.abs_tol,opt.tol)&&s.steady_1d_kcl_ok(x),"parent mixed-Q criterion did not accept");
            V physical;bool kcl=false;size_t evaluations=0;
            const bool accepted=detail::fresh_quantum_acceptance(s.use_lagged_quantum_potential_,5,scale,measurement,opt.abs_tol,opt.tol,
                [&](V& f){require(!s.use_lagged_quantum_potential_,"probe retained lagged flag");s.assemble_residual(x,f);physical=f;++evaluations;},
                [&](){kcl=s.steady_1d_kcl_ok(x);return kcl;});
            require(!accepted&&evaluations==1,"fresh physical residual falsely accepted");
            require(s.use_lagged_quantum_potential_&&saved_n==s.lagged_Qn_&&saved_p==s.lagged_Qp_&&saved_x==x,"rejected probe committed state");++restores;
            real_t norm=0;for(size_t i=0;i<15;++i)norm=std::max(norm,abs_q(physical[i]*scale[i]));smallest_physical_norm=std::min(smallest_physical_norm,norm);
            require(!gate(physical,scale,opt.abs_tol,opt.tol),"physical residual reference should reject");
            s.use_lagged_quantum_potential_=false;
            if(!biased){require(s.steady_1d_kcl_ok(x),"symmetric total current should pass KCL");++kcl_alone_insufficient;}
            const V jn=currents(s,x,c,q,pos,false),jp=currents(s,x,c,q,pos,true);
            for(size_t i=1;i<4;++i) {
                const real_t axis_width=(pos[i+1]-pos[i-1])/TCAD_CONST(2.0);
                const real_t source_width=axis==0?g.dx_cell(i):g.dx_cell(0),weight=axis==0?TCAD_CONST(1.0):source_width/axis_width;
                real_t generation=0;
                if(ii&&biased)for(size_t edge:{i-1,i}) {
                    const real_t field=abs_q(x[edge+1]-x[edge])/(pos[edge+1]-pos[edge]);
                    if(field>=opt.ii_E_floor)generation+=TCAD_CONST(.5)*opt.ii_A_n*exp_q(-opt.ii_B_n/field)*(abs_q(jn[edge])+abs_q(jp[edge]))/QE;
                }
                if(generation>0)++active_ii_rows;
                const real_t fn=weight*(jn[i-1]-jn[i])/QE-generation*source_width;
                const real_t fp=weight*(jp[i]-jp[i-1])/QE-generation*source_width;
                const real_t reference_scale=std::max(TCAD_CONST(1.0),std::max(abs_q(fn),abs_q(fp)));
                require(abs_q(physical[5+i]-fn)<TCAD_CONST(1e-24)*reference_scale&&abs_q(physical[10+i]-fp)<TCAD_CONST(1e-24)*reference_scale,"fresh DG SG/source independent residual mismatch");rows+=2;
            }
            s.use_lagged_quantum_potential_=true;
            // Uniform physical equilibrium passes despite stale poisoned Q.
            V uniform(15,0);for(size_t i=5;i<15;++i)uniform[i]=logs?log_q(TCAD_CONST(2e19)):TCAD_CONST(2e19);
            s.set_phi_dirichlet({{0,0},{1,0},{2,0},{3,0},{4,0}});s.set_electron_bc({{0,TCAD_CONST(2e19)},{4,TCAD_CONST(2e19)}});s.set_hole_bc({{0,TCAD_CONST(2e19)},{4,TCAD_CONST(2e19)}});
            require(detail::fresh_quantum_acceptance(s.use_lagged_quantum_potential_,5,scale,measurement,opt.abs_tol,opt.tol,[&](V& f){s.assemble_residual(uniform,f);},[&](){return s.steady_1d_kcl_ok(uniform);}),"physical equilibrium rejected");
            require(s.use_lagged_quantum_potential_&&saved_n==s.lagged_Qn_&&saved_p==s.lagged_Qp_,"accepted probe committed Q");++restores;++controls;
            s.opt_.max_iter=1;V phi(5,0),n(5,TCAD_CONST(2e19)),p=n;
            require(s.solve(phi,n,p),"uniform public solve did not converge");++controls;
            // Directly test KCL rejection after the residual gate passes.
            size_t kcl_calls=0;bool lagged=true;V ones(3,TCAD_CONST(1.0));
            require(!detail::fresh_quantum_acceptance(lagged,1,ones,ones,opt.abs_tol,opt.tol,[](V& f){f.assign(3,0);},[&](){++kcl_calls;return false;})&&lagged&&kcl_calls==1,"fresh KCL rejection bypassed");++restores;
            ++cases;
        }
        // A throwing probe must restore the flag too. No exception is hidden.
        bool lagged=true;V ones(3,TCAD_CONST(1.0));bool propagated=false;
        try{detail::fresh_quantum_acceptance(lagged,1,ones,ones,TCAD_CONST(1e-20),TCAD_CONST(1e-8),[](V&){throw std::runtime_error("probe");},[](){return true;});}catch(const std::runtime_error&){propagated=true;}
        require(propagated&&lagged,"probe exception lost restoration");++restores;
        size_t contract_checks=1;
        for(int invalid:{0,1,2}) {
            V scale=ones;lagged=true;
            const real_t huge=pow_q(TCAD_CONST(10.0),TCAD_CONST(4900.0));
            if(invalid==1)scale[0]=huge;
            require(!detail::fresh_quantum_acceptance(lagged,1,scale,ones,TCAD_CONST(1e-20),TCAD_CONST(1e-8),
                [&](V& f){f.assign(invalid==2?2:3,0);if(invalid==0)f[0]=sqrt_q(-TCAD_CONST(1.0));if(invalid==1)f[0]=huge;},
                [](){throw std::runtime_error("invalid residual reached KCL");return true;})&&lagged,"invalid residual accepted or flag lost");++restores;++contract_checks;
        }
        lagged=false;
        require(detail::fresh_quantum_acceptance(lagged,1,ones,ones,TCAD_CONST(1e-20),TCAD_CONST(1e-8),[](V& f){f.assign(3,0);},[&](){return !lagged;})&&!lagged,"fresh input flag was not preserved");++restores;++contract_checks;
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"cases\":"<<cases<<",\"parent_gate_counterexamples\":"<<cases<<",\"independent_continuity_rows\":"<<rows<<",\"kcl_alone_insufficient\":"<<kcl_alone_insufficient<<",\"physical_controls\":"<<controls<<",\"state_restorations\":"<<restores<<",\"contract_checks\":"<<contract_checks<<",\"active_ii_rows\":"<<active_ii_rows<<",\"largest_mixed_norm\":"<<(double)largest_mixed_norm<<",\"smallest_physical_norm\":"<<(double)smallest_physical_norm<<"}\n";
    }catch(const std::exception& e){std::cerr<<"case="<<cases<<" "<<e.what()<<'\n';return 1;}
}
