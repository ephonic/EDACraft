#ifndef DSIM_VERI_TIME_HPP
#define DSIM_VERI_TIME_HPP
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <string>

namespace rtl {
struct VeriTimeScale {
  uint64_t unit_fs=1000000000000000ULL,precision_fs=1000000000000000ULL;
  bool directive=false;
};
struct VeriTimeLiteral {std::string number;int exponent;};
inline int veri_time_exponent(uint64_t value) {
  int result=0;
  while(value>1 && value%10==0){value/=10;++result;}
  if(value!=1)throw std::runtime_error("time scale must be a power of ten");
  return result;
}
inline VeriTimeLiteral veri_time_literal(const std::string& spelling) {
  size_t end=spelling.find_first_not_of("0123456789._");
  if(end==std::string::npos || end==0)throw std::runtime_error("time literal requires an explicit unit");
  const auto unit=spelling.substr(end);
  int exponent=unit=="fs"?0:unit=="ps"?3:unit=="ns"?6:unit=="us"?9:unit=="ms"?12:unit=="s"?15:-1;
  if(exponent<0)throw std::runtime_error("invalid time literal unit");
  auto number=spelling.substr(0,end);number.erase(std::remove(number.begin(),number.end(),'_'),number.end());
  return {number,exponent};
}
inline uint64_t veri_time_unit(const std::string& spelling) {
  auto literal=veri_time_literal(spelling);auto point=literal.number.find('.');
  int exponent=literal.exponent;
  if(point!=std::string::npos){exponent-=int(literal.number.size()-point-1);literal.number.erase(point,1);}
  auto first=literal.number.find_first_not_of('0');
  if(first==std::string::npos)throw std::runtime_error("time unit must be positive");
  literal.number.erase(0,first);
  while(literal.number.size()>1 && literal.number.back()=='0'){literal.number.pop_back();++exponent;}
  if(literal.number!="1" || exponent<0 || exponent>17)
    throw std::runtime_error("time unit must be a power of ten between 1fs and 100s");
  uint64_t result=1;while(exponent-->0)result*=10;return result;
}
inline double veri_time_value(const std::string& spelling,const VeriTimeScale& scope) {
  auto literal=veri_time_literal(spelling);
  // Parse the scaled decimal once. Literals remain realtime values; only a
  // delay or an integral conversion rounds them (IEEE 1800-2023, 5.8).
  const auto value=literal.number+"e"+std::to_string(literal.exponent-veri_time_exponent(scope.unit_fs));
  size_t end=0;double result=std::stod(value,&end);
  if(end!=value.size())throw std::runtime_error("invalid time literal");
  return result;
}
}
#endif
