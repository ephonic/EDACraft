#include "newton_solver.h"
#include "gummel_solver.h"
#include "hfs_reference.h"
#include <iostream>
#include <stdexcept>
using namespace tcad;
int main() {
    size_t cases=0;
    auto rejected=[](auto operation) {
        try { operation(); } catch(const std::invalid_argument&) { return; }
        throw std::runtime_error("missing HFS reference guard");
    };
    Grid3D base{5,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
    NewtonOptions no;no.enable_quantum=false;no.hfs_refdens_n=-TCAD_CONST(1.0);
    rejected([&]{NewtonSolver solver(base,no);});
    GummelOptions go;go.enable_quantum=false;go.hfs.refdens_p=-TCAD_CONST(1.0);
    rejected([&]{GummelSolver solver(base,go);});
    no.hfs_refdens_n=TCAD_CONST(1.0);no.hfs_enabled=true;no.enable_quantum=true;
    rejected([&]{NewtonSolver solver(base,no);});
    go.hfs.refdens_p=TCAD_CONST(1.0);go.hfs.enabled=true;go.enable_quantum=true;
    rejected([&]{GummelSolver solver(base,go);});
    if (hfs_reference_chain(TCAD_CONST(2.0),TCAD_CONST(.2),TCAD_CONST(.3),true)!=TCAD_CONST(0.0))
        throw std::runtime_error("shifted density clamp derivative");
    if (hfs_reference_chain(TCAD_CONST(2.0),TCAD_CONST(2.0),TCAD_CONST(2.0),true)!=TCAD_CONST(1.0))
        throw std::runtime_error("shifted log coordinate chain");
    try {
        // Both O(1) and physical density scales: the first keeps linear
        // carrier columns above the existing FD checker's residual skip gate.
        for(real_t density_scale : {TCAD_CONST(1.0),TCAD_CONST(1e19)})
        for(int refcase : {0,1,2})
        for(int axis : {0,1,2}) for(bool graded : {false,true})
        for(bool logarithmic : {false,true}) for(int driving : {0,1})
        for(bool policy : {false,true}) for(bool ii : {false,true})
        for(bool asymmetric : {false,true})
        // Keep FD states away from the cutoff jump. The graded grid has an
        // electric-field edge of exactly 3e5; cutoff boundary values are
        // covered separately by test_hfs_low_field_cutoff.
        for(real_t cutoff : {TCAD_CONST(0.0),TCAD_CONST(3.3e5)})
        for(real_t floor : {TCAD_CONST(1e5)}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
            if(axis==0)grid.nx=5;else if(axis==1)grid.ny=5;else grid.nz=5;
            if(graded) {
                std::vector<real_t> x={0,TCAD_CONST(1e-7),TCAD_CONST(2.5e-7),TCAD_CONST(4e-7),TCAD_CONST(6e-7)};
                if(axis==0)grid.xx=x;else if(axis==1)grid.yx=x;else grid.zx=x;
            }
            NewtonOptions opt;opt.enable_ii=ii;opt.hfs_qf_at_contacts=policy;opt.hfs_enabled=true;opt.enable_quantum=false;
            opt.use_log_space=logarithmic;opt.hfs_driving=driving;opt.hfs_low_field_cutoff=cutoff;opt.ii_E_floor=floor;
            opt.hfs_vsat_n=TCAD_CONST(5e4);opt.hfs_vsat_p=TCAD_CONST(4e4);
            opt.ii_A_n=TCAD_CONST(1e5);opt.ii_B_n=TCAD_CONST(2e5);
            opt.ii_A_p=TCAD_CONST(2e5);opt.ii_B_p=TCAD_CONST(3e5);
            opt.hfs_refdens_n=refcase==1 ? TCAD_CONST(0.0) : TCAD_CONST(.5)*density_scale;
            opt.hfs_refdens_p=refcase==0 ? TCAD_CONST(0.0) : TCAD_CONST(.8)*density_scale;
            NewtonSolver solver(grid,opt);
            std::vector<real_t> phi={0,TCAD_CONST(.025),TCAD_CONST(.07),TCAD_CONST(.13),TCAD_CONST(.205)},n(5),p(5);
            for(size_t i=0;i<5;++i) {
                n[i]=(TCAD_CONST(2.0)+i*TCAD_CONST(.1))*density_scale;
                p[i]=(TCAD_CONST(1.2)+i*TCAD_CONST(.05))*density_scale;
            }
            solver.set_mobility(std::vector<real_t>(5,TCAD_CONST(.1)),std::vector<real_t>(5,TCAD_CONST(.05)));
            solver.set_effective_dos(std::vector<real_t>(5,density_scale),std::vector<real_t>(5,density_scale));
            solver.set_bandgap(std::vector<real_t>(5,0));
            solver.set_phi_dirichlet({{0,phi[0]},{4,phi[4]}});
            if(asymmetric) {
                solver.set_electron_bc({{0,n[0]}});solver.set_hole_bc({{4,p[4]}});
            } else {
                solver.set_electron_bc({{0,n[0]},{4,n[4]}});solver.set_hole_bc({{0,p[0]},{4,p[4]}});
            }
            std::cerr<<"HFSREFERENCE FD scale="<<(double)density_scale<<" axis="<<axis<<" graded="<<graded
                     <<" policy="<<policy<<" ii="<<ii<<" asymmetric="<<asymmetric<<" log="<<logarithmic<<" driving="<<driving<<" cutoff="<<(double)cutoff<<" floor="<<(double)floor<<'\n';
            if(solver.debug_fd_jacobian_check(phi,n,p,1e-5,8)!=0)
                throw std::runtime_error("HFS reference Jacobian mismatch");
            ++cases;
        }
        std::cout<<"{\"fd_cases\":"<<cases<<",\"profile\":\""<<compiled_constants_profile_name()<<"\"}\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
