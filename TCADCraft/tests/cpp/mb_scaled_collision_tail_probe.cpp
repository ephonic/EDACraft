#include "boltzmann_scaled_collision_tail.h"
#include <iostream>

int main() {
    try {
        auto take=[](size_t maximum) {
            size_t n=0;
            if(!(std::cin>>n) || n>maximum)throw std::invalid_argument("bounded tail vector count required");
            std::vector<std::string> r(n);
            for(auto& x:r)if(!(std::cin>>x))throw std::invalid_argument("missing tail input token");
            return r;
        };
        const auto endpoint=take(25000),command=take(6),capacity=take(4096),trial=take(4096);
        std::string extra;if(std::cin>>extra)throw std::invalid_argument("unexpected tail input token");
        for(const auto& s:tcad::native_mb_scaled_collision_tail_raw(endpoint,command,capacity,trial))
            std::cout<<s<<'\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
