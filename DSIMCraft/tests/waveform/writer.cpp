#define DSIM_WAVE_ENABLED 1
#include "dsim/runtime.hpp"
#include "dsim/waveform.hpp"
int main(int argc,char** argv) {
    try {
        dsim::Sim sim;dsim::WaveCapture wave(sim,argc,argv);
        const int widths[]={1,7,8,9,31,32,63,64};
        for(auto width:widths)sim.signal(width,false);
        for(int i=0;i<8;++i)wave.declare(i,{"top"},"s"+std::to_string(i),widths[i]-1,0,false,widths[i]!=1);
        wave.declare(7,{"top","escaped.scope"},"alias[63:0]",63,0,true,true);
        wave.start();
        char kind;while(std::cin>>kind) {
            if(kind=='t') {uint64_t n;if(!(std::cin>>n)||n<sim.now)throw std::runtime_error("invalid test timestamp");sim.run();sim.now=n;sim.run();}
            else if(kind=='v') {int id;uint64_t a,b;if(!(std::cin>>id>>a>>b)||id<0||id>=8)throw std::runtime_error("invalid test value");sim.set(id,dsim::V(a,b,widths[id]));}
            else throw std::runtime_error("invalid test opcode");
        }
        sim.run();wave.close();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
