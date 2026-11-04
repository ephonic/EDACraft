#include "timing_model.hpp"
#include "sdf_annotation.hpp"
#include <cassert>
#include <iostream>
#include <sstream>
using namespace dsim;
int main(int argc,char** argv) {
    assert(argc==2);std::string base=argv[1];auto library=read_timing_models({base+"/models.v"});
    assert(library.models.size()==2);const auto& c=library.model("C");const auto& f=library.model("F");
    assert(c.time.unit_fs==1000000&&c.time.precision_fs==10000&&f.time.unit_fs==10000&&f.time.precision_fs==1000);
    assert(c.paths.size()==4&&c.paths[0].full&&c.paths[0].inputs.size()==2&&c.paths[0].outputs.size()==2);
    assert(c.paths[1].condition=="B == 1'b0"&&c.paths[2].ifnone);
    assert(c.paths[3].edge=="posedge"&&c.paths[3].data=="B"&&c.paths[3].output_polarity=="+");
    assert(c.initial(c.paths[0],0)==std::vector<std::string>({"0.004","0.014"}));
    assert(c.initial(c.paths[0],1)==std::vector<std::string>({"0.005","0.014"}));
    assert(c.initial(c.paths[0],2)==std::vector<std::string>({"0.006","0.014"}));
    assert(c.checks.size()==4&&c.checks[2].arguments.size()==9&&c.checks[2].arguments.back().empty());
    assert(c.pulse_declarations.size()==2&&f.paths[0].data=="1'bx"&&f.checks.size()==2);
    assert(timing_expression_key("(B==1'b0)")==timing_expression_key(" B == 1'b0 "));
    assert(timing_expression_key("B==1'b0")!=timing_expression_key("B===1'b0"));
    assert(timing_expression_key("\\B ==1'b0")==timing_expression_key("B==1'b0"));
    auto design=parse_gate(base+"/net.v","dut",{base+"/cells.lib"},{false,true,true});
    SdfBindOptions options;options.corner=1;options.tick_fs=1000;
    auto annotation=annotate_sdf_paths(base+"/delay.sdf",design,library,options);
    assert(annotation.paths.size()==7&&annotation.path_updates==8);
    std::vector<std::pair<int,int>> expected={{60,50},{70,80},{90,90},{100,100},{110,120},{110,120},{20,20}};
    for(size_t i=0;i<expected.size();++i) {
        auto ticks=annotation.paths[i].delays.ticks(1000);
        assert(ticks[0]==uint64_t(expected[i].first)&&ticks[1]==uint64_t(expected[i].second));
    }
    assert(annotation.paths[0].input==0&&annotation.paths[1].input==1&&annotation.paths[1].output==1);
    options.corner=0;
    auto min_sdf=annotate_sdf_paths(base+"/delay.sdf",design,library,options);
    auto min_model=annotate_sdf_paths(base+"/delay.sdf",design,library,options,0);
    assert(min_sdf.paths.back().delays.ticks(1000)[0]==20);
    assert(min_model.paths.back().delays.ticks(1000)[0]==10);
    // Each invocation owns its staging; failure cannot mutate the model base.
    assert(c.initial(c.paths[0],1)[0]=="0.005");
    Preprocessed escaped;escaped.text="module E(\\A[0] ,Z); input \\A[0] ; output Z; specify (\\A[0] =>Z)=0; endspecify endmodule\n";
    auto names=parse_timing_models(escaped);
    assert(names.model("E").paths[0].inputs[0]=="A[0]");
    assert(names.model("E").ports.at("A[0]")=="input");
    Preprocessed definitions;
    definitions.text="module A(input I,output Z);assign Z=I;specify(I=>Z)=0;endspecify endmodule\n"
        "module B(input I, output Z); /* ignored */ assign Z = I; specify (I => Z) = 0; endspecify endmodule\n"
        "module C(input I,output Z);assign Z=~I;specify(I=>Z)=0;endspecify endmodule\n"
        "module D(input I,output Z);assign Z=I;specify(I=>Z)=2;endspecify endmodule\n"
        "module E(input I,output Z);assign Z=I;specify(posedge I=>(Z:I))=0;endspecify endmodule\n";
    auto identities=parse_timing_models(definitions);
    const auto& key=identities.model("A").definition_key;
    assert(!key.empty()&&key==identities.model("B").definition_key);
    for(auto name:{"C","D","E"})assert(key!=identities.model(name).definition_key);
    definitions.timing.defaults={10000,1000};
    auto scaled=parse_timing_models(definitions).model("A").definition_key;
    definitions.timing.defaults={100000,1000};
    assert(scaled!=parse_timing_models(definitions).model("A").definition_key);
    definitions.timing.defaults={10000,100};
    assert(scaled!=parse_timing_models(definitions).model("A").definition_key);
    std::cout<<"PASS model precision, corners/specparams, conditions, edges, checks, full-pair isolation and ordered SDF updates\n";
}
