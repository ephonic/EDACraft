#include "amor_comm.h"
#include "amor_cap.h"
#include "amor_ckt.h"
#include "amor_subckt.h"
#include "amor_orth_list.h"
#include "amor_unit.h"

using std::string;
using std::istringstream;


void cap::load(orth_list& g, orth_list& c, graph_t& graph, ckt* pckt)
{
  int pnode;
  int nnode;
  
  pnode = pckt->nodename2num(_pos_port);
  nnode = pckt->nodename2num(_neg_port);

  c.stamp(pnode, nnode, _value);
}

void cap::load(orth_list& g, orth_list& c, graph_t& graph, subckt* pckt)
{
  int pnode;
  int nnode;
  
  pnode = pckt->nodename2num(_pos_port);
  nnode = pckt->nodename2num(_neg_port);

  c.stamp(pnode, nnode, _value);
}

