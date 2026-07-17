/** @file 
 *  header file for nodes
 *  @author yangfan(yangfan@fudan.edu.cn)
 *  @date 2006.11.21
 */
#include "amor_node_list.h"

using std::cerr;
using std::endl;
using std::ofstream;

int node_list::nodename2num(string node_name)
{
  if(node_name == "gnd!" || node_name == "gnd")
    return 0;
  
  // check if the node_name is in the nodes2int list
  if(_nodes2int.find(node_name) == _nodes2int.end())
    {
      _nodes2int[node_name] = _num_nodes;
      _int2nodes[_num_nodes] = node_name;
      ++_num_nodes;
      assert(_nodes2int.size() == _int2nodes.size());
    }
  return _nodes2int[node_name];
}


string node_list::num2nodename(int num)
{
  if(_int2nodes.find(num) == _int2nodes.end())
    {
      return "No such node";
    }
  else if (num==0)
    {
      return "gnd";
    }
  else
    {
      return _int2nodes[num];
    }
}

int node_list::get_nodenum(const string &nodename)
{
  if(nodename == "gnd!" || nodename == "gnd")
    return 0;  
  map<string, int>::iterator iter;
  iter = _nodes2int.find(nodename);
  if(iter == _nodes2int.end())
    {
      return -1;
    }
  else
    {
      return iter->second;
    }
}

bool node_list::is_exist(string node)
{
  if(node == "gnd" || node == "gnd!")
    return true;
  
  if(_nodes2int.find(node) == _nodes2int.end())
    {
      return false;
    }
  else
    {
      return true;
    }
  
}


void node_list::dump_nodes(string filename)
{
  ofstream outf(filename.c_str());
  int i;
  for(i = 0; i < _num_nodes; ++i)
    {
      outf << _int2nodes[i] << endl;
    }
  outf.close();
}
