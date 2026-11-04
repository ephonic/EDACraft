/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_ast_node.hpp
 * Summary  : verilog syntax analyzer node class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PARSER_VERILOG_VERI_AST_NODE_HPP_
#define PARSER_VERILOG_VERI_AST_NODE_HPP_

#include <vector>
#include <string>

namespace rtl
{

class VeriNode;

/*
 * class VeriAstNode :
 *     Verilog syntax analyzer abstract-syntax-tree node, for yacc usage
 */
struct VeriAstNode
{
  class VeriNode *node;
};

};
#endif // PARSER_VERILOG_VERI_AST_NODE_HPP_
