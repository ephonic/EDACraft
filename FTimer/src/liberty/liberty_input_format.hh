#pragma once
#include <algorithm>
#include <cctype>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace te::detail {
// A format rejection only. Production must never call the experimental parser.
inline void reject_experimental_db_input(const std::string& path) {
    auto ext=std::filesystem::path(path).extension().string();
    std::transform(ext.begin(),ext.end(),ext.begin(),[](unsigned char c){return char(std::tolower(c));});
    constexpr unsigned char magic[]={3,0x17,0x10,0x63,0,0x40,0xff,3};
    unsigned char header[sizeof(magic)]{};
    std::ifstream in(path,std::ios::binary);
    const bool db_header=in.read(reinterpret_cast<char*>(header),sizeof(header)) &&
                         std::memcmp(header,magic,sizeof(magic))==0;
    if(ext==".db" || db_header)
        throw std::runtime_error("Synopsys .db input is not integrated into the main loader; "
                                 "native parsing is experimental and restricted to standalone tests: "+path);
}
}
