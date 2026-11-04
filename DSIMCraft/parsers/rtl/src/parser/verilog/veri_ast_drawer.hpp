/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_ast_drawer.hpp
 * Summary  : verilog abstract syntax tree drawer
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang   ( 11212020059@fudan.edu.cn )
              Chelsy Huang ( 09300720330@fudan.edu.cn )
 * Date     : 2012.12.10
 */
#ifndef PARSER_VERILOG_VERI_AST_DRAWER_
#define PARSER_VERILOG_VERI_AST_DRAWER_

#include <string>
#include <queue>
#include <fstream>
#include <sstream>

namespace rtl
{

struct VeriAstNode;
class  VeriSymbolTable;
/*
 * class VeriAstDraw :
 *     verilog abstract-syntax-tree drawer.
 *     call draw function to draw. ( output .dot file )
 *     call generate jpg to generate jpg output file.
 */
class VeriAstDrawer
{
  typedef std::string      String;
  typedef std::ofstream    Ofstream;
  typedef const String     CString;
  typedef std::queue< VeriNode * > NodeQueue;
  typedef std::vector< VeriNode *> NodeVec;
  typedef std::queue< int > IQueue;

  typedef VeriSymbolTable  SymbolTable;
  typedef std::queue< SymbolTable *> SymbolTableQueue;

  public:
    VeriAstDrawer( void )
      : _ofile()
      , _dir("")
      , _fname("")
      , _depth(0)
    {
    };

    ~VeriAstDrawer( void ) { clear(); };

    // initializing output filename
    void init( CString& dir, CString& fname );

    // designate components for output
    void prep_for_drawing( void );
    void draw_ast( VeriNode *head );
    void draw_symbol( SymbolTable *table_head );
    void end_drawing( void );

    // generate jpg output file
    void generate_jpg( void );

  protected:
    // determine rank
    void append_rank_edge( int depth );

    // clear status, back to status after construction
    void clear( void );

    String int2string(int n)
    {
      std::stringstream f;
      f << n;
      return f.str();
    }

  private:
    Ofstream _ofile;
    String   _dir;
    String   _fname;
    int      _depth;
};

}

#endif  // UTILITY_AST_DRAW
