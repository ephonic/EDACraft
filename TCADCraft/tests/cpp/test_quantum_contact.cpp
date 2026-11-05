// Prescribed-state audit of the species-specific quantum contact convention.
// The independent DG/SG/source oracle does not call production flux helpers.
#include <bits/stdc++.h>
#define private public
#include "newton_solver.h"
#include "device_simulator.h"
#undef private
using namespace tcad;
using V=std::vector<real_t>;
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
static real_t B(real_t x){return abs_q(x)<TCAD_CONST(1e-25)?TCAD_CONST(1.0)-x/TCAD_CONST(2.0):x/expm1_q(x);}
static void close(real_t a,real_t b,const char* m){require(abs_q(a-b)<=TCAD_CONST(1e-24)*std::max(TCAD_CONST(1.0),std::max(abs_q(a),abs_q(b))),m);}
static V dg(const V& c,const V& pos,real_t coefficient,real_t vt){
    V q(5,0);for(size_t i=1;i<4;++i){const real_t u=sqrt_q(c[i]);
        const real_t lap=TCAD_CONST(2.0)/(pos[i+1]-pos[i-1])*((sqrt_q(c[i+1])-u)/(pos[i+1]-pos[i])-(u-sqrt_q(c[i-1]))/(pos[i]-pos[i-1]));
        q[i]=std::max(-TCAD_CONST(4.0)*vt,std::min(TCAD_CONST(4.0)*vt,coefficient*lap/u));}return q;
}
static V currents(const NewtonSolver& s,const V& phi,const V& c,const V& q,const V& pos,bool hole){
    V j(4);const auto& mu=hole?s.mu_p_:s.mu_n_;const auto& contacts=hole?s.p_bc_:s.n_bc_;
    const real_t sign=hole?-TCAD_CONST(1.0):TCAD_CONST(1.0);
    for(size_t i=0;i<4;++i){const real_t d=pos[i+1]-pos[i],vl=phi[i]+sign*q[i],vr=phi[i+1]+sign*q[i+1];
        real_t m=TCAD_CONST(2.0)*mu[i]*mu[i+1]/(mu[i]+mu[i+1]+TCAD_CONST(1e-30));
        if(s.opt_.hfs_enabled){real_t f=abs_q(vr-vl)/d;
            if(s.opt_.hfs_driving==0&&(s.opt_.hfs_qf_at_contacts||!(contacts.count(i)||contacts.count(i+1))))f=abs_q(vr-vl-sign*s.VT_*log_q(c[i+1]/c[i]))/d;
            const real_t vs=hole?s.opt_.hfs_vsat_p:s.opt_.hfs_vsat_n,beta=hole?s.opt_.hfs_beta_p:s.opt_.hfs_beta_n,r=m*f/vs;
            if(r>TCAD_CONST(1e-12))m/=pow_q(TCAD_CONST(1.0)+pow_q(r,beta),TCAD_CONST(1.0)/beta);}
        const real_t v=(vr-vl)/s.VT_;j[i]=QE*m*s.VT_/d*(hole?c[i]*B(v)-c[i+1]*B(-v):c[i+1]*B(v)-c[i]*B(-v));}return j;
}
// Independent section reference: enumerate reservoir boundaries first,
// then apply the original spread criterion to disjoint edge ranges.
static bool kcl(const V& n,const V& p,const std::map<size_t,real_t>& nb,const std::map<size_t,real_t>& pb){
    V t(n.size());for(size_t i=0;i<n.size();++i)t[i]=n[i]+p[i];
    std::set<size_t> boundaries{0,t.size()};
    for(const auto& bc:nb)if(bc.first>0&&bc.first<t.size())boundaries.insert(bc.first);
    for(const auto& bc:pb)if(bc.first>0&&bc.first<t.size())boundaries.insert(bc.first);
    for(auto a=boundaries.begin(),b=std::next(a);b!=boundaries.end();++a,++b){
        const auto first=t.begin()+*a,last=t.begin()+*b;
        const auto mm=std::minmax_element(first,last);real_t scale=0;
        for(auto i=first;i!=last;++i)scale=std::max(scale,abs_q(*i));
        const real_t spread=*mm.second-*mm.first;
        if(!(spread<=TCAD_CONST(1e-8)||spread/(scale+TCAD_CONST(1e-30))<=TCAD_CONST(.01)))return false;
    }return true;
}
int main(){
    size_t cases=0,rows=0,mismatches=0,flux_checks=0,fd_entries=0,refresh_checks=0,state_checks=0,kcl_cases=0,kcl_mismatches=0;
    try{
        for(int axis:{0,1,2})for(bool graded:{false,true})for(bool logs:{false,true})for(int hfs:{0,1,2})for(bool policy:{false,true})for(int layout:{0,1,2})for(bool ii:{false,true}){
            Grid3D g{5,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};if(axis==1){g.nx=1;g.ny=5;}if(axis==2){g.nx=1;g.nz=5;}
            V pos={0,TCAD_CONST(1e-7),TCAD_CONST(2e-7),TCAD_CONST(3e-7),TCAD_CONST(4e-7)};
            if(graded){pos={0,TCAD_CONST(1e-7),TCAD_CONST(2.5e-7),TCAD_CONST(4e-7),TCAD_CONST(6e-7)};if(axis==0)g.xx=pos;if(axis==1)g.yx=pos;if(axis==2)g.zx=pos;}
            NewtonOptions opt;opt.enable_quantum=true;opt.use_log_space=logs;opt.hfs_enabled=hfs>0;opt.hfs_driving=hfs==1?1:0;opt.hfs_qf_at_contacts=policy;
            opt.hfs_vsat_n=TCAD_CONST(5e4);opt.hfs_vsat_p=TCAD_CONST(4e4);opt.hfs_beta_n=TCAD_CONST(2.0);opt.hfs_beta_p=TCAD_CONST(1.0);
            opt.enable_ii=ii;opt.ii_A_n=TCAD_CONST(1e5);opt.ii_A_p=TCAD_CONST(2e5);opt.ii_B_n=TCAD_CONST(2e5);opt.ii_B_p=TCAD_CONST(3e5);
            NewtonSolver s(g,opt);s.set_semiconductor_mask(std::vector<char>(5,1));s.set_mobility(V(5,TCAD_CONST(.1)),V(5,TCAD_CONST(.05)));
            s.set_effective_dos(V(5,TCAD_CONST(1e19)),V(5,TCAD_CONST(1e19)));s.set_bandgap(V(5,TCAD_CONST(6.0)));s.dg_bn_=TCAD_CONST(1e-15);s.dg_bp_=TCAD_CONST(7e-16);
            V phi={0,TCAD_CONST(.025),TCAD_CONST(.07),TCAD_CONST(.13),TCAD_CONST(.205)},n(5),p(5),x(15);std::map<size_t,real_t> phib,nb,pb;
            for(size_t i=0;i<5;++i){n[i]=TCAD_CONST(2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.07)*i*i);p[i]=TCAD_CONST(1.2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.11)*i*i);x[i]=phi[i];x[5+i]=logs?log_q(n[i]):n[i];x[10+i]=logs?log_q(p[i]):p[i];phib[i]=phi[i];}
            if(layout==0){nb={{0,n[0]},{4,n[4]}};pb={{0,p[0]},{4,p[4]}};}if(layout==1){nb={{1,n[1]}};pb={{3,p[3]}};}
            s.set_phi_dirichlet(phib);s.set_electron_bc(nb);s.set_hole_bc(pb);
            const V raw_n=dg(n,pos,s.dg_bn_,s.VT_),raw_p=dg(p,pos,s.dg_bp_,s.VT_);
            DeviceSimulator d(g.nx,g.ny,g.nz,g.dx,g.dy,g.dz);d.g_=g;d.dg_=DensityGradient(g);
            d.set_quantum_enabled(true);d.set_density_gradient_coefficients(s.dg_bn_,s.dg_bp_);d.set_thermal_voltage(s.VT_);
            d.set_mobility(s.mu_n_,s.mu_p_);d.set_effective_dos(s.Nc_,s.Nv_);d.set_electron_bc(nb);d.set_hole_bc(pb);
            d.set_high_field_saturation(opt.hfs_enabled,opt.hfs_vsat_n,opt.hfs_vsat_p,opt.hfs_beta_n,opt.hfs_beta_p,opt.hfs_driving);d.set_hfs_quasi_fermi_at_contacts(policy);
            for(bool lagged:{false,true}){
                V qn=raw_n,qp=raw_p;for(size_t i=1;i<4;++i)if(lagged){qn[i]+=TCAD_CONST(.003)*i;qp[i]-=TCAD_CONST(.004)*i;}
                s.lagged_Qn_=qn;s.lagged_Qp_=qp;s.use_lagged_quantum_potential_=lagged;const V savedn=qn,savedp=qp;
                // Independent contact reference: only the contacted species.
                for(auto bc:nb)qn[bc.first]=0;for(auto bc:pb)qp[bc.first]=0;
                const V jn=currents(s,phi,n,qn,pos,false),jp=currents(s,phi,p,qp,pos,true);
                V f;s.assemble_residual(x,f);bool differs=false;
                for(size_t i=0;i<5;++i){const real_t width=i==0?pos[1]-pos[0]:(i==4?pos[4]-pos[3]:(pos[i+1]-pos[i-1])/TCAD_CONST(2.0));
                    const real_t source_width=axis==0?width:g.dx,weight=axis==0?TCAD_CONST(1.0):source_width/width;real_t gen=0;
                    if(ii)for(size_t edge=0;edge<4;++edge)if(edge==i||edge+1==i){const real_t field=abs_q(phi[edge+1]-phi[edge])/(pos[edge+1]-pos[edge]);
                        if(field>=opt.ii_E_floor)gen+=TCAD_CONST(.5)*(opt.ii_A_n*exp_q(-opt.ii_B_n/field)*abs_q(jn[edge])+opt.ii_A_p*exp_q(-opt.ii_B_p/field)*abs_q(jp[edge]))/QE;}
                    const real_t en=nb.count(i)?TCAD_CONST(0.0):weight*((i?jn[i-1]:TCAD_CONST(0.0))-(i<4?jn[i]:TCAD_CONST(0.0)))/QE-gen*source_width;
                    const real_t ep=pb.count(i)?TCAD_CONST(0.0):weight*((i<4?jp[i]:TCAD_CONST(0.0))-(i?jp[i-1]:TCAD_CONST(0.0)))/QE-gen*source_width;
                    for(auto pair:{std::make_pair(f[5+i],en),std::make_pair(f[10+i],ep)}){const real_t scale=std::max(TCAD_CONST(1.0),std::max(abs_q(pair.first),abs_q(pair.second)));if(abs_q(pair.first-pair.second)>TCAD_CONST(1e-24)*scale)differs=true;close(pair.first,pair.second,"independent contact continuity/source mismatch");++rows;}}
                if(differs)++mismatches;require(!differs,"contact continuity reference mismatch");
                require(s.lagged_Qn_==savedn&&s.lagged_Qp_==savedp,"assembly changed cached Q");++state_checks;
                SimulationResult result;d.compute_edge_currents(result,phi,n,p,lagged?&qn:nullptr,lagged?&qp:nullptr);
                const V& rn=axis==0?result.Jn_x:(axis==1?result.Jn_y:result.Jn_z);const V& rp=axis==0?result.Jp_x:(axis==1?result.Jp_y:result.Jp_z);
                for(size_t i=0;i<4;++i){close(rn[i],jn[i],"returned electron current");close(rp[i],jp[i],"returned hole current");flux_checks+=2;}
                V physical_n=raw_n,physical_p=raw_p;for(auto bc:nb)physical_n[bc.first]=0;for(auto bc:pb)physical_p[bc.first]=0;
                for(size_t i=0;i<5;++i){close(result.Qn[i],physical_n[i],"returned physical Qn");close(result.Qp[i],physical_p[i],"returned physical Qp");flux_checks+=2;}
                require(s.steady_1d_kcl_ok(x)==kcl(jn,jp,nb,pb),"KCL differs from pinned section flux");++state_checks;
            }
            {
                // Freeze the Q pair for FD; this audits the declared fixed-Q
                // Jacobian and makes no assertion about omitted dQ/dn.
                s.use_lagged_quantum_potential_=true;SparseMatrix jac;s.assemble_jacobian(x,jac);std::vector<V> a(15,V(15,0));
                for(size_t i=0;i<15;++i)for(size_t k=jac.row_offsets()[i];k<jac.row_offsets()[i+1];++k)a[i][jac.col_indices()[k]]+=jac.vals()[k];
                for(size_t col=0;col<15;++col){const real_t h=TCAD_CONST(1e-8)*std::max(abs_q(x[col]),TCAD_CONST(1.0));V lo=x,hi=x,fl,fh;lo[col]-=h;hi[col]+=h;s.assemble_residual(lo,fl);s.assemble_residual(hi,fh);
                    for(size_t row=0;row<15;++row){const real_t fd=(fh[row]-fl[row])/(TCAD_CONST(2.0)*h),scale=std::max(abs_q(fd),abs_q(a[row][col]));if(scale>TCAD_CONST(1e-20))require(abs_q(fd-a[row][col])<=TCAD_CONST(2e-6)*scale,"fixed Q full Jacobian FD");++fd_entries;}}
                const V oldn=s.lagged_Qn_,oldp=s.lagged_Qp_;s.refresh_lagged_quantum_potential(x);
                for(size_t i=0;i<5;++i){close(s.lagged_Qn_[i],nb.count(i)?TCAD_CONST(0.0):oldn[i]+TCAD_CONST(.2)*(raw_n[i]-oldn[i]),"refresh Qn contact/damping");close(s.lagged_Qp_[i],pb.count(i)?TCAD_CONST(0.0):oldp[i]+TCAD_CONST(.2)*(raw_p[i]-oldp[i]),"refresh Qp contact/damping");refresh_checks+=2;}
            }
            ++cases;
        }
        // Manufacture both directions of KCL misclassification. Interior
        // carrier contacts must be applied even to an old unpinned cache.
        for(bool logs:{false,true})for(int hfs:{0,1,2})for(bool policy:{false,true})for(int shape:{0,1}){
            Grid3D g{5,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};NewtonOptions opt;opt.enable_quantum=true;opt.use_log_space=logs;opt.hfs_enabled=hfs>0;opt.hfs_driving=hfs==1?1:0;opt.hfs_qf_at_contacts=policy;
            opt.hfs_vsat_n=TCAD_CONST(5e4);opt.hfs_vsat_p=TCAD_CONST(4e4);NewtonSolver s(g,opt);s.set_semiconductor_mask(std::vector<char>(5,1));s.set_mobility(V(5,TCAD_CONST(.1)),V(5,TCAD_CONST(.05)));s.set_effective_dos(V(5,TCAD_CONST(1e19)),V(5,TCAD_CONST(1e19)));
            V x(15),phi(5),qn(5),qp(5),n(5,TCAD_CONST(2e19)),p(5,TCAD_CONST(1e19)),pos(5);for(size_t i=0;i<5;++i){const real_t t=i;pos[i]=t*g.dx;const real_t psi=TCAD_CONST(.04)*t;
                phi[i]=psi+(shape?TCAD_CONST(.02)*t*t:TCAD_CONST(.02)*(t-TCAD_CONST(1.0))*(t-TCAD_CONST(3.0)));qn[i]=psi-phi[i];qp[i]=phi[i]-psi;x[i]=phi[i];x[5+i]=logs?log_q(n[i]):n[i];x[10+i]=logs?log_q(p[i]):p[i];}
            s.set_electron_bc({{1,n[1]}});s.set_hole_bc({{3,p[3]}});if(!shape){qn[1]=TCAD_CONST(.04);qp[3]=-TCAD_CONST(.03);}
            s.lagged_Qn_=qn;s.lagged_Qp_=qp;s.use_lagged_quantum_potential_=true;qn[1]=0;qp[3]=0;
            const bool expected=kcl(currents(s,phi,n,qn,pos,false),currents(s,phi,p,qp,pos,true),s.n_bc_,s.p_bc_);require(expected==(!shape),"manufactured contact KCL reference");
            const bool actual=s.steady_1d_kcl_ok(x);if(actual!=expected)++kcl_mismatches;require(actual==expected,"contact KCL classification");++kcl_cases;
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"oracle\":\"contact_sections\""<<",\"cases\":"<<cases<<",\"continuity_rows\":"<<rows<<",\"mismatch_states\":"<<mismatches<<",\"returned_flux_and_q_checks\":"<<flux_checks<<",\"fd_entries\":"<<fd_entries<<",\"refresh_checks\":"<<refresh_checks<<",\"state_checks\":"<<state_checks<<",\"kcl_cases\":"<<kcl_cases<<",\"kcl_mismatches\":"<<kcl_mismatches<<"}\n";
    }catch(const std::exception& e){std::cerr<<"case="<<cases<<" "<<e.what()<<'\n';return 1;}
}
