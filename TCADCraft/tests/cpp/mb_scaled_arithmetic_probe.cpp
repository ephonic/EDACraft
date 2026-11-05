#include "boltzmann_scaled_arithmetic.h"
#include <iostream>

int main() {
    try {
        std::string op;size_t n=0,m=0;
        if(!(std::cin>>op>>n>>m) || n>8195 || m>8195)
            throw std::invalid_argument("bounded arithmetic token counts required");
        std::vector<std::string> a(n),b(m);
        for(auto& x:a)if(!(std::cin>>x))throw std::invalid_argument("missing left token");
        for(auto& x:b)if(!(std::cin>>x))throw std::invalid_argument("missing right token");
        std::string extra;if(std::cin>>extra)throw std::invalid_argument("unexpected input token");
        for(const auto& x:tcad::native_mb_scaled_arithmetic_raw(op,a,b))std::cout<<x<<'\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
