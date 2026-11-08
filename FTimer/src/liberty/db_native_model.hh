#pragma once
#include "edacraft/core/liberty_db.hpp"
#include <string>

namespace edacraft::core::native::detail {
// Checked sequential-object profile. Unsupported containers/semantics fail
// atomically; the diagnostic byte scanners are never used to build a model.
bool read_model(const std::string& path, LibertyDB& db, StringPool& pool,
                std::string* error);
}
