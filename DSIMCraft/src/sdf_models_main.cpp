#include "sdf_models.hpp"
#include <cerrno>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <fcntl.h>
#include <unistd.h>

namespace fs=std::filesystem;
// Reserve without clobbering any input or existing evidence, including aliases.
static void reserve(const std::string& path) {
    int fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0666);
    if(fd<0)throw std::runtime_error("cannot create "+path+": "+std::strerror(errno));
    ::close(fd);
}
static void write(const std::string& path,const std::string& data) {
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    out.write(data.data(),std::streamsize(data.size()));out.close();
    if(!out)throw std::runtime_error("cannot write "+path);
}
int main(int argc,char** argv) {
    std::vector<std::string> reserved;
    try {
        std::string sdf,output,report;std::vector<std::string> inputs,libraries;
        dsim::PreprocessOptions options;options.timing_model_source=true;
        for(int i=1;i<argc;++i) {
            std::string a=argv[i];
            if(a=="--help"||a=="-h") {
                std::cout<<"usage: dsim_sdf_models --sdf timing.sdf --models functional.v [--liberty cells.lib] [-I dir] [-D name=value] -o prepared.v --report coverage.json\n"
                         <<"Generate a test model by replacing placeholder specify blocks with zero-initialized SDF identities.\n"
                         <<"Functional code is preserved after lexical preprocessing. All SDF entries are parsed; INTERCONNECT needs no specify declaration.\n"
                         <<"Existing outputs are never overwritten. This does not produce a vendor signoff model or implement negative-check delayed signals/notifiers.\n";return 0;
            }
            if(a!="--sdf"&&a!="--models"&&a!="--liberty"&&a!="-o"&&a!="--report"&&a!="-I"&&a!="-D"&&a!="--timescale")throw std::runtime_error("unknown option "+a);
            if(++i==argc)throw std::runtime_error("missing value for "+a);
            std::string value=argv[i];
            if(a=="--models")inputs.push_back(value);
            else if(a=="--liberty")libraries.push_back(value);
            else if(a=="-I")options.include_dirs.push_back(value);
            else if(a=="-D")options.defines.push_back({value,false});
            else if(a=="--timescale")options.default_timescale=dsim::parse_timescale(value);
            else {
                auto& dest=a=="--sdf"?sdf:a=="-o"?output:report;
                if(!dest.empty())throw std::runtime_error("duplicate option "+a);dest=value;
            }
        }
        if(sdf.empty()||inputs.empty()||output.empty()||report.empty())throw std::runtime_error("--sdf, --models, -o and --report are required (see --help)");
        if(fs::weakly_canonical(output)==fs::weakly_canonical(report))throw std::runtime_error("model and report outputs must differ");
        // Check before parsing large inputs. O_EXCL below remains authoritative.
        for(const auto& path:{output,report})if(fs::exists(fs::symlink_status(path)))throw std::runtime_error("output already exists: "+path);
        auto source=dsim::preprocess(inputs,options);
        auto aliases=dsim::liberty_sdf_conditions(libraries,dsim::parse_timing_models(source));
        auto result=dsim::prepare_sdf_models(source,sdf,aliases);
        result.verilog="// SDF-derived zero-delay test model; functional source preserved after preprocessing.\n`timescale "+dsim::time_unit_name(options.default_timescale.unit_fs)+"/"+dsim::time_unit_name(options.default_timescale.precision_fs)+"\n"+result.verilog;
        reserve(output);reserved.push_back(output);reserve(report);reserved.push_back(report);
        write(output,result.verilog);write(report,result.report);
        // Independently re-read the emitted source through the production reader.
        auto check=dsim::read_timing_models({output},options);
        for(const auto& model:check.models)(void)model.executable_checks(1);
        std::cout<<"Prepared "<<check.models.size()<<" models: "<<output<<"; coverage: "<<report<<'\n';return 0;
    } catch(const std::exception& e) {
        for(const auto& p:reserved){std::error_code ec;fs::remove(p,ec);}
        std::cerr<<"dsim_sdf_models: "<<e.what()<<'\n';return 1;
    }
}
