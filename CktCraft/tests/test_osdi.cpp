// test_osdi.cpp - OSDI library loading and descriptor tests
#include "model/osdi/osdi_library.hpp"
#include <gtest/gtest.h>
#include <cstdlib>
#include <iostream>
using namespace rfsim;

namespace {
std::string projectRootFromTestData() {
    std::string s = RFSIM_TEST_DATA_DIR;          // .../tests/netlists
    auto pos = s.find_last_of("/\\");             // remove /netlists
    if (pos != std::string::npos) s = s.substr(0, pos);
    pos = s.find_last_of("/\\");                  // remove /tests
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}
std::string diodeLibPath() {
    if (const char* p = std::getenv("RFSIM_OSDI_TEST_LIB")) return p;
    std::string root = projectRootFromTestData();
#ifdef _WIN32
    return root + "/models/simple_diode.dll";
#else
    return root + "/models/simple_diode.so";
#endif
}
} // namespace

TEST(OsdiLibrary, LoadRealDiode) {
    OsdiLibrary lib;
    std::string err;
    ASSERT_TRUE(lib.load(diodeLibPath(), err)) << "load error: " << err;
    EXPECT_TRUE(lib.loaded());
    EXPECT_TRUE(lib.versionOk());
    EXPECT_GE(lib.numDescriptors(), 1u);
}

TEST(OsdiLibrary, FindDiodeDescriptor) {
    OsdiLibrary lib;
    std::string err;
    ASSERT_TRUE(lib.load(diodeLibPath(), err));
    const OsdiDescriptor* d = &lib.descriptors()[0];
    ASSERT_NE(d, nullptr);
    EXPECT_GE(d->num_nodes, 2u);
    EXPECT_NE(d->eval, nullptr);
    EXPECT_NE(d->setup_model, nullptr);
    EXPECT_NE(d->setup_instance, nullptr);
    EXPECT_GT(d->model_size, 0u);
    EXPECT_GT(d->instance_size, 0u);
}
