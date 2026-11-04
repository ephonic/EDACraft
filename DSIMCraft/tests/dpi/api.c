#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include "svdpi.h"
#include <string.h>
#include <stdlib.h>
#include <dlfcn.h>
int add_one(int x){return x+1;}
signed char echo_byte(signed char x){return x;}
unsigned short echo_short(unsigned short x){return x;}
long long sum_long(long long a,long long b){return a+b;}
unsigned long long echo_ulong(unsigned long long x){return x;}
svLogic echo_logic(svLogic x){return x;}
svBit invert_bit(svBit x){return !x;}
const char* decorate(const char* x){return strcmp(x,"hello")==0?"hello dpi":"BAD";}
void copy_text(const char* x,const char** y){*y=x;}
void out_args(int x,int* y,long long* z){*y=x+7;*z+=x;}
void packed_transfer(const svLogicVecVal* input,svLogicVecVal* output,svBitVecVal* bits){
  for(int i=0;i<5;++i)output[i]=input[i];
  bits[0]^=0x76543210;bits[1]^=0xfedcba98;bits[2]^=1;
}
void single(const svLogicVecVal* input,svLogicVecVal* output){*output=*input;}
int integer_value(const svLogicVecVal* input){return input[0].aval==0xf0f0f0f0u&&input[0].bval==0x00ff00ffu;}
void fill_time(svLogicVecVal* output){output[0].aval=0x87654321;output[1].aval=0x12345678;output[0].bval=output[1].bval=0;}
static int external_count;
int bump(void){return ++external_count;}
int count(void){return external_count;}
int pure_twice(int x){return x*2;}
static int invoke(const char* name,int value){
  void* symbol=dlsym(RTLD_DEFAULT,name);int(*fn)(int)=0;
  if(!symbol)abort();memcpy(&fn,&symbol,sizeof(fn));return fn(value);
}
int callback(int value){
  if(!svGetScope()||strcmp(svGetNameFromScope(svGetScope()),"top.a"))return -1000;
  svScope original=svGetScope(),other=svGetScopeFromName("top.b");
  if(!other||svGetScopeFromName("missing"))return -2000;
  int a=invoke("hook",value);if(svGetScope()!=original)return -3000;
  if(svSetScope(other)!=original)return -4000;
  int b=invoke("hook",value+1);if(svSetScope(original)!=other)return -5000;
  return a+b;
}
int nested(int value){return invoke("inner",value);}
int ordinary_scope(void){return svGetScope()!=0;}
int context_scope(void){return svGetScope()!=0;}
int bad_callback(int value){return invoke("hook",value);}
static void* lookup(const char* name){void* p=dlsym(RTLD_DEFAULT,name);if(!p)abort();return p;}
int typed_gateway(void){
  int(*fn)(signed char,long long*,const char**,svLogicVecVal*,svBitVecVal*);void* p=lookup("typed");memcpy(&fn,&p,sizeof(fn));
  long long out=0;const char* text="begin";svLogicVecVal vec[4]={{0}};svBitVecVal bits[3]={0xabcdef01,0x23456789,1};
  int result=fn(-5,&out,&text,vec,bits);
  if(result!=-2||out!=-10000000005LL||strcmp(text,"begin!")||vec[0].aval!=0x12345678||vec[0].bval||vec[1].aval!=0xffffffff||vec[1].bval!=0xffffffff||vec[2].aval||vec[2].bval!=0xffffffff||vec[3].aval!=1||vec[3].bval)return -900;
  if(bits[0]!=0xdd99dd11||bits[1]!=0xdd99dd11||bits[2])return -901;
  void(*empty)(void);p=lookup("empty");memcpy(&empty,&p,sizeof(empty));empty();
  const char*(*greeting)(void);p=lookup("greeting");memcpy(&greeting,&p,sizeof(greeting));
  return strcmp(greeting(),"hello export")?-902:42;
}
int wrong_scope(int value){svSetScope(svGetScopeFromName("top"));return invoke("hook",value);}
