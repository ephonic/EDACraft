/* unistd.h — MSVC 兼容 shim（仅供 vaParser 工具链在 Windows/MSVC 下构建）。
 * POSIX unistd.h 中的 isatty/fileno/access 等符号在 MSVC 的 <io.h> 中提供。 */
#pragma once
#include <io.h>
#include <stdlib.h>
#include <process.h>
