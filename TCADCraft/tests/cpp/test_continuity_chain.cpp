#include "continuity_chain.h"
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace tcad;
static void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
static real_t population_gate() {
    return std::max(TCAD_CONST(1e-22),TCAD_CONST(10000.0)*epsilon_q());
}
static real_t conditioned_endpoint_gate() {
    // Independent quad reconstruction of the rounded 101-node input bounds
    // the zero/weak-sink endpoint cases' infinity-norm condition by 3e7.
    // Keep the ordinary gate for the other controls; quad's 1e-22 is unchanged.
    return std::max(population_gate(),TCAD_CONST(3e7)*epsilon_q());
}

struct Problem {
    SparseMatrix matrix;
    Vector rhs,mobility,from,to,weight,expected,sink;
    std::map<size_t,real_t> contacts;
};
static Problem make_problem(size_t count,size_t contact,bool extreme,bool gap=false,
                            real_t reaction=TCAD_CONST(0.0)) {
    Problem p{SparseMatrix(count),Vector(count),Vector(count,1),Vector(count),Vector(count),
              Vector(count),Vector(count),Vector(count),{}};
    for(size_t i=0;i<count;++i) {
        p.expected[i]=extreme?exp_q(TCAD_CONST(.5)*i):TCAD_CONST(10.0)+i*i+TCAD_CONST(.2)*i*i*i;
        p.weight[i]=TCAD_CONST(.1)+TCAD_CONST(.03)*(i+1);
        p.sink[i]=reaction*(TCAD_CONST(1.0)+real_t(i%5)/10)*p.weight[i];
        if(i+1<count) {
            p.from[i]=extreme?exp_q(TCAD_CONST(.5)):TCAD_CONST(1.2)+TCAD_CONST(.01)*i;
            p.to[i]=extreme?TCAD_CONST(1.0):TCAD_CONST(.8)+TCAD_CONST(.02)*i;
        }
    }
    if(gap) {p.mobility[count/2]=0;p.expected[count/2]=EPSILON;}
    p.contacts[contact]=p.expected[contact];
    if(gap) p.contacts[count-1]=p.expected[count-1];
    // Independent face balance with prescribed populations, including actual
    // nonzero source/sink and nonuniform row measures. No A.apply to manufacture RHS.
    Vector flux(count,0);
    if(!extreme) for(size_t i=0;i+1<count;++i)
        if(p.mobility[i]>0 && p.mobility[i+1]>0)
            flux[i]=p.from[i]*p.expected[i]-p.to[i]*p.expected[i+1];
    for(size_t i=0;i<count;++i) {
        if(p.contacts.count(i)) {p.matrix.add_entry(i,i,1);p.rhs[i]=p.expected[i];continue;}
        if(p.mobility[i]==0) {p.matrix.add_entry(i,i,TCAD_CONST(1e20));p.rhs[i]=1;continue;}
        real_t diagonal=0;
        if(i && p.mobility[i-1]>0) {
            diagonal+=p.weight[i]*p.to[i-1];
            p.matrix.add_entry(i,i-1,-p.weight[i]*p.from[i-1]);
        }
        if(i+1<count && p.mobility[i+1]>0) {
            diagonal+=p.weight[i]*p.from[i];
            p.matrix.add_entry(i,i+1,-p.weight[i]*p.to[i]);
        }
        p.matrix.add_entry(i,i,diagonal+p.sink[i]);
        p.rhs[i]=p.weight[i]*(flux[i]-(i?flux[i-1]:TCAD_CONST(0.0)))+p.sink[i]*p.expected[i];
    }
    p.matrix.finalize();return p;
}
static bool solve(const Problem& p,Vector& result) {
    return solve_single_reservoir_chain(p.matrix,p.rhs,p.mobility,p.contacts,p.from,p.to,p.weight,p.sink,
                                        TCAD_CONST(1e-10),result);
}
static void check_weak_reaction(bool reverse) {
    // Symmetric SRH has R=(density-ni)/(2*tau). Solve the two unknowns
    // independently in closed form, then audit the tiny reservoir flux.
    const real_t diffusion=TCAD_CONST(2.585e11),reaction=TCAD_CONST(50.0);
    const real_t ni=TCAD_CONST(1e19),reservoir=TCAD_CONST(1e23);
    const real_t determinant=diffusion*diffusion+3*diffusion*reaction+reaction*reaction;
    Vector expected={ni+diffusion*diffusion*(reservoir-ni)/determinant,
                     ni+diffusion*(diffusion+reaction)*(reservoir-ni)/determinant,
                     reservoir};
    if(reverse)std::reverse(expected.begin(),expected.end());
    SparseMatrix matrix(3);Vector rhs(3),mobility(3,1),from(3,diffusion),to=from,weight(3,1),sink(3,reaction);
    const size_t contact=reverse?0:2;std::map<size_t,real_t> bc{{contact,reservoir}};
    for(size_t i=0;i<3;++i) {
        if(i==contact){matrix.add_entry(i,i,1);rhs[i]=reservoir;continue;}
        real_t diagonal=reaction;
        if(i){matrix.add_entry(i,i-1,-diffusion);diagonal+=diffusion;}
        if(i+1<3){matrix.add_entry(i,i+1,-diffusion);diagonal+=diffusion;}
        matrix.add_entry(i,i,diagonal);rhs[i]=reaction*ni;
    }
    matrix.finalize();Vector output;
    check(solve_single_reservoir_chain(matrix,rhs,mobility,bc,from,to,weight,sink,TCAD_CONST(1e-8),output),
          "weak implicit reaction was rejected");
    for(size_t i=0;i<3;++i)
        check(abs_q(output[i]/expected[i]-1)<population_gate(),"weak reaction density differs from closed form");
    const size_t neighbour=1;
    const real_t flux=diffusion*(reservoir-output[neighbour]);
    real_t integrated=0;
    for(size_t i=0;i<3;++i)if(i!=contact)integrated+=reaction*(output[i]-ni);
    // The current subtracts nearly equal populations: its roundoff scale is
    // epsilon*diffusion/reaction, while quad retains the tighter fixed gate.
    const real_t current_gate=std::max(TCAD_CONST(1e-18),TCAD_CONST(256.0)*epsilon_q()*diffusion/reaction);
    check(abs_q(flux/integrated-1)<current_gate,"weak reaction/current balance lost");
}
int main() {
    try {
        check(std::string(compiled_constants_profile_name())==constants_profile_name(),
              "linked core constants profile differs from test header");
        size_t checks=0;
        for(real_t reaction:{TCAD_CONST(0.0),TCAD_CONST(1e-12),TCAD_CONST(.3)})
        for(bool extreme:{false,true}) for(size_t contact:{size_t(0),size_t(50),size_t(100)}) {
            auto p=make_problem(101,contact,extreme,false,reaction);Vector result;
            check(solve(p,result),"conservative chain rejected a valid sourced/reflected problem");
            const real_t gate=(!extreme && contact!=50 && reaction<=TCAD_CONST(1e-12))
                ? conditioned_endpoint_gate() : population_gate();
            for(size_t i=0;i<result.size();++i)
                check(abs_q(result[i]/p.expected[i]-1)<gate,
                      "chain differs from independent prescribed populations");
            ++checks;
        }
        for(real_t reaction:{TCAD_CONST(0.0),TCAD_CONST(1e-12),TCAD_CONST(.3)}) {
            auto split=make_problem(11,0,false,true,reaction);Vector result;
            check(solve(split,result),"independently contacted components failed");
            for(size_t i=0;i<result.size();++i)
                check(abs_q(result[i]/split.expected[i]-1)<population_gate(),"component solution mixed across insulator");
            ++checks;
        }
        for(int bad=0;bad<11;++bad) {
            auto p=make_problem(11,0,false);Vector before(11,TCAD_CONST(17.0)),after=before;
            if(bad==0) p.contacts[10]=p.expected[10];
            if(bad==1) p.contacts.clear();
            if(bad==2) p.from[3]=0;
            if(bad==3) p.weight[4]=0;
            if(bad==4) p.mobility[4]=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
            if(bad==5) p.rhs[4]-=TCAD_CONST(1e8); // drives a negative population
            if(bad==6) p.from[2]*=TCAD_CONST(1.5); // does not describe assembled A
            if(bad==7) p.sink[4]=-1;
            if(bad==8) p.sink[4]=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
            if(bad==9) p.sink.pop_back();
            if(bad==10) p.sink[4]=TCAD_CONST(1e8); // does not describe assembled A
            check(!solve(p,after),"invalid or unsupported chain was accepted");
            check(after==before,"failed chain changed caller output");++checks;
        }
        for(bool reverse:{false,true}){check_weak_reaction(reverse);++checks;}
        std::cout<<checks<<" conservative source, reaction, dynamic-range, component and rejection cases passed; bits="
                 <<real_mantissa_bits()<<" population_gate="<<double(population_gate())
                 <<" conditioned_endpoint_gate="<<double(conditioned_endpoint_gate())
                 <<" profile="<<constants_profile_name()<<'\n';
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
