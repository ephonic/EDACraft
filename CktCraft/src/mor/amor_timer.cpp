#include "amor_timer.h"
#include "stdio.h"

void timer::start()
{
  gettimeofday(&_start, NULL);
}

double timer::end()
{
  double t;
  timeval endt;
  gettimeofday(&endt, NULL);
  t = (1e6 * (endt.tv_sec - _start.tv_sec) + (endt.tv_usec - _start.tv_usec)) / 1e6;

  return t;
  
}
