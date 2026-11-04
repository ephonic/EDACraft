/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_preproc.cpp
 * Summary  : verilog pre-processer class functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#include <fstream>
#include <cctype>
#include <iostream>

#include "general_err.hpp"
#include "veri_err.hpp"
#include "veri_err_token.hpp"
#include "veri_pretoken.hpp"
#include "verilog_token.hpp"

#include "cfg_mgr.hpp"
#include "src_mgr.hpp"

#include "veri_preproc.hpp"
#include "veri_preproc_tokens_status.hpp"

#ifdef DEBUG_VERI_PROPROC_
#include <iostream>
using std::cout;
using std::endl;
#endif

namespace rtl
{

// Expand object aliases at the use site, while the active macro definitions
// are still available. Preserve strings/comments and function macro calls.
static std::string expand_object_macro_references(
    const std::string& text, VeriPreProc& preproc, int depth = 64)
{
  if (depth <= 0) return text;
  std::string result;
  bool line_comment = false, block_comment = false, quoted = false;
  for (size_t i = 0; i < text.size();)
  {
    const char c = text[i];
    const char next = i + 1 < text.size() ? text[i + 1] : '\0';
    if (line_comment) {
      result += c;
      if (c == '\n') line_comment = false;
      ++i;
      continue;
    }
    if (block_comment) {
      result += c;
      ++i;
      if (c == '*' && next == '/') {
        result += next; ++i; block_comment = false;
      }
      continue;
    }
    if (quoted) {
      result += c;
      ++i;
      if (c == '\\' && i < text.size()) result += text[i++];
      else if (c == '"') quoted = false;
      continue;
    }
    if (c == '/' && (next == '/' || next == '*')) {
      result += c; result += next; i += 2;
      line_comment = next == '/'; block_comment = next == '*';
      continue;
    }
    if (c == '"') { quoted = true; result += c; ++i; continue; }
    if (c == '`' && (std::isalpha(static_cast<unsigned char>(next)) || next == '_')) {
      size_t end = i + 2;
      while (end < text.size() &&
             (std::isalnum(static_cast<unsigned char>(text[end])) ||
              text[end] == '_' || text[end] == '$')) ++end;
      std::string value;
      if (preproc.get_object_macro(text.substr(i + 1, end - i - 1), value))
        result += expand_object_macro_references(value, preproc, depth - 1);
      else result += text.substr(i, end - i);
      i = end;
      continue;
    }
    result += c;
    ++i;
  }
  return result;
}

bool
VeriPreProc::get_object_macro(const std::string& name, std::string& value)
{
  VeriDef *def = _define_hash.hash_value(name);
  if( def == NULL || def->type() > 1 )
    return false;

  VPPtVec empty;
  value = def->get_result(empty);
  return true;
}

VeriPreProc::VeriPreProc( void ) :\
    \
    _parse_name(""),
    _fname(),
    _file_st(),
    _input(),
    \
    _toks(),
    _status(),
    _linenos(),
    _cur_pos(),
    _pre_pos(),
    \
    _cur_status(vpSTART),
    _cur_name(""),
    _cur_st(),
    _cur_s(NULL),
    _cur_length(0),
    _cur_line(0),
    _cur_col(0),
    _cpos(0),
    _ppos(0),
    _cur_tok(),
    \
    _quoted_dirs(),
    _sys_dirs(),
    \
    _include_headers(),
    \
    _output(""),
    _file_depth(0),
    _err(),
    \
    _define_hash(),
    \
    _asso_values(),
    _word_list(),
    _total_keywords(16),
    _min_word_length(4),
    _max_word_length(18),
    _min_hash_value(5),
    _max_hash_value(30)
{
  _cmgr = Cfg_mgr::get_instance();
  _smgr = Src_mgr::get_instance();
  _err  = VeriErr::get_instance();

  // reg func ... 

  register int i;
  _define_hash.hash_create(100);

  for( i = 0 ; i < 97 ; ++i )
    _asso_values[i] = 31;

  _asso_values[ 97] = 31;   // a
  _asso_values[ 98] = 31;   // b
  _asso_values[ 99] = 15;   // c
  
  _asso_values[100] =  5;   // d
  _asso_values[101] =  5;   // e
  _asso_values[102] = 15;   // f
  _asso_values[103] = 31;   // g
  _asso_values[104] = 31;   // h
  _asso_values[105] =  0;   // i
  _asso_values[106] = 31;   // j
  _asso_values[107] = 31;   // k
  _asso_values[108] =  5;   // l
  _asso_values[109] = 31;   // m

  _asso_values[110] =  0;   // n
  _asso_values[111] =  5;   // o
  _asso_values[112] = 31;   // p
  _asso_values[113] = 31;   // q
  _asso_values[114] =  0;   // r
  _asso_values[115] = 31;   // s
  _asso_values[116] = 10;   // t
  _asso_values[117] =  0;   // u
  _asso_values[118] = 31;   // v
  _asso_values[119] = 31;   // w

  for( i = 120 ; i < 256 ; ++i )
    _asso_values[i] = 31;

  _word_list[ 0] = "";
  _word_list[ 1] = "";
  _word_list[ 2] = "";
  _word_list[ 3] = "";
  _word_list[ 4] = "";
  _word_list[ 5] = "undef";
  _word_list[ 6] = "";
  _word_list[ 7] = "include";
  _word_list[ 8] = "";
  _word_list[ 9] = "line";

  _word_list[10] = "endif";
  _word_list[11] = "";
  _word_list[12] = "";
  _word_list[13] = "resetall";
  _word_list[14] = "else";
  _word_list[15] = "elsif";
  _word_list[16] = "define";
  _word_list[17] = "unconnected_drive";
  _word_list[18] = "endcelldefine";
  _word_list[19] = "timescale";
  
  _word_list[20] = "ifdef";
  _word_list[21] = "ifndef";
  _word_list[22] = "";
  _word_list[23] = "";
  _word_list[24] = "nonconnected_drive";
  _word_list[25] = "default_nettype";
  _word_list[26] = "";
  _word_list[27] = "";
  _word_list[28] = "";
  _word_list[29] = "";

  _word_list[30] = "celldefine";
}

VeriPreProc::~VeriPreProc( void )
{
  clear();
};

int
VeriPreProc::init(CString& fname,
                  const SVector& sys_dirs, const SVector& quote_dirs)
{
  _sys_dirs    = sys_dirs;
  _quoted_dirs = quote_dirs;

  return init(fname);
}

int
VeriPreProc::init(CString& fname)
{
  int re = cache_file( fname );
  if( re != OK )
    return re;

  _parse_name  = fname;

  _cur_status = vpSTART;
  _cur_name   = fname;
  _cur_length = _cur_st.st_size;
  _cur_line   = 1;
  _cur_col    = 0,
  _cpos       = 0;
  _ppos       = 0;

  _output.clear();

  save_context();
  //append_include_head(_fname.back());
  return OK;
}

int
VeriPreProc::append_quote_dir( CString& dir )
{
  _quoted_dirs.push_back( dir );
  return OK;
}

int
VeriPreProc::parse( void )
{
  if( !_parse_name.empty() )
  {
    int if_return = 0;
    parse_recursivly( vpNORMAL, if_return );
    if( _err->has_err() == IS_TRUE )
      return ERR;
    else
    {
      after_parse( );
      _smgr->set_src(_output);
      _smgr->set_fname( _parse_name );
      return OK;
    }
  }
  else
    return ERR;
}

int
VeriPreProc::has_err( void ) const
{
  return _err->has_err();
}

const std::string&
VeriPreProc::get_err_info( void ) const
{
  return _err->get_err_info();
}

void
VeriPreProc::clear( void )
{
  _output = "";
  _file_depth = 0;

  _define_hash.clear();

  _fname.clear();
  _file_st.clear();
  _input.clear();
  _toks.clear();
  _status.clear();
  _linenos.clear();
  _cur_pos.clear();
  _pre_pos.clear();
  _include_headers.clear();

  _cur_status = vpSTART;
  _cur_name   = "";
  _cur_length = 0;
  _cur_line   = 0;
  _cur_col    = 0;
  _cur_s      = NULL;
  _cpos       = 0;
  _ppos       = 0;
  _cur_tok.clear();
    
  _quoted_dirs.clear();
  _sys_dirs.clear();
  _parse_name = "";
}

void
VeriPreProc::clean_up( void )
{
  _output = "";
  _file_depth = 0;

  _define_hash.clean_up();

  _fname.clear();
  _file_st.clear();
  _input.clear();
  _toks.clear();
  _status.clear();
  _linenos.clear();
  _cur_pos.clear();
  _pre_pos.clear();
  _cur_tok.clear();
  _include_headers.clear();

  int re = cache_file( _parse_name );
  if( re != OK )
  {
    _parse_name = "";
    _cur_status = vpSTART;
    _cur_name   = "";
    _cur_length = 0;
    _cur_line   = 0;
    _cur_col    = 0;
    _cur_s      = NULL;
    _cpos       = 0;
    _ppos       = 0;
  }
  else
  {
    _cur_status = vpSTART;
    _cur_name   = _parse_name;
    _cur_length = _cur_st.st_size;
    _cur_line   = 1;
    _cur_col    = 0;
    _cpos       = 0;
    _ppos       = 0;
    save_context();
//    append_include_head( _fname.back() );
  }
}

int
VeriPreProc::cache_file( CString& fname )
{
  std::ifstream infile;
  infile.open(fname.c_str() , std::ios::binary);
  if( infile.fail() )
    return vPRE_FILE_OPEN_ERROR;
  if(stat(fname.c_str(), &_cur_st) != OK)
  {
    infile.close();
    clear();
    return vPRE_FILE_STAT_ERROR;
  }

  _cur_s = new char[_cur_st.st_size + 2];
  infile.read(_cur_s, _cur_st.st_size);
  _cur_s[_cur_st.st_size     ] = ' ';
  _cur_s[_cur_st.st_size + 1 ] = '\0';
  _cur_st.st_size += 2;
  infile.close();

  _err->include_file( 1, fname );
  return OK;
}

int
VeriPreProc::append_include_quote(Uint /* plot_line */, CString& fname)
{
  String infile = search_file_quote( fname );

  if( !infile.empty() )
  {
    int re = append_file_data( infile );
    if( re == OK )
      append_include_head( infile );
    else
      return re;
    return OK;
  }
  else
    return vPRE_FILE_OPEN_ERROR;
}

int
VeriPreProc::append_include_sys(Uint /* plot_line */, CString& fname)
{
  String infile = search_file_sys( fname );

  if( !infile.empty() )
  {
    int re = append_file_data(  infile );
    if( re == OK )
      append_include_head( infile );
    else
      return re;
    return OK;
  }
  else
    return vPRE_FILE_OPEN_ERROR;
}

std::string
VeriPreProc::search_file_quote(CString& name)
{
  const char *src = name.c_str();
  Uint length = name.length();
  Uint step   = 0;
  Uint i;

  for( i = 0 ; i < length ; ++i )
  {
    if( src[i] != ' ' )
      break;
  }
  length -= i;
  step   += i;
  src    += i;

  for( i = length - 1 ; i < length ; --i )
  {
    if( src[i] != ' ' )
      break;
  }
  length = i + 1;

  String fname = "";
  std::ifstream infile;

  SVector::const_iterator cisv = _quoted_dirs.begin();
  for( ; cisv != _quoted_dirs.end() ; ++cisv )
  {
    fname = (*cisv + name);
    infile.open( fname.c_str(), std::ios::binary);
    if( infile.good() )
    {
      infile.close();
      return fname;
    }
  }
  return "";
}

std::string
VeriPreProc::search_file_sys(CString& name)
{
  String fname = name;
  std::ifstream infile;
  
  SVector::const_iterator cisv = _sys_dirs.begin();
  for( ; cisv != _sys_dirs.end() ; ++cisv )
  {
    fname = *cisv + name;
    infile.open(fname.c_str(), std::ios::binary);
    if( infile.good() )
    {
      infile.close();
      return fname;
    }
  }
  fname = "";
  return fname;
}

int
VeriPreProc::append_file_data(CString& fname)
{
  _file_depth++;
  change_context();

  int re = cache_file( fname );
  if( re != OK )
    return re;

  _cur_st.st_size += 2;
  _cur_length      = _cur_st.st_size;
  _cur_status      = vpSTART;
  _cur_name        = fname;
  _cur_line        = 1;
  _cur_col         = 0;
  _cpos            = 0;
  _ppos            = 0;
  _cur_tok.clear();

  save_context();
  return OK;
}

void
VeriPreProc::append_include_head(CString& fname)
{
#ifdef DEBUG_VERI_PROPROC_
  _include_headers[fname]++;
  String re = "";
  re = re + "`line " + "1 \"" + fname + "\" 1\n";
  std::cout << " debug(append_include_head) : " << re;
  _output += re;
#else
  _include_headers[fname]++;
  _output = _output + "`line " + "1 \"" + fname + "\" 1\n";
#endif
}

void
VeriPreProc::append_line_info_tail( Uint lineno )
{
#ifdef DEBUG_VERI_PROPROC_
  String re = "";
  re = re + "`line " + int2string(lineno) + " \"" + _fname.back() + "\" ";
  _output += re;
  cout << " debug(append_line_info_tail) : " << re;
  re = "";
  re = re + "0\n";
  cout << re;
  _output += re;
#else
  _output = _output + "`line " + int2string(lineno) + " \"" + _fname.back() + "\" ";
  _output = _output + "0\n";
#endif
}

void
VeriPreProc::append_include_tail(Uint lineno)
{
#ifdef DEBUG_VERI_PROPROC_
  String re = "";
  re = re + "`line " + int2string(lineno) + " \"" + _fname.back() + "\" ";
  _output += re;
  cout << " debug(append_line_info_tail) : " << re;
  re = "";
  re = re + "2\n";
  cout << re;
  _output += re;
#else
  _output = _output + "`line " + int2string(lineno) + " \"" + _fname.back() + "\" ";
  _output = _output + "2\n";
#endif
}

int
VeriPreProc::parse_recursivly(int if_flag, int& across)
{
  int       t  = 0;
  int       re = 0;
  Uint      plot_line = 0;
  String    s = "";
  String    mem_s = "";
  String    other = "";
  int       def_type = 0;
  String    def_name = "";
  SVector   def_vars;
  VeriDef  *def = NULL, *tdef= NULL;

  int if_return   = 0;
  int else_found  = IS_FALSE;
  int has_comment = IS_FALSE;
  int is_line_head = IS_TRUE;
  int def_status_no_vars = IS_FALSE;
  int def_anti_depth = 0;  // bracket nesting depth inside macro arguments

  if( if_flag == vpNORMAL )
    get_context();
  else
  {
    _status.push_back(_cur_status);
    _cur_status = vpSTART;
  }

  if( _file_depth > 100 )
  {
    _err->append_err(ERR_FATEL, _cur_line, _cur_col,
                     vPRE_INC_TOO_DEEP, other);
    return ERR;
  }

  while( (t = get_next_tok()) != NONE )
  {
    switch( _cur_status )
    {

      case vpSTART:
        switch( t )
        {
          case vtNL :
            _cur_line++;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                if( has_comment == IS_TRUE && is_line_head == IS_TRUE )
                {
                  append_line_info_tail(_cur_line);
                  has_comment  = IS_FALSE;
                  is_line_head = IS_FALSE;
                }
                else
                  _output += '\n';
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            has_comment  = IS_FALSE;
            is_line_head = IS_TRUE;
            _cur_col = 0;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++;
            break;
          
          case vpUNDEF      :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpUNDEF_0;
                break;
              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;
          
          case vpINCLUDE :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpINCLUDE_0;
                break;
              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpLINE       :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpLINE_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpENDIF      :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
                _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                 vPRE_ENDIF_WITHOUT_IF, other);
                break;

              case vpIF_SUCC :
              case vpIF_FAIL :
              case vpIF_SKIP :
                across = vpAC_ENDIF;
                _cur_status = _status.back();
                _status.pop_back();
                return OK;
                break;

              default:
                break;
            }
            break;

          case vpRESET_ALL :
            is_line_head = IS_FALSE;
            // do reset all operation
            break;

          case vpELSE :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
                _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                 vPRE_ELSE_WITHOUT_IF, other );
                break;

              case vpIF_SUCC :
              case vpIF_FAIL :
                across = vpAC_ELSE;
                _cur_status = _status.back();
                _status.pop_back();
                return OK;
                break;

              case vpIF_SKIP :
                if( else_found == IS_TRUE )
                  _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                   vPRE_ELSE_WITHOUT_IF, other );
                else_found = IS_TRUE;
                break;

              default:
                break;
            }
            break;

          case vpELIF       :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
                _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                 vPRE_ELIF_WITHOUT_IF, other );
                break;

              case vpIF_SUCC :
              case vpIF_FAIL :
                across = vpAC_ELSIF;
                _cur_status = _status.back();
                _status.pop_back();
                return OK;

              case vpIF_SKIP :
                break;

              default:
                break;
            }
            break;

          case vpDEFINE     :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                def_status_no_vars = IS_FALSE;
                plot_line = _cur_line;
                _cur_status = vpDEFINE_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpUNCONN_DRIVE :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpUNCONN_DRIVE_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpEND_CELL_DEF :
            is_line_head = IS_FALSE;
            // do end cell define operation
            break;

          case vpTIMESCALE :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpTIMESCALE_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpIFDEF      :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpIFDEF_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
                re = parse_recursivly( vpIF_SKIP, if_return );
                if( re != OK )
                  _err->append_err(ERR_ERROR, _cur_line, _cur_col, re, other );
                else if( if_return != vpAC_ENDIF )
                  _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                   vPRE_ENDIF_MISSING, other );
                _cur_status = vpSTART;
                break;
              default:
                break;
            }
            break;

          case vpIFNDEF      :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpIFNDEF_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
                re = parse_recursivly( vpIF_SKIP, if_return );
                if( re != OK )
                  _err->append_err(ERR_ERROR, _cur_line, _cur_col, re, other );
                else if( if_return != vpAC_ENDIF )
                  _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                   vPRE_ENDIF_MISSING, other );
                _cur_status = vpSTART;
                break;
              default:
                break;
            }
            break;

          case vpNON_CONN_DRIVE :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpNON_CONN_DRIVE_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpDEFAULT_NETTYPE :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                plot_line = _cur_line;
                _cur_status = vpDEFAULT_NETTYPE_0;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpCELL_DEF:
            is_line_head = IS_FALSE;
            // do cell define opreration
            break;

          case vtCOMM       :
            has_comment = IS_TRUE;
            break;

          case vtCOMM_ERR :
            is_line_head = IS_FALSE;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_COMM_NOT_END, other );
            break;

          case vtSTR_ERR :
            is_line_head = IS_FALSE;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_QUOTE_NOT_END, other );
            break;

          case vtSTR    :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                cpystring( _cur_s, _cpos - _ppos , _ppos, s );
                _output = _output + s;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vtIDENT:
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                cpystring( _cur_s, _cpos - _ppos , _ppos, s );
                _output += s;
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          case vpDEF_VAR :
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                cpystring( _cur_s, _cpos - _ppos , _ppos, s );
                def = _define_hash.hash_value(s);
                if( def != NULL )
                {
                  def_type = def->type();
                  switch( def_type )
                  {
                    case 0:
                      break;
                    case 1:
                      _toks.push_back(VPPtok(t, s, NONE, NONE));
                      _output += expand_object_macro_references(def->get_result(_toks), *this);
                      _toks.clear();
                      break;
                    case 2:  case 3:
                      _cur_status = vpDEF_ANTI_0;
                      break;
                    default:
                      _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                       vPRE_NOT_KNOWN_ERR, other );
                      _cur_status = vpSTART;
                      break;
                  } // switch def_type
                } // if def != NULL
                else
                {
                  _output += "`" + s;
                  _cur_status = vpSTART;
                } // if def == NULL
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;

          default:
            is_line_head = IS_FALSE;
            switch( if_flag )
            {
              case vpNORMAL :
              case vpIF_SUCC :
                cpystring( _cur_s, _cpos - _ppos , _ppos, s );
     //           _cur_tok.set( t, s, NONE, NONE );
                _output += s;
                s = "";
                break;

              case vpIF_FAIL :
              case vpIF_SKIP :
              default:
                break;
            }
            break;
        }
        break;

      case vpUNDEF_0:
        switch( t )
        {
          case vtWHITE :
            continue;
            break;

          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++;
            break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            def = _define_hash.hash_value(s);
            if( def != NULL )
              _define_hash.hash_delete(s);
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            break;

          case vtNL :
            is_line_head = IS_TRUE;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_line++;
            _cur_status = vpSTART;
            _cur_col = 0;
            break;

          default : 
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_UNEXPECTED_TOK, other );
            _cur_status = vpSTART;
          break;
        }
        break;

      case vpINCLUDE_0:
        switch( t )
        {
          case vtTRAN:
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _err->append_err(ERR_FATEL, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_status = vpSTART;
            _cur_col = 0;
            break;

          case vtWHITE:
            continue;
            break;

          case vtSTR:
            cpystring( _cur_s, _cpos - _ppos - 2 , _ppos + 1, s );
            change_context();
            re = append_include_quote(plot_line, s);
            if( re != OK )
            {
              _err->append_err(ERR_FATEL, _cur_line, _cur_col, re, other );
              get_context();
            }
            else{
              re = parse_recursivly( vpNORMAL, if_return );
              get_context();
              if( re != OK )
                _err->append_err(ERR_FATEL, _cur_line, _cur_col, re, other );
              else
                append_line_info_tail(_cur_line);
            }
            _cur_status = vpSTART;
            break;

          case vtSTR_ERR:
            _err->append_err(ERR_FATEL, _cur_line, _cur_col,
                             vPRE_QUOTE_NOT_END, other );
            _cur_status = vpSTART;
            break;

          default :
            _err->append_err(ERR_FATEL, _cur_line, _cur_col,
                             vPRE_NOT_KNOWN_ERR, other );
            _cur_status = vpSTART;
            break;
        }
        break;

      case vpLINE_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          default :
            break;
        }
        break;

      case vpUNCONN_DRIVE_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            if( s == "pull0" )
              _cmgr->set_veri_unconn( 0 );
            else if( s == "pull1" )
              _cmgr->set_veri_unconn( 1 );
            else
              _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                               vPRE_UNCONN_ERR, other );

            _cur_status = vpSTART;
            break;

          default :
            break;
        }
        break;

      case vpNON_CONN_DRIVE_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            if( s == "pull0" )
              _cmgr->set_veri_nonconn( 0 );
            else if( s == "pull1" )
              _cmgr->set_veri_nonconn( 1 );
            else
              _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                               vPRE_UNCONN_ERR, other );

            _cur_status = vpSTART;
            break;

          default :
            break;
        }
        break;

      case vpTIMESCALE_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          default :
            break;
        }
        break;

      case vpDEFAULT_NETTYPE_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );

            if( s == "wire" )
              _cmgr->set_veri_default_nettype( vvWIRE );
            else if( s == "tri" )
              _cmgr->set_veri_default_nettype( vvTRI );
            else if( s == "tri0" )
              _cmgr->set_veri_default_nettype( vvTRI0 );
            else if( s == "wand" )
              _cmgr->set_veri_default_nettype( vvWAND );
            else if( s == "triand" )
              _cmgr->set_veri_default_nettype( vvTRIAND );
            else if( s == "wor" )
              _cmgr->set_veri_default_nettype( vvWOR );
            else if( s == "trior" )
              _cmgr->set_veri_default_nettype( vvTRIOR );
            else if( s == "trireg" )
              _cmgr->set_veri_default_nettype( vvTRIREG );
            else if( s == "none" )
              _cmgr->set_veri_default_nettype( vvNONE );
            else
              _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                               vPRE_DEFAULT_NETTYPE_ERR, other );

            _cur_status = vpSTART;
            break;

          default:
            break;
        }
        break;

      case vpCELL_DEF_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          default :
            break;
        }
        break;

      case vpDEFINE_0 :
        switch( t )
        {
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
          
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_line++;
            _cur_col = 0;
            break;

          case vtWHITE :
            continue; break;

          case vtIDENT :
            def = new VeriDef;
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            def_name = s;
            _cur_status = vpDEFINE_1;
            break;

          default :
            if( def != NULL )
              delete def;
            def = NULL;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_UNEXPECTED_TOK, other );

            _cur_status = vpSTART;
            break;
        }
        break;

      case vpDEFINE_1:
        switch( t )
        {
          case vtWHITE :
            def_status_no_vars = IS_TRUE; break;

          case vtCOMM :
            break;

          case vtNL :
            is_line_head = IS_TRUE;
            def_status_no_vars = IS_FALSE;
            def_type = 0;
            def->init(def_type, def_name, def_vars);
            tdef = _define_hash.hash_value(def_name);
            if( tdef != NULL )
              _define_hash.hash_delete(def_name);
            _define_hash.hash_insert(def_name, def);
            def = NULL;
            def_name = "";
            def_type = 0;
   //          def_vars.clear();
   
            _cur_line++;
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            _cur_col = 0;
            break;

          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++;
            break;

          case vtLB :
            if( def_status_no_vars == IS_TRUE )
            {
              def_status_no_vars = IS_FALSE;
              def_type = 1;
              cpystring( _cur_s, _cpos - _ppos, _ppos, s );

              def->init(def_type, def_name, def_vars);
              _toks.push_back(VPPtok(t, s, NONE, NONE));
              _cur_status = vpDEFINE_5;
            }
            else
              _cur_status = vpDEFINE_2;
            break;
            
          default :
            def_status_no_vars = IS_FALSE;
            def_type = 1;
            def->init(def_type, def_name, def_vars);
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            if (t == vpDEF_VAR) s = "`" + s;
            _toks.push_back(VPPtok(t, s, NONE, NONE));
            _cur_status = vpDEFINE_5;
            break;
        }
        break;

      case vpDEFINE_2:
        switch( t )
        {
          case vtWHITE :
            continue;
            break;

          case vtCOMM :
            break;
   
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++;
            break;

          case vtNL :
            is_line_head = IS_TRUE;
            if( def != NULL )
              delete def;
            def = NULL;
            def_type = 0;
            def_name = "";
            def_vars.clear();
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_line++;
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            _cur_col = 0;
            break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            def_vars.push_back(s);
            _cur_status = vpDEFINE_3;
            break;

          default :
            if( def != NULL )
              delete def;
            def = NULL;
            def_type = 0;
            def_name = "";
            def_vars.clear();
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_COMMA_EXPECTED, other );
            _cur_status = vpSTART;
            break; 
        }
        break;

      case vpDEFINE_3:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtCOMM :
            break;

          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;
            
          case vtNL :
            is_line_head = IS_TRUE;
            _cur_line++;
            if( def != NULL )
              delete def;
            def = NULL;
            def_type = 0;
            def_name = "";
            def_vars.clear();
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_col = 0;
            _cur_status = vpSTART;
            break;
            
          case vtIDENT :
            def_type = 0;
            def_name = "";
            def_vars.clear();
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_COMMA_EXPECTED, other );
            _cur_status = vpSTART;
            break;

          case vtCOMMA :
            _cur_status = vpDEFINE_2; break;

          case vtRB :
            _cur_status = vpDEFINE_4; break;
            
          default :
            if( def != NULL )
              delete def;
            def = NULL;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_UNEXPECTED_TOK, other );
            _cur_status = vpSTART;
            break;
        }
        break;

      case vpDEFINE_4:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtCOMM :
            break;

          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;
            
          case vtNL :
            is_line_head = IS_TRUE;
            def_type = 2;
            def->init(def_type, def_name, def_vars);
            tdef = _define_hash.hash_value(def_name);
            if( tdef != NULL )
              _define_hash.hash_delete(def_name);
            _define_hash.hash_insert(def_name, def);
            def = NULL;
            def_name = "";
            def_type = 0;
            def_vars.clear();
            _cur_line++;
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            _cur_col = 0;
            break;

          default :
            def_type = 3;
            def->init(def_type, def_name, def_vars);
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            if (t == vpDEF_VAR) s = "`" + s;
            _toks.push_back(VPPtok(t, s, NONE, NONE));
            _cur_status = vpDEFINE_5;
            break;
        }
        break;

      case vpDEFINE_5:
        switch( t )
        {
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;

          case vtCOMM :
            break;

          case vtNL :
            is_line_head = IS_TRUE;
            re = def->parse(_toks);
            _toks.clear();
            if( re == OK )
            {
              tdef = _define_hash.hash_value(def_name);
              if( tdef != NULL )
                _define_hash.hash_delete(def_name);
              _define_hash.hash_insert(def_name, def);
            }
            else{
              if( def != NULL )
                delete def;
            }
            def = NULL;
            def_type = 0;
            def_name = "";
            def_vars.clear();
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            break;

          default :
            cpystring( _cur_s,  _cpos - _ppos , _ppos, s );
            if (t == vpDEF_VAR) s = "`" + s;
            _toks.push_back(VPPtok(t, s, NONE, NONE));
            break;
        }
        break;

      case vpDEF_ANTI_0:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtNL :
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;

          case vtLB :
            _cur_status = vpDEF_ANTI_2; break;

          default :
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_LEFT_BRA_NEDDED, other );
            _cur_status = vpSTART;
            break;
        }
        break;

      case vpDEF_ANTI_2:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtNL :
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;

          case vtIDENT :
          case vtDIGIT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            _toks.push_back(VPPtok(t, s, NONE, NONE));
            _cur_status = vpDEF_ANTI_3;
            break;

          default :
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_ID_EXPECTED, other );
            _cur_status = vpSTART;
            break;
        }
        break;

      case vpDEF_ANTI_3:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtNL :
          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;

          case vtLB :
            def_anti_depth++;
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            _toks.push_back(VPPtok(t, s, NONE, NONE));
            break;

          case vtRB :
            if( def_anti_depth > 0 ) {
              def_anti_depth--;
              cpystring( _cur_s, _cpos - _ppos , _ppos, s );
              _toks.push_back(VPPtok(t, s, NONE, NONE));
            } else {
              _output += def->get_result(_toks);
              _toks.clear();
              _cur_status = vpSTART;
            }
            break;

          case vtCOMMA :
            if( def_anti_depth > 0 ) {
              cpystring( _cur_s, _cpos - _ppos , _ppos, s );
              _toks.push_back(VPPtok(t, s, NONE, NONE));
            } else {
              _cur_status = vpDEF_ANTI_2;
            }
            break;

          /* tokens that can appear inside macro arguments (expressions) */
          case vtIDENT :
          case vtDIGIT :
          case vtUNKNOWN :
          case vtDOT :
          case vtADD :
          case vtSUB :
          case vtMOD :
          case vtQUES :
          case vtCOLON :
          case vtLBB :
          case vtRBB :
          case vpDEF_VAR :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            /* Check if this is a defined macro (strip leading '`') */
            if( s.size() > 1 && s[0] == '`' ) {
              String macro_name = s.substr(1);
              tdef = _define_hash.hash_value(macro_name);
              if( tdef != NULL && tdef->type() <= 1 ) {
                /* simple macro - expand directly */
                _output += tdef->get_result(_toks);
                break;
              } else if( tdef != NULL ) {
                /* parameterized macro - need '(' next */
                _toks.push_back(VPPtok(t, s, NONE, NONE));
                /* Continue collecting for nested param macro */
                break;
              }
            }
            _toks.push_back(VPPtok(t, s, NONE, NONE));
            break;

          default :
            _cur_status = vpSTART;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_DEF_UNEXPECTED_TOK, other );
            break;
        }
        break;

      case vpIFDEF_0:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;

          case vtNL :
            is_line_head = IS_TRUE;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_line++;
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            _cur_col = 0;
            break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            def = _define_hash.hash_value(s);
            if( def != NULL )  // match !
            { 
              append_line_info_tail(_cur_line);
              re = parse_recursivly( vpIF_SUCC, if_return );
              if( re != OK )
                _err->append_err(ERR_ERROR, _cur_line, _cur_col, re, other );
              else
              {
                if( if_return != vpAC_ENDIF )
                {
                  // find " `endif "
                  re = parse_recursivly( vpIF_SKIP, if_return );
                  if( re != OK )
                    _err->append_err(ERR_ERROR, _cur_line, _cur_col, re, other );
                  else
                  {
                    if( if_return != vpAC_ENDIF )
                      _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                       vPRE_ENDIF_MISSING, other );
                  }
                } // if if_return != vpAC_ENDIF
                _cur_status = vpSTART;
                append_line_info_tail(_cur_line);

              } // if parse_recursivly returns OK
            }  // if definition exists in define hash
            else // mismatch !!
            {
              re = parse_recursivly( vpIF_FAIL, if_return );
              if( re != OK )
              {
                _err->append_err(ERR_ERROR, _cur_line, _cur_col, re, other );
                _cur_status = vpSTART;
                append_line_info_tail(_cur_line);
              }
              else
              {
                switch( if_return )
                {
                  case vpAC_ELSIF :
                    _cur_status = vpIFDEF_0; break;

                  case vpAC_ELSE :
                    append_line_info_tail(_cur_line);
                    re = parse_recursivly( vpIF_SUCC, if_return );
                    if( re != OK )
                      _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                       re, other );
                    else
                    {
                      if( if_return != vpAC_ENDIF )
                        _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                         vPRE_ENDIF_MISSING, other );
                    }
                    _cur_status = vpSTART;
                    break;

                  case vpAC_ENDIF :
                    append_line_info_tail(_cur_line);
                    _cur_status = vpSTART;
                    break;

                  default:
                    break;
                }
              }
            } // parsing ifdef-fail situation
            break;

          default:
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_UNEXPECTED_TOK, other );
            _cur_status = vpSTART;
            break;
        }
        break;

      case vpIFNDEF_0:
        switch( t )
        {
          case vtWHITE :
            continue; break;

          case vtTRAN :
            is_line_head = IS_TRUE;
            _cur_col = 0;
            _cur_line++; break;

          case vtNL :
            is_line_head = IS_TRUE;
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_NL_NOT_EXPECTED, other );
            _cur_line++;
            _cur_col = 0;
            _cur_status = vpSTART;
            append_line_info_tail(_cur_line);
            break;

          case vtIDENT :
            cpystring( _cur_s, _cpos - _ppos , _ppos, s );
            def = _define_hash.hash_value(s);
            if( def == NULL )  // match !
            {
              append_line_info_tail(_cur_line);
              re = parse_recursivly( vpIF_SUCC, if_return );
              if( re != OK )
                _err->append_err(ERR_ERROR, _cur_line, _cur_col, re, other );
              else
              {
                if( if_return != vpAC_ENDIF )
                {
                  // find " `endif "
                  re = parse_recursivly( vpIF_SKIP, if_return );
                  if( re != OK )
                    _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                     re, other );
                  else
                  {
                    if( if_return != vpAC_ENDIF )
                      _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                       vPRE_ENDIF_MISSING, other );
                  }
                } // if if_return != vpAC_ENDIF
                _cur_status = vpSTART;
                append_line_info_tail(_cur_line);

              } // if parse_recursivly returns OK
            }  // if definition exists in define hash
            else
            {
              re = parse_recursivly( vpIF_FAIL, if_return );
              if( re != OK )
              {
                _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                 re, other );
                _cur_status = vpSTART;
                append_line_info_tail(_cur_line);
              }
              else
              {
                switch( if_return )
                {
                  case vpAC_ELSIF :
                    _cur_status = vpIFDEF_0; break;

                  case vpAC_ELSE :
                    append_line_info_tail(_cur_line);
                    re = parse_recursivly( vpIF_SUCC, if_return );
                    if( re != OK )
                      _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                       re, other );
                    else
                    {
                      if( if_return != vpAC_ENDIF )
                        _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                                         vPRE_ENDIF_MISSING, other );
                    }
                    _cur_status = vpSTART;
                    break;

                  case vpAC_ENDIF :
                    append_line_info_tail(_cur_line);
                    _cur_status = vpSTART;
                    break;

                  default:
                    break;
                }
              }
            } // parsing ifdef-fail situation
            break;

          default:
            _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                             vPRE_UNEXPECTED_TOK, other );
            _cur_status = vpSTART;
            break;
        }
        break;

      default:
        _err->append_err(ERR_ERROR, _cur_line, _cur_col,
                         vPRE_NOT_KNOWN_ERR, other );
        break;
    }
  }

  if( if_flag == vpNORMAL )
  {
    _output += '\n';
    if( _file_depth > 0 )
      append_include_tail(_cur_line);
    else
      _output += '\0';
    end_file();
  }
  else{
    _cur_status = _status.back();
    _status.pop_back();
    append_line_info_tail(_cur_line);
  }
  return OK;
}

int
VeriPreProc::get_next_tok( void )
{
  int status   = vtSTART;
  static String s = "";

  _ppos = _cpos;
  for( ; _cpos < _cur_length ; ++_cpos )
  {
    switch ( status )
    {
      case vtSTART:
        switch(_cur_s[_cpos])
        {
          case 0x00 :   // '\0'
            return NONE; _cur_col++; break;
          case 0x01 : case 0x02 : case 0x03 : case 0x04 : case 0x05 :
          case 0x06 : case 0x07 : case 0x08 :
            _cpos++; _cur_col++;    return vtUNKNOWN;        break;
          case 0x09 :   // tab 
            _cpos++; _cur_col++;   return vtWHITE;        break;
          case 0x0A :   // '\n'
            _cpos++; return vtNL;           break;
          case 0x0B : case 0x0C : // vt && ff
            _cpos++; _cur_col++;   return vtWHITE;          break;
          case 0x0D :   // '\r'
            if( _cur_s[_cpos + 1] == 0x0D )
            {
              _cpos += 2;
              return vtNL;
              break;
            }
            else
            {
              _cpos++;
              _cur_col++;
              return vtNL;
              break;
            }
          case 0x0E : case 0x0F : case 0x10 : case 0x11 : case 0x12 : case 0x13 :
          case 0x14 : case 0x15 : case 0x16 : case 0x17 : case 0x18 : case 0x19 :
          case 0x1A : case 0x1B : case 0x1C : case 0x1D : case 0x1E : case 0x1F :
            _cpos++; _cur_col++;   return vtUNKNOWN;        break;
          case 0x20 :    // ' '    
            _cpos++; _cur_col++;   return vtWHITE;        break;
          case 0x21 :    // '!'
            status = vtNEG_0;                  break;
          case 0x22 :    // '"'               
            _ppos  = _cpos;
            status = vtSTR_0;                  break;
          case 0x23 :    // '#'                
            _ppos  = _cpos;
            status = vtDELAY_0;                break;
          case 0x24 :    // '$'    
            status = vtIDENT_0;
            _cpos++; _cur_col++;   return vtUNKNOWN;        break;
          case 0x25 :    // '%'    
            _cpos++; _cur_col++;   return vtMOD;          break;
          case 0x26 :    // '&'                
            status = vtAND_0;                  break;
          case 0x27 :    // '''
            _ppos = _cpos;
            status = vtDIGIT_0;                break;
          case 0x28 :    // '('
            _cpos++; _cur_col++;   return vtLB;           break;
          case 0x29 :    // ')'
            _cpos++; _cur_col++;   return vtRB;           break;
          case 0x2A :    // '*'
            status = vtMUL_0;                  break;
          case 0x2B :    // '+'
            _cpos++; _cur_col++;   return vtADD;
          case 0x2C :    // ','
            _cpos++; _cur_col++;   return vtCOMMA;        break;
          case 0x2D :    // '-'
            _cpos++; _cur_col++;   return vtSUB;
          case 0x2E :    // '.'
            _cpos++; _cur_col++;   return vtDOT;          break;
          case 0x2F :    // '/'
            status = vtCOMM_0;                 break;
          case 0x30 : case 0x31 : case 0x32 : case 0x33 : case 0x34 :
          case 0x35 : case 0x36 : case 0x37 : case 0x38 : case 0x39 :  // 0-9
            status = vtDIGIT_0;                break;
          case 0x3A :    // ':'
            _cpos++; _cur_col++;   return vtCOLON;        break;
          case 0x3B :    // ';'
            _cpos++; _cur_col++;   return vtSEMI;         break;
          case 0x3C :    // '<'
            status = vtLESS_0;                 break;
          case 0x3D :    // '='
            status = vtEQ_0;                   break;
          case 0x3E :    // '>'
            status = vtGREAT_0;                break;
          case 0x3F :    // '?'
            _cpos++; _cur_col++;   return vtQUES;         break;
          case 0x40 :    // '@'
            _cpos++; _cur_col++;   return vtUNKNOWN;      break;
          case 0x41 : case 0x42 : case 0x43 : case 0x44 : case 0x45 : case 0x46 :
          case 0x47 : case 0x48 : case 0x49 : case 0x4A : case 0x4B : case 0x4C :
          case 0x4D : case 0x4E : case 0x4F : case 0x50 : case 0x51 : case 0x52 :
          case 0x53 : case 0x54 : case 0x55 : case 0x56 : case 0x57 : case 0x58 :
          case 0x59 : case 0x5A :      // A-Z
            _ppos = _cpos;
            status = vtIDENT_0;     break;
          case 0x5B :    // '['
            _cpos++; _cur_col++;   return vtUNKNOWN;
          case 0x5C :    // '\'
            _ppos = _cpos;
            status = vtANTI_0;                 break;
          case 0x5D :    // ']'
            _cpos++; _cur_col++;   return vtUNKNOWN;
          case 0x5E :    // '^'
            status = vtXOR_0;                  break;
          case 0x5F :    // '_'
            _ppos = _cpos;
            status = vtIDENT_0;                break;
          case 0x60 :    // '`'
            status = vtP_0;    break;
          case 0x61 : case 0x62 : case 0x63 : case 0x64 : case 0x65 : case 0x66 :
          case 0x67 : case 0x68 : case 0x69 : case 0x6A : case 0x6B : case 0x6C :
          case 0x6D : case 0x6E : case 0x6F : case 0x70 : case 0x71 : case 0x72 :
          case 0x73 : case 0x74 : case 0x75 : case 0x76 : case 0x77 : case 0x78 :
          case 0x79 : case 0x7A :   // a-z
            _ppos = _cpos;
            status = vtIDENT_0;          break;
          case 0x7B :    // '{'
            _cpos++; _cur_col++;   return vtLBB;    break;
          case 0x7C :    // '|'
            status = vtOR_0;             break;
          case 0x7D :    // '}'
            _cpos++; _cur_col++;   return vtRBB;    break;
          case 0x7E :    // '~'
            status = vtREV_0;            break;
          case 0x7F :    // DEL
            _cpos++; _cur_col++;   return vtUNKNOWN;  break;
          default :
            _cpos++; _cur_col++;   return vtUNKNOWN;  break;
        }
        break;

      case vtNEG_0:
        if( _cur_s[_cpos] == '=' )
          status = vtNEG_1;
        else
          return vtLOGIC_NEG;
        break;

      case vtNEG_1:
        if( _cur_s[_cpos] == '=' )
        {
          _cpos++;
          _cur_col++;
          return vtCASE_INEQ;
        }
        else
          return vtLOGIC_INEQ;
        break;

      case vtSTR_0:
        if( _cur_s[_cpos] == '\\' )
          status = vtSTR_1;
        else if( _cur_s[_cpos] == '\"' )
        {
          _cpos++;
          _cur_col++;
          return vtSTR;
        }
        else if( _cur_s[_cpos] == '\0' )
          return vtSTR_ERR;
        else
          continue;
        break;

      case vtSTR_1:
        status = vtSTR_0;
        break;

      case vtDELAY_0:
        if( isdigit(_cur_s[_cpos]) || _cur_s[_cpos] == '_' )
          continue;
        else
          return vtDELAY;
        break;

      case vtAND_0:
        if( _cur_s[_cpos] == '&' )
        {
          _cpos++;
          _cur_col++;
          return vtANDAND;
        }
        else
          return vtAND;
        break;

      case vtMUL_0  :
        if( _cur_s[_cpos] == '*' )
        {
          _cpos++;
          _cur_col++;
          return vtPOW;
        }
        else
          return vtMUL;
        break;

      case vtLESS_0 :
        if( _cur_s[_cpos] == '=' )
        {
          _cpos++;
          _cur_col++;
          return vtLE;
        }
        else if( _cur_s[_cpos] == '<' )
          status = vtLESS_1;
        else
          return vtLT;
        break;

      case vtLESS_1:
        if( _cur_s[_cpos] == '<' )
        {
          _cpos++;
          _cur_col++;
          return vtLOGIC_LS;
        }
        else
          return vtARITH_LS;
        break;
      
      case vtEQ_0   :
        if( _cur_s[_cpos] == '=' )
          status = vtEQ_1;
        else
          return vtASSIGN;
        break;

      case vtEQ_1 :
        if( _cur_s[_cpos] == '=' )
        {
          _cpos++;
          _cur_col++;
          return vtCASE_EQ;
        }
        else
          return vtLOGIC_EQ;
        break;
      
      case vtGREAT_0 :
        if( _cur_s[_cpos] == '=' )
        {
          _cpos++;
          _cur_col++;
          return vtGE;
        }
        else if( _cur_s[_cpos] == '>' )
          status = vtGREAT_1;
        else
          return vtGT;
        break;

      case vtGREAT_1:
        if( _cur_s[_cpos] == '>' )
        {
          _cpos++;
          _cur_col++;
          return vtLOGIC_RS;
        }
        else
          return vtARITH_RS;
        break;
      
      case vtIDENT_0:
        if(    _cur_s[_cpos] == '$'
            || _cur_s[_cpos] == '_'
            || isalpha(_cur_s[_cpos])
            || isdigit(_cur_s[_cpos])
          )
          continue;
        else
          return vtIDENT;
        break;

      case vtIDENT_1:
        if( isspace(_cur_s[_cpos]) )
          return vtIDENT;
        else
          continue;
        break;
      
      case vtANTI_0 :
        if( _cur_s[_cpos] == '\n' )
        {
          _cpos++;
          _cur_col++;
          return vtTRAN;
        }
        else if( _cur_s[_cpos] == '\0' )
          return vtUNKNOWN;
        else if( _cur_s[_cpos] == '\r' &&
                 _cur_s[_cpos+1] == '\n' )
        {
          _cpos += 2;
          return vtTRAN;
        }
        else
          status = vtIDENT_1;
        break;
      
      case vtXOR_0  :
        if( _cur_s[_cpos] == '~' )
        {
          _cpos++;
          _cur_col++;
          return vtXORN;
        }
        else
          return vtXOR;
        break;

      case vtOR_0 :
        if( _cur_s[_cpos] == '|' )
        {
          _cpos++;
          _cur_col++;
          return vtOROR;
        }
        else
          return vtOR;
        break;

      case vtREV_0:
        if( _cur_s[_cpos] == '^' )
        {
          _cpos++;
          _cur_col++;
          return vtXNOR_REDUC;
        }
        else if( _cur_s[_cpos] == '&' )
        {
          _cpos++;
          _cur_col++;
          return vtNAND_REDUC;
        }
        else if( _cur_s[_cpos] == '|' )
        {
          _cpos++;
          _cur_col++;
          return vtNOR_REDUC;
        }
        else
          return vtNEG_B;
        break;
      
      case vtDIGIT_0:
        if( isspace(_cur_s[_cpos]) || _cur_s[_cpos] == ',' ||
            _cur_s[_cpos] == ')' || _cur_s[_cpos] == ']' )
          return vtDIGIT;
        else
          continue;
        break;

      case vtCOMM_0:
        if( _cur_s[_cpos] == '*' )
          status = vtCOMM_1;
        else if( _cur_s[_cpos] == '/' )
          status = vtCOMM_3;
        else
          return vtUNKNOWN;
        break;

      case vtCOMM_1:
        if( _cur_s[_cpos] == '*' )
          status = vtCOMM_2;
        else if( _cur_s[_cpos] == '\n' )
        {
          _cur_line++;
          _cur_col = 0;
        }
        break; 

      case vtCOMM_2:
        if( _cur_s[_cpos] == '/' )
        {
          _cpos++;
          _cur_col++;
          return vtCOMM;
        }
        else if( _cur_s[_cpos] == '\n' )
        {
          _cur_line++;
          _cur_col = 0;
          status = vtCOMM_1;
        }
        else if( _cur_s[_cpos] == '\0' )
          return vtCOMM_ERR;
        else
          status = vtCOMM_1;
        break;

      case vtCOMM_3:
        if( _cur_s[_cpos] == '\\' )
          status = vtCOMM_4;
        else if( _cur_s[_cpos] == '\n' )
          return vtCOMM;
        else if( _cur_s[_cpos] == '\0' )
        {
          return vtCOMM; 
        }
        else
          continue;
        break;

      case vtCOMM_4:
        status = vtCOMM_3;
        break;

      case vtP_0    :
        if(    isspace(_cur_s[_cpos])
            && _cur_s[_cpos] != '\n'
            && _cur_s[_cpos] != '\r'
          )
          status = vtP_1;
        else if( _cur_s[_cpos] == '$'
              || _cur_s[_cpos] == '_'
              || isalpha(_cur_s[_cpos])
              || isdigit(_cur_s[_cpos])
          )
        {
          _ppos = _cpos;
          status = vtP_2;
        }
        else
          return vtUNKNOWN;
        break;

      case vtP_1:
        if(    isspace(_cur_s[_cpos])
            && _cur_s[_cpos] != '\n'
            && _cur_s[_cpos] != '\r'
          )
          continue;
        else if( _cur_s[_cpos] == '$'
              || _cur_s[_cpos] == '_'
              || isalpha(_cur_s[_cpos])
              || isdigit(_cur_s[_cpos])
          )
        {
          _ppos = _cpos;
          status = vtP_2;
        }
        else
          return vtIDENT;

      case vtP_2:
        if( _cur_s[_cpos] == '$'
         || _cur_s[_cpos] == '_'
         || isalpha(_cur_s[_cpos])
         || isdigit(_cur_s[_cpos])
          )
          continue;
        else
        {
           cpystring( _cur_s, _cpos - _ppos , _ppos, s );
           return in_word_set( &_cur_s[_ppos] , _cpos - _ppos );
        }
        break;

      default:
#ifdef DEBUG_VERI_PROPROC_
        cout << " what is this status in pre_parse ?? : " << status << endl;
#else
        return vtUNKNOWN;
#endif
        break;
    }
  }
  return vtUNKNOWN;
}

int
VeriPreProc::in_word_set (register const char *str, register Uint len)
{
  Uint i;
  for( i = 0 ; i < len ; ++i )
  {
    if( isalpha( str[i] ) )
      break;
  }

  len = len - i;
  str = &str[i];

  if (len <= _max_word_length && len >= _min_word_length)
  {
    register int key = perfect_hash (str, len);
    
    if (key >= _min_hash_value && key <= _max_hash_value )
    {
      register const char *s = _word_list[key].c_str();
      if (*str == *s && !strncmp (str + 1, s + 1, len - 1))
      {
        switch(key)
        {
          case  5 : return vpUNDEF;
          case  7 : return vpINCLUDE;
          case  9 : return vpLINE;
          case 10 : return vpENDIF;
          case 13 : return vpRESET_ALL;
          case 14 : return vpELSE;
          case 15 : return vpELIF;
          case 16 : return vpDEFINE;
          case 17 : return vpUNCONN_DRIVE;
          case 18 : return vpEND_CELL_DEF;
          case 19 : return vpTIMESCALE;
          case 20 : return vpIFDEF;
          case 21 : return vpIFNDEF;
          case 24 : return vpNON_CONN_DRIVE;
          case 25 : return vpDEFAULT_NETTYPE;
          case 30 : return vpCELL_DEF;

          default : return vpDEF_VAR;    break;
        }
      }
      else
        return vpDEF_VAR;
    }
  }
  return vpDEF_VAR;
}

void
VeriPreProc::end_file( void )
{
  _fname.pop_back();
  _file_st.pop_back();
  _err->exclude_file();

  delete[] _input.back();
  _input.back() = NULL;
  _input.pop_back();
  _toks.clear();
  _status.pop_back();
  _linenos.pop_back();
  _cur_pos.pop_back();
  _pre_pos.pop_back();

  _file_depth--;
}

void
VeriPreProc::save_context( void )
{
  _status.push_back(_cur_status);
  _fname.push_back(_cur_name);
  _file_st.push_back(_cur_st);
  _input.push_back(_cur_s);
  _linenos.push_back(_cur_line);
  _cur_pos.push_back(_cpos);
  _pre_pos.push_back(_ppos);
  _toks.clear();
}

void
VeriPreProc::change_context( void )
{
  _status.back()  = _cur_status;
  _file_st.back() = _cur_st;
  _linenos.back() = _cur_line;
  _cur_pos.back() = _cpos;
  _pre_pos.back() = _ppos;
}

void
VeriPreProc::get_context( void )
{
  _cur_status = _status.back();
  _cur_name   = _fname.back();
  _cur_st     = _file_st.back();

  if(!_input.empty())
    _cur_s      = _input.back();
  else
    _cur_s      = NULL;

  _cur_length = _cur_st.st_size;
  _cur_line   = _linenos.back();
  _cpos       = _cur_pos.back();
  _ppos       = _pre_pos.back();

  _err->back_to_file( _cur_line );
}

int
VeriPreProc::after_parse( void )
{
  int  start = 0;
  int  end   = 0;
  int  final = _output.size();
  int  last_line = IS_FALSE;

  String last = "";
  String tmp  = _output;
  _output = "";

  while( 1 )
  {
    end = cnt_one_line( tmp, start );
    if( end >= final && end <= start )
      break;

    if( tmp.substr( start, 5 ) == "`line" )
    {
      if( last_line == IS_FALSE )
        _output.append( last );
      else if( last_line == IS_TRUE && last[last.size()-2] == '2' )
        _output.append( last );

      last_line = IS_TRUE;
    }
    else
    {
      _output.append( last );
      last_line = IS_FALSE;
    }
    
    last = tmp.substr( start, end - start + 1 );
    start = end + 1;
  }

  _output.append( last );
  return OK;
}

int
VeriPreProc::cnt_one_line( CString& content, int start )
{
  Uint i;
  for( i = start; i < content.size(); ++i )
    if( content[i] == '\n' )
      return i;
  return i;
}

};
