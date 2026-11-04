#include "sdf.hpp"
#include <chrono>
#include <iostream>
int main(int argc,char** argv) {
    try {
        if(argc!=2)throw std::runtime_error("usage: sdf_check file.sdf");
        auto start=std::chrono::steady_clock::now();
        auto stats=dsim::read_sdf(argv[1]);std::cout<<stats.report();
        std::cerr<<"seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<'\n';
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
