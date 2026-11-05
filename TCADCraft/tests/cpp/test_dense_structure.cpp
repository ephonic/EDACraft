// Dense fallback must not discard off-band links or mis-scale fixed rows.
#include "linear_solver.h"
#include <iostream>
#include <stdexcept>
using namespace tcad;
int main() {
    try {
        for (bool off_band : {false,true})
            for (bool scaled_boundary : {false,true}) {
                SparseMatrix matrix(4);
                const real_t left=scaled_boundary?TCAD_CONST(2.0):TCAD_CONST(1.0),right=scaled_boundary?TCAD_CONST(4.0):TCAD_CONST(1.0);
                matrix.add_entry(0,0,left);matrix.add_entry(3,3,right);
                matrix.add_entry(1,1,-TCAD_CONST(3.0));matrix.add_entry(1,0,TCAD_CONST(1.0));
                matrix.add_entry(1,off_band?3:2,TCAD_CONST(2.0));
                matrix.add_entry(2,2,-TCAD_CONST(4.0));matrix.add_entry(2,off_band?0:1,TCAD_CONST(1.0));
                matrix.add_entry(2,3,TCAD_CONST(1.0));matrix.finalize();
                Vector expected{TCAD_CONST(2.0),TCAD_CONST(3.0),TCAD_CONST(4.0),TCAD_CONST(5.0)},rhs=matrix.apply(expected),actual(4,TCAD_CONST(0.0));
                SolverOptions options;options.type=SolverType::DENSE_DIRECT;
                LinearSolver solver(options);solver.solve(matrix,rhs,actual);
                for (size_t i=0;i<4;++i)
                    if(abs_q(actual[i]-expected[i])>TCAD_CONST(1e-12))
                        throw std::runtime_error("dense solve dropped a nonlocal edge or mis-scaled a boundary row");
                std::cout << "off_band=" << off_band << " scaled_boundary=" << scaled_boundary << " passed\n";
            }
        {
            SparseMatrix matrix(5);
            matrix.add_entry(0,0,TCAD_CONST(1.0));matrix.add_entry(4,4,TCAD_CONST(1.0));
            matrix.add_entry(1,1,TCAD_CONST(3.0));matrix.add_entry(1,3,TCAD_CONST(0.5));matrix.add_entry(1,2,-TCAD_CONST(0.4));
            matrix.add_entry(2,2,TCAD_CONST(4.0));matrix.add_entry(2,1,TCAD_CONST(0.2));matrix.add_entry(2,3,TCAD_CONST(0.6));
            matrix.add_entry(3,3,TCAD_CONST(5.0));matrix.add_entry(3,1,TCAD_CONST(0.3));matrix.add_entry(3,2,TCAD_CONST(0.2));
            matrix.finalize();
            Vector expected{TCAD_CONST(1.0),TCAD_CONST(2.0),TCAD_CONST(3.0),TCAD_CONST(4.0),TCAD_CONST(5.0)},rhs=matrix.apply(expected),actual(5,TCAD_CONST(0.0));
            SolverOptions options;options.type=SolverType::DENSE_DIRECT;
            LinearSolver solver(options);solver.solve(matrix,rhs,actual);
            for(size_t row=0;row<5;++row)
                if(abs_q(actual[row]-expected[row])>TCAD_CONST(1e-12))
                    throw std::runtime_error("nonlocal edges between free variables were discarded");
        }
        {
            SparseMatrix matrix(4);
            matrix.add_entry(0,0,TCAD_CONST(1.0));matrix.add_entry(3,3,TCAD_CONST(1.0));
            matrix.add_entry(1,0,TCAD_CONST(1.0));matrix.add_entry(1,2,TCAD_CONST(1.0));
            matrix.add_entry(2,1,TCAD_CONST(1.0));matrix.add_entry(2,2,TCAD_CONST(1.0));matrix.add_entry(2,3,TCAD_CONST(1.0));
            matrix.finalize();
            Vector expected{TCAD_CONST(1.0),TCAD_CONST(2.0),TCAD_CONST(3.0),TCAD_CONST(4.0)},rhs=matrix.apply(expected),actual(4,TCAD_CONST(0.0));
            SolverOptions options;options.type=SolverType::DENSE_DIRECT;
            LinearSolver solver(options);solver.solve(matrix,rhs,actual);
            for(size_t row=0;row<4;++row)
                if(abs_q(actual[row]-expected[row])>TCAD_CONST(1e-12))
                    throw std::runtime_error("zero Thomas pivot did not fall back to pivoted solve");
        }
        for (real_t magnitude : {TCAD_CONST(1e-80),TCAD_CONST(1e-30),TCAD_CONST(1.0),TCAD_CONST(1e30),TCAD_CONST(1e80)}) {
            SparseMatrix matrix(5);
            matrix.add_entry(0,0,TCAD_CONST(1.0));matrix.add_entry(4,4,TCAD_CONST(1.0));
            const real_t coefficients[3][3]={{TCAD_CONST(4.0),TCAD_CONST(1.0),TCAD_CONST(2.0)},{TCAD_CONST(0.5),TCAD_CONST(3.0),TCAD_CONST(1.0)},{TCAD_CONST(1.0),TCAD_CONST(0.2),TCAD_CONST(5.0)}};
            for(size_t row=0;row<3;++row) for(size_t col=0;col<3;++col)
                matrix.add_entry(row+1,col+1,coefficients[row][col]*magnitude);
            matrix.finalize();
            Vector expected{TCAD_CONST(1.0),TCAD_CONST(2.0),TCAD_CONST(3.0),TCAD_CONST(4.0),TCAD_CONST(5.0)},rhs=matrix.apply(expected),actual(5,TCAD_CONST(0.0));
            SolverOptions options;options.type=SolverType::DENSE_DIRECT;
            LinearSolver solver(options);solver.solve(matrix,rhs,actual);
            for(size_t row=0;row<5;++row)
                if(abs_q(actual[row]-expected[row])>TCAD_CONST(1e-12))
                    throw std::runtime_error("dense solver changed a nonsingular system under unit scaling");
        }
        for (real_t coupling : {TCAD_CONST(1.0),TCAD_CONST(1e12),TCAD_CONST(1e24),TCAD_CONST(1e36)}) {
            SparseMatrix matrix(5);
            matrix.add_entry(0,0,TCAD_CONST(1.0));matrix.add_entry(3,3,TCAD_CONST(1.0));matrix.add_entry(4,4,TCAD_CONST(1.0));
            matrix.add_entry(1,0,coupling);matrix.add_entry(1,1,TCAD_CONST(1e-25));
            matrix.add_entry(1,2,-TCAD_CONST(1e-25));matrix.add_entry(1,3,coupling);
            matrix.add_entry(2,0,-coupling);matrix.add_entry(2,1,TCAD_CONST(1e-25));
            matrix.add_entry(2,2,TCAD_CONST(2e-25));matrix.add_entry(2,4,TCAD_CONST(1e-25));matrix.finalize();
            Vector expected{TCAD_CONST(1.73162e-5),TCAD_CONST(0.0),TCAD_CONST(0.0),TCAD_CONST(1e20),TCAD_CONST(1e-20)};
            Vector rhs=matrix.apply(expected),actual(5,TCAD_CONST(0.0));
            SolverOptions options;options.type=SolverType::DENSE_DIRECT;
            LinearSolver solver(options);solver.solve(matrix,rhs,actual);
            for(size_t row : {0u,3u,4u})
                if(actual[row]!=expected[row])
                    throw std::runtime_error("quiet-carrier pivot regularization corrupted a fixed row");
            std::cout << "fixed rows retained at coupling=" << (double)coupling << '\n';
        }
    } catch(const std::exception& error) {std::cerr << error.what() << '\n';return 1;}
    return 0;
}
