#ifndef COMPRESSED_MATRIX_H
#define COMPRESSED_MATRIX_H
/**
 * @file
 * Header file for the compressed_matrix class.
 * @author Yami
 * @date Oct. 10, 2005
 */
#include <cassert>
#include <cstddef>
#include <cstring>
#include "typeint.h"

using std::memcpy;

/**
 * @group matrix_computation  Matrix computation support.
 * This module includes an orthogonal list for storing the
 * data of a sparse matrix, a column compressed matrix
 * interface for eigenvalue computation of sparse matries,
 * a linear solver wrapper of UMFPACK,  and
 * a wrapper of ARPACK for eigenvalues & eigenvectors compuation.
 */


/**
 * @addtogroup matrix_computation
 * @{
 */

/**
 * A class acturally owns the data of a compressed_matrix.
 * Note, we don't distinguish column-compressed or row-compressed
 * format here, because the difference between the two lies in the
 * user level. If one consider it as a column-compressed format,
 * the ind is row index and ptr is column pointer.
 */
template<class T>
struct compref
{
    integer count;
    bool is_own;

    /** number of rows. */
    integer nrow;
    /** number of columns. */
    integer ncol;
    /** Number of Non-Zeros. */
    integer nnz;

    /** array of nonzero values. */
    T* nzval;
    /** array of indices. */
    integer* ind;
    /** array of pointers. */
    integer* ptr;
};

/**
 * A class represents a compressed sparse matrix.
 */
template<class T>
class compressed_matrix
{
private:
    /** pointer to the real memory. */
    compref<T>* _pref;
private:
    void free_memory();
public:
    //ctor and dtor
    
    /** Construct an empty (0-by-0) matrix. */
    compressed_matrix();
    /** Construct a m-by-n with nnz nonzeros matrix, memory is
     * allocated but not initialized.
     */
    compressed_matrix(integer m, integer n, integer nnz);
    /** Construct a m-by-n with nnz nonzeros matrix, data and memory space
     *  supplied by nzval, ind, ptr.
     */
    compressed_matrix(integer m, integer n, integer nnz, 
                      T* nzval, integer* ind, integer* ptr);
    /** Construct a matrix sharing the memory with rhs. */
    compressed_matrix(const compressed_matrix<T>& rhs);
    ~compressed_matrix();

    //properties

    /** Is an empty matrix (0-by-0)? */
    bool is_empty() const;
    /** Get the size of d th dimension. */
    integer size(integer d) const;
    /** Get the number of nonzeros. */
    integer nnz() const;
    /** Get the array of nonzero values. */
    T* nzval() const;
    /** Get the array of indices. */
    integer* ind() const;
    /** Get the array of pointers. */
    integer* ptr() const;
    
    /** Allocate memory for this matrix if this matrix is empty.
     * If this matrix is empty, then new memory is allocated and
     * return true, otherwise no memory will be allocated and return
     * false.
     */
    bool allocate(integer m, integer n, integer nnz);
    /** Hard copy. */
    compressed_matrix<T>& operator=(const compressed_matrix<T>& rhs);
    void set_zero();
}; //class compressed_matrix

template<class T>
inline 
compressed_matrix<T>::compressed_matrix()
{
    _pref = new compref<T>;
    _pref->nrow = _pref->ncol = _pref->nnz = 0;
    _pref->nzval = NULL;
    _pref->ind = _pref->ptr = NULL;
    _pref->count = 1;
    _pref->is_own = true;
}

template<class T>
inline 
compressed_matrix<T>::compressed_matrix(integer m, integer n, integer nnz)
    :_pref(NULL)
{
    assert(m>0 && n>0);

    _pref = new compref<T>;
    _pref->nrow = m;
    _pref->ncol = n;
    _pref->nnz = nnz;

    _pref->nzval = new T[nnz];
    _pref->ind = new integer[nnz];
    _pref->ptr = new integer[n+1];

    // set nzval = 0;
    memset(_pref->nzval, 0, _pref->nnz * sizeof(T));

    _pref->count = 1;
    _pref->is_own = true;
}

template<class T>
inline 
compressed_matrix<T>::compressed_matrix(integer m, integer n, integer nnz, 
                      T* nzval, integer* ind, integer* ptr)
    :_pref(NULL)
{
    assert(m>0 && n>0);
        
    _pref = new compref<T>;

    _pref->nrow = m;
    _pref->ncol = n;
    _pref->nnz = nnz;

    _pref->nzval = nzval;
    _pref->ind = ind;
    _pref->ptr = ptr;

    _pref->count = 2;

    _pref->is_own = false;
}

template<class T>
inline 
compressed_matrix<T>::compressed_matrix(const compressed_matrix<T>& rhs)
    :_pref(rhs._pref)
{
    _pref->count++;
}

template<class T>
inline void 
compressed_matrix<T>::free_memory()
{
    --_pref->count;
    if(_pref->count == 0)
    {
        delete[] _pref->nzval;
        delete[] _pref->ind;
        delete[] _pref->ptr;

        delete   _pref;
    }
    else if(_pref->count == 1 && !_pref->is_own)
    {
        delete _pref;
    }
    _pref = NULL;
}

template<class T>
inline 
compressed_matrix<T>::~compressed_matrix()
{
    free_memory();
}

template<class T>
inline bool 
compressed_matrix<T>::is_empty() const
{
    return _pref->nzval == NULL;
}

template<class T>
inline integer
compressed_matrix<T>::size(integer d) const
{
    return d==0 ? _pref->nrow : _pref->ncol;
}

template<class T>
inline integer
compressed_matrix<T>::nnz() const
{
    return _pref->nnz;
}

template<class T>
inline T*
compressed_matrix<T>::nzval() const
{
    return _pref->nzval;
}

template<class T>
inline integer*
compressed_matrix<T>::ind() const
{
    return _pref->ind;
}

template<class T>
inline integer*
compressed_matrix<T>::ptr() const
{
    return _pref->ptr;
}


template<class T>
inline bool
compressed_matrix<T>::allocate(integer m, integer n, integer nnz)
{
    assert(m>0 && n>0 && nnz>0 && nnz<m*n);

    if(!is_empty() || !_pref->is_own) return false;
    
    _pref->nrow = m;
    _pref->ncol = n;
    _pref->nnz = nnz;

    _pref->nzval = new T[nnz];
    _pref->ind = new integer[nnz];
    _pref->ptr = new integer[n+1];

    _pref->count = 1;
    _pref->is_own = true;

    return true;
}

template<class T>
inline compressed_matrix<T>& 
compressed_matrix<T>::operator=(const compressed_matrix<T>& rhs)
{
    assert(is_empty()
           || (_pref->nrow == rhs._pref->nrow
               && _pref->ncol == rhs._pref->ncol
               && _pref->nnz == rhs._pref->nnz)
           );
    if(this == &rhs) return *this;

    if(is_empty() ) allocate(rhs.size(0), rhs.size(1), rhs.nnz() );

    memcpy(_pref->nzval, rhs._pref->nzval, _pref->nnz*sizeof(T));
    memcpy(_pref->ind, rhs._pref->ind, _pref->nnz*sizeof(integer));
    memcpy(_pref->ptr, rhs._pref->ptr, (_pref->ncol+1)*sizeof(integer));
    return *this;
}

template<class T>
inline void compressed_matrix<T>::set_zero()
{
   memset(_pref->nzval, 0, _pref->nnz * sizeof(T));
}

/** @} */ //end group compressed_matrix


#endif
