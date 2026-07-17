/* Prototypes for __malloc_hook, __free_hook */ 
#include <malloc.h> 
#include <stdlib.h>
#include <stdio.h>
#include <vector>


const int MAX_SIZE = 100000;
int current_pos = 0;

int memory_usage = 0;


struct stack_map_t
{
  void* addr;
  int size;
};


stack_map_t stack_map[MAX_SIZE];


int find_size(stack_map_t a[], void * b)
{
  int i;

  for(i = 0; i <= current_pos; ++i)
    {
      if(a[i].addr == b)
	{
	  return i;
	}
    }

  return -1;
}

/* Prototypes for our hooks.  */ 

     static void my_init_hook (void); 
     static void *my_malloc_hook (size_t, const void *); 
     static void my_free_hook (void*, const void *); 

     static void *(*old_malloc_hook) (size_t __size, __const __malloc_ptr_t); 
     static void (*old_free_hook)  (void *__ptr, __const __malloc_ptr_t); 
                    
/* Override initializing hook from the C library. */ 
void (*__malloc_initialize_hook) (void) = my_init_hook; 

static void my_init_hook (void) 
{ 
    old_malloc_hook = __malloc_hook; 
    old_free_hook = __free_hook; 
    __malloc_hook = my_malloc_hook; 
    __free_hook = my_free_hook; 
} 
     
     static void * 
          my_malloc_hook (size_t size, const void *caller) 
{ 
    void *result; 
    /* Restore all old hooks */ 
    __malloc_hook = old_malloc_hook; 
    __free_hook = old_free_hook; 
    /* Call recursively */ 
    result = malloc (size); 
    /* Save underlying hooks */ 
    old_malloc_hook = __malloc_hook; 
    old_free_hook = __free_hook; 
    /* printf might call malloc, so protect it too. */ 
    // printf ("malloc (%u) returns %p\n", (unsigned int) size, result);
    int i;
    memory_usage += size;
    i = find_size(stack_map, result);
    if(i != -1)
      {
	stack_map[i].addr = result;
	stack_map[i].size = size;
      }
    else
      {
	current_pos++;
	stack_map[current_pos].addr = result;
	stack_map[current_pos].size = size;
      }
    printf("ALLOC size %d  - memory usage: %d\n", size, memory_usage);
    /* Restore our own hooks */ 
    __malloc_hook = my_malloc_hook; 
    __free_hook = my_free_hook; 
    return result; 
} 
     
     static void 
          my_free_hook (void *ptr, const void *caller) 
{ 
    /* Restore all old hooks */ 
    __malloc_hook = old_malloc_hook; 
    __free_hook = old_free_hook; 
    /* Call recursively */ 
    free (ptr); 
    /* Save underlying hooks */ 
    old_malloc_hook = __malloc_hook; 
    old_free_hook = __free_hook; 
    /* printf might call free, so protect it too. */ 
    //   printf ("freed pointer %p\n", ptr);
    int i = find_size(stack_map, ptr);
    if(i == -1)
      printf("Memory Error: attempt to free unalloc memory \n ");
    memory_usage -= stack_map[i].size;
    printf("FREE size %d - memory usage: %d\n", stack_map[i].size,  memory_usage);
    /* Restore our own hooks */ 
    __malloc_hook = my_malloc_hook; 
    __free_hook = my_free_hook; 
} 
     
