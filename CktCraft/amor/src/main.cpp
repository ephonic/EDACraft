#include "amor.h"

int main(int argc, char** argv)
{
  amor* _am = new amor();
  _am->run(argv[1], argv[2]);
}
