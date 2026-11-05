// Audit the actual convergence guard against independent SG currents and
// assembled continuity rows, including conservative and nonconservative Q.
#include <bits/stdc++.h>
#define private public
#include "newton_solver.h"
#undef private
#include "density_gradient.h"
using namespace tcad;
using V = std::vector<real_t>;

static real_t B(real_t v) {
    return abs_q(v)<TCAD_CONST(1e-25) ? TCAD_CONST(1.0)-v/TCAD_CONST(2.0) : v/expm1_q(v);
}
static V currents(const NewtonSolver& s,const V& x,const V& qn,const V& qp,bool old=false) {
    V result(4,TCAD_CONST(0.0));
    for(size_t i=0;i<4;++i) for(bool hole : {false,true}) {
        const auto& mus=hole?s.mu_p_:s.mu_n_;const auto& dos=hole?s.Nv_:s.Nc_;
        const real_t sign=hole?-TCAD_CONST(1.0):TCAD_CONST(1.0);
        const auto& q=hole?qp:qn;const size_t offset=hole?10:5;
        real_t cl=x[offset+i],cr=x[offset+i+1];
        if(s.opt_.use_log_space){cl=exp_q(cl);cr=exp_q(cr);}
        const real_t vl=x[i]+sign*q[i],vr=x[i+1]+sign*q[i+1],d=s.g_.dx_edge(i);
        real_t mu=TCAD_CONST(2.0)*mus[i]*mus[i+1]/(mus[i]+mus[i+1]+TCAD_CONST(1e-30));
        if(s.opt_.hfs_enabled && !old) {
            const auto& contacts=hole?s.p_bc_:s.n_bc_;
            const bool contact=contacts.count(i)||contacts.count(i+1);
            real_t f=abs_q(vr-vl)/d;
            if(s.opt_.hfs_driving==0 && (s.opt_.hfs_qf_at_contacts||!contact)) {
                const real_t vlq=vl-sign*s.VT_*log_q(std::max(cl,TCAD_CONST(1.0))/std::max(dos[i],TCAD_CONST(1.0)));
                const real_t vrq=vr-sign*s.VT_*log_q(std::max(cr,TCAD_CONST(1.0))/std::max(dos[i+1],TCAD_CONST(1.0)));
                f=abs_q(vrq-vlq)/d;
            }
            if(f<s.opt_.hfs_low_field_cutoff)f=0;
            const real_t vs=hole?s.opt_.hfs_vsat_p:s.opt_.hfs_vsat_n;
            const real_t beta=hole?s.opt_.hfs_beta_p:s.opt_.hfs_beta_n;
            const real_t r=mu*f/vs;
            if(r>TCAD_CONST(1e-12))mu/=pow_q(TCAD_CONST(1.0)+pow_q(r,beta),TCAD_CONST(1.0)/beta);
        }
        const real_t delta=(vr-vl)/s.VT_;
        result[i]+=QE*mu*s.VT_/d*(hole ? cl*B(delta)-cr*B(-delta) : cr*B(delta)-cl*B(-delta));
    }
    return result;
}
static bool passes(const V& j) {
    const auto bounds=std::minmax_element(j.begin(),j.end());real_t scale=0;
    for(auto v:j)scale=std::max(scale,abs_q(v));
    const real_t spread=*bounds.second-*bounds.first;
    return spread<=TCAD_CONST(1e-8)||spread/(scale+TCAD_CONST(1e-30))<=TCAD_CONST(.01);
}

int main() {
    size_t cases=0,rows=0,accepted=0,rejected=0,old_false_reject=0,old_false_accept=0,state_checks=0;
    try {
        for(bool quantum : {false,true}) for(bool graded : {false,true})
        for(bool logs : {false,true}) for(int hfs : {0,1,2})
        for(bool policy : {false,true})
        for(real_t cutoff : {TCAD_CONST(0.0),TCAD_CONST(1e5),TCAD_CONST(1e9)})
        for(int shape : {0,1,2,3}) {
            Grid3D grid{5,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
            V pos={0,TCAD_CONST(1e-7),TCAD_CONST(2e-7),TCAD_CONST(3e-7),TCAD_CONST(4e-7)};
            if(graded){pos={0,TCAD_CONST(1e-7),TCAD_CONST(2.5e-7),TCAD_CONST(4e-7),TCAD_CONST(6e-7)};grid.xx=pos;}
            NewtonOptions opt;opt.enable_quantum=quantum;opt.use_log_space=logs;
            opt.hfs_enabled=hfs>0;opt.hfs_driving=hfs==1?1:0;opt.hfs_qf_at_contacts=policy;
            opt.hfs_low_field_cutoff=cutoff;opt.hfs_vsat_n=TCAD_CONST(5e4);opt.hfs_vsat_p=TCAD_CONST(4e4);
            NewtonSolver s(grid,opt);s.set_semiconductor_mask(std::vector<char>(5,1));
            s.set_mobility(V(5,TCAD_CONST(.1)),V(5,TCAD_CONST(.05)));
            s.set_effective_dos(V(5,TCAD_CONST(1e20)),V(5,TCAD_CONST(1e20)));
            s.set_bandgap(V(5,TCAD_CONST(6.0)));
            V x(15),qn(5),qp(5),n(5),p(5),zero(5,0);
            for(size_t i=0;i<5;++i) {
                const real_t t=pos[i]/pos.back(),linear=TCAD_CONST(.3)*t,curved=TCAD_CONST(.3)*t*t;
                x[i]=shape==0?curved:linear;
                const real_t psi=shape==1?curved:linear;
                qn[i]=psi-x[i];qp[i]=x[i]-psi;
                n[i]=TCAD_CONST(2e19);p[i]=TCAD_CONST(1e19);
                if(shape>=2){n[i]*=TCAD_CONST(1.0)+TCAD_CONST(.07)*i*i;p[i]*=TCAD_CONST(1.0)+TCAD_CONST(.11)*i;}
                if(shape==3){qn[i]+=TCAD_CONST(.003)*i*i;qp[i]-=TCAD_CONST(.002)*i*i;}
                x[5+i]=logs?log_q(n[i]):n[i];x[10+i]=logs?log_q(p[i]):p[i];
            }
            qp[4]=TCAD_CONST(0.0);  // Contact-compatible manufactured Q.
            s.set_electron_bc({{0,n[0]}});s.set_hole_bc({{4,p[4]}});
            s.lagged_Qn_=qn;s.lagged_Qp_=qp;s.use_lagged_quantum_potential_=true;
            const V qn_before=qn,qp_before=qp;
            const V j=currents(s,x,quantum?qn:zero,quantum?qp:zero);
            const bool expected=passes(j),actual=s.steady_1d_kcl_ok(x);
            if(actual!=expected)throw std::runtime_error("independent KCL classification mismatch");
            if(actual)++accepted;else ++rejected;
            if(quantum && shape<2) {
                const bool old=passes(currents(s,x,zero,zero,true));
                if(shape==0 && (!actual||old))throw std::runtime_error("missed quantum conservative counterexample");
                if(shape==1 && (actual||!old))throw std::runtime_error("missed bare-phi conservative counterexample");
                if(actual&&!old)++old_false_reject;
                if(!actual&&old)++old_false_accept;
            }
            V F;s.assemble_residual(x,F);
            real_t scale=TCAD_CONST(1.0);for(auto v:j)scale=std::max(scale,abs_q(v));
            for(size_t i=1;i<4;++i) {
                const real_t divergence=QE*(F[10+i]-F[5+i]);
                if(abs_q(divergence-(j[i]-j[i-1]))>TCAD_CONST(1e-24)*scale)
                    throw std::runtime_error("continuity residual/current divergence mismatch");
                ++rows;
            }
            if(qn_before!=s.lagged_Qn_||qp_before!=s.lagged_Qp_)throw std::runtime_error("guard mutated Picard state");
            // Force the fresh-DG branch while deliberately retaining stale Q.
            if(quantum) {
                s.use_lagged_quantum_potential_=false;
                DensityGradient dg(grid);dg.set_coefficients(s.dg_bn_,s.dg_bp_);dg.set_semiconductor_mask(s.semi_mask_);dg.set_thermal_voltage(s.VT_);
                V fresh_n,fresh_p;dg.quantum_potential(n,p,fresh_n,fresh_p);
                if(s.steady_1d_kcl_ok(x)!=passes(currents(s,x,fresh_n,fresh_p)))throw std::runtime_error("fresh DG selection mismatch");
                ++state_checks;
                s.use_lagged_quantum_potential_=true;s.lagged_Qp_.clear();
                if(s.steady_1d_kcl_ok(x)!=passes(currents(s,x,fresh_n,fresh_p)))throw std::runtime_error("incomplete Q pair did not use fresh DG");
                ++state_checks;
                s.lagged_Qp_=qp;s.semi_mask_.clear();
                if(s.steady_1d_kcl_ok(x)!=passes(currents(s,x,zero,zero)))throw std::runtime_error("empty mask did not suppress DG");
                ++state_checks;
            }
            // Existing applicability exclusions must remain unchanged.
            for(int bypass=0;bypass<5;++bypass) {
                auto saved=s.opt_;auto gsave=s.g_;
                if(bypass==0)s.opt_.transient_enabled=true;
                if(bypass==1)s.opt_.freeze_n=true;
                if(bypass==2)s.opt_.freeze_p=true;
                if(bypass==3)s.g_.ny=2;
                if(bypass==4)s.g_.nx=2;
                if(!s.steady_1d_kcl_ok(x))throw std::runtime_error("changed KCL applicability");
                s.opt_=saved;s.g_=gsave;++state_checks;
            }
            ++cases;
        }
        if(!accepted||!rejected||old_false_accept!=72||old_false_reject!=72)throw std::runtime_error("counterexample counts");
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"cases\":"<<cases<<",\"continuity_rows\":"<<rows<<",\"accepted\":"<<accepted<<",\"rejected\":"<<rejected<<",\"parent_false_accept\":"<<old_false_accept<<",\"parent_false_reject\":"<<old_false_reject<<",\"state_checks\":"<<state_checks<<"}\n";
        return 0;
    } catch(const std::exception& e){std::cerr<<"case="<<cases<<" "<<e.what()<<'\n';return 1;}
}
