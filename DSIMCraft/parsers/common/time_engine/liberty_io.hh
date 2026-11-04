#pragma once

#include <iosfwd>
#include <string>

namespace edacraft::core {
class LibertyDB;
class StringPool;
}

namespace te {

bool save_core_liberty_binary(const edacraft::core::LibertyDB& db,
                              const edacraft::core::StringPool& pool,
                              std::ostream& out,
                              bool compress = false);

bool load_core_liberty_binary(const std::string& filepath,
                              edacraft::core::LibertyDB& db,
                              edacraft::core::StringPool& pool);

bool read_core_liberty_file(const std::string& filepath,
                            edacraft::core::LibertyDB& db,
                            edacraft::core::StringPool& pool);

} // namespace te
