#ifndef ELEMENT_H_
#define ELEMENT_H_


/**
 * @file
 * Header file for the element class.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */



#include <string>
#include <vector>
#include "amor_node_list.h"
#include "amor_orth_list.h"
#include "graph.h"


class ckt;
class subckt;

/**
 * @group parser module for netlist parsing. This module includes a base class element and two inherit classes
 * res and cap for resistors and capacitors, respectively. We use the module to assist the parsing of
 * the circuit, i.e., holding the data of the elements and loading the data into matrix for further
 * partition, reduction and netlist dumping.
 */



/**
 * @addtogroup parser
 * @{
*/


/**
 * Base class for capacitor/resistor.
 *
*/

class element
{

public:
  /** default constructor. */
  element(std::string pos_port, std::string neg_port, double value)
    : _pos_port(pos_port),
      _neg_port(neg_port),
      _value(value)
  {
  }
  
  /** default deconstructor. */
  virtual ~element();


public:
  /** load interface for capacitor/resistor. */
  virtual void load(orth_list& g, orth_list& c, graph_t& graph, ckt* pckt) = 0;

  /** load interface for capacitor/resistor. */
  virtual void load(orth_list& g, orth_list& c, graph_t& graph, subckt* pckt) = 0;

  /** return the positive port */
  std::string get_pos_port() {return _pos_port;}

  /** return the negative port. */
  std::string get_neg_port() {return _neg_port;}

  /** get the value */
  double get_value() {return _value;}

  /** set the positive port */
  void set_pos_port(std::string name) {_pos_port = name; }

  /** set the negative port */
  void set_neg_port(std::string name) {_neg_port = name; }

  /** get type */
  virtual char get_type() = 0;
   
protected:
  /** positive port */
  std::string _pos_port;

  /** negative port */
  std::string _neg_port;

  /** cap/res value */
  double _value;
  

};

/**
 * @}
 */


#endif
