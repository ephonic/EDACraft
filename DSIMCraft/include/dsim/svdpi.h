#ifndef DSIM_SVDPI_H
#define DSIM_SVDPI_H
/* Public scalar/packed-vector and scope subset of the IEEE DPI C ABI. */
#include <stdint.h>
typedef unsigned char svBit;
typedef unsigned char svLogic;
typedef uint32_t svBitVecVal;
typedef struct {uint32_t aval,bval;} svLogicVecVal;
typedef void* svScope;
#define sv_0 0
#define sv_1 1
#define sv_z 2
#define sv_x 3
#ifdef __cplusplus
extern "C" {
#endif
svScope svGetScope(void);
svScope svSetScope(const svScope scope);
svScope svGetScopeFromName(const char* name);
const char* svGetNameFromScope(const svScope scope);
#ifdef __cplusplus
}
#endif
#endif
