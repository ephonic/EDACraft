#include "boltzmann_scaled_powerlaw.h"
#include <iostream>
int main() {
    try {
        std::vector<std::vector<std::string>> groups;
        for(size_t limit:{size_t(25000),size_t(18),size_t(1)}) {
            size_t n;if(!(std::cin>>n) || n>limit)throw std::invalid_argument("bounded root input count required");
            std::vector<std::string> v(n);
            for(auto& s:v)if(!(std::cin>>s) || s.size()>256)throw std::invalid_argument("missing or long root token");
            groups.push_back(v);
        }
        std::string extra;if(std::cin>>extra)throw std::invalid_argument("unexpected root input token");
        const auto wire=tcad::native_mb_scaled_powerlaw_raw(groups[0],groups[1],groups[2]);
        for(const auto& s:wire)std::cout<<s<<'\n';return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
