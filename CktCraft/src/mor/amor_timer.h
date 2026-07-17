#ifndef TIMER_H_
#define TIMER_H_

#include <sys/time.h>


class timer
{
public:
  timer() {}
  void start();
  double end();

private:
  struct timeval _start;
};


#endif
