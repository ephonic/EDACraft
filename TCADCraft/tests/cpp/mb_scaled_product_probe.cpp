#include "boltzmann_scaled_product.h"
#include <iostream>

int main() {
    try {
        size_t n=0,m=0;
        if(!(std::cin>>n>>m) || n>4096 || m>4096 || n*m>65536)
            throw std::invalid_argument("bounded vector counts required");
        std::vector<std::string> a(n),b(m);
        for(auto& x:a)if(!(std::cin>>x))throw std::invalid_argument("missing left input");
        for(auto& x:b)if(!(std::cin>>x))throw std::invalid_argument("missing right input");
        std::string extra;if(std::cin>>extra)throw std::invalid_argument("unexpected input token");
        for(const auto& x:tcad::native_mb_scaled_product_raw(a,b))std::cout<<x<<'\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
