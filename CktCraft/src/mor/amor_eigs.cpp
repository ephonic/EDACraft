#include "amor_eigs.h"
#include "amor_comm.h"
#include "amor_orth_list.h"
#include "amor_compressed_matrix.h"
#include "amor_linear_solver.h"


#ifndef NDEBUG
#include "amor_matrix_util.h"
#endif


using std::vector;
using std::map;
using std::cerr;
using std::endl;

#define MIN(x,y) ( x > y ? y : x)
#define MAX(x,y) ( x >y ? x :y)

int eigs_wrapper::eigs(orth_list& G, vector<int>& ind, int neigs, double *eigvals, double* eigvecs)
{
  int i;
  int nrows = ind.size();
  // allocate memory for arpack
  int ido = 0;
  int n = nrows;

  int nev = neigs;

  double* resid = new double[n];
  int ncv = MIN(MAX(2*nev,20), n);

  double* V = new double[n * ncv];
  int ldv = n;

  double tol = 2.2204e-16;
  
  int *iparam = new int[11];

  for(i = 0; i < 11; ++i)
    iparam[i] = 0;

  for(i = 0; i < n; ++i)
    resid[i] = 1.0;
  
  iparam[0] = 1; // ishift = 1
  iparam[2] = MAX(300, 2*n/MAX(ncv,1)); // maxiter = 300
  iparam[6] = 3; // mode = shift mode

  int *ipntr = new int[11];
  double* workd = new double[3*n];

  int lworkl = ncv * (ncv + 8);
  double* workl = new double[lworkl];
  int info = 0;
  logical rvec = 1;
  double sigma = -1e-4;
  logical *sel = new logical[n];
  char bmat = 'I';
  char which[3] = "LM";
  char howmny = 'A';

  // calculate A = K - sigma * I
  _A = get_A(G, ind, -sigma);
  _sv = new linear_solver(*_A);


#ifndef NDEBUG
  mxArray* Amx = compressed_to_mxarray(_A);

  MATFile *fp = matOpen("A.mat", "w");
  
  matPutVariable(fp, "A", Amx);

  mxFree(Amx);
  matClose(fp);
#endif


  // call arpack to compute the eigenvalues and eigenvectors
  while(ido != 99)
    {
      F77NAME(dsaupd)(&ido, &bmat, &n, which, &nev, &tol, resid,
                       &ncv, V, &ldv, iparam, ipntr, workd,
                       workl, &lworkl, &info);

      if(ido == 1 || ido == -1)
	{
	  mv(nrows, &workd[ipntr[0]-1], &workd[ipntr[1]-1]);
	}
	else if(ido == 2)
	{
	  cerr << "ido = 2" << endl;
	}
    }

  if(info != 0)
    {
      delete[] resid;
      delete[] V;
      delete[] iparam;
      delete[] ipntr;
      delete[] workd;
      delete[] workl;
      delete[] sel;
      delete _A;
      delete _sv;
      _A = NULL;
      _sv = NULL;

      return info;
    }
  else
    {
      F77NAME(dseupd)(&rvec, &howmny, sel, eigvals, V, &n,
		      &sigma, &bmat, &n, which, &nev, &tol, resid,
                       &ncv, V, &ldv, iparam, ipntr, workd,
		      workl, &lworkl, &info);
      
      memcpy(eigvecs, V, n * neigs * sizeof(double));
      delete[] resid;
      delete[] V;
      delete[] iparam;
      delete[] ipntr;
      delete[] workd;
      delete[] workl;
      delete[] sel;
      delete _A;
      delete _sv;
      _A = NULL;
      _sv = NULL;

      return info;
    }
  
  
}


void eigs_wrapper::mv(int size, double* x, double* y)
{
  _sv->solve(x, y);
}


compressed_matrix<double>* eigs_wrapper::get_A(orth_list& G, vector<int>& ind, double sigma)
{
  int size = ind.size();
  int i;
  map<int, map<int, double> > & Gdata = G.get_data();
  map<int, double>::iterator iter;
  vector<int>::iterator iter_ind;
  int nnzmax = 0;

  for(i = 0; i < size; ++i)
    nnzmax += Gdata[ind[i]].size();

  compressed_matrix<double>* A = new compressed_matrix<double>(size, size, nnzmax);
  int* ptr = A->ptr();
  int* index = A->ind();
  double* nzval = A->nzval();
  vector<double*> diags(size);

  double* diag_values = new double[size];

  for(i = 0; i < size; ++i)
    diag_values[i] = 0.0;

  int nnz = 0;

  for(i = 0; i < size; ++i)
    {
      ptr[i] = nnz;
      for(iter = Gdata[ind[i]].begin(); iter != Gdata[ind[i]].end(); ++iter)
	{
	  if(iter->first == ind[i])
	    {
	      index[nnz] = i;
	      nzval[nnz] = sigma;
	      diags[i] = &nzval[nnz];
	      ++nnz;

	    }
	  else
	    {
	      iter_ind = find(ind.begin(), ind.end(), iter->first);
	      if(iter_ind != ind.end())
		{
		  index[nnz] = iter_ind - ind.begin();
		  nzval[nnz] = iter->second;
		  diag_values[i] += nzval[nnz];
		  ++nnz;
		}
	    }

	}
    }
  ptr[size] = nnz;

  for(i = 0; i < size; ++i)
    {
      *diags[i] -= diag_values[i];
    }

  delete[] diag_values;
  return A;
}

