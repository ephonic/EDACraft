#ifndef AMOR_H_
#define AMOR_H_

#include "amor_ckt.h"

class amor{
public:
  amor();
  ~amor();
  void set_maxblocksize(int size);

  int run(const char* inputfile, const char* outputfile);

private:
  int _maxblocksize;
  ckt* _org_ckt;
  
  
};



#endif
