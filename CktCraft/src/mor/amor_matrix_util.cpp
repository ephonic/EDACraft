#include "amor_matrix_util.h"


using std::cout;
using std::endl;
using std::memcpy;


//#ifdef DEBUG

void write_matrix_file(FILE* fp, const compressed_matrix<doublereal>& mat)
{
    fprintf(fp, "%d %d\n",mat.size(0), mat.size(1));

    integer* ind = mat.ind();
    integer* ptr = mat.ptr();
    double* nzval = mat.nzval();
    
    integer j, beg, end;

    for(j=0; j<mat.size(1); ++j){
        for(beg = ptr[j], end = ptr[j+1]; beg<end; ++beg){
            fprintf(fp, "%d %d %.16e\n ",ind[beg]+1, j+1, nzval[beg]);
        }
    }
}


void write_matrix_file(FILE* fp, compressed_matrix<doublecomplex>& mat)
{
    fprintf(fp, "%d %d\n",mat.size(0), mat.size(1));

    integer* ind = mat.ind();
    integer* ptr = mat.ptr();
    doublecomplex* nzval = mat.nzval();
    
    integer j, beg, end;

    for(j=0; j<mat.size(1); ++j){
        for(beg = ptr[j], end = ptr[j+1]; beg<end; ++beg){
            fprintf(fp, "%d %d %.16e+%.16ei\n ",ind[beg]+1, j+1, nzval[beg].r, nzval[beg].i);
        }
    }
}


#ifndef NDEBUG

mxArray* compressed_to_mxarray(compressed_matrix<double> * cmatrix)
{
  int m, n;
  int nnz;
  m = cmatrix->size(0);
  n = cmatrix->size(1);
  nnz = cmatrix->ptr()[n];
  mxArray *smat;
  smat = mxCreateSparse(m, n, nnz, mxREAL);

  memcpy(mxGetPr(smat), cmatrix->nzval(), nnz * sizeof(double));
  memcpy(mxGetIr(smat), cmatrix->ind(), nnz * sizeof(int));
  memcpy(mxGetJc(smat), cmatrix->ptr(), (n+1) * sizeof(int));
  
  return smat;
}


// mxArray* dense_to_mxarray(dense_vector<double> *dvec)
// {
//   int m, n;
//   m = dvec->size(0);
//   n = dvec->size(1);

//   mxArray *dmat;
//   dmat = mxCreateDoubleMatrix(m, n, mxREAL);

//   memcpy(mxGetPr(dmat), dvec->data(), m * n * sizeof(double));
	 
//   return dmat;
// }


// mxArray* dense_to_mxarray(dense_matrix<double> *dmat)
// {
//   int m, n;
//   m = dmat->size(0);
//   n = dmat->size(1);

//   mxArray *dmatret;
//   dmatret = mxCreateDoubleMatrix(m, n, mxREAL);

//   memcpy(mxGetPr(dmatret), dmat->data(), m * n * sizeof(double));
	 
//   return dmatret;
// }

mxArray* doublep_to_mxarray(double* data, int row, int col)
{
  mxArray *dmat;
  dmat = mxCreateDoubleMatrix(row, col, mxREAL);

  memcpy(mxGetPr(dmat), data, row * col * sizeof(double));

  return dmat;
}



#endif

compressed_matrix<double> * setup_compressed_matrix(int m, int n, std::map<int, std::map<int, double *> > &matrix_pattern)
{
  std::map<int, std::map<int, double *> >::iterator iter;
  std::map<int, double*>::iterator in_iter;
  double *nzval;
  int *ind;
  int *ptr;
  int nnz = 0;
  int nnz_t = 0;
  int i;
  compressed_matrix<double> *mat;

  // first count the number of non-zeros
  for(iter = matrix_pattern.begin(); iter != matrix_pattern.end(); iter++)
    {
      nnz += (iter->second).size();
    }
  
  mat = new compressed_matrix<double>(m, n, nnz);

  ind = mat->ind();
  ptr = mat->ptr();
  nzval = mat->nzval();

  for(i = 0; i < n; i++)
    {
      ptr[i] = nnz_t;
      for(in_iter = (matrix_pattern)[i].begin();
	  in_iter != (matrix_pattern)[i].end();
	  in_iter++)
	{
	  ind[nnz_t] = in_iter->first;
	  // set the pointer of _matrix_pattern to actual data
	  in_iter->second = &nzval[nnz_t];
	  ++nnz_t;
	} // end for in_iter
      
    } // end for _matrix_size
  ptr[i] = nnz_t;

  return mat;
}


