/** @file 
 *  header file for nodes
 *  @author yangfan(yangfan@fudan.edu.cn)
 *  @date 2006.11.21
 */


#ifndef NODES_H_
#define NODES_H_
#include "amor_comm.h"
#include <map>

using std::map;
using std::string;

/** @addtogroup parser
 *  @{
*/


/**
 * A node list dictionary.
 *
*/


class node_list
{
public:
  /** a map for node name to integer conversion. */
  map<string, int> _nodes2int;

  /** a map for integer to node name conversion. */
  map<int, string> _int2nodes;

  /** number of nodes.*/
  int _num_nodes;

 public:
  /** default constructor. */
  explicit node_list():_num_nodes(0) {}

  /** convert node name to integer and put the node name into the dictionary. */
  int nodename2num(string node_name);

  /** convert the integer to node name by searching the dictionary.*/
  string num2nodename(int num);

  /** return the node number.*/
  int node_nums() {return _num_nodes-1;}

  /** get node id by node name. */
  int get_nodenum(const string &nodename);

  /** check whether the node in the node dictionary. */
  bool is_exist(string node);

  /** dump all the nodes into a file.*/
  void dump_nodes(std::string filename);

};

/** @} */

#endif
