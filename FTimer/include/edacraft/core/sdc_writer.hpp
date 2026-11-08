#ifndef EDACRAFT_CORE_SDC_WRITER_HPP
#define EDACRAFT_CORE_SDC_WRITER_HPP

#include "edacraft/core/constraint_db.hpp"
#include <string>

namespace edacraft::core {

// Write ConstraintDB to an SDC text string.
// Useful for debugging, golden reference files, and interop.
std::string write_sdc(const ConstraintDB& constraints);

// Write ConstraintDB to an SDC file.
bool write_sdc_file(const std::string& filepath, const ConstraintDB& constraints);

} // namespace edacraft::core

#endif // EDACRAFT_CORE_SDC_WRITER_HPP
