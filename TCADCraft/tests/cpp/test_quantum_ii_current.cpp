// Test the fixed-Q source operator directly: the DG Picard iteration holds
// Q constant while Newton differentiates phi and linear/log carrier blocks.
#include <bits/stdc++.h>
#define private public
#include "newton_solver.h"
#include "gummel_solver.h"
#undef private
using namespace tcad;

int main() {
    size_t cases=0, columns=0, entries=0;
    try {
        for(real_t scale : {TCAD_CONST(1.0),TCAD_CONST(1e19)})
        for(int axis : {0,1,2}) for(bool graded : {false,true})
        for(bool logs : {false,true}) for(int driving : {0,1})
        for(bool policy : {false,true})
        for(real_t cutoff : {TCAD_CONST(0.0),TCAD_CONST(3.3e5),TCAD_CONST(1e6)})
        for(real_t floor : {TCAD_CONST(1e5),TCAD_CONST(1e6)}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
            if(axis==0)grid.nx=5;else if(axis==1)grid.ny=5;else grid.nz=5;
            std::vector<real_t> widths(4,TCAD_CONST(1e-7));
            if(graded) {
                std::vector<real_t> coordinates={0,TCAD_CONST(1e-7),TCAD_CONST(2.5e-7),TCAD_CONST(4e-7),TCAD_CONST(6e-7)};
                if(axis==0)grid.xx=coordinates;else if(axis==1)grid.yx=coordinates;else grid.zx=coordinates;
                for(size_t i=0;i<4;++i)widths[i]=coordinates[i+1]-coordinates[i];
            }
            NewtonOptions opt;opt.enable_quantum=true;opt.enable_ii=true;opt.hfs_enabled=true;
            opt.use_log_space=logs;opt.hfs_driving=driving;opt.hfs_qf_at_contacts=policy;
            opt.hfs_low_field_cutoff=cutoff;opt.ii_E_floor=floor;
            opt.hfs_vsat_n=TCAD_CONST(5e4);opt.hfs_vsat_p=TCAD_CONST(4e4);
            opt.hfs_beta_n=TCAD_CONST(2.0);opt.hfs_beta_p=TCAD_CONST(1.0);
            opt.ii_A_n=TCAD_CONST(1e5);opt.ii_B_n=TCAD_CONST(2e5);opt.ii_A_p=TCAD_CONST(2e5);opt.ii_B_p=TCAD_CONST(3e5);
            NewtonSolver solver(grid,opt);
            std::vector<real_t> phi={0,TCAD_CONST(.025),TCAD_CONST(.07),TCAD_CONST(.13),TCAD_CONST(.205)},n(5),p(5);
            std::vector<real_t> qn={0,TCAD_CONST(.007),-TCAD_CONST(.009),TCAD_CONST(.013),0};
            std::vector<real_t> qp={0,-TCAD_CONST(.004),TCAD_CONST(.006),TCAD_CONST(.005),0};
            for(size_t i=0;i<5;++i){n[i]=(TCAD_CONST(2.0)+i*TCAD_CONST(.1))*scale;p[i]=(TCAD_CONST(1.2)+i*TCAD_CONST(.05))*scale;}
            solver.set_mobility(std::vector<real_t>(5,TCAD_CONST(.1)),std::vector<real_t>(5,TCAD_CONST(.05)));
            solver.set_effective_dos(std::vector<real_t>(5,scale),std::vector<real_t>(5,scale));
            solver.set_electron_bc({{0,n[0]}});solver.set_hole_bc({{4,p[4]}});
            GummelOptions go;go.enable_quantum=true;go.VT=solver.VT_;go.ii.enabled=true;
            go.ii.A_n=opt.ii_A_n;go.ii.B_n=opt.ii_B_n;go.ii.A_p=opt.ii_A_p;go.ii.B_p=opt.ii_B_p;go.ii.E_floor=floor;
            go.hfs.enabled=true;go.hfs.driving=driving;go.hfs.quasi_fermi_at_contacts=policy;
            go.hfs.vsat_n=opt.hfs_vsat_n;go.hfs.vsat_p=opt.hfs_vsat_p;go.hfs.beta_n=opt.hfs_beta_n;go.hfs.beta_p=opt.hfs_beta_p;go.hfs.low_field_cutoff=cutoff;
            GummelSolver gs(grid,go);gs.set_mobility(solver.mu_n_,solver.mu_p_);gs.set_effective_dos(std::vector<real_t>(5,scale),std::vector<real_t>(5,scale));
            gs.set_electron_bc({{0,n[0]}});gs.set_hole_bc({{4,p[4]}});gs.set_transport_quantum_state(qn,qp);
            std::vector<real_t> expected(5,0),gg;
            auto B=[](real_t x){return x/expm1_q(x);};
            for(size_t i=0;i<4;++i) {
                real_t edge=0,E=abs_q((phi[i+1]-phi[i])/widths[i]);
                for(bool hole : {false,true}) {
                    const auto& c=hole?p:n;const auto& q=hole?qp:qn;
                    const real_t sign=hole?-TCAD_CONST(1.0):TCAD_CONST(1.0);
                    const real_t vl=phi[i]+sign*q[i],vr=phi[i+1]+sign*q[i+1];
                    const bool contact=hole?i==3:i==0;
                    real_t force=abs_q(vr-vl)/widths[i];
                    if(driving==0&&(policy||!contact))
                        force=abs_q((vr-vl)+(hole?TCAD_CONST(1.0):-TCAD_CONST(1.0))*go.VT*log_q(c[i+1]/c[i]))/widths[i];
                    if(force<cutoff)force=0;
                    const real_t mu=hole?TCAD_CONST(.05):TCAD_CONST(.1),vs=hole?TCAD_CONST(4e4):TCAD_CONST(5e4);
                    const real_t beta=hole?TCAD_CONST(1.0):TCAD_CONST(2.0);
                    const real_t mobility=mu/pow_q(TCAD_CONST(1.0)+pow_q(mu*force/vs,beta),TCAD_CONST(1.0)/beta);
                    const real_t delta=(vr-vl)/go.VT;
                    const real_t particle=mobility*go.VT/widths[i]*(hole?(c[i]*B(delta)-c[i+1]*B(-delta)):(c[i]*B(-delta)-c[i+1]*B(delta)));
                    if(E>=floor)edge+=(hole?go.ii.A_p:go.ii.A_n)*exp_q(-(hole?go.ii.B_p:go.ii.B_n)/E)*abs_q(particle);
                }
                expected[i]+=edge/TCAD_CONST(2.0);expected[i+1]+=edge/TCAD_CONST(2.0);
            }
            gs.evaluate_impact_ionization(phi,n,p,gg);
            for(size_t i=0;i<5;++i) {
                const real_t actual=solver.compute_ii_at(phi.data(),n.data(),p.data(),i,qn.data(),qp.data());
                const real_t limit=TCAD_CONST(1e-24)*std::max(abs_q(expected[i]),TCAD_CONST(1.0));
                if(abs_q(actual-expected[i])>limit||abs_q(gg[i]-expected[i])>limit)throw std::runtime_error("independent quantum source mismatch");
            }
            // This checks every node's source row, including boundary deposition,
            // without mixing unrelated Poisson or DG fixed-point derivatives.
            SparseMatrix J(15);
            for(size_t i=0;i<5;++i)solver.add_ii_jacobian_row(J,5+i,phi.data(),n.data(),p.data(),i,TCAD_CONST(1.0),qn.data(),qp.data());
            J.finalize();
            for(size_t col=0;col<15;++col) {
                auto ph=phi,nh=n,hh=p;const size_t node=col%5;
                real_t value=col<5?phi[node]:(col<10?n[node]:p[node]);
                const real_t h=logs&&col>=5?TCAD_CONST(1e-8):TCAD_CONST(1e-8)*std::max(abs_q(value),TCAD_CONST(1.0));
                auto change=[&](int direction){
                    if(col<5)ph[node]=value+direction*h;
                    else (col<10?nh:hh)[node]=logs?value*exp_q(direction*h):value+direction*h;
                };
                change(1);std::vector<real_t> plus(5);for(size_t i=0;i<5;++i)plus[i]=-solver.compute_ii_at(ph.data(),nh.data(),hh.data(),i,qn.data(),qp.data());
                change(-1);
                for(size_t i=0;i<5;++i) {
                    real_t minus=-solver.compute_ii_at(ph.data(),nh.data(),hh.data(),i,qn.data(),qp.data());
                    real_t fd=(plus[i]-minus)/(TCAD_CONST(2.0)*h),an=0;
                    for(size_t e=J.row_offsets()[5+i];e<J.row_offsets()[6+i];++e)if(J.col_indices()[e]==col)an=J.vals()[e];
                    const real_t denom=std::max(abs_q(fd),abs_q(an));
                    if(denom>TCAD_CONST(1e-20)&&abs_q(fd-an)>TCAD_CONST(2e-6)*denom)throw std::runtime_error("fixed-Q source Jacobian mismatch");
                    ++entries;
                }
                ++columns;
            }
            ++cases;
        }
        std::cout<<"{\"source_cases\":"<<cases<<",\"fd_columns\":"<<columns<<",\"fd_entries\":"<<entries<<",\"profile\":\""<<compiled_constants_profile_name()<<"\"}\n";
        return 0;
    } catch(const std::exception& e){std::cerr<<"case="<<cases<<" "<<e.what()<<'\n';return 1;}
}
