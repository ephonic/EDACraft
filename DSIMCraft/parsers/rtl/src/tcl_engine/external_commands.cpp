
/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : external_commands.cpp
 * Summary  : tcl command line commands
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */


#include "tcl_token.hpp"
#include "tcl_engine.hpp"
#include "external_commands.hpp"

#include "src_mgr.hpp"
#include "veri_preproc.hpp"
#include "veri_parser.hpp"

namespace p_tcl_engine
{

static TclEngine *TclCmd = NULL;
typedef std::string String;

#define pTCL_FUNC( name ) \
  int name( ClientData /*client_data*/, Tcl_Interp* interp,\
            int objc, Tcl_Obj* CONST objv[])

pTCL_FUNC( p_init_5138_func )
{
  Tcl_Obj* ore = NULL;
  String   res = "";

  TclCmd = TclEngine::get_instance();
  if( objc != 1 ) 
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }
  
  res  = "  command \"help\" will give you simple guidence\n";
  res += "  command \"list_func\" will list all synthesis-oriented functions\n";
  res += "supported\n";
  ore = Tcl_NewStringObj(res.c_str(), res.length());
  Tcl_SetObjResult(interp, ore);
  return TCL_OK;
}

pTCL_FUNC( p_history )
{
  Tcl_Obj* ore = NULL;
  String   res = "";

  if(    objc < TclCmd->min_func_var("history")
      || objc > TclCmd->max_func_var("history") )
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }

  res = TclCmd->get_history();
  ore = Tcl_NewStringObj(res.c_str(), res.length());
  Tcl_SetObjResult(interp, ore);
  return TCL_OK;
}

pTCL_FUNC( p_help_func )
{
  Tcl_Obj* ore = NULL;
  String   res = "";

  if(    objc < TclCmd->min_func_var("help")
      || objc > TclCmd->max_func_var("help") )
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }

  res  = "    This TCL Engine can read .tcl scripts in batch mode, or\n";
  res += "communicate with user in console mode. All Tcl original functions\n";
  res += "are supported, and several synthesis-tool-oriented functions are\n";
  res += "supported as well. All added functions could be reached by\n";
  res += "list_func command.\n";
  ore = Tcl_NewStringObj(res.c_str(), res.length());
  Tcl_SetObjResult(interp, ore);
  return TCL_OK;
}

pTCL_FUNC( p_list_func )
{
  Tcl_Obj* ore = NULL;
  String   res = "";

  if(    objc < TclCmd->min_func_var("list_func")
      || objc > TclCmd->max_func_var("list_func") )
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }

  if( objc > TclCmd->min_func_var("list_func") )
  {
    if( strcmp(Tcl_GetString(objv[1]), "TRUE") == 0 )
      res = TclCmd->cmd_list( IS_TRUE );
    else if( strcmp(Tcl_GetString(objv[1]), "FALSE") == 0 )
      res = TclCmd->cmd_list( IS_FALSE );
    else
      TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT_TYPE);
  }
  else
    res = TclCmd->cmd_list( IS_FALSE );

  ore = Tcl_NewStringObj(res.c_str(), res.length());
  Tcl_SetObjResult(interp, ore);
  return TCL_OK;
}

pTCL_FUNC( p_ls )
{
  Tcl_Obj* ore = NULL;
  String   res = "";

  if(    objc < TclCmd->min_func_var("ls")
      || objc > TclCmd->max_func_var("ls") )
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }

  String dir;
  if( objc > TclCmd->min_func_var("ls") )
    dir = Tcl_GetString( objv[1] );
  else
    dir = ".";
  res = TclCmd->posix_ls( dir );
  ore = Tcl_NewStringObj(res.c_str(), res.length());
  Tcl_SetObjResult(interp, ore);
  return TCL_OK;

}


pTCL_FUNC( p_run )
{
  String    res = "";
  Tcl_Obj*  ore = NULL;

  if(    objc < TclCmd->min_func_var("run")
      || objc > TclCmd->max_func_var("run") )
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }

  TclCmd->set_script_name(Tcl_GetString(objv[1]));
  res = TclCmd->eval_file(Tcl_GetString(objv[1]));
  ore = Tcl_NewStringObj(res.c_str(),res.length());
  Tcl_SetObjResult(interp,ore);
  return TCL_OK;
}

#include <iostream>

pTCL_FUNC( p_read_veri )
{
  using rtl::Src_mgr;
  using rtl::VeriPreProc;
  using rtl::VeriParser;

  String   res = "";
  Tcl_Obj *ore = NULL;
  int      ret = OK;

  if(    objc < TclCmd->min_func_var("read_veri")
      || objc > TclCmd->max_func_var("read_veri") )
  {
    TclCmd->get_detail(res,Tcl_GetString(objv[0]),pTCL_WRONG_ARGUMENT);
    ore = Tcl_NewStringObj(res.c_str(), res.length());
    Tcl_SetObjResult(interp, ore);
    return TCL_ERROR;
  }

  do
  {
    res.append("\n");
    VeriPreProc *vpreproc = VeriPreProc::get_instance();
    ret = vpreproc->init(Tcl_GetString(objv[1]));
    if( ret != OK )
    {
      res.append("verilog pre-processer initialzation error\n");
      break;
    }
    ret = vpreproc->parse();
    if( ret != OK )
    {
      res.append("verilog pre-processer parsing error\n");
      break;
    }
    else
      res.append("verilog pre-processer parsing ok\n");

    Src_mgr *src_mgr = Src_mgr::get_instance();
    std::cout << src_mgr->src() << std::endl;
    std::cout << " src preparser dump finished. " << std::endl;
    VeriParser *vparser = VeriParser::get_instance();
    ret = vparser->init();
    if( ret != OK )
    {
      res.append("verilog syntax parser initialzation error\n");
      break;
    }
    else
      res.append("verilog syntax parser initialzation finished\n");

    ret = vparser->parse();
    if( ret != OK )
    {
      res.append("verilog syntax parser parsing error\n");
      break;
    }
    else
      res.append("verilog syntax parser parsing finished\n");
    vparser->dump_ast( Tcl_GetString(objv[2]) );

  }while(0);

  if( ret == OK )
    res.append("parsing ok");
  
  ore = Tcl_NewStringObj(res.c_str(), res.length());
  Tcl_SetObjResult(interp, ore);
  return TCL_ERROR;
}

#undef pTCL_FUNC

};
