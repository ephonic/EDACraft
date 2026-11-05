#include "boltzmann_scaled_collision_compact.h"
#include <iostream>
int main() {
    try {
        std::vector<std::vector<std::string>> groups;
        for(size_t limit:{size_t(25000),size_t(6)}) {
            size_t n;
            if(!(std::cin>>n) || n>limit)throw std::invalid_argument("bounded trace input required");
            std::vector<std::string> raw(n);
            for(auto& s:raw)if(!(std::cin>>s) || s.size()>256)
                throw std::invalid_argument("missing or long trace token");
            groups.push_back(raw);
        }
        std::string extra;
        if(std::cin>>extra)throw std::invalid_argument("unexpected trace input token");
        const auto wire=tcad::native_mb_scaled_collision_compact_raw(groups[0],groups[1]);
        for(const auto& s:wire)std::cout<<s<<'\n';
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
