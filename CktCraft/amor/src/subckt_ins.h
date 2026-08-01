#ifndef SUBCKT_INS_H_
#define SUBCKT_INS_H_

#include <string>
#include <vector>

/**
 * @file
 * Header file for the capacitor class.
 * @author Yang Fan
 * @date July 17, 2010
 */


/**
 * @addtogroup parser
 * @{
 *
 */


/**
 * A class for holding the data of a subckt instance.
 *
*/

class subckt_ins
{
public:
  /** construct a subckt by a line */
  subckt_ins(std::string line) : _line(line)
  {
  }

  /** set instance name */
  void set_ins_name(std::string name)
  {
    _ins_name = name;
  }

  /** get instance name */
  std::string& get_ins_name()
  {
    return _ins_name;
  }

  /** set subckt name */
  void set_ref_name(std::string name)
  {
    _ref_name = name;
  }

  /** add a port to port vector */
  void add_port(std::string name)
  {
    _port_vec.push_back(name);
  }

  /** add property */
  void add_prop(std::string prop)
  {
    _prop_vec.push_back(prop);
  }

  /** get port name by index */
  std::string get_port(int index)
  {
    return _port_vec[index];
  }

  /** get subckt name */
  std::string& get_ref_name() {return _ref_name;}

  /** get the port vector */
  std::vector<std::string>& get_port_vec()
  {
    return _port_vec;
  }

  /** get line */
  std::string& get_line()
  {
    return _line;
  }

  /** get number of properties */
  int get_num_props()
  {
    return _prop_vec.size();
  }
  
private:
  /** line of subckt instance, for quick dump */
  std::string _line;
  
  /** instance name */
  std::string _ins_name;

  /** reference name */
  std::string _ref_name;

  /** port vector */
  std::vector<std::string> _port_vec;

  /** property vector */
  std::vector<std::string> _prop_vec;

  
};



/** @} */

#endif

