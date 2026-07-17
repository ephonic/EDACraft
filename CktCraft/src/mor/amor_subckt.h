#ifndef SUBCKT_H_
#define SUBCKT_H_


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
#include "amor_ckt.h"
#include "amor_node_list.h"
#include "amor_orth_list.h"
#include "graph.h"
#include "amor_subckt_ins.h"
#include <utility>





/** @group reduction the main module of the programme.
 *  The module includes a subckt class holding the data of the circuit, and
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


class subckt : public ckt
{
public:
  /** default constructor, with input filename and outfilename as arguments. */
  subckt() : ckt(), _pure_para(true)
  { 
     _nl.nodename2num("0");
  }


private:
  /** subckt name  */
  std::string _subckt_name;

  /** port list */
  std::list<std::string> _port_list;

  /** prop vector */
  std::vector<std::string> _prop_vec;

  /** pure parasitic subckt flag */
  bool _pure_para;

public:
  
  /** parse the netlist */
  void parse_line(std::string& line);

  /** post parse after parsing all the lines */
  void post_parse();


  /** dump the netlist from the reduced circuit. */
  void dump_netlist(std::ofstream& outf);


  /** set the name of subckt */
  void set_subckt_name(std::string name)
  {
    _subckt_name = name;
  }

  /** add a port to the port list */
  void add_port(std::string port)
  {
    _port_list.push_back(port);
    _nl.nodename2num(port);
  }

  /** add property */
  void add_prop(std::string prop)
  {
    _prop_vec.push_back(prop);
  }

  /** get the number of nodes in this subckt */
  int get_num_nodes()
  {
    return _num_nodes;
  }

  bool is_pure_para()
  {
    return _pure_para;
  }

  void set_pure_para(bool status)
  {
    _pure_para = status;
  }

  int get_num_subckt_ins()
  {
    return _subckt_ins_list.size();
  }


  std::string get_name()
  {
    return _subckt_name;
  }

  int find_port(std::string name);

  void collect_referenced_subckts(std::map<std::string, int> &referenced_subckts);

};


/** @} */

#endif

