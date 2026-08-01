/* gnu_compat.h — MSVC 下的 GNU 扩展函数 shim（/FI 强制包含）。
 * 目前提供 asprintf/vasprintf（derYacc.y 等使用）。 */
#pragma once
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

#ifdef _MSC_VER
#ifndef RFSIM_GNU_COMPAT_IMPL
#define RFSIM_GNU_COMPAT_IMPL
static int rfsim_vasprintf(char** strp, const char* fmt, va_list ap) {
    va_list ap2;
    va_copy(ap2, ap);
    int n = vsnprintf(NULL, 0, fmt, ap2);
    va_end(ap2);
    if (n < 0) return n;
    *strp = (char*)malloc((size_t)n + 1);
    if (!*strp) return -1;
    return vsnprintf(*strp, (size_t)n + 1, fmt, ap);
}
static int asprintf(char** strp, const char* fmt, ...) {
    va_list ap;
    int r;
    va_start(ap, fmt);
    r = rfsim_vasprintf(strp, fmt, ap);
    va_end(ap);
    return r;
}
#endif
#endif /* _MSC_VER */
