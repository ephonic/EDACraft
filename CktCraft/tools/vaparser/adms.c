
/* ------- code automatically created by mkelements.pl -------------- */
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "adms.h"


/*s1: realloced s2: constant ret: s1=s1s2*/
void adms_k2strconcat (char **s1,const char* s2)
{
  if(!s2)
    return;
  if(*s1)
  {
    int l1=strlen(*s1);
    int l2=strlen(s2);
    *s1=(char*)realloc(*s1,(l1+l2+1)*sizeof(char));
    memcpy(*s1+l1,s2,l2+1);
  }
  else
    *s1=strdup(s2);
}
/*s1: realloced s2: freed ret: s1=s1s2*/
void adms_strconcat (char **s1,char *s2)
{
  adms_k2strconcat(s1,s2);
  free(s2);
}
FILE* adms_file_open_read (const char* myfilename)
{
  FILE* fh=fopen(myfilename,"r");
  if(!fh)
    adms_message_fatal(("%s: failed to open file [read mode]\n",myfilename))
      return fh;
}

p_admsmain globaladmsmain;
p_admsmain root(void) {return globaladmsmain;}

p_slist adms_slist_last (p_slist l)
{
  if(l)
  {
    while(l->next)
      l=l->next;
  }
  return l;
}
p_slist adms_slist_new (p_adms d)
{
  p_slist newl=NULL;
  adms_slist_push(&newl,d);
  return newl;
}
p_slist adms_slist_copy (p_slist l)
{
  p_slist copiedl=NULL;
  while(l)
  {
    adms_slist_push(&copiedl,l->data);
    l=l->next;
  }
  return adms_slist_reverse(copiedl);
}
void adms_slist_push(p_slist* l,p_adms data)
{
  p_slist n=(p_slist)malloc(sizeof(t_slist));
  n->next=*l;
  n->data=data;
  *l=n;
}
p_adms adms_slist_pull(p_slist* l)
{
  if(*l)
  {
    p_slist n=*l;
    p_adms data=n->data;
    *l=(*l)->next;
    free(n);
    return data;
  }
  return NULL;
}
void adms_slist_concat (p_slist* l1,p_slist l2)
{
  if(l2)
  {
    if(*l1)
      adms_slist_last(*l1)->next=l2;
    else
      *l1=l2;
  }
}
unsigned int adms_slist_length (p_slist l)
{
  unsigned int length=0;
  while(l)
  {
    length++;
    l=l->next;
  }
  return length;
}
p_slist adms_slist_nth (p_slist l,unsigned int  n)
{
  while (n-->0 && l)
    l=l->next;
  return l;
}
p_adms adms_slist_nth_data (p_slist l,unsigned int n)
{
  while (n-->0 && l)
    l=l->next;
  return l ? l->data : ((p_adms)0);
}
p_slist adms_slist_find (p_slist l,p_kadms data)
{
  while(l)
  {
    if(l->data==data)
      break;
    l=l->next;
  }
  return l;
}
int adms_slist_index (p_slist l, p_kadms data)
{
  int i=0;
  while(l)
  {
    if(l->data==data)
      return i;
    i++;
    l=l->next;
  }
  return -1;
}
p_slist adms_slist_reverse (p_slist l)
{
  p_slist p=NULL;
  while(l)
  {
    p_slist n=l->next;
    l->next=p;
    p=l;
    l=n;
  }
  return p;
}
void adms_slist_inreverse (p_slist* l)
{
  *l=adms_slist_reverse(*l);
}
void adms_slist_free (p_slist l)
{
  while(l)
  {
    p_slist freed=l;
    l=l->next;
    free(freed);
  }
}

char*adms_kclone(const char* m)
{
  if(m)
  {
    int l=strlen(m);
    char*mycpy=(char*)malloc((l+1)*sizeof(char));
    memcpy(mycpy,m,l);
    mycpy[l]='\0';
    return mycpy;
  }
  else
    return NULL;
}
char*adms_knclone(const char* m,const int l)
{
  char*mycpy=(char*)malloc((l+1)*sizeof(char));
  memcpy(mycpy,m,l);
  mycpy[l]='\0';
  return mycpy;
}
char* adms_integertostring(int value)
{
  char* string=(char*)malloc(sizeof(char)*50);
  sprintf(string,"%i",value);
  return string;
}

void bp(void) {}

_t_message (adms_message_fatal_impl)
{
  va_list ap;
  int insideformat=0;
  int i;
  char* s;
  double d;
  void* p;
  fputs("[fatal..] ",stderr);
  va_start(ap, format);
  for(;*format;format++)
  {
    if(insideformat)
    {
      insideformat=0;
      switch(*format) 
      {
      case 's':
        s=va_arg (ap,char*);
        if(s) fputs(s,stderr); else fputs("NULL",stderr);
        break;
      case 'e':
        d=va_arg (ap,double);
        fprintf(stderr,"%e",d);
        break;
      case 'g':
        d=va_arg (ap,double);
        fprintf(stderr,"%g",d);
        break;
      case 'f':
        d=va_arg (ap,double);
        fprintf(stderr,"%f",d);
        break;
      case 'i':
        i=va_arg (ap,int);
        fprintf(stderr,"%i",i);
        break;
      case 'p':
        p=va_arg (ap,void*);
        fprintf(stderr,"%p",p);
        break;
      default:
        fputc(*format,stderr);
      }
    }
    else
    {
      switch(*format) 
      {
      case '%':
        insideformat=1;
        break;
      default:
        fputc(*format,stderr);
      }
    }
  }
  va_end (ap);
  fflush(stderr);
  bp(),exit(1);
}

_t_message (adms_message_info_impl)
{
  va_list ap;
  int insideformat=0;
  int i;
  char* s;
  double d;
  void* p;
  fputs("[info...] ",stdout);
  va_start(ap, format);
  for(;*format;format++)
  {
    if(insideformat)
    {
      insideformat=0;
      switch(*format) 
      {
      case 's':
        s=va_arg (ap,char*);
        if(s) fputs(s,stdout); else fputs("NULL",stdout);
        break;
      case 'e':
        d=va_arg (ap,double);
        fprintf(stdout,"%e",d);
        break;
      case 'g':
        d=va_arg (ap,double);
        fprintf(stdout,"%g",d);
        break;
      case 'f':
        d=va_arg (ap,double);
        fprintf(stdout,"%f",d);
        break;
      case 'i':
        i=va_arg (ap,int);
        fprintf(stdout,"%i",i);
        break;
      case 'p':
        p=va_arg (ap,void*);
        fprintf(stdout,"%p",p);
        break;
      default:
        fputc(*format,stdout);
      }
    }
    else
    {
      switch(*format) 
      {
      case '%':
        insideformat=1;
        break;
      default:
        fputc(*format,stdout);
      }
    }
  }
  va_end (ap);
  fflush(stdout);
}

_t_message (adms_message_warning_impl)
{
  va_list ap;
  int insideformat=0;
  int i;
  char* s;
  double d;
  void* p;
  fputs("[warning] ",stderr);
  va_start(ap, format);
  for(;*format;format++)
  {
    if(insideformat)
    {
      insideformat=0;
      switch(*format) 
      {
      case 's':
        s=va_arg (ap,char*);
        if(s) fputs(s,stderr); else fputs("NULL",stderr);
        break;
      case 'e':
        d=va_arg (ap,double);
        fprintf(stderr,"%e",d);
        break;
      case 'g':
        d=va_arg (ap,double);
        fprintf(stderr,"%g",d);
        break;
      case 'f':
        d=va_arg (ap,double);
        fprintf(stderr,"%f",d);
        break;
      case 'i':
        i=va_arg (ap,int);
        fprintf(stderr,"%i",i);
        break;
      case 'p':
        p=va_arg (ap,void*);
        fprintf(stderr,"%p",p);
        break;
      default:
        fputc(*format,stderr);
      }
    }
    else
    {
      switch(*format) 
      {
      case '%':
        insideformat=1;
        break;
      default:
        fputc(*format,stderr);
      }
    }
  }
  va_end (ap);
  fflush(stderr);
}

_t_message (adms_message_verbose_impl)
{
  va_list ap;
  int insideformat=0;
  int i;
  char* s;
  double d;
  void* p;
  fputs("[verbose] ",stdout);
  va_start(ap, format);
  for(;*format;format++)
  {
    if(insideformat)
    {
      insideformat=0;
      switch(*format) 
      {
      case 's':
        s=va_arg (ap,char*);
        if(s) fputs(s,stdout); else fputs("NULL",stdout);
        break;
      case 'e':
        d=va_arg (ap,double);
        fprintf(stdout,"%e",d);
        break;
      case 'g':
        d=va_arg (ap,double);
        fprintf(stdout,"%g",d);
        break;
      case 'f':
        d=va_arg (ap,double);
        fprintf(stdout,"%f",d);
        break;
      case 'i':
        i=va_arg (ap,int);
        fprintf(stdout,"%i",i);
        break;
      case 'p':
        p=va_arg (ap,void*);
        fprintf(stdout,"%p",p);
        break;
      default:
        fputc(*format,stdout);
      }
    }
    else
    {
      switch(*format) 
      {
      case '%':
        insideformat=1;
        break;
      default:
        fputc(*format,stdout);
      }
    }
  }
  va_end (ap);
  fflush(stdout);
}
