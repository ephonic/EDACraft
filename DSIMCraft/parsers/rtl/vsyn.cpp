/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : main.hpp
 * Summary  : main function
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include <iostream>

#include "general_err.hpp"
#include "tcl_engine.hpp"
#include "src_mgr.hpp"
#include "verilog_token.hpp"
#include "veri_err.hpp"
#include "veri_preproc.hpp"
#include "veri_parser.hpp"
#include "veri_module.hpp"
#include "veri_mod_container.hpp"
#include "veri_node.hpp"
#include "veri_stmt.hpp"
#include "veri_decl.hpp"
#include "veri_exp.hpp"
#include "veri_inst.hpp"

#include <dirent.h>
#include <sys/types.h>

int
main( int argc, char **argv )
{
  typedef std::string  String;
  using std::cout;
  using std::cin;
  using std::endl;
  using rtl::OK;
  using rtl::IS_TRUE;

//  cout << "  ------------------------------------" << endl;
  cout << "  Welcome to FDU verilog synthesis 0.1" << endl;
  cout << "  " << endl;

  using p_tcl_engine::TclEngine;
  using rtl::Src_mgr;
  using rtl::VeriPreProc;
  using rtl::VeriParser;
  using rtl::VeriErr;

/*
  String cache;
  TclEngine *tcl_engine = TclEngine::get_instance();
  cache = tcl_engine->init();
  cout << cache << endl;
  while(1)
  {
    cout << "vsyn $: ";
    getline(cin, cache);
    cache = tcl_engine->eval( cache );
    if( cache == "exit" )
      break;
    cout << cache << endl;
  }
*/

  if( argc != 2 )
  {
    cout << " Wrong # of arguments " << endl;
    return 0;
  }

//  Src_mgr     *smgr     = Src_mgr::get_instance();
  VeriErr     *verr     = VeriErr::get_instance();
  VeriPreProc *vpreproc = VeriPreProc::get_instance();
  VeriParser  *vparser  = VeriParser::get_instance();

//  String in_dir  = "./testcases/test_preproc/";
  String in_dir  = "./testcases/first_100/";
  String out_dir = "./testcases/test_output/";
  String fname   = argv[1];

  vpreproc->append_quote_dir( in_dir );

  cout << " processing file : " << in_dir + fname << endl;

  int ret;
  ret = vpreproc->init( in_dir + fname );
  if( ret != OK )
  {
    cout << " file not cached correctly " << endl;
    return 0;
  }
  ret = vpreproc->parse();
  if( ret != OK )
  {
    cout << " preprocessor parsed error " << endl;
    cout << verr->get_err_info( ) << endl;
    return 0;
  }
  else
    cout << " preprocessor parsed ok " << endl;

  // process
  ret = vparser->init();
  ret = vparser->parse();

  cout << vparser->get_err_info( );

  if( vparser->has_err( ) != IS_TRUE ) {
    vparser->dump_ast( out_dir );

    /** 
      foreach all modules
    **/
    cout << "ALL MODULES:" << endl;
    FOREACH_ALL_MODULES(mod, vparser) {
      cout << "module name:" << mod->name() << endl;
      // Your code here
    }

    rtl::VeriMod *mod = vparser->module(vparser->get_top_module());
    cout << endl << "top module name:" << mod->name() << endl;

    /**
      foreach all ports of top module 
    **/
    cout << endl << "PORTS OF TOP MODULE:" << endl;
    FOREACH_PORTS_OF_MODULE(it, mod) {
      rtl::VeriVar* var = (rtl::VeriVar*)(((rtl::VeriPrimaryExp*)it)->var());
      cout << var->name() << "[" << var->dstart() << ":" << var->dend() << "]" << endl;
      // Your code here
    }

    /**
      foreach all instantiations of top module 
    **/
    cout << endl << "INSTS OF TOP MODULE:" << endl;
    FOREACH_INSTS_OF_MODULE(it, mod) {
      rtl::VeriModInstantiation* inst = (rtl::VeriModInstantiation*)it;
      for(auto iter : inst->mod_list()) {
        rtl::VeriModInstance* modInst = (rtl::VeriModInstance*)iter;
        rtl::VeriMod* modInstMod = (rtl::VeriMod*)(modInst->hive());
        // NOTE: the return type of inst_name() may also be VeriArrayExp*
        cout << "\tinst name:" << ((rtl::VeriPrimaryExp*)(modInst->inst_name()))->str() 
          << ", corresponding module:" << modInstMod->name() << endl << "\t\tinst    nets:";
        for (auto net : ((rtl::VeriMultiExp*)modInst->arg())->exp()) {
          rtl::VeriVar* netInst = (rtl::VeriVar*)(((rtl::VeriPrimaryExp*)net)->var());
          cout << netInst->name() << "[" << netInst->dstart() << ":" << netInst->dend() << "]" << ", ";
        }
        cout << endl << "\t\tmodule ports:";
        FOREACH_PORTS_OF_MODULE(iter2, modInstMod) {
          rtl::VeriVar* instModPort = (rtl::VeriVar*)(((rtl::VeriPrimaryExp*)iter2)->var());
          cout << instModPort->name() << "[" << instModPort->dstart() << ":" << instModPort->dend() << "]" << ", ";
        }
        cout << endl;
      } 
      // Your code here
      // main interface of VeriModInstantiation is: param(), mod_list()
    }

    /**
      Generally, foreach all items of top module('it' means VeriNode*), including:
        VeriVarDecl*, VeriModInstantiation*, ... 
      You can organize your code based on the tok_type() and detail_type()
    **/
    cout << endl << "ITEMS OF TOP MODULE:" << endl;
    FOREACH_ITEMS_OF_MODULE(it, mod) {
      // declaration: variable, parameter, int number, port list, ...
      if (it->tok_type() == vtDECL)
      {
        if (it->detail_type() == vsDECL_VAR) {
          // rtl::VeriVarDecl* var = (rtl::VeriVarDecl*)it;
          // Your code here
        }
        else if (it->detail_type() == vsDECL_PARAM) {
          // rtl::VeriParamDecl* para = (rtl::VeriParamDecl*)it;
          // Your code here
        }
        else{
          // Your code here
        }
      }
      // instantiation: instantiated module, ...
      else if (it->tok_type() == vtINST)
      {
        if (it->detail_type() == vsINST_MOD_INSTANTIATION) {
          // rtl::VeriModInstantiation* inst = (rtl::VeriModInstantiation*)it;
          // Your code here, can also be comleted by FOREACH_INSTS_OF_MODULE
        }
        else{
          // Your code here
        }
      }
      // statement: always, assign, case, initial, ...
      else if (it->tok_type() == vtSTMT)
      {
        if (it->detail_type() == vsSTMT_ALWAYS) {
          // rtl::VeriAlwaysStmt* always = (rtl::VeriAlwaysStmt*)it;
          // Your code here
        }
        else if (it->detail_type() == vsSTMT_CONT_ASSIGN) {
          // rtl::VeriContAssignStmt* assign = (rtl::VeriContAssignStmt*)it;
          // Your code here
        }
        else{
          // Your code here
        }
      }
    }  
  }

  return 0;
}
