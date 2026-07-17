#ifndef CAP_H_
#define CAP_H_

/**
 * @file
 * Header file for the capacitor class.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */


#include "amor_comm.h"
#include "amor_element.h"
#include "graph.h"
#include "amor_ckt.h"
#include "amor_subckt.h"


/**
 * @addtogroup parser
 * @{
 *
 */


/**
 * A class for holding the data of a capacitor.
 *
*/

class cap : public element
{

public:
  /** construct an resistor class by a capacitor card. */
  cap(std::string pos_port, std::string neg_port, double c): element(pos_port, neg_port, c)
  {
  }

  /** default deconstructor */
  virtual ~cap() {}

public:
  /** load the capacitor data into orthogonal lists and graphs for reduction. */
  virtual void load(orth_list& g, orth_list& c, graph_t& graph, ckt* pckt);
  
  /** load the capacitor data into orthogonal lists and graphs for reduction. */
  virtual void load(orth_list& g, orth_list& c, graph_t& graph, subckt* pckt);

  /** get type */
  virtual char get_type() {return 'c';}
  
};



/** @}*/

#endif
