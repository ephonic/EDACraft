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

// Production inputs are Liberty text and ftimer binary caches only.
// Synopsys .db input is rejected until the standalone parser is complete.
bool read_core_liberty_file(const std::string& filepath,
                            edacraft::core::LibertyDB& db,
                            edacraft::core::StringPool& pool);

} // namespace te
