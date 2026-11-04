#include "gate_source.hpp"
#include "gate_compiler.hpp"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace dsim;
namespace fs=std::filesystem;
static void put(const fs::path& p,const std::string& text){std::ofstream f(p);f<<text;assert(bool(f));}
int main(int argc,char** argv) {
    assert(argc==2);fs::path root=argv[1];fs::create_directories(root);
    auto file=root/"net.v",lib=root/"cells.lib";
    put(lib,"library(l){cell(B){pin(A){direction:input;}pin(Z){direction:output;function:\"A\";}}}");
    const std::string structural="module child(input a,output z); B u(.A(a),.Z(z)); endmodule\nmodule dut(input a,output z); child c(a,z); endmodule\n";
    put(file,"`timescale 1ns/10ps\n// module fake `UNKNOWN\n"+structural+"`timescale 1ps/1fs\nmodule unused; endmodule\n");
    auto fast=prepare_gate_source(file.string());assert(fast.fast_path&&fast.lines.empty()&&fast.modules.size()==3);
    assert(fast.time("child").precision_fs==10000&&fast.time("unused").precision_fs==1);
    auto a=parse_gate(file.string(),"dut",{lib.string()},{false,true,false});
    assert(a.structural_precision_fs==10000&&a.top_time.unit_fs==1000000);
    assert(a.timing_names->scopes.size()==2);
    for(const auto& scope:a.timing_names->scopes)assert(scope.time.precision_fs==10000);
    put(file,"`define UNUSED 1\n`timescale 1ns/10ps\n"+structural+"`timescale 1ps/1fs\nmodule unused; endmodule\n");
    auto slow=prepare_gate_source(file.string());assert(!slow.fast_path&&!slow.lines.empty());
    auto b=parse_gate(file.string(),"dut",{lib.string()},{false,true,false});
    assert(a.cpp(1000)==b.cpp(1000)&&a.pin_nets==b.pin_nets&&a.constants==b.constants);
    assert(a.top_time.precision_fs==b.top_time.precision_fs&&a.structural_precision_fs==b.structural_precision_fs);
    put(file,"/* module fake `BAD */\r\n`celldefine\r\n`timescale 10ps/1ps\r\nmodule \\d.u (input a,output z); wire \\module`text ; B u(.A(a),.Z(z)); endmodule\r\n`endcelldefine\r\n`resetall\r\nmodule other; endmodule\r\n");
    PreprocessOptions options;options.default_timescale={1000000,10000};
    auto escaped=prepare_gate_source(file.string(),options);
    assert(escaped.fast_path&&escaped.modules.size()==2&&escaped.modules[0].name=="d.u");
    assert(escaped.time("d.u").precision_fs==1000&&escaped.time("other").precision_fs==10000);
    assert(escaped.modules[0].line==4&&escaped.modules[1].line==7);
    // A comment forces the common directive implementation; timing remains
    // identical and body strings/escaped identifiers do not create directives.
    put(file,"`timescale 1ns /* scale */ / 10ps\n"+structural);
    auto commented=prepare_gate_source(file.string());assert(!commented.fast_path&&commented.time("dut").precision_fs==10000);
    std::cout<<"PASS structural source fast/fallback equivalence, ownership API, escaped names, CRLF, comments, hierarchy/scope time and unused-module precision\n";
}
