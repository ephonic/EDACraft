#include "comm.h"
#include "res.h"
#include "ckt.h"
#include "subckt.h"
#include "orth_list.h"
#include "unit.h"
#include "graph.h"

using std::string;
using std::istringstream;


void res::load(orth_list& g, orth_list& c, graph_t& graph, ckt* pckt)
{
  int pnode;
  int nnode;
  
  pnode = pckt->nodename2num(_pos_port);
  nnode = pckt->nodename2num(_neg_port);

  g.stamp(pnode, nnode, _value);

  if(pnode != 0 && nnode != 0)
    add_edge(pnode-1, nnode-1, graph);
    
}

void res::load(orth_list& g, orth_list& c, graph_t& graph, subckt* pckt)
{
  int pnode;
  int nnode;
  

  pnode = pckt->nodename2num(_pos_port);
  nnode = pckt->nodename2num(_neg_port);

  g.stamp(pnode, nnode, _value);

  if(pnode != 0 && nnode != 0)
    add_edge(pnode-1, nnode-1, graph);
    
}

