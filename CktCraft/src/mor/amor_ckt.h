#ifndef CKT_H_
#define CKT_H_


/**
 * @file
 * Header file for the circuit.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */


#include <iostream>
#include <vector>
#include <map>
#include <list>
#include "amor_comm.h"
#include "amor_element.h"
#include "amor_node_list.h"
#include "amor_orth_list.h"
#include "graph.h"
#include <utility>
#include <stack>


class subckt;
class subckt_ins;

/** @group reduction the main module of the programme.
 *  The module includes a ckt class holding the data of the circuit, and
 *  the partition, reduction and reduced netlist dumping routines.
 *
*/


/** @addtogroup reduction
 *  @{
*/


/**
 * A class for holding the data of a circuit.
 *
*/


class ckt
{
public:
  /** default constructor, with input filename and outfilename as arguments. */
  ckt() :
    _partition_label(NULL),
    _subblock_threshold(10),
    _geps(1e-12),
    _ceps(1e-18),
    _relative_tol(1e-4),
    _subckt_mode(false),
    _special_node_mode(false),
    _current_sckt(NULL)
  {
  }

  /** deconstructor */
  ~ckt();

public:
  /** node list dictionary */
  node_list _nl;
  
protected:
  /** _element_list hold all the linear elements (resistors and capacitors). */
  std::list<element *> _element_list;

  /** number of ports of the linear circuit.
   *  The nodes of MOSFETs and the preserved nodes are viewed as ports of the linear circuit.
  */
  int _num_ports;

  /** number of the nodes. */
  int _num_nodes;

  /** an orthogonal list which holds the stamped data of resistors. */
  orth_list _g_list;

  /** an orthogonal list which holds the stamped data of capacitors. */
  orth_list _c_list;

  /** a graph model representing the connection of resistors.
   *  The connected components are obtained by partition this graph.
  */
  Graph _graph;

  /** data which holding the partition results. */
  int* _partition_label;

  /** the maximum number of ports in a partition. */
  int _subblock_threshold;

  /** a utility variable to label the nodes during partition.*/
  int _block_id;

  /** an orthognal list holding the data of the resistance part of the reduced circuit.*/
  orth_list _red_g_list;

  /** an orthogonal list holding the data of the capacitance part of the reduced circuit. */
  orth_list _red_c_list;

  /** reserved lines of the netlist before the linear elements, including the comments. */
  std::list<std::string> _reserved_header;

  /** reserved lines of the netlist after all the elements, mainly including the analysis operations. */
  std::list<std::string> _reserved_tail;

  /** threshold for dumping a grounded resistor.*/
  double _geps;

  /** threshold for dumping a grounded capacitor. */
  double _ceps;

  /** subckt instance list */
  std::list<subckt_ins*> _subckt_ins_list;

  /** relative tolerance to control the partition size */
  double _relative_tol;

private:
  /** parse a line */
  void parse_line(std::string& line, std::string& oline);
  

private:
  /** subckt mode */
  bool _subckt_mode;

  /** special node mode */
  bool _special_node_mode;

  /** current subckt ptr */
  subckt* _current_sckt;

  /** subckt pointer stack */
  std::stack<subckt*> _subckt_stack;

  /** list of subckts */
  static std::list<subckt* > _subckt_list;

  /** current path */
  std::string _cwd;

  /** referenced subckts */
  map<string, int> _referenced_subckts;

public:
  
  /** parse the netlist */
  void parse(const char* filename);

  /** post parse */
  void post_parse();

  /** partition the nodes, by a hierarchical partition algorithm. */
  void partition();

  /** reduce the linear circuit according to the resulted partition by the partition algorithm.*/
  void reduction();

  /** dump the netlist from the reduced circuit. */
  void dump_netlist(const char* outfile);

  /** set the max block size */
  void set_max_blocksize(int size)
  {
    _subblock_threshold = size;
  }

  /** convert nodename to number */
  int nodename2num(std::string name)
  {
    return _nl.nodename2num(name);
  }

  /** dump a line */
  void dump_line(std::string& line, std::ofstream& outf);

  /** get subckt by name */
  static subckt* get_subckt_by_name(std::string& name);

  /** free subckt list */
  static void free_subckt_list();

  /** get element list */
  std::list<element*> & get_element_list()
  {
    return _element_list;
  }

  /** set current working directory */
  void set_cwd(std::string name)
  {
    _cwd = name;
  }

  /** add to tail */
  void add_tail(std::string line)
  {
    _reserved_tail.push_back(line);
  }


protected:
  /** expand pure parasitic subckts */
  int expand();

  /** get the number of subckt instances */
  int get_subckt_ins_num()
  {
    return  _subckt_ins_list.size();
  }

  
  /** a helper function for recursive partion the sub-blocks. */
  void subblock_partition(std::vector<int>& sub_block_ind);

  /** ascend sorting helper function.*/
  void asort(int* ind, double* sorted_values, int size, double* values);

  /** descend sorting helper function. */
  void dsort(int* ind, double* sorted_values, int size, double* values);

  /** calculate the difference of the values */
  void diff(int size, double* values);
  
  /** find the connected omponent after each partition */
  void check_conn(std::vector<int>& sub_block_ind, int* ind, int* final_ind, int k, int* conn_label, int& num_check);

};


/** @} */

/** @addtogroup utility
 *  @{
*/


/** a functor for ascent sorting. This functor is employed to sort a vector
 *  during partition.
 *
*/
class sort_less
{
public:
  bool operator()(const std::pair<int, double>& first, const std::pair<int, double>& second) const
  {
    if(first.second < second.second)
      return true;
    else
      return false;
  }
  
};


/** a functor for descend sorting. This functor is employed to sort a vector
 *  during the partion procedure.
 * 
*/
class sort_great
{
public:
  bool operator()(const std::pair<int, double>& first, const std::pair<int, double>& second) const
  {
    if(first.second > second.second)
      return true;
    else
      return false;
  }
};

/** @} */

#endif

