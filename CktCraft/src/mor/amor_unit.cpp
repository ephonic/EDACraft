#include "amor_unit.h"

using namespace std;

double process_unit(const string& value, bool& status)
{
  status = true;
  char scale = 'A';
  double scaled_value;
  istringstream iss(value);

  if(! (iss >> scaled_value))
    {
      status = false;
      return 0.0;
    }

  iss >> scale;

  
  switch(scale)
    {
    case 'f':
      scaled_value *= 1e-15;
      break;
      
    case 'p':
      scaled_value *= 1e-12;
      break;
    case 'n':
      scaled_value *= 1e-9;
      break;
    case 'u':
      scaled_value *= 1e-6;
      break;
    case 'm':
      scaled_value *= 1e-3;
      break;
    case 'k':
      scaled_value *= 1e3;
      break;
    case 'x':
      scaled_value *= 1e6;
      break;
    case 'g':
      scaled_value *= 1e9;
      break;
    default:
      scaled_value *= 1;
      break;
      
    }
  return scaled_value;
}
