#!/usr/bin/env bash
# regen_registry.sh — 汇总 src/model/generated/*_reg.inc 重写 generated_registry.cpp
# 的 >>> AUTO-INCLUDES / >>> AUTO-REGISTRY 标记段。
#
# 用法（在 CktCraft 目录或任意目录运行均可）:
#   tools/regen_registry.sh
#
# 每个 *_reg.inc 由 vaParser --format=rfsim 生成，含两行：
#   第 1 行: #include "<base>_gen.h"
#   第 2 行:     {"<module>", &makeGen<<Class>GenModel>},
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GEN_DIR="$SCRIPT_DIR/../src/model/generated"
REG="$GEN_DIR/generated_registry.cpp"

if [ ! -f "$REG" ]; then
    echo "error: $REG not found" >&2
    exit 1
fi

# 注意：必须用 msys 的 sort（PATH 可能先命中 C:/Windows/system32/sort.exe）
SORT=/usr/bin/sort
includes=$(cat "$GEN_DIR"/*_reg.inc 2>/dev/null | grep '^#include' | $SORT -u)
rows=$(cat "$GEN_DIR"/*_reg.inc 2>/dev/null | grep 'makeGen<' | $SORT -u)

if [ -z "$includes" ] || [ -z "$rows" ]; then
    echo "error: no *_reg.inc snippets found in $GEN_DIR" >&2
    exit 1
fi

awk -v inc="$includes" -v reg="$rows" '
/^\/\/ >>> AUTO-INCLUDES/ { print; print inc; skip=1; next }
/^\/\/ <<< AUTO-INCLUDES/ { skip=0; print; next }
/^\/\/ >>> AUTO-REGISTRY/  { print; print reg; skip=1; next }
/^\/\/ <<< AUTO-REGISTRY/  { skip=0; print; next }
skip { next }
{ print }
' "$REG" > "$REG.tmp"

mv "$REG.tmp" "$REG"
echo "registry regenerated: $(echo "$rows" | wc -l) model(s)"
