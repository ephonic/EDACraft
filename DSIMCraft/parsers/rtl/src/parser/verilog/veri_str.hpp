/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_str.hpp
 * Summary  : verilog syntax analyzer true node class : string
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_STR_HPP_
#define PARSER_VERILOG_VERI_STR_HPP_

#include "veri_node.hpp"

#include <vector>
#include <string>

namespace rtl
{

// Decode the contents of an SV string literal identically for packed constants
// and runtime strings. Hex escapes consume at most two digits; octal, three.
inline std::string veri_decode_string(const std::string& text)
{
  std::string bytes;
  auto hex=[](unsigned char c)->int {
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    if(c>='A'&&c<='F')return c-'A'+10;
    return -1;
  };
  for(size_t i=0;i<text.size();++i) {
    char c=text[i];
    if(c=='\\'&&i+1<text.size()) {
      c=text[++i];
      switch(c) {
        case 'n':c='\n';break;case 't':c='\t';break;case 'r':c='\r';break;
        case 'f':c='\f';break;case 'v':c='\v';break;case 'a':c='\a';break;case 'b':c='\b';break;
        default:
          if(c>='0'&&c<='7') {
            unsigned value=unsigned(c-'0');int count=1;
            while(count<3&&i+1<text.size()&&text[i+1]>='0'&&text[i+1]<='7') {
              value=value*8+unsigned(text[++i]-'0');++count;
            }
            c=char(value&255);
          } else if(c=='x'&&i+1<text.size()&&hex(text[i+1])>=0) {
            unsigned value=0;int count=0;
            while(count<2&&i+1<text.size()&&hex(text[i+1])>=0) {
              value=value*16+unsigned(hex(text[++i]));++count;
            }
            c=char(value);
          }
          // Other escapes quote the next character, dropping the backslash.
          break;
      }
    }
    bytes+=c;
  }
  return bytes;
}

/*
 * class VeriStmt :
 *     Verilog syntax analyzer true node : Statement
 */
class VeriStr : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;

  public:
    VeriStr( Uint idx, int line, int col, VeriMod *mod )
      :  VeriNode( idx, vtSTR, vtSTR, line, col, mod )
    {}

    virtual ~VeriStr( void ) { clear(); }

    // accessors
    CString& str( void ) const { return _str; }

    // mutators
    void set_str( CString& str ) { _str = str; }

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  private:
    String _str;
};

};
#endif // PARSER_VERILOG_VERI_STMT_HPP_
