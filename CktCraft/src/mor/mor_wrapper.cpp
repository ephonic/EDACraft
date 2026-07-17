// mor_wrapper.cpp — MOR 集成 wrapper（调用 amor 做降阶）
#include "mor_wrapper.h"

#ifdef RFSIM_USE_MOR
#include "amor_amor.h"

bool rfsim::runMorReduction(const std::string& inputPath,
                            const std::string& reducedPath,
                            const MorOptions& opts) {
    ::amor am;
    am.set_maxblocksize(opts.maxBlockSize);
    int ret = am.run(inputPath.c_str(), reducedPath.c_str());
    return (ret == 0);
}
#else
// 无 MOR 编译：降阶不可用，返回 false（调用方用原网表）
bool rfsim::runMorReduction(const std::string&, const std::string&, const MorOptions&) {
    return false;
}
#endif
