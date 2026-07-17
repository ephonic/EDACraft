#ifndef LINEAR_SOLVER_H
#define LINEAR_SOLVER_H

/**
 * @file
 * Header file for the linear solver wrapper.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */


#include "amor_comm.h"
#include "amor_compressed_matrix.h"

#ifdef RFSIM_USE_UMFPACK
#include <umfpack.h>
#else
// Fallback: 如果无 UMFPACK，mor 降阶不可用（eigs 的 shift-invert 需 UMFPACK）
// 用 KLU 替代——但 amor linear_solver 接口绑定了 UMFPACK API。
// 暂时 stub，运行时报错。
#define UMFPACK_CONTROL 20
#define UMFPACK_INFO 90
#endif

/** @addtogroup matrix_computation
 *  @[
*/


/**
 * A linear solver wrapper for UMFPACK.
 *
*/

class linear_solver
{
public:
  /** construct a linear solver with a sparse matrix. */
  linear_solver(compressed_matrix<double>& A):
    _n(A.size(0)),
    _m(A.size(1)),
    _nnz(A.ptr()[_n]),
    _Ap(A.ptr()),
    _Ai(A.ind()),
    _Ax(A.nzval()),
    _symbolic(NULL),
    _numeric(NULL)
  {
    umfpack_di_defaults(_control);
  }

  /** default deconstructor. */
  ~linear_solver()
  {
    umfpack_di_free_symbolic(&_symbolic);
    umfpack_di_free_numeric(&_numeric);
  }

public:
  /** factorize helper function. */
  void factorize();

  /** solve y = A\X. */
  void solve(double* x, double* y);

private:
  /** symbolic factorization */
  void symbolic();

  /** numeric factorization */
  void numeric();


private:
  /** number of rows. */
  int _n;

  /** number of columns. */
  int _m;

  /** number of non-zero values. */
  int _nnz;

  /** column pointer of the sparse matrix. */
  int* _Ap;

  /** row index of the sparse matrix. */
  int* _Ai;

  /** non-zero values of the sparse matrix.*/
  double* _Ax;

  /** control parameters for UMFPACK.*/
  double _control[UMFPACK_CONTROL];

  /** information parameters for UMFPACK.*/
  double _info[UMFPACK_INFO];

  /** symbolic factorization data.*/
  void* _symbolic;

  /** numeric factorization data.*/
  void* _numeric;
  
};


/** @} */

#endif
