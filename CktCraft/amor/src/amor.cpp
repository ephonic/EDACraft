#include "amor.h"

using namespace std;

amor::amor() {
  _maxblocksize = 35;
  _org_ckt = new ckt;
}

void amor::set_maxblocksize(int size)
{
  _maxblocksize = size;
}

amor::~amor() {
  if(_org_ckt != NULL)
    delete _org_ckt;
}

int amor::run(const char* inputfile, const char* outputfile)
{
  _org_ckt->set_max_blocksize(_maxblocksize);
  _org_ckt->parse(inputfile);
  _org_ckt->post_parse();
  _org_ckt->partition();
  _org_ckt->reduction();
  _org_ckt->dump_netlist(outputfile);
  _org_ckt->free_subckt_list();

  return 0;
  
}

