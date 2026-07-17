#ifndef UTIL_H_
#define UTIL_H_

/**
 * @file
 * Header file for unit parsing.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */



#include "amor_comm.h"

/** @group utility misc modules supporting the main programm. */

/** @addtogroup utility
 *  @{
*/

/** convert a value with unit into real value. for example, "1u" is converted to 1e-6.*/
double process_unit(const std::string &value, bool& status);

/** @} */

#endif
