#!/bin/sh
# Generated files are checked in, so normal builds do not need Flex/Bison.
set -eu
cd "$(dirname "$0")/.."
parser_dir=parsers/rtl/src/parser/verilog
"${BISON:-bison}" -p verilog -b verilog --defines="$parser_dir/verilog_yacc.hpp" -o "$parser_dir/verilog_yacc.cpp" "$parser_dir/verilog.y"
"${FLEX:-flex}" -Pverilog --nounistd -o "$parser_dir/verilog_lex.cpp" "$parser_dir/verilog.l"
