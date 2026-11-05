#include "boltzmann_endpoint_powerlaw.h"
#include <iostream>
int main(){try{std::vector<std::vector<std::string>> v(3);size_t n;std::string s;
for(auto& group:v){if(!(std::cin>>n)||n>60000)throw std::invalid_argument("probe input budget");
for(size_t i=0;i<n;++i){if(!(std::cin>>s)||s.size()>64)throw std::invalid_argument("probe token");group.push_back(s);}}
auto r=tcad::native_mb_endpoint_powerlaw_raw(v[0],v[1],v[2]);for(auto& x:r)std::cout<<x<<'\n';return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
