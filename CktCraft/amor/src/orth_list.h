#ifndef ORTH_LIST_H
#define ORTH_LIST_H


/**
 * @file
 * Header file for the orthogonal list.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */


#include <map>


/** @addtogroup matrix_computation
 *  @{
*/


/**
 * A class for orthogonal list.
 *
*/

class orth_list
{
public:
  /** default constructor */
  orth_list() {}
  
  /** default deconstructor */
  ~orth_list() {}

public:
  /** stamp the value into the orthogonal list. */
  void stamp(int i, int j, double val = 0)
  {
    if(i != 0 && j != 0)
      {
	_data[i-1][i-1] += val;
	_data[j-1][j-1] += val;
	_data[i-1][j-1] -= val;
	_data[j-1][i-1] -= val;
      }
    else if(i == 0 && j != 0)
      _diags[j-1] += val;
    else if(i !=0 && j == 0)
      _diags[i-1] += val;
	  
  }

  /** get the real data of the orthogonal list. */
  std::map<int, std::map<int, double> > & get_data()
  {
    return _data;
  }

  /** get the diagonal elements of the orthogonal list. */
  std::map<int, double>& get_diags()
  {
    return _diags;
  }
  
private:
  /** real data member of the orthogonal list. */
  std::map<int, std::map<int, double> > _data;

  /** the diagonal elements of the orthogonal list.*/
  std::map<int, double> _diags;
  
};


/** @}*/

#endif
