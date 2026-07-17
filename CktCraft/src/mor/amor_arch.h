//      LAPACK++ (V. 1.1)
//      (C) 1992-1996 All Rights Reserved.


// Linkage names between C, C++, and Fortran (platform dependent)

#ifndef HSIS_ARCH_H
#define HSIS_ARCH_H


#if  defined(RIOS) && !defined(CLAPACK)
#define F77NAME(x) x
#else
#define F77NAME(x) x##_
#endif

#if defined(SGI) && !defined(SGI_DEC)
#define SGI_DEC

extern "C" {
	void mkidxname() {}
	void mkdatname() {}
}

#endif

#endif // HSIS_ARCH_H
