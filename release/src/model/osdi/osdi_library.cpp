// osdi_library.cpp — OSDI 共享库加载实现（跨平台 dlopen/LoadLibrary）
#include "osdi_library.hpp"

#ifdef _WIN32
  #include <windows.h>
#else
  #include <dlfcn.h>
#endif

#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>

extern "C" void rfsim_osdi_log(void* /*handle*/, char* msg, uint32_t lvl) {
    if (!msg) return;
    const char* prefix = "VA";
    switch (lvl & LOG_LVL_MASK) {
        case LOG_LVL_DEBUG:   prefix = "VA debug"; break;
        case LOG_LVL_DISPLAY: prefix = "VA"; break;
        case LOG_LVL_INFO:    prefix = "VA info"; break;
        case LOG_LVL_WARN:    prefix = "VA warn"; break;
        case LOG_LVL_ERR:     prefix = "VA error"; break;
        case LOG_LVL_FATAL:   prefix = "VA fatal"; break;
        default:              prefix = "VA unknown"; break;
    }
    if (lvl & LOG_FMT_ERR) {
        std::fprintf(stderr, "%s: FAILED TO FORMAT \"%s\"\n", prefix, msg);
    } else {
        std::fprintf(stderr, "%s: %s\n", prefix, msg);
    }
    // OSDI spec says ownership of msg is transferred to the simulator and should
    // be freed here.  Host and OpenVAF-generated dll both link UCRT (ucrtbase +
    // VCRUNTIME140) under MSVC /MD, so they share the same process heap; the
    // historical cross-CRT corruption that forced an intentional leak here is
    // gone after Sprint S2's MSVC toolchain switch (see plan0621-v4.md §2,
    // docs/known_issues.md KI-2).  Spec-compliant free now safe.
    std::free(msg);
}

namespace rfsim {

namespace {

#ifdef _WIN32
using LibHandle = HMODULE;
LibHandle openLib(const char* path) { return LoadLibraryA(path); }
void* sym(LibHandle h, const char* name) { return (void*)GetProcAddress(h, name); }
void closeLib(LibHandle h) { if (h) FreeLibrary(h); }
#else
using LibHandle = void*;
LibHandle openLib(const char* path) { return dlopen(path, RTLD_NOW | RTLD_LOCAL); }
void* sym(LibHandle h, const char* name) { return dlsym(h, name); }
void closeLib(LibHandle h) { if (h) dlclose(h); }
#endif

std::string toLower(std::string s) {
    for (auto& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

} // namespace

OsdiLibrary::~OsdiLibrary() {
    closeLib((LibHandle)handle_);
}

OsdiLibrary::OsdiLibrary(OsdiLibrary&& o) noexcept
    : handle_(o.handle_), path_(std::move(o.path_)),
      descriptors_(o.descriptors_), numDesc_(o.numDesc_),
      verMajor_(o.verMajor_), verMinor_(o.verMinor_) {
    o.handle_ = nullptr; o.descriptors_ = nullptr; o.numDesc_ = 0;
}

OsdiLibrary& OsdiLibrary::operator=(OsdiLibrary&& o) noexcept {
    if (this != &o) {
        closeLib((LibHandle)handle_);
        handle_ = o.handle_; path_ = std::move(o.path_);
        descriptors_ = o.descriptors_; numDesc_ = o.numDesc_;
        verMajor_ = o.verMajor_; verMinor_ = o.verMinor_;
        o.handle_ = nullptr; o.descriptors_ = nullptr; o.numDesc_ = 0;
    }
    return *this;
}

bool OsdiLibrary::load(const std::string& path, std::string& errMessage) {
    closeLib((LibHandle)handle_);
    handle_ = nullptr; descriptors_ = nullptr; numDesc_ = 0;
    verMajor_ = 0; verMinor_ = 0;
    path_ = path;

    LibHandle h = openLib(path.c_str());
    if (!h) {
#ifdef _WIN32
        errMessage = "LoadLibrary failed: " + std::to_string(GetLastError());
#else
        const char* e = dlerror();
        errMessage = std::string("dlopen failed: ") + (e ? e : "unknown");
#endif
        return false;
    }
    handle_ = (void*)h;

    // 解析 OSDI 标准导出符号
    // 注意: OSDI_DESCRIPTORS 是 OsdiDescriptor[] 数组(数组首元素地址),非指针的指针。
    //       OSDI_NUM_DESCRIPTORS / VERSION_* 是单个 uint32 值。
    auto* pDesc = (const OsdiDescriptor*)sym(h, "OSDI_DESCRIPTORS");
    auto* pNum  = (uint32_t*)sym(h, "OSDI_NUM_DESCRIPTORS");
    auto* pVMaj = (uint32_t*)sym(h, "OSDI_VERSION_MAJOR");
    auto* pVMin = (uint32_t*)sym(h, "OSDI_VERSION_MINOR");

    if (!pDesc || !pNum || !pVMaj || !pVMin) {
        errMessage = path + ": missing OSDI export symbols (not an OSDI library?)";
        closeLib(h); handle_ = nullptr;
        return false;
    }

    descriptors_ = pDesc;          // 直接是数组首地址
    numDesc_ = *pNum;
    verMajor_ = *pVMaj;
    verMinor_ = *pVMin;

    if (!versionOk()) {
        errMessage = path + ": OSDI version " + std::to_string(verMajor_) + "." +
                     std::to_string(verMinor_) + " unsupported (need " +
                     std::to_string(OSDI_VERSION_MAJOR_CURR) + "." +
                     std::to_string(OSDI_VERSION_MINOR_CURR) + ")";
        // 版本不匹配仍保留加载，让上层决定是否继续
    }

    // 注册 OSDI 日志回调（如 $strobe/$display）。该符号是 DLL 导出的函数指针变量。
    void** plog = (void**)sym(h, "osdi_log");
    if (plog) {
        *plog = (void*)&rfsim_osdi_log;
    }
    return true;
}

bool OsdiLibrary::reload(std::string& errMessage) {
    if (path_.empty()) {
        errMessage = "reload: no prior path stored";
        return false;
    }
    std::string savedPath = path_;
    // 释放当前句柄（FreeLibrary/dlclose）。即便 FreeLibrary 因引用计数 > 0
    // 未真正卸载，host 端 handle_ 仍清零，后续 LoadLibrary 重新拿新句柄。
    closeLib((LibHandle)handle_);
    handle_ = nullptr;
    descriptors_ = nullptr;
    numDesc_ = 0;
    verMajor_ = 0;
    verMinor_ = 0;
    path_.clear();
    // 重新加载。失败时对象处于未加载态，调用方需自行处理。
    return load(savedPath, errMessage);
}

const OsdiDescriptor* OsdiLibrary::findDescriptor(const std::string& name) const {
    if (!descriptors_) return nullptr;
    std::string low = toLower(name);
    for (uint32_t i = 0; i < numDesc_; ++i) {
        const OsdiDescriptor& d = descriptors_[i];
        if (d.name && toLower(d.name) == low) return &d;
    }
    return nullptr;
}

} // namespace rfsim
