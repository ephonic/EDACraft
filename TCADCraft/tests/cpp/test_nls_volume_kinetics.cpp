// Prescribed-field numerical references, independent of the Poisson solve.
#include "poisson_solver.h"
#include <iostream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>

using namespace tcad;
static bool audit = false;
static int checks = 0;
static void require(bool ok, const char* message) {
    ++checks;
    if (!audit && !ok) throw std::runtime_error(message);
}
static void row(const char* label, real_t value, real_t expected, real_t atol=TCAD_CONST(1e-25)) {
    if (audit) std::cout << label << ',' << std::setprecision(17)
                         << (double)value << ',' << (double)expected << '\n';
    const real_t rounding = TCAD_CONST(64.0)*epsilon_q()*abs_q(expected);
    require(abs_q(value-expected) <= std::max(atol,rounding), label);
}
static PoissonSolver nls(const Grid3D& grid, real_t tau=TCAD_CONST(1.0), real_t E0=TCAD_CONST(0.0),
                         real_t dt=TCAD_CONST(1.0), real_t Ec=TCAD_CONST(1.0), int axis=0) {
    PoissonSolver solver(grid);
    solver.set_ferroelectric(std::vector<char>(grid.npts(),1),-TCAD_CONST(1e8),TCAD_CONST(1e18));
    solver.set_ferroelectric_model(2);
    solver.set_ferroelectric_preisach(TCAD_CONST(.2),Ec,TCAD_CONST(1.0));
    solver.set_ferroelectric_polar_axis(axis);
    solver.set_ferroelectric_nls(tau,E0,dt);
    return solver;
}
static real_t output(PoissonSolver& solver, const std::vector<real_t>& phi, int axis=0) {
    solver.update_ferroelectric_polarization(phi);
    return solver.fe_polarization()[axis];
}
int main(int argc, char** argv) {
    audit = argc>1 && std::string(argv[1])=="--audit";
    if (audit) std::cout << "case,measured,reference\n";
    try {
        Grid3D grid{5,1,1,TCAD_CONST(.25),TCAD_CONST(1.0),TCAD_CONST(1.0)};
        auto solver=nls(grid);
        std::vector<real_t> P(15,TCAD_CONST(0.0));
        for (size_t i=0;i<5;++i) P[3*i]=i%2 ? -TCAD_CONST(.2) : TCAD_CONST(.2);
        solver.set_fe_polarization(P);
        row("uniform_boundary_volume",output(solver,std::vector<real_t>(5,TCAD_CONST(0.0))),TCAD_CONST(0.0));

        for (int refine=0;refine<2;++refine) {
            Grid3D g{(size_t)(refine?5:3),1,1,TCAD_CONST(.5),TCAD_CONST(2.0),TCAD_CONST(3.0)};
            g.xx=refine ? std::vector<real_t>{TCAD_CONST(0.0),TCAD_CONST(.05),TCAD_CONST(.1),TCAD_CONST(.55),TCAD_CONST(1.0)}
                        : std::vector<real_t>{TCAD_CONST(0.0),TCAD_CONST(.1),TCAD_CONST(1.0)};
            auto s=nls(g); std::vector<real_t> state(3*g.npts(),TCAD_CONST(0.0));
            for (size_t i=0;i<g.nx;++i) {
                real_t x=g.xx[i];
                state[3*i]= x<=TCAD_CONST(.1) ? TCAD_CONST(2.0)*x : (TCAD_CONST(.2)/TCAD_CONST(.9))*(TCAD_CONST(1.0)-x);
            }
            s.set_fe_polarization(state);
            row(refine?"nonuniform_inserted_nodes":"nonuniform_original_nodes",
                output(s,std::vector<real_t>(g.npts(),TCAD_CONST(0.0))),TCAD_CONST(.1));
        }
        for (int axis=0;axis<3;++axis) {
            Grid3D g{(size_t)(axis==0?3:1),(size_t)(axis==1?3:1),
                     (size_t)(axis==2?3:1),TCAD_CONST(.5),TCAD_CONST(.5),TCAD_CONST(.5)};
            const std::vector<real_t> positions{TCAD_CONST(0.0),TCAD_CONST(.1),TCAD_CONST(1.0)};
            if (axis==0) g.xx=positions;
            else if (axis==1) g.yx=positions;
            else g.zx=positions;
            auto s=nls(g,TCAD_CONST(1.0),TCAD_CONST(2e8),TCAD_CONST(1.0),TCAD_CONST(1.0),axis);
            std::vector<real_t> phi{TCAD_CONST(0.0),-TCAD_CONST(1e7),-TCAD_CONST(1e8)};
            const real_t expected=TCAD_CONST(.2)*(TCAD_CONST(1.0)-exp_q(-exp_q(-TCAD_CONST(2.0))));
            row(axis==0?"linear_nonuniform_x":axis==1?"linear_nonuniform_y":"linear_nonuniform_z",
                output(s,phi,axis),expected);
            std::vector<real_t> Ex,Ey,Ez;
            s.compute_electric_field(phi,Ex,Ey,Ez);
            const auto& fields=axis==0?Ex:axis==1?Ey:Ez;
            for (real_t field:fields)
                require(abs_q(field-TCAD_CONST(1e8))<std::max(TCAD_CONST(1e-20),
                    TCAD_CONST(64.0)*epsilon_q()*TCAD_CONST(1e8)),"reported nonuniform electric field");
        }
        Grid3D g{3,1,1,TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(1.0)};
        for (int shifted=0;shifted<2;++shifted) {
            auto s=nls(g,TCAD_CONST(1.0),TCAD_CONST(30.0),TCAD_CONST(1.0));
            s.set_ferroelectric_builtin_field(shifted?TCAD_CONST(80.0):-TCAD_CONST(20.0));
            const real_t value=output(s,shifted?std::vector<real_t>{TCAD_CONST(0.0),-TCAD_CONST(110.0),-TCAD_CONST(200.0)}
                                              :std::vector<real_t>{TCAD_CONST(0.0),-TCAD_CONST(10.0),TCAD_CONST(0.0)});
            row(shifted?"translated_effective_field":"original_effective_field",
                value,TCAD_CONST(.2)*(TCAD_CONST(1.0)-exp_q(-exp_q(-TCAD_CONST(1.0)))));
        }
        {
            auto s=nls(g,TCAD_CONST(1.0),TCAD_CONST(0.0),TCAD_CONST(.2),TCAD_CONST(400.0));
            row("finite_low_field_Merz",output(s,{TCAD_CONST(0.0),-TCAD_CONST(1.0),-TCAD_CONST(2.0)}),
                TCAD_CONST(.2)*(TCAD_CONST(1.0)-exp_q(-TCAD_CONST(.2))));
        }
        {
            auto s=nls(g,TCAD_CONST(1.0),TCAD_CONST(0.0),TCAD_CONST(1e-40));
            // Leading Taylor coefficient, with O(dt^2) below quad precision.
            row("short_pulse_Taylor",output(s,{TCAD_CONST(0.0),-TCAD_CONST(1.0),-TCAD_CONST(2.0)}),TCAD_CONST(2e-41),TCAD_CONST(1e-66));
        }
        {
            // Merz intermediate exp(22500) overflows binary128, but dt/tau
            // has a representable log and the switching fraction is ~1.
            auto s=nls(g,TCAD_CONST(1e-4900),TCAD_CONST(22500.0),TCAD_CONST(1e4900));
            row("quad_compensated_Merz",output(s,{TCAD_CONST(0.0),-TCAD_CONST(1.0),-TCAD_CONST(2.0)}),TCAD_CONST(.2));
        }
        if (!audit) {
            auto s=nls(g,TCAD_CONST(2.0),TCAD_CONST(0.0),TCAD_CONST(.2));
            const real_t nan=(real_t)std::numeric_limits<double>::quiet_NaN();
            const real_t inf=(real_t)std::numeric_limits<double>::infinity();
            for (const auto& bad:std::vector<std::vector<real_t>>{
                    {TCAD_CONST(0.0),TCAD_CONST(0.0),TCAD_CONST(.2)},{-TCAD_CONST(1.0),TCAD_CONST(0.0),TCAD_CONST(.2)},{nan,TCAD_CONST(0.0),TCAD_CONST(.2)},
                    {inf,TCAD_CONST(0.0),TCAD_CONST(.2)},{TCAD_CONST(2.0),-TCAD_CONST(1.0),TCAD_CONST(.2)},{TCAD_CONST(2.0),inf,TCAD_CONST(.2)},
                    {TCAD_CONST(2.0),TCAD_CONST(0.0),TCAD_CONST(0.0)},{TCAD_CONST(2.0),TCAD_CONST(0.0),-TCAD_CONST(1.0)},{TCAD_CONST(2.0),TCAD_CONST(0.0),nan}}) {
                bool rejected=false;
                try {s.set_ferroelectric_nls(bad[0],bad[1],bad[2]);}
                catch (const std::invalid_argument&) {rejected=true;}
                require(rejected,"invalid NLS parameters accepted");
            }
            row("invalid_parameter_preserved_config",output(s,{TCAD_CONST(0.0),-TCAD_CONST(1.0),-TCAD_CONST(2.0)}),
                TCAD_CONST(.2)*(TCAD_CONST(1.0)-exp_q(-TCAD_CONST(.1))));
            auto bounded=nls(g);
            bounded.set_ferroelectric(std::vector<char>{1,1,0},-TCAD_CONST(1e8),TCAD_CONST(1e18));
            for (int step=0;step<20;++step) {
                const real_t sign=step%2?TCAD_CONST(1.0):-TCAD_CONST(1.0);
                output(bounded,{TCAD_CONST(0.0),-sign*TCAD_CONST(100.0),-sign*TCAD_CONST(200.0)});
                const auto& state=bounded.fe_polarization();
                for (size_t i=0;i<2;++i) {
                    require(abs_q(state[3*i])<=TCAD_CONST(.2),"NLS amplitude exceeds Ps");
                    require(state[3*i+1]==TCAD_CONST(0.0) && state[3*i+2]==TCAD_CONST(0.0),"NLS off-axis polarization");
                }
                require(state[6]==TCAD_CONST(0.0),"non-FE polarization is not zero");
            }
            std::cout << checks << " NLS quadrature, coordinate, Merz, invariance, input and bound checks passed.\n";
        }
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
    return 0;
}
