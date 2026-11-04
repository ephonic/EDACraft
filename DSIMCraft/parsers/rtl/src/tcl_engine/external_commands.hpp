/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : external_commands.hpp
 * Summary  : tcl command line commands
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef TCL_ENGINE_EXTERNAL_COMMANDS_
#define TCL_ENGINE_EXTERNAL_COMMANDS_

#include <tcl.h>
#include <ctime>
#include <string>
#include <vector>
#include <iostream>
#include <sstream>
#include <cctype>
#include <complex>

#include "tcl_engine.hpp"

namespace p_tcl_engine
{

#define pTCL_FUNC( name ) \
  int name( ClientData /*client_data*/, Tcl_Interp* /*interp*/,\
            int objc, Tcl_Obj* CONST objv[])

// tcl_commands, for general purpose
// ===================================================================
pTCL_FUNC( p_help_func );
pTCL_FUNC( p_ls        );
pTCL_FUNC( p_list_func );
pTCL_FUNC( p_run       );
pTCL_FUNC( p_history   );

// tcl_commands, for verilog processing
// ===================================================================
pTCL_FUNC( p_read_veri );


// tcl_commands, for initialization usage
// ===================================================================
pTCL_FUNC( p_init_5138_func );

#undef pTCL_FUNC

};

#endif // TCL_ENGINE_EXTERNAL_COMMANDS_
