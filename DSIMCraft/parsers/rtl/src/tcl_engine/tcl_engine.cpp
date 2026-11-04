/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : tcl_engine.cpp
 * Summary  : tcl command line engine class functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#include <dirent.h>
#include <stddef.h>
#include <unistd.h>
#ifdef _WIN32
#include <windows.h>
#endif

#include <cstdlib>
#include <cstring>
#include <iostream>

#include "general_err.hpp"
#include "tcl_engine.hpp"
#include "external_commands.hpp"

namespace p_tcl_engine
{

#define debug_tcl_engine_

#ifdef debug_tcl_engine_
#include <iostream>
  using std::cout;
  using std::endl;
#endif // debug_tcl_engine_

TclEngine::~TclEngine()
{
	if(_interp != NULL)
    Tcl_DeleteInterp(_interp);
  _interp = NULL;
}

TclEngine::TclEngine() :
	_interp(NULL),
  // output config
	_line_width(80),
	_min_char_tab(2),
  _cmd_name_max_width(0),
  _cmd_var_max_width(0),
  _cmd_comment_max_width(0),
  _hide_file(IS_TRUE),
  // history part
  _cmd_shift(0),
  _cmd_index(0),
	_num_history(50),
	_cmds(NULL),
  // script handler
  _script_name( "" ),
  _LINE( 0 )
{
};

std::string
TclEngine::init( void )
{
  _interp = Tcl_CreateInterp();

  _cmds = new String[_num_history];

  for( int i = 0; i < _num_history; i++ )
  {
  	_cmds[i] = "";
  }

  _cmd_slib.reserve( 100 );

  register_commands();
  init_command_lib();
  Tcl_EvalEx( _interp, "p_init_5138", strlen("p_init_5138"), TCL_EVAL_DIRECT );
  String re = Tcl_GetStringResult(_interp);
  Tcl_FreeResult( _interp );
  return re;
}

std::string
TclEngine::eval(CString& expr)
{
  String re;   
  if( expr == "exit"  )
  {
    register_history( expr );
    del_reg_cmd( );
    Tcl_Finalize( );
    clear();
    return expr;
  }
  else if( expr == "clear" )
  {
    register_history( expr );
    return expr;
  }
  else
  {
    Tcl_EvalEx(_interp, expr.c_str(), expr.size(), TCL_EVAL_DIRECT );
    re = Tcl_GetStringResult(_interp);
    Tcl_FreeResult( _interp );
    register_history(expr);
    return re;
  }
}

void
TclEngine::clear( void )
{
  if( _interp != NULL )
    Tcl_DeleteInterp( _interp );
  _interp = NULL;
  delete[] _cmds;
}

std::string
TclEngine::eval_file(const char* fname)
{
  String re;   
  String expr = "run ";
  expr.append(fname);
  register_history( expr );

  Tcl_EvalFile(_interp, fname);
  re = Tcl_GetStringResult( _interp );
  return re;
}

const std::string&
TclEngine::get_expr( int dir ) const
{
  switch( dir )
  {
    case pTCL_UP   : return get_last_expr();
    case pTCL_DOWN : return get_next_expr();
    default: return _cmds[0];
  }
} 

std::string
TclEngine::match(CString& in) const
{
  CmdLib::const_iterator i;
  int max_ratio = 0;
  int max_ratio_2 = 0;
  String max_string;
  String max_string_2;
  int ratio = 0;
  for( i = _cmd_lib.begin(); i != _cmd_lib.end(); ++i )
  {
    if( i->second._name.find(in) < i->second._name.length() )
    {
      ratio = cal_match_ratio( in.c_str(), in.length(),
                               i->second._name.c_str(), i->second._name.length() );
      if( ratio >= max_ratio )
      {
        max_ratio_2 = max_ratio;
        max_ratio = ratio;
        max_string_2 = max_string;
        max_string = i->second._name;
      }
      else if( ratio >= max_ratio_2 )
      {
        max_ratio_2 = ratio;
        max_string_2 = i->second._name;
      }
    }
	}

	if( max_ratio == max_ratio_2 && max_ratio > 0 )
  {
    ratio = cal_match_ratio( max_string.c_str(), max_string.length(),
                             max_string_2.c_str(), max_string_2.length() );
    return max_string.substr(0,ratio);
	}
	else if( max_ratio == max_ratio_2 )
    return max_string;
	else
    return max_string;
}              	
               	
void
TclEngine::multi_match(CString& in, SVector& ret ) const
{
	CmdLib::const_iterator i;
	SVector retname;
	SVector retvar;
	SVector retcomment;
	SVector::iterator i1,i2,i3;
	int max_width1, max_width2, max_width3;
	int num = 0;

	for( i = _cmd_lib.begin(); i != _cmd_lib.end(); ++i )
  {
    if(i->second._name.find(in) < i->second._name.length())
    {
      retname.insert(retname.end(),i->second._name);
      retvar.insert(retvar.end(),i->second._var);
      retcomment.insert(retcomment.end(),i->second._comment);
      num++;
    }
	}

	if(num != 0)
  {
    ret.insert(ret.end(), convert(num));
    max_width1 = get_largest_width(retname)    + _min_char_tab;
    max_width2 = get_largest_width(retvar)     + _min_char_tab;
    max_width3 = get_largest_width(retcomment) + _min_char_tab;

    norm_svector( max_width1, retname );
    norm_svector( max_width2, retvar );
    norm_svector( max_width3, retcomment );
    
    i1 = retname.begin();
    i2 = retvar.begin();
    i3 = retcomment.begin();
    for( ; i1 != retname.end(); i1++, i2++, i3++ )
    {
      i1->append(*i2);
      i1->append(*i3);
      ret.insert(ret.end(),*i1);
    }
	}
	else
    ret.insert(ret.end(), "0");
};

int
TclEngine::cal_match_ratio( const char* in, int length1,
                            const char* pattern, int length2 ) const
{
	int ratio = 0;
	int step = 0;
	int mini = length1 < length2 ? length1 : length2;
	if( mini < 0 )
    return 0;
	for( step = 0; step < mini; step++  )
  {
    if( in[step] == pattern[step] )
      ratio++;
    else
      break;
	}
	return ratio;
}

std::string
TclEngine::get_history() const
{
  String re;
	int i;
	if( _cmd_index > 0 ) {
    if(_cmd_index < _num_history - 1 && _cmds[_cmd_index+1] == "") {
      for( i = 0; i < _cmd_index; i++ )
      {
        re.append(_cmds[i]);
        re.append("\n");
      }
    }
    else{
      for( i = _cmd_index+1; i % _num_history != _cmd_index; i++)
      {
        re.append(_cmds[i % _num_history]);
        re.append("\n");
      }
    }
	}
  return re;
}

std::string&
TclEngine::get_last_expr() const
{
	_cmd_shift--;
	int ac_shift = cmd_history_idx_adjust(_cmd_shift + _num_history, _num_history);

	if(    _cmds[(_cmd_index + ac_shift)%_num_history] == ""
      || _cmd_shift < -(_num_history) +1)
    return _cmds[(++_cmd_index + ac_shift)% _num_history];

	return _cmds[(_cmd_index + ac_shift)% _num_history];
}

std::string&
TclEngine::get_next_expr() const
{
	_cmd_shift++;
	int ac_shift = cmd_history_idx_adjust(_cmd_shift +  _num_history, _num_history);

	if(    _cmds[(_cmd_index + ac_shift)% _num_history] == ""
      || _cmd_shift >  _num_history -1)
    return _cmds[(--_cmd_shift + ac_shift)% _num_history];

	return _cmds[(_cmd_index + ac_shift)% _num_history];
}

void
TclEngine::register_history( CString& expr )
{
	_cmds[_cmd_index] = expr;
	_cmd_index = (_cmd_index + 1) % _num_history;
	_cmd_shift = 0;
}

void
TclEngine::register_commands() {
#define pTCLREG( name, func ) Tcl_CreateObjCommand(_interp,\
                                                   #name, func, \
                                                   (ClientData) NULL, \
                                                   (Tcl_CmdDeleteProc *) NULL )

  pTCLREG( help,        p_help_func );
  pTCLREG( ls,          p_ls        );
  pTCLREG( l,           p_ls        );
  pTCLREG( list_func,   p_list_func );
	pTCLREG( run,         p_run       );
  pTCLREG( history,     p_history   );
  pTCLREG( read_veri,   p_read_veri );

  pTCLREG( p_init_5138, p_init_5138_func );

#undef pTCLREG
}

void
TclEngine::del_reg_cmd()
{
  Tcl_DeleteCommand( _interp, "help" );
  Tcl_DeleteCommand( _interp, "ls" );
  Tcl_DeleteCommand( _interp, "l" );
  Tcl_DeleteCommand( _interp, "list_func" );
  Tcl_DeleteCommand( _interp, "run" );
  Tcl_DeleteCommand( _interp, "history" );
  Tcl_DeleteCommand( _interp, "read_veri" );
  Tcl_DeleteCommand( _interp, "p_init_5138" );
}

void
TclEngine::init_command_lib()
{
  add_reg_cmd("help"      , 0, 0,  "",
                 "help information" );
  add_reg_cmd("run"       , 1, 1,  "filename",
                 "run a script_file");
  add_reg_cmd("ls"        , 0, 0,  "",
                 "emulate bash basic ls");
  add_reg_cmd("list_func" , 0, 1,  "TRUE/FALSE",
                 "list functions, in completion mode or not");
  add_reg_cmd("history"	  , 0, 0,  "",
                 "list all the commands you have typed");
  add_reg_cmd("read_veri" , 2, 2,  "verilog src file",
                 "read, syntax-analyze verilog source file");
  add_reg_cmd("exit"      , 0, 0,  "",
                 "exit the program");
}

void
TclEngine::add_reg_cmd( CString& name, int min_var, int max_var,
                        CString& var, CString& comment )
{
  // update output config
  if( name.size() > _cmd_name_max_width )
    _cmd_name_max_width = name.size();
  if( var.size() > _cmd_var_max_width )
    _cmd_var_max_width = var.size();
  if( comment.size() > _cmd_comment_max_width )
    _cmd_comment_max_width = comment.size();

  // insert complete command
  _cmd_lib.insert( CmdLib::value_type( name,
                                       CmdRec(name,
                                              min_var,
                                              max_var,
                                              var,
                                              comment)
                                     )
                 );

  // insert name
  _cmd_slib.push_back( name );
}

void
TclEngine::append_err_msg( int err, String& ret, int other ) const
{
  switch( err )
  {
    case pTCL_WRONG_ARGUMENT:
      ret.append( "Wrong # of arguments" ); break;
    case pTCL_WRONG_ARGUMENT_TYPE:
      ret = ret + "type of argument:" +  convert(other) + " is wrong"; break;
    case pTCL_OP_ERROR:
      ret.append( "Function variable type error"); break;
    case pTCL_OP_UNKNOWN_ERROR:
      ret.append( "Function variable unrecognizable"); break;
    case pTCL_DIV_0_ERROR:
      ret.append( "Warning : Divided by zero"); break;

    default :
      break;
  }
}

std::string
TclEngine::cmd_list( int is_complete ) const
{
  String res = "";
/*
  Uint comment_used =   _cmd_name_max_width + _cmd_var_max_width
                      + 2*_min_char_tab + 5;
  Uint comment_left = _line_width - comment_left;
*/
  if( is_complete == IS_TRUE )
  {

    res = res + append_white( _cmd_name_max_width + _min_char_tab, "  name");
    res = res + "  var  ";
    res = res + append_white( _cmd_var_max_width + _min_char_tab, "var_type");
    res = res + "comment\n";

    CmdLib::const_iterator it = _cmd_lib.begin();
    for( ; it != _cmd_lib.end(); ++it )
    {
      const CmdRec& rec = it->second;
      res = res + append_white( _cmd_name_max_width + _min_char_tab, rec._name );
      res = res + append_white( 2, convert(rec._min_var));
      res = res + "-";
      res = res + append_white( 3, convert(rec._max_var));
      res = res + append_white( _cmd_var_max_width + _min_char_tab, rec._var );
      res = res + rec._comment + "\n";
    }
  }
  else
    organize_output( _cmd_slib, res );
  return res;
}

std::string
TclEngine::posix_ls( CString& dname ) const
{
  String res = "";

#ifdef _WIN32
  SVector fnames;
  std::string pattern = std::string(dname.c_str());
  if (!pattern.empty() && pattern.back() != '/' && pattern.back() != '\\')
    pattern += '\\';
  pattern += "*";
  WIN32_FIND_DATAA data{};
  HANDLE handle = FindFirstFileA(pattern.c_str(), &data);
  if (handle == INVALID_HANDLE_VALUE) {
    get_detail(res, "ls", pTCL_DIR_OPEN);
    return res;
  }
  do {
    const char* name = data.cFileName;
    if (std::strcmp(name, ".") == 0 || std::strcmp(name, "..") == 0)
      continue;
    if (name[0] == '.' && _hide_file == IS_TRUE)
      continue;
    fnames.push_back((data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
                         ? String(name) + "/" : String(name));
  } while (FindNextFileA(handle, &data));
  FindClose(handle);
  organize_output(fnames, res);
  return res;
#else

  typedef struct dirent Dirent;
  DIR    *dp    = opendir( dname.c_str() );
  Dirent *dir   = NULL;
  Dirent *entry = NULL;
  int     dir_ret = 0;
  SVector fnames;

  if( dp == NULL )
  {
    get_detail( res, "ls", pTCL_DIR_OPEN );
  }
  
  int dir_offset = offsetof(Dirent, d_name) + pathconf("./", _PC_NAME_MAX) + 1;
  entry = (Dirent*)malloc(dir_offset); // allocate entry
  while( 1 )
  {
    // readdir_r return 0 on success
    //           return EBADF on failure
    //           return 0 and dir == NULL on end of directory
    dir_ret = readdir_r( dp, entry, &dir );
    if( dir_ret != 0 || dir == NULL )
      break;
#ifdef debug_tcl_engine_posix_ls_
    cout << dir << " " << dir->d_name << endl;
#endif // debug_tcl_engine_
    if(    strcmp(dir->d_name, "."  ) == 0
        || strcmp(dir->d_name, ".." ) == 0 )
      continue;
    if( dir->d_name[0] == '.' && _hide_file == IS_TRUE )
      continue;
    else
    {
      if( dir->d_type == DT_DIR )
        fnames.push_back( String(dir->d_name) + "/" );
      else
        fnames.push_back( dir->d_name );
    }
  }
  free(entry);
#ifdef debug_tcl_engine_posix_ls_
  cout << " fnames collection completed... " << endl;
#endif // debug_tcl_engine_
  organize_output( fnames, res );
  return res;
#endif
}

unsigned int
TclEngine::get_num_of_line( int min_width, int max_width ) const
{
  unsigned int re = static_cast<unsigned int>
                      (static_cast<float>(max_width) / min_width);
  if( re == 0 )
    re = 1;
  return re;
}

std::string
TclEngine::erase_white(CString& in) const
{
  String temp;
  for( unsigned int i = 0; i < in.length(); i++ )
  {
    if(in.c_str()[i] != ' ')
      temp += in.c_str()[i];
  }
  return temp;
}

int
TclEngine::is_double( CString& in ) const
{
  String s = erase_white(in);
  unsigned int isdot = 0;
  unsigned int ise   = 0;
  for( unsigned int i = 0; i < s.length(); i++ )
  {
    if( !isdigit(s.c_str()[i]) \
        && s.c_str()[i] != '+' \
        && s.c_str()[i] != 'e' \
        && s.c_str()[i] != 'E' \
        && s.c_str()[i] != '-' \
        && s.c_str()[i] != '.' )
      return IS_FALSE;
    if( s.c_str()[i] == '.' )
      isdot++;
    if( s.c_str()[i] == 'e' || s.c_str()[i] == 'E' )
      ise++;
    if( isdot > 1 || ise > 1)      // dot and e can only have once
      return IS_FALSE;
  }
  return IS_TRUE;
}

int
TclEngine::is_complex( CString& in, float& out1, float& out2 ) const
{
  String s = erase_white(in);
  int pos;
  if(    ((pos = s.find("i",0)) == s.length() - 1)
      || ((pos = s.find("I",0)) == s.length() - 1) ) // has i
  {
    s.erase(pos,1);
    if( (pos = s.find("+",0)) != String::npos ) // has '+'
    {
      if(    is_double(s.substr(0, pos))
          && is_double(s.substr(pos+1, s.length()-pos-1)) ) // is real number
      {
        out1 = convert(s.substr(0,pos));
        out2 = convert(s.substr(pos+1,s.length()-pos-1));
        return IS_TRUE;
      }
      return IS_FALSE;
    }
    else if( (pos = s.find("-",0)) != String::npos ) // has '-'
    {
      if(    is_double(s.substr(0,pos))
          && is_double(s.substr(pos+1,s.length()-pos-1)) ) // is real number
      {
        out1 = convert(s.substr(0,pos));
        out2 = convert(s.substr(pos+1,s.length()-pos-1));
        return IS_TRUE;
      }
      return IS_FALSE;
    }
    else  // has i but no + nor -
    {
      if( is_double(s) )
      {
        out2 = convert(s);
        return IS_TRUE;
      }
    }
    return IS_FALSE;
  }
  return IS_FALSE;
}

void
TclEngine::organize_output( CString* in, int len, String& out ) const
{
  int max_width   = get_largest_width(in, len) + _min_char_tab;
  int num_of_line = get_num_of_line( max_width, _line_width );
  norm_string( in, len, num_of_line, max_width, out);
}

void
TclEngine::organize_output( const SVector& in, String& out ) const
{
  int max_width   = get_largest_width(in) + _min_char_tab;
  int num_of_line = get_num_of_line(max_width, _line_width);
  norm_string( in, num_of_line, max_width, out );
}

unsigned int
TclEngine::get_largest_width( const SVector& ori ) const
{
  SVector::const_iterator i;
  unsigned int max_width = 0;
  for( i = ori.begin(); i != ori.end(); ++i) {
    if(max_width <= i->length())
      max_width = i->length();
  }
  return max_width;
}

unsigned int
TclEngine::get_largest_width( CString* in, int num ) const
{
  unsigned int max_width = 0;
  for( int i = 0; i < num; i++ )
  {
    if( max_width < in[i].length() )
      max_width = in[i].length();
  }
  return max_width;
}

std::string
TclEngine::append_white( Uint max_length, CString& in ) const
{
  String out = in;
  for( Uint i = 0; i < max_length - in.size(); ++i )
    out.append(" ");
  return out;
}

void
TclEngine::norm_string( const SVector& in, Uint num_of_line, Uint max_width,
                        String& out ) const
{
  int i, j;
  SVector::const_iterator ires;
  String temp;

  out = "";
  for(i = 1, ires = in.begin(); ires != in.end(); ++ires, i++ )
  {
    out.append(*ires);
    if( i % num_of_line )
    {
      temp = "";
      for(j = 0; j < ( max_width - ires->length()); j++)
        temp.append(" ");
      out.append(temp);
    }
    else
      out.append("\n");
  }
}

void
TclEngine::norm_string( CString* in, Uint len, Uint num_of_line,
                        Uint max_width, String& out) const
{
  Uint i, j, k;
  String temp;

  out = "";
  for(i = 0, j = 0, k = 0; i < len; i++)
  {
    if( in[i] != "" )
    {
      out.append(in[i]);
      if( (++j) % num_of_line )
      {
        temp = "";
        for( k = 0; k < ( max_width - in[i].length()); k++ )
          temp.append(" ");
        out.append(temp);
      }
      else
        out.append("\n");
    }
  }
}

void
TclEngine::norm_svector( Uint max_width, SVector& in ) const
{
  SVector::iterator i;
  String temp = "";
  unsigned int j;
  for( i = in.begin(); i != in.end(); ++i )
  {
    temp = "";
    for( j = 0; j < max_width - i->length(); j++)
      temp.append(" ");
    i->append(temp);
  }
}

int
TclEngine::cmd_history_idx_adjust(int n, int num) const
{
 while( n > num )
   n -= num;
 while( n < 0 )
   n += num;
 return n;
}

};
