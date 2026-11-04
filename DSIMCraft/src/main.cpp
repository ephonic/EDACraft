#include "liberty/db_api.h"
#include "compiler.hpp"
#include "model_compiler_config.hpp"
#include "gate_compiler.hpp"
#include "gate_partition.hpp"
#include "preprocessor.hpp"
#include "gate_source.hpp"
#include "sdf.hpp"
#include "sdf_binding.hpp"
#include "sdf_annotation.hpp"
#include "timing_model.hpp"
#include "gate_timing.hpp"
#include <algorithm>
#include <cctype>
#include <cerrno>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <regex>
#include <spawn.h>
#include <stdexcept>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
extern char** environ;
namespace fs=std::filesystem;
static std::string read(const fs::path& p) {
    std::ifstream f(p,std::ios::binary); if(!f) throw std::runtime_error("cannot read "+p.string());
    return {std::istreambuf_iterator<char>(f),{}};
}
// Inspect only code tokens: comments and strings may legitimately contain these characters.
static std::string code_only(const std::string& text) {
    std::string code=text;
    for(size_t i=0;i<code.size();++i) {
        if(code[i]=='"') {
            code[i]=' ';
            while(++i<code.size()) {
                char c=code[i]; code[i]=' ';
                if(c=='\\' && i+1<code.size()) {code[++i]=' ';continue;}
                if(c=='"') break;
            }
        } else if(code[i]=='\\') {
            while(i<code.size()&&!std::isspace(static_cast<unsigned char>(code[i])))code[i++]=' ';
            if(i==code.size())break;
        } else if(code[i]=='/' && i+1<code.size() && code[i+1]=='/') {
            while(i<code.size() && code[i]!='\n') code[i++]=' ';
        } else if(code[i]=='/' && i+1<code.size() && code[i+1]=='*') {
            code[i++]=' '; code[i]=' ';
            while(++i<code.size()) {
                if(code[i]=='*' && i+1<code.size() && code[i+1]=='/') {code[i++]=' ';code[i]=' ';break;}
                if(code[i]!='\n') code[i]=' ';
            }
        }
    }
    return code;
}
int main(int argc,char** argv) {
    try {
        if(argc>=2 && std::string(argv[1])=="--liberty-db-info") {
            if(argc!=3) throw std::runtime_error("usage: dsim --liberty-db-info library.db");
            edacraft::core::native::DbDocument document;std::string error;
            if(!edacraft::core::native::read_synopsys_db(argv[2],document,&error))
                throw std::runtime_error(error);
            std::cout<<edacraft::core::native::db_document_json(document)<<'\n';
            return 0;
        }
        std::string top,out="simv",cxx=DSIM_DEFAULT_CXX,cpp,ir,gate_file,gate_top,preprocessed_file,deps_file,sdf_file,sdf_bind_file,sdf_annotate_file;
        dsim::SdfBindOptions sdf_binding;bool sdf_bind_options=false;
        dsim::PreprocessOptions preprocessing;
        bool preprocess_only=false,time_option=false,systemverilog=true;
        bool wave_support=false,timing_model_check=false,disable_checks=false;
        bool ieee_continuous_delays=false,continuous_delay_option=false;
        bool time_wheel=false;
        size_t partition_count=0;
        size_t threads=0;
        bool gate_batch=false,gate_scalar_timing=false,gate_sdf_jobs=false,gate_path_dictionary=false,gate_fold_zero_inputs=false;
        bool gate_auto_zero_inputs=true;
        bool gate_auto_scalar_timing=true;
        std::vector<std::string> gate_models;
        int model_corner=1;bool model_corner_option=false;
        std::vector<std::string> list_dependencies,original(argv+1,argv+argc);
        auto arguments=dsim::expand_filelists(original,list_dependencies);
        bool compact_memories=false,shared_functions=false;
        bool emit_only=false,gate_check=false; std::vector<std::string> files,libraries,cxx_flags,dpi_libraries; std::string dpi_header_file;
        for(size_t i=0;i<arguments.size();++i) {
            std::string a=arguments[i];
            if(a=="--help"||a=="-h") {
                std::string default_flags;
                for(const auto& flag:dsim::default_model_cxx_flags)default_flags+=" "+flag;
                std::cout<<"dsim 0.13.0 - compiled Verilog simulator\nusage: dsim [--top top] [-o simv] [--cxx c++] [--emit-cpp model.cpp] [--emit-only] [--emit-ir elaboration.json] sources.v...\n"
                         <<"  --liberty-db-info FILE: native Synopsys DB extraction/coverage JSON (no vendor tools)\n"
                         <<"  --compact-memories: experimental compact fixed variable arrays >=1024 elements; serial/no waveform; element access and memory files only\n"
                         <<"  --cxx PATH / --cxx-flag ARG: C++ compiler and repeatable literal arguments (no shell)\n"
                         <<"    default: "<<DSIM_DEFAULT_CXX<<" "<<DSIM_DEFAULT_OPTIMIZATION<<default_flags<<" (Intel uses strict floating point)\n"
                         <<"    example: --cxx icpx --cxx-flag -O3 --cxx-flag -xHost\n"
                         <<"  --dpi-lib FILE: repeatable native DPI-C shared library (runtime override also supported)\n"
                         <<"  --dpi-header FILE: emit C import/export prototypes; include/dsim/svdpi.h supplies ABI types\n"
                         <<"  --top NAME: select a root (default: infer unique root; prefer root named top)\n"
                         <<"  --language systemverilog|verilog: RTL keyword set (default systemverilog); -sverilog / --verilog\n"
                         <<"  -I dir / +incdir+dir, -D name[=value] / +define+name[=value], -U name\n"
                         <<"  -f list (cwd relative), -F list (list relative); -E (preprocess to stdout)\n"
                         <<"  +libext+EXT[+EXT...]: accept library suffix declarations with explicitly listed sources (-y lookup is not supported)\n"
                         <<"  --emit-preprocessed expanded.v --emit-deps dependencies.json\n"
                         <<"  --wave-support: enable native VCD/DWF runtime options (requires libzstd)\n"
                         <<"    runtime: --waveform PATH --wave-codec raw|zstd --wave-compression-jobs 1..16 (default 1)\n"
                         <<"    .vcd selects text VCD, .dwf selects DWF; --wave-format vcd|dwf overrides the suffix\n"
                         <<"    runtime: --wave-async --wave-buffer-bytes BYTES (one receiver/encoder/writer thread, DWF/Zstd)\n"
                         <<"    selection: --wave-scope HIER (repeatable) --wave-depth N (0: unlimited)\n"
                         <<"    signals: --wave-include GLOB --wave-exclude GLOB (repeatable; quote * and ?)\n"
                         <<"    interval: --wave-start TICKS --wave-end TICKS (inclusive, compiled precision)\n"
                         <<"  --timescale UNIT/PRECISION: default RTL timescale (default 1s/1s; directives override)\n"
                         <<"  --continuous-delay-mode vcs|ieee: continuous assignment delay selection (default vcs)\n"
                         <<"  --time-wheel: experimental stable near-time buckets and far-time heap (default off)\n"
                         <<"  --shared-functions: share function/automatic-task bodies and activation frames (serial RTL)\n"
                         <<"  --sdf-check timing.sdf [--emit-ir summary.json]: independent streaming SDF parser (check only)\n"
                         <<"  --sdf-bind-check timing.sdf --gate-netlist design.v --gate-top dut --liberty pins.lib --sdf-tick 1ps [--sdf-corner min|typ|max] [--sdf-unit 1ns] [--emit-ir binding.json]\n"
                         <<"  --timing-model-check models.v... [--emit-ir models.json]: extract specify metadata (no functional compilation)\n"
                         <<"  --gate-models models.v: specify metadata for SDF binding/annotation (CLI or static source task)\n"
                         <<"  --sdf-annotate timing.sdf: compiled IOPATH/INTERCONNECT delays and common nonnegative timing checks; unsupported entries fail\n"
                         <<"  $sdf_annotate(file, instance, config, log, mtm): static time-zero annotation of one explicit gate root\n"
                         <<"  --no-timingchecks: explicitly disable checks with CLI or source SDF annotation\n"
                         <<"  --gate-model-corner min|typ|max: initial specify corner, independent of --sdf-corner (default typ)\n"
                         <<"  --gate-netlist design.v --gate-top dut [--liberty cells.lib] testbench.v\n"
                         <<"  --gate-partition-report N: gate-only zero-delay domain/load analysis in --emit-ir (execution remains serial)\n"
                         <<"  --threads 1..128: experimental whole-program independent-domain parallel code generation\n"
                         <<"    runtime: --parallel-stats, --parallel-window TICKS; SDF gate scopes remain atomic, dump tasks not yet supported\n"
                         <<"  --gate-batch: experimental FIFO-preserving compiled combinational batches (single thread)\n"
                         <<"  --gate-scalar-timing / --no-gate-scalar-timing: scalar SDF delivery storage (automatic without waveform support)\n"
                         <<"  --gate-sdf-jobs: experimental dedicated IC/IOPATH jobs (requires --gate-scalar-timing)\n"
                         <<"  --gate-path-dictionary: experimental shared transition tables for SDF module paths (default off)\n"
                         <<"  --gate-fold-zero-inputs: force elimination of all-zero IC/PORT input channels (automatic without wave support)\n"
                         <<"  --no-gate-fold-zero-inputs: preserve all IC/PORT input channels\n"
                         <<"  --gate-check --gate-netlist design.v --gate-top dut [--liberty cells.lib] [--emit-ir network.json]\n"; return 0;
            }
            if(a=="--dpi-lib"||a=="--dpi-header") {
                if(++i==arguments.size()||arguments[i].empty())throw std::runtime_error(a+" requires a path");
                if(a=="--dpi-lib")dpi_libraries.push_back(arguments[i]);
                else {if(!dpi_header_file.empty())throw std::runtime_error("--dpi-header may only be specified once");dpi_header_file=arguments[i];}
                continue;
            }
            if(a=="--compact-memories") {compact_memories=true;continue;}
            if(a=="--shared-functions") {shared_functions=true;continue;}
            if(a=="--cxx-flag") {
                if(++i==arguments.size()||arguments[i].empty())throw std::runtime_error("--cxx-flag requires one nonempty compiler argument");
                cxx_flags.push_back(arguments[i]);continue;
            }
            if(a=="--language") {
                if(++i==arguments.size()||(arguments[i]!="verilog"&&arguments[i]!="systemverilog"))throw std::runtime_error("--language requires verilog or systemverilog");
                systemverilog=arguments[i]=="systemverilog";continue;
            }
            if(a=="-sverilog"||a=="--systemverilog"){systemverilog=true;continue;}
            if(a=="--verilog"){systemverilog=false;continue;}
            if(a=="--version") { std::cout<<"dsim 0.13.0\n"; return 0; }
            if(a=="--gate-batch") {gate_batch=true;continue;}
            if(a=="--gate-scalar-timing") {gate_scalar_timing=true;gate_auto_scalar_timing=false;continue;}
            if(a=="--no-gate-scalar-timing") {gate_scalar_timing=false;gate_auto_scalar_timing=false;continue;}
            if(a=="--gate-sdf-jobs") {gate_sdf_jobs=true;continue;}
            if(a=="--gate-path-dictionary") {gate_path_dictionary=true;continue;}
            if(a=="--gate-fold-zero-inputs") {gate_fold_zero_inputs=true;gate_auto_zero_inputs=false;continue;}
            if(a=="--no-gate-fold-zero-inputs") {gate_fold_zero_inputs=false;gate_auto_zero_inputs=false;continue;}
            if(a=="--time-wheel") {time_wheel=true;continue;}
            if(a=="--continuous-delay-mode") {
                if(++i==arguments.size()||continuous_delay_option)throw std::runtime_error("--continuous-delay-mode requires one vcs or ieee value");
                if(arguments[i]!="vcs"&&arguments[i]!="ieee")throw std::runtime_error("--continuous-delay-mode requires vcs or ieee");
                ieee_continuous_delays=arguments[i]=="ieee";continuous_delay_option=true;continue;
            }
            if(a=="--threads") {
                if(++i==arguments.size()||threads)throw std::runtime_error("--threads requires one positive worker count");
                const auto& value=arguments[i];
                if(value.empty()||value.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("thread count must be an integer in 1..128");
                auto count=std::stoull(value);if(!count||count>128)throw std::runtime_error("thread count must be in 1..128");
                threads=size_t(count);continue;
            }
            if(a=="--gate-partition-report") {
                if(++i==arguments.size()||partition_count)throw std::runtime_error("--gate-partition-report requires one positive count");
                const auto& value=arguments[i];
                if(value.empty()||value.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("partition count must be a positive integer");
                auto parsed=std::stoull(value);if(!parsed||parsed>65536)throw std::runtime_error("partition count must be in 1..65536");
                partition_count=size_t(parsed);continue;
            }
            if(a=="--no-timingchecks") {disable_checks=true;continue;}
            if(a=="--sdf-annotate") {
                if(++i==arguments.size()||!sdf_annotate_file.empty())throw std::runtime_error("--sdf-annotate requires one SDF file");
                sdf_annotate_file=arguments[i];continue;
            }
            if(a=="--wave-support") {wave_support=true;continue;}
            if(a=="--timing-model-check") {timing_model_check=true;continue;}
            if(a=="--gate-models") {
                if(++i==arguments.size())throw std::runtime_error("missing argument for --gate-models");
                gate_models.push_back(arguments[i]);continue;
            }
            if(a=="--gate-model-corner") {
                if(++i==arguments.size())throw std::runtime_error("missing argument for --gate-model-corner");
                auto v=arguments[i];if(v!="min"&&v!="typ"&&v!="max")throw std::runtime_error("model corner must be min, typ or max");
                model_corner=v=="min"?0:v=="typ"?1:2;model_corner_option=true;continue;
            }
            if(a=="-E"||a=="--preprocess") {preprocess_only=true;continue;}
            if(a=="-I"||a=="--include-dir"||a=="-D"||a=="-U"||a=="--emit-preprocessed"||a=="--emit-deps") {
                if(++i==arguments.size())throw std::runtime_error("missing argument for "+a);
                if(a=="-I"||a=="--include-dir")preprocessing.include_dirs.push_back(arguments[i]);
                else if(a=="-D"||a=="-U")preprocessing.defines.push_back({arguments[i],a=="-U"});
                else if(a=="--emit-deps")deps_file=arguments[i];else preprocessed_file=arguments[i];
                continue;
            }
            if(a.rfind("-I",0)==0&&a.size()>2) {preprocessing.include_dirs.push_back(a.substr(2));continue;}
            if((a.rfind("-D",0)==0||a.rfind("-U",0)==0)&&a.size()>2) {preprocessing.defines.push_back({a.substr(2),a[1]=='U'});continue;}
            if(a.rfind("+incdir+",0)==0||a.rfind("+define+",0)==0) {
                bool dirs=a.rfind("+incdir+",0)==0;size_t start=8;
                while(start<=a.size()) {auto end=a.find('+',start);auto part=a.substr(start,end-start);if(part.empty())throw std::runtime_error("empty "+a.substr(0,8)+" entry");if(dirs)preprocessing.include_dirs.push_back(part);else preprocessing.defines.push_back({part,false});if(end==std::string::npos)break;start=end+1;}
                continue;
            }
            // Suffix declarations have no effect when every source is listed.
            // Keep -y rejected until demand-driven library discovery exists.
            if(a.rfind("+libext+",0)==0) {
                size_t start=8;
                while(start<=a.size()) {
                    auto end=a.find('+',start);auto extension=a.substr(start,end-start);
                    if(extension.empty()||extension.find_first_of("/\\ \t\r\n")!=std::string::npos)
                        throw std::runtime_error("+libext+ requires nonempty file suffixes without path separators or whitespace");
                    if(end==std::string::npos)break;
                    start=end+1;
                }
                continue;
            }
            if(a=="--emit-only") {emit_only=true;continue;}
            if(a=="--gate-check") {gate_check=true;continue;}
            if(a=="--timescale") {
                if(++i==arguments.size())throw std::runtime_error("--timescale requires unit/precision");
                preprocessing.default_timescale=dsim::parse_timescale(arguments[i]);time_option=true;continue;
            }
            if(a=="--sdf-bind-check") {
                if(++i==arguments.size()||!sdf_bind_file.empty())throw std::runtime_error("--sdf-bind-check requires one SDF file");
                sdf_bind_file=arguments[i];continue;
            }
            if(a=="--sdf-corner"||a=="--sdf-tick"||a=="--sdf-unit") {
                if(++i==arguments.size())throw std::runtime_error("missing argument for "+a);
                sdf_bind_options=true;
                if(a=="--sdf-corner") {
                    auto v=arguments[i];if(v!="min"&&v!="typ"&&v!="max")throw std::runtime_error("SDF corner must be min, typ or max");
                    sdf_binding.corner=v=="min"?0:v=="typ"?1:2;
                } else if(a=="--sdf-tick")sdf_binding.tick_fs=dsim::parse_time_unit(arguments[i]);
                else sdf_binding.default_unit_fs=dsim::parse_time_unit(arguments[i]);
                continue;
            }
            if(a=="--sdf-check") {
                if(++i==arguments.size()||!sdf_file.empty())throw std::runtime_error("--sdf-check requires one SDF file");
                sdf_file=arguments[i];continue;
            }
            if(a=="--top"||a=="-top"||a=="-o"||a=="--cxx"||a=="--emit-cpp"||a=="--emit-ir"||a=="--gate-netlist"||a=="--gate-top"||a=="--liberty") {
                if(++i==arguments.size()) throw std::runtime_error("missing argument for "+a);
                if(a=="--top"||a=="-top") top=arguments[i]; else if(a=="-o") out=arguments[i]; else if(a=="--cxx") cxx=arguments[i]; else if(a=="--emit-ir") ir=arguments[i];
                else if(a=="--gate-netlist") { if(!gate_file.empty()) throw std::runtime_error("only one structural gate file is supported yet"); gate_file=arguments[i]; }
                else if(a=="--gate-top") gate_top=arguments[i]; else if(a=="--liberty") libraries.push_back(arguments[i]); else cpp=arguments[i];
            } else if(!a.empty() && (a[0]=='-'||a[0]=='+')) throw std::runtime_error("unknown option "+a);
            else files.push_back(a);
        }
        if((!dpi_libraries.empty()||!dpi_header_file.empty())&&(gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("DPI options require simulation code generation");
        if(time_wheel&&(gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--time-wheel requires simulation code generation");
        if(continuous_delay_option&&(gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--continuous-delay-mode requires simulation code generation");
        if(gate_batch&&(gate_file.empty()||gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--gate-batch requires gate simulation code generation");
        if(gate_scalar_timing&&((sdf_annotate_file.empty()&&gate_models.empty())||gate_file.empty()||gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--gate-scalar-timing requires SDF-annotated gate simulation code generation");
        if(gate_sdf_jobs&&!gate_scalar_timing)throw std::runtime_error("--gate-sdf-jobs requires --gate-scalar-timing and SDF-annotated gate simulation code generation");
        if(gate_path_dictionary&&((sdf_annotate_file.empty()&&gate_models.empty())||gate_file.empty()||gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--gate-path-dictionary requires SDF-annotated gate simulation code generation");
        if(gate_fold_zero_inputs&&((sdf_annotate_file.empty()&&gate_models.empty())||gate_file.empty()||gate_check||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--gate-fold-zero-inputs requires SDF-annotated gate simulation code generation");
        if(threads&&(preprocess_only||gate_check||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--threads requires simulation code generation");
        if(partition_count&&(gate_file.empty()||preprocess_only||timing_model_check||!sdf_bind_file.empty()||!sdf_file.empty()))throw std::runtime_error("--gate-partition-report requires functional gate binding/code generation");
        if(partition_count&&!gate_check&&ir.empty())throw std::runtime_error("--gate-partition-report requires --emit-ir or --gate-check");
        if(!sdf_file.empty()) {
            if(!sdf_annotate_file.empty()||disable_checks||model_corner_option||timing_model_check||!gate_models.empty()||!sdf_bind_file.empty()||sdf_bind_options||!files.empty()||!gate_file.empty()||!gate_top.empty()||!libraries.empty()||gate_check||wave_support||preprocess_only||emit_only||time_option||!cpp.empty()||!preprocessed_file.empty()||!deps_file.empty()||!preprocessing.defines.empty()||!preprocessing.include_dirs.empty()||out!="simv"||(cxx!=DSIM_DEFAULT_CXX||!cxx_flags.empty())||!top.empty())
                throw std::runtime_error("--sdf-check is independent: use only an SDF file and optional --emit-ir");
            if(!ir.empty()) {
                auto output=fs::weakly_canonical(fs::absolute(ir));
                std::vector<std::string> protected_inputs=list_dependencies;protected_inputs.push_back(sdf_file);
                for(const auto& input:protected_inputs)if(output==fs::weakly_canonical(fs::absolute(input))||(fs::exists(ir)&&fs::exists(input)&&fs::equivalent(ir,input)))
                    throw std::runtime_error("SDF summary would overwrite an input: "+input);
            }
            auto report=dsim::read_sdf(sdf_file).report();
            if(!ir.empty()){std::ofstream f(ir,std::ios::binary);if(!f)throw std::runtime_error("cannot write "+ir);f<<report;f.close();if(!f)throw std::runtime_error("failed writing "+ir);}
            std::cout<<report;return 0;
        }
        if(sdf_bind_file.empty()&&sdf_annotate_file.empty()&&gate_models.empty()&&sdf_bind_options)throw std::runtime_error("SDF binding options require --sdf-bind-check or --sdf-annotate");
        if(disable_checks&&sdf_annotate_file.empty()&&gate_models.empty())throw std::runtime_error("--no-timingchecks requires --sdf-annotate");
        if(!sdf_annotate_file.empty()) {
            if(gate_file.empty()||gate_models.empty()||libraries.empty())throw std::runtime_error("--sdf-annotate requires --gate-netlist, --gate-models and --liberty");
            if(!sdf_bind_file.empty()||timing_model_check||gate_check||preprocess_only)throw std::runtime_error("--sdf-annotate requires simulation code generation");
            if(sdf_binding.tick_fs)throw std::runtime_error("--sdf-annotate derives global precision from RTL and models; omit --sdf-tick");
        }
        if(timing_model_check&&(!gate_models.empty()||!sdf_bind_file.empty()||!gate_file.empty()||!gate_top.empty()||!libraries.empty()||gate_check||wave_support||preprocess_only||emit_only||!cpp.empty()||out!="simv"||(cxx!=DSIM_DEFAULT_CXX||!cxx_flags.empty())||!top.empty()))throw std::runtime_error("--timing-model-check accepts model files, preprocessing/time options and optional reports only");
        if(!gate_models.empty()&&sdf_bind_file.empty()&&sdf_annotate_file.empty()&&(gate_file.empty()||gate_check||preprocess_only))throw std::runtime_error("--gate-models requires --sdf-bind-check, --sdf-annotate or a static $sdf_annotate gate simulation");
        if(model_corner_option&&gate_models.empty())throw std::runtime_error("--gate-model-corner requires --gate-models");
        if(!sdf_bind_file.empty()) {
            if(gate_file.empty())throw std::runtime_error("--sdf-bind-check requires --gate-netlist");
            if(!files.empty()||gate_check||wave_support||preprocess_only||emit_only||!cpp.empty()||!preprocessed_file.empty()||out!="simv"||(cxx!=DSIM_DEFAULT_CXX||!cxx_flags.empty())||!top.empty())throw std::runtime_error("--sdf-bind-check accepts gate preprocessing, topology and binding options only; omit RTL/code-generation options");
            if(!sdf_binding.tick_fs)throw std::runtime_error("--sdf-bind-check requires explicit --sdf-tick target precision");
        }
        if(gate_file.empty() && (gate_check||!gate_top.empty()||!libraries.empty())) throw std::runtime_error("gate options require --gate-netlist");
        if(!gate_file.empty() && gate_top.empty()) throw std::runtime_error("--gate-netlist requires --gate-top");
        if(files.empty() && !gate_check && sdf_bind_file.empty()) throw std::runtime_error("no Verilog inputs (use --help)");
        if(gate_check && (!files.empty()||emit_only||!cpp.empty())) throw std::runtime_error("--gate-check only parses and binds the gate design; omit RTL sources and C++ options");
        if(preprocess_only&&(!gate_file.empty()||gate_check||emit_only))throw std::runtime_error("-E preprocesses RTL sources only; omit gate/emit-only options");
        if(wave_support&&(gate_check||preprocess_only))throw std::runtime_error("--wave-support requires simulation code generation");
#ifndef DSIM_ZSTD_LIBRARY
        if(wave_support)throw std::runtime_error("--wave-support unavailable: rebuild dsim with libzstd headers/library");
#endif
        if(cpp.empty()) cpp=out+".dsim.cpp";
        auto absolute=[](const fs::path& p){return fs::weakly_canonical(fs::absolute(p));};
        if(absolute(cpp)==absolute(out)) throw std::runtime_error("C++ output and executable paths must differ");
        if(!ir.empty() && (absolute(ir)==absolute(cpp)||absolute(ir)==absolute(out)))
            throw std::runtime_error("IR, C++ and executable output paths must differ");
        auto same_path=[&](const fs::path& a,const fs::path& b) {return absolute(a)==absolute(b)||(fs::exists(a)&&fs::exists(b)&&fs::equivalent(a,b));};
        for(const auto& f:files)if(!gate_file.empty()&&same_path(f,gate_file))throw std::runtime_error("gate netlist must not also be passed as an RTL source");
        preprocessing.timing_model_source=timing_model_check;
        auto processed=dsim::preprocess(files,preprocessing);
        std::shared_ptr<dsim::GateSource> gate_source;
        if(!gate_file.empty())gate_source=std::make_shared<dsim::GateSource>(dsim::prepare_gate_source(gate_file,preprocessing));
        dsim::TimingLibrary timing_library;
        if(!gate_models.empty())timing_library=dsim::read_timing_models(gate_models,preprocessing);
        for(const auto& f:processed.dependencies)if(!gate_file.empty()&&absolute(f)==absolute(gate_file))throw std::runtime_error("gate netlist must not also be passed as an RTL source");
        for(auto& library:dpi_libraries) {
            library=absolute(library).string();
            if(!fs::is_regular_file(library))throw std::runtime_error("DPI library is not a regular file: "+library);
        }
        auto inputs=processed.dependencies;
        inputs.insert(inputs.end(),dpi_libraries.begin(),dpi_libraries.end());
        inputs.insert(inputs.end(),list_dependencies.begin(),list_dependencies.end());
        if(gate_source)inputs.insert(inputs.end(),gate_source->dependencies.begin(),gate_source->dependencies.end());
        inputs.insert(inputs.end(),libraries.begin(),libraries.end());
        if(!sdf_bind_file.empty())inputs.push_back(sdf_bind_file);
        if(!sdf_annotate_file.empty())inputs.push_back(sdf_annotate_file);
        inputs.insert(inputs.end(),timing_library.dependencies.begin(),timing_library.dependencies.end());
        processed.dependencies=inputs;
        std::vector<std::string> outputs={cpp,out};
        if(!ir.empty())outputs.push_back(ir);
        if(!dpi_header_file.empty())outputs.push_back(dpi_header_file);
        if(!preprocessed_file.empty())outputs.push_back(preprocessed_file);
        if(!deps_file.empty())outputs.push_back(deps_file);
        for(size_t i=0;i<outputs.size();++i) {
            for(size_t j=0;j<i;++j)if(same_path(outputs[i],outputs[j]))throw std::runtime_error("output paths must differ");
            for(const auto& f:inputs)if(same_path(f,outputs[i]))throw std::runtime_error("output would overwrite an input: "+f);
        }
        auto write=[](const std::string& path,const std::string& text) {
            std::ofstream f(path,std::ios::binary);if(!f)throw std::runtime_error("cannot write "+path);f<<text;f.close();if(!f)throw std::runtime_error("failed writing "+path);
        };
        auto source=processed.text;
        auto write_auxiliary=[&]() {
            if(!preprocessed_file.empty())write(preprocessed_file,processed.text);
            if(!deps_file.empty()) {
                auto report=processed.report();
                if(gate_source)report.insert(report.rfind('}'),",\"gate_preprocessing\":"+gate_source->report()+"\n");
                write(deps_file,report);
            }
        };
        if(preprocess_only||timing_model_check||gate_check||!sdf_bind_file.empty())write_auxiliary();
        if(preprocess_only){std::cout<<source;return 0;}
        if(timing_model_check) {
            auto report=dsim::parse_timing_models(processed).report();
            if(!ir.empty())write(ir,report);
            std::cout<<report;return 0;
        }
        for(auto range:processed.compiler_directives)for(size_t i=range.first;i<range.second;++i)if(source[i]!='\n')source[i]=' ';
        auto code=code_only(source);
        // Token boundaries include '$': a signal named x$dumpvars or text in
        // comments/strings/escaped identifiers must not enable instrumentation.
        if(std::regex_search(code,std::regex("(^|[^a-zA-Z0-9_$])\\$(dumpfile|dumpvars|dumpoff|dumpon|dumpall)([^a-zA-Z0-9_$]|$)"))) {
            wave_support=true;
#ifndef DSIM_ZSTD_LIBRARY
            throw std::runtime_error("dump tasks require libzstd: rebuild dsim with libzstd headers/library");
#endif
        }
        std::smatch match;
        auto reject=[&](const std::string& message) {
            size_t line=1+size_t(std::count(source.begin(),source.begin()+match.position(),'\n'));
            auto at=processed.lines.at(line-1);throw std::runtime_error(at.file+":"+std::to_string(at.line)+": "+message);
        };
        if(std::regex_search(code,match,std::regex("\\bspecify\\b")))reject("specify timing is not supported yet");
        dsim::GateDesign gate;
        if(!gate_file.empty()) gate=dsim::parse_gate(gate_file,gate_top,libraries,dsim::GateOptions{wave_support,!sdf_bind_file.empty()||!sdf_annotate_file.empty()||!gate_models.empty(),!sdf_bind_file.empty(),gate_source});
        gate.batch_enabled=gate_batch;
        gate.parallel_enabled=threads!=0;
        gate.scalar_timing_enabled=gate_scalar_timing ||
            (gate_auto_scalar_timing&&!wave_support&&(!sdf_annotate_file.empty()||!gate_models.empty()));
        gate.sdf_jobs_enabled=gate_sdf_jobs;
        gate.path_dictionary_enabled=gate_path_dictionary;
        // Pin channels have observable initialization deltas in ordered waves.
        // Keep them when instrumentation is compiled, unless explicitly forced.
        gate.fold_zero_inputs=gate_fold_zero_inputs ||
            (gate_auto_zero_inputs&&!wave_support&&(!sdf_annotate_file.empty()||!gate_models.empty()));
        if(!sdf_bind_file.empty()) {
            auto report=gate_models.empty()?dsim::bind_sdf_file(sdf_bind_file,gate,sdf_binding).report():
                dsim::annotate_sdf_paths(sdf_bind_file,gate,timing_library,sdf_binding,model_corner).report(timing_library,sdf_binding.tick_fs);
            if(!ir.empty())write(ir,report);
            std::cout<<report;return 0;
        }
        if(!sdf_annotate_file.empty()) {
            auto annotation=dsim::annotate_sdf_paths(sdf_annotate_file,gate,timing_library,sdf_binding,model_corner,true,!disable_checks);
            if(annotation.negative_check_limits_clamped)std::cerr<<"SDF: "<<annotation.negative_check_limits_clamped<<" negative timing-check limit updates clamped to zero (nonnegative check mode; delayed reference/data mode is not implemented)\n";
            gate.timing=dsim::build_gate_timing(gate,timing_library,annotation,disable_checks);
        }
        if(partition_count)gate.partitioning_report=dsim::gate_partition_report(gate,partition_count);
        if(gate_check) {
            auto report=gate.report();
            if(!ir.empty()) {
                std::ofstream f(ir); if(!f) throw std::runtime_error("cannot write "+ir);
                f<<report<<'\n'; f.close(); if(!f) throw std::runtime_error("failed writing "+ir);
            }
            std::cout<<report<<'\n'; return 0;
        }
        dsim::SdfTaskHandler sdf_task_handler=[&](std::vector<dsim::SdfTask>& tasks) {
            if(tasks.empty())return;
            auto error=[&](const std::string& message) {throw std::runtime_error("line "+std::to_string(tasks.front().line)+": "+message);};
            if(tasks.size()!=1)error("multiple $sdf_annotate calls/reannotation are not implemented");
            if(!sdf_annotate_file.empty())error("do not combine --sdf-annotate with a source $sdf_annotate task");
            if(gate_file.empty()||gate_models.empty()||libraries.empty())error("$sdf_annotate requires --gate-netlist, --gate-top, --gate-models and --liberty");
            if(sdf_binding.tick_fs)error("$sdf_annotate derives global precision from RTL and models; omit --sdf-tick");
            auto& task=tasks.front();
            const auto task_file=absolute(task.file).string();
            for(const auto& output:outputs)if(same_path(task_file,output))error("output would overwrite SDF task input: "+task_file);
            if(std::find(inputs.begin(),inputs.end(),task_file)==inputs.end())inputs.push_back(task_file);
            processed.dependencies=inputs;
            if(!task.configuration.empty()) {
                // VCS W-2024.09 accepts a nonexistent third (configuration)
                // argument. Never ignore an actual configuration file.
                if(fs::exists(task.configuration))error("$sdf_annotate configuration files are not implemented: "+task.configuration);
                std::cerr<<"SDF: missing configuration file "<<task.configuration<<"; using default annotation (VCS-compatible missing-config behavior)\n";
            }
            if(!task.logfile.empty()) {
                task.logfile=absolute(task.logfile).string();
                for(const auto& input:inputs)if(same_path(task.logfile,input))error("SDF annotation log would overwrite an input: "+input);
                for(const auto& output:outputs)if(same_path(task.logfile,output))error("SDF annotation log conflicts with a compiler output: "+output);
            }
            auto binding=sdf_binding;
            if(task.corner>=0)binding.corner=task.corner;
            auto annotation=dsim::annotate_sdf_paths(task_file,gate,timing_library,binding,
                model_corner_option?model_corner:binding.corner,true,!disable_checks);
            if(annotation.negative_check_limits_clamped)std::cerr<<"SDF: "<<annotation.negative_check_limits_clamped<<" negative timing-check limit updates clamped to zero (nonnegative check mode; delayed reference/data mode is not implemented)\n";
            auto timing=dsim::build_gate_timing(gate,timing_library,annotation,disable_checks);
            task.report=annotation.report(timing_library,timing->precision_fs);
            gate.timing=std::move(timing);
        };
        std::string elaboration;
        std::string generated,dpi_header;
        try {auto wave=wave_support?read(DSIM_WAVEFORM_PATH):std::string();if(wave.rfind("#pragma once\n",0)==0)wave.erase(0,13);
            auto paths=(gate.timing||!gate_models.empty())?read(DSIM_PATH_PATH):std::string();if(paths.rfind("#pragma once\n",0)==0)paths.erase(0,13);
            if(gate.path_dictionary_enabled) {auto dictionary=read(DSIM_PATH_DICTIONARY_PATH);if(dictionary.rfind("#pragma once\n",0)==0)dictionary.erase(0,13);paths+="\n"+dictionary;}
            std::string parallel;
            if(threads) {
                auto header=[](const std::string& path,std::initializer_list<const char*> includes) {
                    auto text=read(path);if(text.rfind("#pragma once\n",0)==0)text.erase(0,13);
                    for(auto name:includes) {
                        std::string line=std::string("#include \"")+name+"\"\n";auto pos=text.find(line);
                        if(pos==std::string::npos)throw std::runtime_error("missing parallel runtime include marker");
                        text.erase(pos,line.size());
                    }
                    return text;
                };
                parallel=header(DSIM_PARTITION_PATH,{})+"\n"+header(DSIM_PARALLEL_PATH,{"runtime.hpp","partition.hpp"});
                if(wave_support)parallel+="\n"+header(DSIM_PARALLEL_WAVE_PATH,{"parallel.hpp","waveform.hpp"});
            }
            auto dpi=read(DSIM_DPI_PATH);if(dpi.rfind("#pragma once\n",0)==0)dpi.erase(0,13);
            auto dpi_include=dpi.find("#include \"svdpi.h\"\n");
            if(dpi_include==std::string::npos)throw std::runtime_error("missing DPI runtime include marker");
            auto dpi_types=read(fs::path(DSIM_DPI_PATH).parent_path()/"svdpi.h");
            if(dpi_types.rfind("#pragma once\n",0)==0)dpi_types.erase(0,13);
            dpi.replace(dpi_include,std::string("#include \"svdpi.h\"\n").size(),dpi_types+"\n");
            generated=dsim::compile_rtl(source,top,read(DSIM_RUNTIME_PATH),ir.empty()?nullptr:&elaboration,gate_file.empty()?nullptr:&gate,wave,processed.timing,paths,read(DSIM_WIDE_PATH),ieee_continuous_delays,time_wheel,threads,parallel,systemverilog,dpi,dpi_libraries,&dpi_header,read(DSIM_CONSTRAINT_PATH),sdf_task_handler,compact_memories,shared_functions); }
        catch(const std::exception& e) {
            std::string message=e.what();std::smatch where;
            // Parser diagnostics may contain many independent source positions,
            // including the previous declaration in a duplicate-definition error.
            const auto stub=gate_file.empty()?std::string():gate.stub();
            const size_t prefix=std::count(stub.begin(),stub.end(),'\n');
            const std::regex position("\\[([0-9]+) : ([0-9]+)\\]");
            std::string mapped;size_t offset=0;
            for(std::sregex_iterator it(message.begin(),message.end(),position),end;it!=end;++it) {
                const auto& at=*it;size_t n=std::stoul(at[1]);
                mapped.append(message,offset,size_t(at.position())-offset);
                if(n>prefix&&n-prefix<=processed.lines.size()) {
                    const auto& location=processed.lines[n-prefix-1];
                    mapped+='['+location.file+':'+std::to_string(location.line)+':'+at[2].str()+']';
                } else mapped+=at.str();
                offset=size_t(at.position()+at.length());
            }
            mapped.append(message,offset,std::string::npos);message=std::move(mapped);
            if(std::regex_search(message,where,std::regex("line ([0-9]+)"))) {
                size_t n=std::stoul(where[1]);
                if(n>prefix&&n-prefix<=processed.lines.size()) {auto at=processed.lines[n-prefix-1];throw std::runtime_error(at.file+":"+std::to_string(at.line)+": "+message);}
            }
            throw std::runtime_error(message);
        }
        if(!gate_models.empty()&&sdf_annotate_file.empty()&&!gate.timing)
            throw std::runtime_error("--gate-models requires --sdf-annotate or an executable static $sdf_annotate task");
        write_auxiliary();
        if(!dpi_header_file.empty())write(dpi_header_file,dpi_header);
        if(!ir.empty()) {
            std::ofstream report(ir,std::ios::binary); if(!report) throw std::runtime_error("cannot write "+ir);
            report<<elaboration; report.close(); if(!report) throw std::runtime_error("failed writing "+ir);
        }
        std::ofstream output(cpp,std::ios::binary); if(!output) throw std::runtime_error("cannot write "+cpp);
        output<<generated; output.close(); if(!output) throw std::runtime_error("failed writing "+cpp);
        if(emit_only) { std::cout<<"generated "<<cpp<<'\n'; return 0; }
        // No shell: paths and compiler arguments retain their exact bytes.
        std::string temporary=out+".tmp.XXXXXX"; std::vector<char> temp(temporary.begin(),temporary.end()); temp.push_back(0);
        int fd=mkstemp(temp.data()); if(fd<0) throw std::runtime_error("cannot create compiler output: "+std::string(std::strerror(errno))); close(fd);
        temporary=temp.data();
        std::vector<std::string> args={cxx,"-std=c++17",DSIM_DEFAULT_OPTIMIZATION}; std::vector<char*> av;
        // Intel enables relaxed floating-point transformations by default.
        // Keep standard simulation semantics; explicit user flags follow.
        const auto compiler_name=fs::path(cxx).filename().string();
        if(compiler_name=="icpx"||compiler_name=="icpc")args.push_back("-fp-model=strict");
        if(cxx==DSIM_DEFAULT_CXX)args.insert(args.end(),dsim::default_model_cxx_flags.begin(),dsim::default_model_cxx_flags.end());
        args.insert(args.end(),cxx_flags.begin(),cxx_flags.end());
        args.insert(args.end(),{cpp,"-o",temporary});
        if(threads&&!wave_support)args.push_back("-pthread");
        if(generated.find("#define DSIM_DPI_ENABLED 1\n")!=std::string::npos) {
#ifdef __APPLE__
            args.push_back("-Wl,-export_dynamic");
#else
            args.push_back("-Wl,--export-dynamic");
            args.push_back("-ldl");
#endif
        }
        if(generated.find("#define DSIM_CONSTRAINT_ENABLED 1\n")!=std::string::npos) {
#ifdef DSIM_Z3_LIBRARY
            args.push_back(std::string("-I")+DSIM_Z3_INCLUDE);args.push_back(DSIM_Z3_LIBRARY);
#else
            throw std::runtime_error("constraint randomization requires Z3; rebuild dsim with DSIM_Z3_INCLUDE and DSIM_Z3_LIBRARY");
#endif
        }
#ifdef DSIM_ZSTD_LIBRARY
        if(wave_support) {args.push_back(std::string("-I")+DSIM_ZSTD_INCLUDE);args.push_back(DSIM_ZSTD_LIBRARY);args.push_back("-pthread");}
#endif
        for(auto& arg:args) av.push_back(arg.data());
        av.push_back(nullptr);
        pid_t pid; int err=posix_spawnp(&pid,cxx.c_str(),nullptr,nullptr,av.data(),environ);
        if(err) {fs::remove(temporary);throw std::runtime_error("cannot start C++ compiler: "+std::string(std::strerror(err)));}
        int status=0; pid_t waited;
        do {waited=waitpid(pid,&status,0);} while(waited<0 && errno==EINTR);
        if(waited<0 || !WIFEXITED(status)||WEXITSTATUS(status)!=0) {fs::remove(temporary);throw std::runtime_error("C++ compilation failed; generated source: "+cpp);}
        fs::rename(temporary,out); std::cout<<"compiled "<<top<<" -> "<<out<<" (C++: "<<cpp<<")\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<"dsim: "<<e.what()<<'\n'; return 1;}
}
