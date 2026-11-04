#pragma once
#include "time.hpp"
#include <cstddef>
#include <functional>
#include <string>
#include <vector>
namespace dsim {
struct GateDesign;
// Static time-zero annotation requests discovered from the elaborated RTL AST.
// The driver validates dependencies/outputs and binds the separate gate IR.
struct SdfTask {
    std::string file,target,configuration,logfile,report;
    int corner=-1,line=0;
};
using SdfTaskHandler=std::function<void(std::vector<SdfTask>&)>;
// Behavioral RTL frontend only. Gate netlists use the separate Network parser.
std::string compile_rtl(const std::string& source,const std::string& top,const std::string& runtime,std::string* elaboration=nullptr,const GateDesign* gate=nullptr,const std::string& waveform={},const TimingConfig& timing={},const std::string& path_runtime={},const std::string& wide_runtime={},bool ieee_continuous_delays=false,bool time_wheel=false,size_t threads=0,const std::string& parallel_runtime={},bool systemverilog=true,const std::string& dpi_runtime={},const std::vector<std::string>& dpi_libraries={},std::string* dpi_header=nullptr,const std::string& constraint_runtime={},SdfTaskHandler sdf_tasks={},bool compact_memories=false,bool shared_functions=false);
}
