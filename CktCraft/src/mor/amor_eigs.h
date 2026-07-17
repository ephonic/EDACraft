#ifndef EIGS_H
#define EIGS_H

/**
 * @file
 * Header file for the circuit.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */


#include "amor_comm.h"
#include "arpackf.h"
#include "amor_orth_list.h"
#include "amor_compressed_matrix.h"
#include "amor_linear_solver.h"

/**
 * @addtogroup matrix_computation
 * @{
*/


/**
 * A wrapper class for calculating the eigvalues and eigenvectors of a sparse matrix.
 *
*/

class eigs_wrapper
{
public:
  /** default constructor. */
  eigs_wrapper():_sv(NULL), _A(NULL) {}

  /** default deconstructor. */
  ~eigs_wrapper()
  {
    if(_A != NULL)
      delete _A;
    
    if(_sv != NULL)
      delete _sv;
  }

public:
  /** calculate the eigenvalues and eigenvectors of sub-matrix represented by orthogonal list G.
   *  ind represent the index of the sub-matrix.
  */
  int eigs(orth_list& G, std::vector<int>& ind, int neigs, double *eigvals, double* eigvecs);

private:
  /** get the sub-matrix of G(ind,ind). */
  compressed_matrix<double>* get_A(orth_list& G, std::vector<int>& ind, double sigma);

  /** matrix-vector multiplication called by the ARPACK routines.*/
  void mv(int size, double* x, double* y);
  

private:
  /** a sparse linear solver wrapper of UMFPACK. */
  linear_solver* _sv;

  /** the sparse sub-matrix. */
  compressed_matrix<double>* _A;
  
};

/** @} */

#endif
