#ifndef RES_H_
#define RES_H_

/**
 * @file
 * Header file for the resistor class.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */


#include "amor_comm.h"
#include "amor_element.h"
#include "amor_ckt.h"
#include "amor_subckt.h"



/**
 * @addtogroup parser
 * @{
*/


/**
 * A class for holding the data of a resistor.
 *
*/

class res : public element
{
public:
  /** construct an resistor class by a capacitor card. */
  res(std::string pos_port, std::string neg_port, double g): element(pos_port, neg_port, g)
  {
  }

  /** default deconstructor */
  virtual ~res() {}
  
public:
  /** load the resistor data into orthogonal lists and graphs for reduction. */
  virtual void load(orth_list& g, orth_list& c, graph_t& graph, ckt* pckt);

  /** load the resistor data into orthogonal lists and graphs for reduction. */
  virtual void load(orth_list& g, orth_list& c, graph_t& graph, subckt* pckt);

  /** return type */
  virtual char get_type() {return 'r';}
  
};

/** @} */

#endif
