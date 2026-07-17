#ifndef LAPACKINT_FORTRAN_UTIL_H
#define LAPACKINT_FORTRAN_UTIL_H
/**
 * @file
 * This file contains assistant routines for blas and lapack.
 * @author Yami
 * @date Oct. 10, 2005
 */

#include "typeint.h"


/**
 * We use specialized template class to determine the atom type of
 * a tyep. Here atom type refers to the plain data type provided by
 * the C language. complex's atom type is real, because a complex
 * is consisted by two real number.
 *
 * One can use fortran_type<doublecomplex>::atom_type to get the atom
 * type of doublecomplex. This utility is used in template programming.
 */
template<class T>
struct fortran_type;

template<>
struct fortran_type<real>
{
    typedef real atom_type;
};

template<>
struct fortran_type<doublereal>
{
    typedef doublereal atom_type;
};

template<>
struct fortran_type<complex>
{
    typedef real atom_type;
};

template<>
struct fortran_type<doublecomplex>
{
    typedef doublereal atom_type;
};


inline bool
is_valid_op(char trans)
{
    return (trans=='n' || trans=='N' 
            || trans=='t' || trans=='T'
            || trans=='c' || trans=='C');
}

/**
 * As you see, Conjugated transposed is transposed.
 */
inline bool
is_transposed(char trans)
{
    return trans=='t' || trans=='T' || trans=='c' || trans=='C';
}

inline bool
is_conjugated(char trans)
{
    return trans=='c'||trans=='C';
}

#endif //LAPACKINT_BLAS_UTIL_H

