#include "amor_linear_solver.h"


void linear_solver::symbolic()
{
  umfpack_di_symbolic(_m, _n, _Ap, _Ai, _Ax, &_symbolic, _control, _info);
}


void linear_solver::numeric()
{
  umfpack_di_numeric(_Ap, _Ai, _Ax, _symbolic, &_numeric, _control, _info);
}

void linear_solver::factorize()
{
  symbolic();
  numeric();
}

void linear_solver::solve(double* x, double* y)
{
  if(_symbolic == NULL)
    symbolic();

  if(_numeric == NULL)
    numeric();
  
  umfpack_di_solve(UMFPACK_A, _Ap, _Ai, _Ax, y, x, _numeric, _control, _info);
}

