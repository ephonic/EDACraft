#include "comm.h"
#include "cap.h"
#include "ckt.h"
#include "subckt.h"
#include "orth_list.h"
#include "unit.h"

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

