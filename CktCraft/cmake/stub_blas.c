// stub_blas.c - 最小 BLAS 实现（供 UMFPACK 链接用）
// 用简单 C 循环实现 UMFPACK 需要的 BLAS-1/2/3 函数。
// MSVC 下 UMFPACK 用无下划线函数名（dgemv 而非 dgemv_）。
#include <math.h>
#include <string.h>

// BLAS-1
void daxpy(int *n, double *da, double *dx, int *incx, double *dy, int *incy) {
    int nn = *n;
    for (int i = 0; i < nn; ++i) dy[i * (*incy)] += *da * dx[i * (*incx)];
}
void dcopy(int *n, double *dx, int *incx, double *dy, int *incy) {
    int nn = *n;
    for (int i = 0; i < nn; ++i) dy[i * (*incy)] = dx[i * (*incx)];
}
void dscal(int *n, double *da, double *dx, int *incx) {
    int nn = *n;
    for (int i = 0; i < nn; ++i) dx[i * (*incx)] *= *da;
}
void dswap(int *n, double *dx, int *incx, double *dy, int *incy) {
    int nn = *n;
    for (int i = 0; i < nn; ++i) {
        double t = dx[i * (*incx)]; dx[i * (*incx)] = dy[i * (*incy)]; dy[i * (*incy)] = t;
    }
}
double ddot(int *n, double *dx, int *incx, double *dy, int *incy) {
    double s = 0; int nn = *n;
    for (int i = 0; i < nn; ++i) s += dx[i * (*incx)] * dy[i * (*incy)];
    return s;
}
double dnrm2(int *n, double *dx, int *incx) {
    double s = 0; int nn = *n;
    for (int i = 0; i < nn; ++i) { double v = dx[i * (*incx)]; s += v * v; }
    return sqrt(s);
}
double dasum(int *n, double *dx, int *incx) {
    double s = 0; int nn = *n;
    for (int i = 0; i < nn; ++i) s += fabs(dx[i * (*incx)]);
    return s;
}
int idamax(int *n, double *dx, int *incx) {
    int nn = *n, idx = 0; double mx = 0;
    for (int i = 0; i < nn; ++i) { double v = fabs(dx[i * (*incx)]); if (v > mx) { mx = v; idx = i; } }
    return idx + 1;
}
void drot(int *n, double *dx, int *incx, double *dy, int *incy, double *c, double *s) {
    int nn = *n;
    for (int i = 0; i < nn; ++i) {
        double x = dx[i*(*incx)], y = dy[i*(*incy)];
        dx[i*(*incx)] = *c * x + *s * y;
        dy[i*(*incy)] = -(*s) * x + *c * y;
    }
}
void drotg(double *da, double *db, double *c, double *s) {
    double r = sqrt((*da)*(*da) + (*db)*(*db));
    if (r > 0) { *c = *da / r; *s = *db / r; } else { *c = 1; *s = 0; }
    *da = r;
}

// BLAS-2
void dgemv(char *trans, int *m, int *n, double *alpha, double *a, int *lda,
            double *x, int *incx, double *beta, double *y, int *incy) {
    int mm = *m, nn = *n;
    for (int i = 0; i < mm; ++i) y[i] *= *beta;
    for (int j = 0; j < nn; ++j)
        for (int i = 0; i < mm; ++i)
            y[i] += *alpha * a[j * mm + i] * x[j];
}
void dger(int *m, int *n, double *alpha, double *x, int *incx,
           double *y, int *incy, double *a, int *lda) {
    int mm = *m, nn = *n;
    for (int j = 0; j < nn; ++j)
        for (int i = 0; i < mm; ++i)
            a[j * mm + i] += *alpha * x[i] * y[j];
}
void dtrsv(char *uplo, char *trans, char *diag, int *n, double *a, int *lda,
            double *x, int *incx) {
    int nn = *n;
    for (int i = 0; i < nn; ++i) {
        double s = x[i];
        for (int j = 0; j < i; ++j) s -= a[j * nn + i] * x[j];
        x[i] = s / a[i * nn + i];
    }
}

// BLAS-3
void dgemm(char *transa, char *transb, int *m, int *n, int *k,
            double *alpha, double *a, int *lda, double *b, int *ldb,
            double *beta, double *c, int *ldc) {
    int mm = *m, nn = *n, kk = *k;
    for (int j = 0; j < nn; ++j)
        for (int i = 0; i < mm; ++i)
            c[j * mm + i] *= *beta;
    for (int j = 0; j < nn; ++j)
        for (int l = 0; l < kk; ++l)
            for (int i = 0; i < mm; ++i)
                c[j * mm + i] += *alpha * a[l * mm + i] * b[j * kk + l];
}
void dtrsm(char *side, char *uplo, char *transa, char *diag, int *m, int *n,
            double *alpha, double *a, int *lda, double *b, int *ldb) {
    int mm = *m, nn = *n;
    for (int j = 0; j < nn; ++j) {
        for (int i = 0; i < mm; ++i) {
            double s = b[j * mm + i];
            for (int l = 0; l < i; ++l) s -= a[i * mm + l] * b[j * mm + l];
            b[j * mm + i] = s / a[i * mm + i] * (*alpha);
        }
    }
}
void dsyrk(char *uplo, char *trans, int *n, int *k, double *alpha,
            double *a, int *lda, double *beta, double *c, int *ldc) {
    int nn = *n, kk = *k;
    for (int j = 0; j < nn; ++j)
        for (int i = 0; i <= j; ++i) {
            double s = 0;
            for (int l = 0; l < kk; ++l) s += a[l * nn + i] * a[l * nn + j];
            c[j * nn + i] = *beta * c[j * nn + i] + *alpha * s;
        }
}
