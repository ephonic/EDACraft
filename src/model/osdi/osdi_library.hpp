// osdi_library.hpp — OSDI 共享库加载器（dlopen + 符号解析）
//
// 加载 OpenVAF 编译的模型共享库，解析 OSDI 标准导出符号：
//   OSDI_DESCRIPTORS, OSDI_NUM_DESCRIPTORS, OSDI_VERSION_MAJOR/MINOR
// 并按模型名查找对应的 OsdiDescriptor。
//
// 平台：POSIX 用 dlopen/dlsym，Windows 用 LoadLibrary/GetProcAddress。
#ifndef RFSIM_MODEL_OSDI_OSDI_LIBRARY_HPP
#define RFSIM_MODEL_OSDI_OSDI_LIBRARY_HPP

#include "osdi_0_3.h"
#include "../../rfsim.hpp"
#include <memory>
#include <string>
#include <vector>

namespace rfsim {

// 已加载的 OSDI 共享库。RAII：析构时释放句柄。
// 多个同模型实例共享同一个 OsdiLibrary。
class OsdiLibrary {
public:
    OsdiLibrary() = default;
    ~OsdiLibrary();

    // 禁拷贝（持有 OS 句柄），允许移动
    OsdiLibrary(const OsdiLibrary&) = delete;
    OsdiLibrary& operator=(const OsdiLibrary&) = delete;
    OsdiLibrary(OsdiLibrary&&) noexcept;
    OsdiLibrary& operator=(OsdiLibrary&&) noexcept;

    // 从路径加载共享库。成功返回 true。
    // 失败时填充 errMessage。
    bool load(const std::string& path, std::string& errMessage);

    [[nodiscard]] bool loaded() const noexcept { return handle_ != nullptr; }
    [[nodiscard]] const std::string& path() const noexcept { return path_; }

    // 版本校验：返回 (major, minor)，未加载返回 (0,0)
    [[nodiscard]] uint32_t versionMajor() const noexcept { return verMajor_; }
    [[nodiscard]] uint32_t versionMinor() const noexcept { return verMinor_; }
    [[nodiscard]] bool versionOk() const noexcept {
        return verMajor_ == OSDI_VERSION_MAJOR_CURR && verMinor_ == OSDI_VERSION_MINOR_CURR;
    }

    // descriptor 数组
    [[nodiscard]] uint32_t numDescriptors() const noexcept { return numDesc_; }
    [[nodiscard]] const OsdiDescriptor* descriptors() const noexcept { return descriptors_; }

    // 按模型名(name, 小写)查找 descriptor。未找到返回 nullptr。
    [[nodiscard]] const OsdiDescriptor* findDescriptor(const std::string& name) const;

private:
    void* handle_ = nullptr;        // dlopen/LoadLibrary 句柄
    std::string path_;
    const OsdiDescriptor* descriptors_ = nullptr;
    uint32_t numDesc_ = 0;
    uint32_t verMajor_ = 0;
    uint32_t verMinor_ = 0;
};

} // namespace rfsim

#endif // RFSIM_MODEL_OSDI_OSDI_LIBRARY_HPP
