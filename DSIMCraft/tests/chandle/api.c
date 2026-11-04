#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include "svdpi.h"
#include <stdint.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>
static int slots[2] = {41, 73};
static int foreign_calls;
void *get_handle(int i) { return &slots[i & 1]; }
int inspect_handle(void *p) { return p == &slots[0] ? slots[0] : p == &slots[1] ? slots[1] : p == 0 ? -1 : -2; }
void exchange_handles(void *a, void **b, void **c) { *b = *c; *c = a; }
int counted_handle(void *p) { ++foreign_calls; return inspect_handle(p); }
int handle_calls(void) { return foreign_calls; }
void *callback_handle(void *p, void **out, void **io) {
 void *symbol=dlsym(RTLD_DEFAULT,"hook_handle");
 void *(*hook)(void *,void **,void **)=0;
 if(!symbol)abort();
 memcpy(&hook,&symbol,sizeof(hook));return hook(p,out,io);
}
