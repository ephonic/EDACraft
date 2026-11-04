#pragma once
#include "timing_model.hpp"

namespace dsim {
struct PreparedSdfModels {
    std::string verilog,report;
};
// Explicitly replace placeholder specify blocks with a zero-initialized union
// of the SDF identities. This is a generated test model, not a vendor library.
// It does not annotate values, alter functional code or relax runtime matching.
using SdfConditionAliases=std::map<std::string,std::map<std::string,std::string>>;
SdfConditionAliases liberty_sdf_conditions(const std::vector<std::string>& files,const TimingLibrary&);
PreparedSdfModels prepare_sdf_models(const Preprocessed&,const std::string& sdf,const SdfConditionAliases& = {});
}
