#ifndef MATRIX_UTIL_H_
#define MATRIX_UTIL_H_

#include "amor_compressed_matrix.h"
#include "amor_comm.h"

#ifndef NDEBUG
#include "mat.h"  // matlab interface
#include "matrix.h" // matlab interface
#endif

#ifndef NDEBUG
mxArray* compressed_to_mxarray(compressed_matrix<double> * cmatrix);

//mxArray* dense_to_mxarray(dense_vector<double> *dvec);

//mxArray* dense_to_mxarray(dense_matrix<double> *dmat);

mxArray* doublep_to_mxarray(double *data, int row, int col);
#endif


compressed_matrix<double> * setup_compressed_matrix(int m, int n, std::map<int, std::map<int, double *> > &matrix_pattern);


#endif

