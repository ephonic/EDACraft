#include "time_engine/engine.hh"
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    te::TimingEngine timer;
    timer.read_liberty(argv[1]); timer.read_verilog(argv[2]); timer.read_sdc(argv[3]);
    timer.link_design(); timer.update_timing();
    std::cout << "setup_slack_ns=" << timer.worst_slack(te::MinMax::Max) << '\n';
}
