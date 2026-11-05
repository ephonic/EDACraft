#include "boltzmann_scaled_component_division.h"
#include <iostream>

int main() {
    try {
        size_t n=0;
        if(!(std::cin>>n) || n>4096)throw std::invalid_argument("bounded atom count required");
        const auto read_wire=[](size_t maximum) {
            size_t size=0;
            if(!(std::cin>>size) || size>maximum)throw std::invalid_argument("bounded value token count required");
            std::vector<std::string> wire(size);
            for(auto& token:wire)if(!(std::cin>>token) || token.size()>64)
                throw std::invalid_argument("missing or long value token");
            return wire;
        };
        std::vector<std::vector<std::string>> atoms;
        for(size_t i=0;i<n;++i)atoms.push_back(read_wire(5));
        const auto divisor=read_wire(8195);
        std::string extra;
        if(std::cin>>extra)throw std::invalid_argument("unexpected input token");
        const auto out=tcad::native_mb_scaled_component_division_raw(atoms,divisor);
        for(const auto& token:out)std::cout<<token<<'\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}
}
