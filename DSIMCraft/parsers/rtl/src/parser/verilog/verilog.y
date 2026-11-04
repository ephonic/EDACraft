%{
/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : verilog.y
 * Summary  : verilog syntax analyzer
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#include <cstdlib>
#include <cstring>
#include <iostream>

#include "general_err.hpp"
#include "verilog_token.hpp"
#include "veri_node.hpp"
#include "veri_parser.hpp"
#include "veri_stmt.hpp"
#include "veri_inst.hpp"
#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include <stdexcept>
using rtl::VeriParamDecl;
using rtl::VeriTfDecl;
using rtl::VeriFuncDecl;

using rtl::OK;
using rtl::IS_TRUE;
using rtl::IS_FALSE;
using rtl::VeriAstNode;
using rtl::VeriNode;
using rtl::VeriParser;

#define YYINITDEPTH 1000
#define YYMAXDEPTH 50000

extern char *verilogtext;

int yylex();
extern int veriloglex_destroy( void );
extern int veri_col;
extern int veri_lno;

// Count recovered syntax errors too: Bison may return success after recovery.
// Property expressions use existing owned conditional and timing-control nodes.
static rtl::VeriCondStmt* sva_condition(VeriNode* expr,VeriNode* yes,VeriNode* no=nullptr) {
  return static_cast<rtl::VeriCondStmt*>(rtl::VeriParser::get_instance()->gen_cond_stmt(expr->line(),expr->col(),expr,yes,no));
}
static VeriNode* sva_number(const char* value) {
  return rtl::VeriParser::get_instance()->gen_primary(value,veri_lno,veri_col,veNUM);
}
// Each cycle-count wrapper owns its constant expression and following term.
// Ordinary branch traversal/clone/cleanup thus visits every sequence operand.
static VeriNode* sva_cycle(VeriNode* count,VeriNode* next) {
  auto* node=sva_condition(count,next);node->set_property_cycle_delay();return node;
}
static VeriNode* sva_term(VeriNode* expr,VeriNode* next=nullptr) {
  if(!next)next=rtl::VeriParser::get_instance()->gen_dummy_stmt(expr->line(),expr->col());
  auto* node=sva_condition(expr,next);node->set_property_term();return node;
}
// A repetition wrapper owns its count and one ordinary expression term.
// Expansion happens after elaboration, so instance/generate parameters bind
// in their own scope and the parser never duplicates expression ownership.
static VeriNode* sva_repeat(VeriNode* expr,VeriNode* count,VeriNode* next=nullptr) {
  auto* node=sva_condition(count,sva_term(expr,next));node->set_property_repetition();return node;
}
// The body and continuation have separate owned branches. Repeating a group
// must never repeat the sequence that follows its closing parenthesis.
static VeriNode* sva_group(VeriNode* body,VeriNode* count=nullptr,VeriNode* next=nullptr) {
  if(!count)count=sva_number("1");
  if(!next)next=rtl::VeriParser::get_instance()->gen_dummy_stmt(body->line(),body->col());
  auto* node=sva_condition(count,body,next);node->set_property_group();return node;
}
static VeriNode* sva_declare_sequence(char* name,VeriNode* body,char* closing) {
  std::string identifier=name,label=closing?closing:"";free(name);free(closing);
  if(!label.empty()&&identifier!=label)throw std::runtime_error("sequence closing label does not match: "+identifier);
  auto* node=sva_condition(sva_number("0"),body);
  node->set_assertion_kind(8);node->set_property_name(identifier);return node;
}
static VeriNode* sva_specification(VeriNode* clock,VeriNode* disable,VeriNode* antecedent,VeriNode* consequent,int delay) {
  auto* parser=rtl::VeriParser::get_instance();
  // Both sequences are owned statement branches; keep expressions in expression
  // slots so validation, lexical binding and instance cloning remain ordinary.
  auto* spec=sva_condition(disable,sva_condition(sva_number("1"),consequent,antecedent));
  spec->set_property_delay(delay);
  return parser->gen_proc_timing_control_stmt(clock,spec);
}
static rtl::VeriCondStmt* sva_body(VeriNode* node) {
  if(node->detail_type()==vsSTMT_PROC_TIME_CONTROL)node=static_cast<rtl::VeriProcTimeContStmt*>(node)->stmt();
  return static_cast<rtl::VeriCondStmt*>(node);
}

static VeriNode* clocking_node(int kind,const std::string& name,const VeriNode::NodeVec& children={},int direction=0,bool step=false) {
  return rtl::VeriParser::get_instance()->gen_clocking(veri_lno,veri_col,kind,name,children,direction,step);
}
static VeriNode* clocking_ports(VeriNode* ports,int direction,VeriNode* skew) {
  bool first=true;
  for(auto* node:static_cast<rtl::VeriModuleItemList*>(ports)->item_list()) {
    auto* item=static_cast<rtl::VeriClocking*>(node);item->direction=direction;
    auto* copy=skew?(first?skew:rtl::veri_clone_syntax(skew)):nullptr;first=false;
    item->children.push_back(copy);if(copy)copy->set_father(item);
  }
  return ports;
}
static VeriNode* clocking_default(int direction,VeriNode* skew) {
  return clocking_node(vsDECL_CLOCKING_ITEM,"",{nullptr,skew},direction);
}
// Prototypes remain ordinary owned declaration children through instance clones.
static VeriNode* modport_join(VeriNode* left,VeriNode* right) {
  if(!left)return right;if(!right)return left;
  auto* parser=rtl::VeriParser::get_instance();
  return parser->append_mod_item_list(parser->gen_mod_item_list(left),right);
}

// Keep the most recent bracket pending until the following token distinguishes
// a receiver selection from the final foreach iterator list. This avoids the
// identifier/index reduce-reduce ambiguity in a separate selection grammar.
static VeriNode* foreach_receiver(VeriNode* object,VeriNode* pending) {
  if(!pending)return object;
  if(pending->detail_type()==veEXP_MULTI ||
     (pending->detail_type()==veEXP_PRI &&
      static_cast<rtl::VeriPrimaryExp*>(pending)->pri_type()==veVAR &&
      static_cast<rtl::VeriPrimaryExp*>(pending)->str().empty()))
    throw std::runtime_error("foreach receiver selection requires one index expression");
  auto* parser=rtl::VeriParser::get_instance();
  return parser->gen_array(object,parser->gen_range(pending,vrSINGLE,nullptr));
}

int verilog_syntax_errors = 0;
int verilog_first_error_line = 0;
void yyerror(const char *str)
{
  if (verilog_syntax_errors == 0) verilog_first_error_line = veri_lno;
  ++verilog_syntax_errors;
  std::cerr << "Verilog syntax error at line " << veri_lno
            << " col " << veri_col << " near '"
            << (verilogtext ? verilogtext : "") << "': "
            << (str ? str : "") << std::endl;
}

%}

%union
{
  class VeriNode *tok;
  int operation;

  struct
  {
    int   col;
    int   line;
    char *content;
  }symbol;

  struct { int col; int line; char *content; bool abstract_class; }class_spec;

  struct
  {
    int  col;
    int  line;
    int  extra[3];
    class VeriNode *node[3];
  }extra_tok;
}

%token<symbol> vINSIDE vWILD_EQ vWILD_NE
%token<symbol> vSVA_REPEAT
%token MY_EOF
%token<symbol> vPORT_DELIM vPARAM_DELIM vEVENT_ALL vDUMMY_PORT
%token<symbol> vSIGN_FUNC vUNSIGN_FUNC

%token<symbol> vNOT_SUPPORTED

%token<symbol> vALWAYS vALWAYS_COMB vALWAYS_FF vALWAYS_LATCH
%token<symbol> vFINAL vBIND
%token<symbol> vAND_ASCII vASSIGN vAUTO vBEGIN vBIT vBUF_ASCII vBUFIF_A
%token<symbol> vSTATIC
%token<symbol> vBYTE
%token<symbol> vUNIQUE vUNIQUE0 vPRIORITY
%type <extra_tok> unique_priority cond_head case_head case_keyword
%token<symbol> vBUFIF_B vCASE vCASEX vCASEZ vCELL vCONFIG vDEFAULT
%token<symbol> vDESIGN vDISABLE vDO vELSE vEND vENDCASE vENDCONFIG vENDFUNC
%token<symbol> vENDGEN vENDMODULE vENDSPEC vENDTASK
%token<symbol> vFOR vFUNC vGEN vGENVAR vHIGHZ_A vHIGHZ_B vIF
%token<symbol> vREPEAT vFOREVER vFOREACH
%type<tok> foreach_indices foreach_index
%type<extra_tok> foreach_array
%token<symbol> vPATTERN_OPEN
%token<symbol> vNEW
%token<symbol> vCLASS vENDCLASS vNULL vTHIS vSUPER vEXTENDS vVIRTUAL vPURE vLOCAL vPROTECTED vCONTEXT vEXTERN
%token<symbol> vINC_DIR vINIT vINOUT vINPUT vINSTANCE vINT vINT2
%token<symbol> vREAL vSHORTREAL vREALTIME
%token<symbol> vLIBLIST vLIB vLOCAL_PARAM vMODULE vNAND_ASCII
%token<symbol> vNEGEDGE vNOR_ASCII vNOT_ASCII vNOTIF_A
%token<symbol> vNOTIF_B vOR_ASCII vOUTPUT vPARAMETER
%token<symbol> vPOSEDGE vPULL_A vPULL_B vREG vSHORTINT vTRIAND vTRIOR
%token<symbol> vSCALARED vSIGNED vSPECIFY vSPEC_PARAM
%token<symbol> vVOID
%token<symbol> vSTRONG_A vSTRONG_B vSUPPLY_A vSUPPLY_B vTASK vTIME vTRI
%token<symbol> vUSE vUNSIGNED vVECTORED vWAND vWEAK_A vWEAK_B vWHILE vWIRE vWOR
%token<symbol> vTYPE
%token<symbol> vTYPEDEF vENUM vSTRUCT vUNION vPACKED vFORCE vRELEASE
%type <tok> func_port_list_opt task_port_list_opt
%type<tok> packed_members packed_member
%type<extra_tok> packed_kind packed_sign
%type<tok> enum_body enum_members enum_member
%type<tok> named_port_ids
%type<tok> typedef_declaration named_declaration named_variable_list named_variable_init named_declarator
%token<symbol> vLONGINT
%token<symbol> vXNOR_ASCII vXOR_ASCII

%token<symbol> vIDENT vLOGIC vNUMBER vTIME_LITERAL vTIMEUNIT vTIMEPRECISION vSYS_IDENT vDUMPVARS vCONCAT_IDENT vUNSIGNED_NUM

%token<symbol> vARITH_LS vARITH_RS vANDAND vXNOR vNAND vNOR vPOW
%token<symbol> vOROR vLE vGE vLOGIC_LS vLOGIC_RS vLOGIC_EQ vLOGIC_INEQ
%token<symbol> vCASE_EQ vCASE_INEQ

%token<symbol> '+' '=' '-' '*' '/' '%' '>' '<' '!' '~' '&' '|' '^' '?'

%token<symbol> '#' '@' '[' ']' '{' '}' ';' ',' '.' '(' ')' ':'
%token<symbol> vATTR_L vATTR_R
%token<symbol> vPRIMITIVE vENDPRI

%token<symbol> vSTR vFILE
%token<symbol> vRANGE_ADD vRANGE_SUB

  /* system part */
%token<symbol> vPATHPULSE

%token<symbol> vBREAK vCONTINUE vINCR vDECR vRETURN
%token<symbol> vASSERT vASSUME vCOVER
%type<extra_tok> cast_type query_type
%type<extra_tok> simple_assertion_kind
%type<tok> immediate_assertion_statement wait_order_statement
%token<symbol> vADD_EQ vSUB_EQ vMUL_EQ vDIV_EQ vMOD_EQ vAND_EQ vOR_EQ vXOR_EQ vLS_EQ vRS_EQ vALS_EQ vARS_EQ
%type<operation> compound_operator
%type<tok> compound_assignment
%token<symbol> vWAIT vWAIT_ORDER vEVENT vTRIGGER vNBA_TRIGGER
%token<symbol> vREF vCONST
%token<symbol> vRAND vRANDC vCONSTRAINT
%type<tok> constraint_block constraint_items constraint_item constraint_set
%token<symbol> vCLOCKING vENDCLOCKING vSTEP
%type<tok> clocking_declaration clocking_items clocking_item clocking_signals clocking_signal clocking_skew clocking_skew_opt
%token<symbol> vIFF
%token<symbol> vCOVERGROUP vENDGROUP vCOVERPOINT vCROSS vBINS vIGNORE_BINS vILLEGAL_BINS
%type<tok> coverage_declaration coverage_event coverage_items coverage_item coverage_body coverage_bins coverage_bin coverage_values coverage_value coverage_iff coverage_option
%type<operation> coverage_bin_kind
%type<tok> coverage_cross_names

  /* priorities */
%nonassoc LOWER_THAN_ELSE
%nonassoc vELSE

%precedence INTEGRAL_DEFAULT
%precedence vSIGNED vUNSIGNED
%nonassoc LOWER_THAN_A
%nonassoc LOWER_THAN_B
%nonassoc LOWER_THAN_C  /* for nonblocking assignment disambiguation */
%right '='
%left ',' vOR_ASCII
%nonassoc vIFF
%right '?' ':'
%left vRANGE_ADD vRANGE_SUB
%left vOROR
%left vANDAND
%left '|'
%left '^'
%left '&'
%left vLOGIC_EQ vLOGIC_INEQ vCASE_EQ vCASE_INEQ
%left vGE vLE '<' '>'
%left vARITH_LS vARITH_RS vLOGIC_LS vLOGIC_RS
%left '+' '-'
%left '%' '*' '/'
%left vNAND vPOW vNOR vXNOR
%left UOR
%left UAND
%left UNEG
%left UNAND
%left UNOR
%left UXNOR
%left UXOR
%left ULNOT
%left UADD
%left UMINUS
%precedence vNEW
%left vINCR vDECR
%left '(' ')' '[' ']'
%nonassoc '.'
%nonassoc vATTR_L vATTR_R

  /* start symbol */
%type <tok> for_steps_opt for_steps for_step for_condition
%type <tok> verilog_synthesis_unit

/* A.1 Source test */
/* A.1.1 Library source text */

/* A.1.2 Config source text */

/* A.1.3 Module and primitive source text */
%type <tok> source_text module_declaration
%type <tok> time_declaration
%type <tok> enum_variable_declaration
%type <symbol> time_scale_value
%type <symbol> module_keyword interface_keyword
%type <tok> bind_directive
%type <extra_tok> module_port_part
%type <tok> module_item_list

/* A.1.4 Module parameters and ports */
%type <tok> param_decl_list
%type <tok> port_decl_list port_declaration
%type <extra_tok> integral_type qualified_integral_type parameter_type
%type <extra_tok> port_type
%type <extra_tok> in_or_out tf_direction

/* A.1.5 Module items */
%type <tok> class_access_item module_item module_or_gen_item
%type <tok> module_or_gen_item_declaration

/* A.2 Declarations */
/* A.2.1 Declaration types */
/* A.2.1.1 Module parameter declarations */
%type <tok> param_declaration param_decl_item specparam_declaration
%type <extra_tok> class_value_declarator param_declarator

/* A.2.1.2 Port declarations */
/* A.2.1.3 Type declarations */
%type <tok> genvar_declaration int_declaration
%type <tok> net_declaration reg_declaration
%type <extra_tok> variable_type
%type <extra_tok> vector_or_scalar
%type <extra_tok> net_decl_a net_decl_b

/* A.2.2 Declaration data types */
/* A.2.2.1 Net and variable types */
%type <extra_tok> net_type

/* A.2.2.2 Strengths */
%type <tok> drive_strength
%type <extra_tok> strength0 strength1

/* A.2.2.3 Delays */
%type <tok> delay3 procedural_delay

/* A.2.3 Declaration lists */
%type <tok> specparam_assignment_list

/* A.2.4 Declaration assignments */
%type <tok> specparam_assignment

/* A.2.5 Declaration ranges */
/* A.2.6 Function declarations */
%type <tok> func_declaration func_declaration_body func_item_declaration func_port_list
%type <symbol> subroutine_end_name
%type <tok> func_item_decl_list block_item_decl_list
%type <extra_tok> func_declarator

/* A.2.7 Task declarations */
%type <tok> subroutine_body
%type <tok> task_declaration task_declaration_body task_item_decl_list task_item_declaration
%type <tok> task_port_list implicit_tf_declaration tf_declaration
%type <extra_tok> tf_port_declarator

/* A.2.8 Block item declarations */
%type <tok> block_item_declaration

/* A.3 Primitive instances */
/* A.3.1 Primitive instantiation and instances */
%type <tok> gate_instantiation gate_instance_list gate_instance

/* A.3.2 Primitive strengths */
/* A.3.3 Primitive terminals */

/* A.3.4 Primitive gate and switch types */
%type <extra_tok> gatetype

/* A.4 Module and generated instantiation */
/* A.4.1 Module instantiation */
%type <tok> module_instantiation

/* A.4.2 Generated instantiation */
%type <tok> generated_instantiation gen_item_or_null gen_item gen_item_list
%type <tok> gen_cond_statement genvar_case_item gen_loop_statement
%type <tok> gen_block gen_case_statement
%type <tok> genvar_case_item_list

/* A.5 UDP declaration and instantiation */
/* A.5.1 UDP declaration */
%type <tok> udp_declaration

/* A.5.2 UDP ports */
/* A.5.3 UDP body */
/* A.5.4 UDP instantiation */

/* A.6 Behavioral statements */
/* A.6.1 Continuous assignment statements */
%type <tok> continuous_assign

/* A.6.2 Procedural blocks and assignments */
%type <tok> blocking_assignment assignment_event_control
%type <tok> nonblocking_assignment

/* A.6.3 Parallel and sequential blocks */
%type <tok> seq_block parallel_block seq_block_body parallel_block_body
%token<symbol> vFORK vJOIN vJOIN_ANY vJOIN_NONE
%token<symbol> vWITH
%token<symbol> vVAR_PORT
%token<symbol> vRANDOM_FUNC
%token<symbol> vPACKAGE vENDPACKAGE vIMPORT vSCOPE vSTRING_TYPE vCHANDLE
%token<symbol> vPROPERTY vENDPROPERTY vOVERLAP vNONOVERLAP vCYCLEDELAY
%token<symbol> vSEQUENCE vENDSEQUENCE
%type<symbol> sva_sequence_end
%token<symbol> vINTERFACE vENDINTERFACE vMODPORT
%token<symbol> vEXPORT
%type<tok> interface_declaration interface_port_declaration modport_declaration virtual_interface_type
%type<symbol> modport_start
%type<tok> class_access_prototype modport_items modport_ports modport_prototype modport_func_ports modport_task_ports
%type<tok> sva_spec sva_disable sva_actions sva_assertion sva_declaration
%type<tok> sva_sequence sva_temporal_sequence sva_consequent sva_cycle_count
%type<extra_tok> sva_kind

%type<tok> package_declaration package_items package_items_opt import_declaration import_items import_item header_imports
%type<tok> dpi_export_declaration export_declaration export_items export_item
%type<symbol> dpi_c_name
%type<extra_tok> dpi_import_property
%type<symbol> package_end_name
%type<operation> fork_join_keyword
%type <tok> stmt_list

/* A.6.4 Statements */
%type <tok> statement stmt_or_null func_statement

/* A.6.5 Timing control statements */
%type <tok> event_control disable_statement
%type <tok> procedural_timing_control_statement

/* A.6.6 Conditioinal statements */
%type <tok> cond_statement

/* A.6.7 Case statements */
%type <tok> case_statement case_item case_item_list
%type <tok> inside_item inside_list inside_case_item inside_case_list

/* A.6.8 Looping statements */
%type <tok> loop_statement

/* A.6.9 Task enable statements */
%type <tok> sys_caller

/* A.7 Specify section */
/* A.7.1 Specify block declaration */
/* A.7.2 Specify path declaration */
/* A.7.3 Specify block terminals */
/* A.7.4 Specify path delays */
/* A.7.5 System timing checks */
/* A.7.5.1 System timing check commands */
/* A.7.5.2 System timing check command arguments */
/* A.7.5.3 System timing check event definitions */

/* A.8 Expressions */
/* A.8.1 Concatenations */
%type <tok> concat multi_concat stream_concat
%type <tok> dump_target dump_targets

/* A.8.2 Function calls */
/* A.8.3 Expressions */
%type <tok> expression assignment_expression postfix_expression
%type <tok> unary_expression pow_expression multiplicative_expression
%type <tok> additive_expression shift_expression relational_expression
%type <tok> equality_expression and_expression xor_expression
%type <tok> bit_or_expression logical_and_expression logical_or_expression
%type <tok> conditional_expression
%type <tok> mintypmax_expression
%type <tok> range packed_range

/* A.8.4 Primaries */
%type <tok> assignment_pattern pattern_items pattern_item
%type <tok> primary

/* A.8.5 Expression left_side values */
/* A.8.6 Operators */
/* A.8.7 Numbers */

/* A.9 General */
/* A.9.l Attributes */
%type <tok> attr_inst_list attr_instance

/* A.9.2 Comments */
/* A.9.3 Identifiers */

%type <tok> error

%type <extra_tok> subroutine_lifetime
%type <symbol> package_header
%type <class_spec> class_header
%type <tok> class_parameters_opt class_parameter_list class_parameter class_extends_opt class_type_spec class_application class_nonexpr_type class_argument class_arguments class_arguments_opt
%type <tok> class_declaration

%start verilog_synthesis_unit

%%

/* Whole */
verilog_synthesis_unit
  : source_text MY_EOF
    {
      YYACCEPT;
    }
  ;

/* A.1 Source text */
/* A.1.1 Library source text */
/* A.1.3 Module and primitive source text */

/* udp_declaration not supported */
source_text
  : import_declaration { veri_parser->compilation_import($1);$$=NULL; }
  | class_declaration { veri_parser->compilation_declaration($1);$$=NULL; }
  | typedef_declaration { veri_parser->compilation_declaration($1);$$=NULL; }
  | source_text class_declaration { veri_parser->compilation_declaration($2);$$=NULL; }
  | source_text typedef_declaration { veri_parser->compilation_declaration($2);$$=NULL; }
  | time_declaration { veri_parser->compilation_time($1);$$=NULL; }
  | source_text time_declaration { veri_parser->compilation_time($2);$$=NULL; }
  | source_text import_declaration { veri_parser->compilation_import($2);$$=NULL; }
  | interface_declaration
  | bind_directive
  | source_text bind_directive
  | source_text interface_declaration
  | package_declaration
  | source_text package_declaration
  | module_declaration
    {
    }
  | udp_declaration
    {
    }
  | source_text module_declaration
    {
    }
  | source_text udp_declaration
    {
    }
  ;

bind_directive
  : vBIND vIDENT { veri_parser->begin_bind($2.content);free($2.content); }
    module_instantiation { veri_parser->end_bind($4);$$=nullptr; }
  ;

package_declaration
  : package_header ';' package_items_opt vENDPACKAGE package_end_name
    { $$=veri_parser->gen_package($1.line,$1.col,$1.content,$3,$5.content);free($1.content);free($5.content); }
  ;
package_header
  : vPACKAGE vIDENT
    { $$=$2;$$.line=$1.line;$$.col=$1.col;veri_parser->set_default_subroutine_automatic(false); }
  | vPACKAGE subroutine_lifetime vIDENT
    { $$=$3;$$.line=$1.line;$$.col=$1.col;veri_parser->set_default_subroutine_automatic($2.extra[0]==IS_TRUE); }
  ;
package_end_name
  : %empty { $$.content=NULL; }
  | ':' vIDENT { $$=$2; }
  ;
package_items_opt
  : %empty { $$=NULL; }
  | package_items { $$=$1; }
  ;
package_items
  : module_item { $$=veri_parser->gen_mod_item_list($1); }
  | package_items module_item { $$=veri_parser->append_mod_item_list($1,$2); }
  | export_declaration { $$=veri_parser->gen_mod_item_list($1); }
  | package_items export_declaration { $$=veri_parser->append_mod_item_list($1,$2); }
  ;
dpi_import_property
  : %empty { $$.extra[0]=0; }
  | vPURE { $$.extra[0]=1; }
  | vCONTEXT { $$.extra[0]=2; }
  ;
dpi_c_name
  : %empty { $$.content=NULL; }
  | vIDENT '=' { $$=$1; }
  ;
dpi_export_declaration
  : vEXPORT vSTR dpi_c_name vFUNC vIDENT ';'
    { $$=veri_parser->gen_dpi_export($1.line,$1.col,$2.content,$3.content,$5.content,false);free($2.content);free($3.content);free($5.content); }
  | vEXPORT vSTR dpi_c_name vTASK vIDENT ';'
    { $$=veri_parser->gen_dpi_export($1.line,$1.col,$2.content,$3.content,$5.content,true);free($2.content);free($3.content);free($5.content); }
  ;
import_declaration
  : vIMPORT import_items ';' { $$=$2; }
  | vIMPORT vSTR dpi_import_property dpi_c_name modport_prototype ';'
    { $$=veri_parser->qualify_dpi_import($5,$2.content,$4.content,$3.extra[0]);free($2.content);free($4.content); }
  ;
import_items
  : import_item { $$=$1; }
  | import_items ',' import_item
    { static_cast<rtl::VeriImportStmt*>($1)->append(*static_cast<rtl::VeriImportStmt*>($3));$$=$1; }
  ;
import_item
  : vIDENT vSCOPE '*'
    { $$=veri_parser->gen_import($1.line,$1.col,$1.content,"*");free($1.content); }
  | vIDENT
    { std::string name=$1.content;auto separator=name.find("::");
      if(separator==std::string::npos)throw std::runtime_error("import requires package::member or package::*");
      $$=veri_parser->gen_import($1.line,$1.col,name.substr(0,separator).c_str(),name.substr(separator+2).c_str());free($1.content); }
  ;

export_declaration
  : vEXPORT export_items ';' { $$=$2; }
  | vEXPORT '*' vSCOPE '*' ';'
    { $$=veri_parser->gen_import($1.line,$1.col,"*","*",true); }
  ;
export_items
  : export_item { $$=$1; }
  | export_items ',' export_item
    { static_cast<rtl::VeriImportStmt*>($1)->append(*static_cast<rtl::VeriImportStmt*>($3));$$=$1; }
  ;
export_item
  : vIDENT vSCOPE '*'
    { $$=veri_parser->gen_import($1.line,$1.col,$1.content,"*",true);free($1.content); }
  | vIDENT
    { std::string name=$1.content;auto separator=name.find("::");
      if(separator==std::string::npos)throw std::runtime_error("export requires package::member or package::*");
      $$=veri_parser->gen_import($1.line,$1.col,name.substr(0,separator).c_str(),name.substr(separator+2).c_str(),true);free($1.content); }
  ;

// Header imports are a separate owned child, resolved before parameters/ports.
header_imports
  : %empty { $$=NULL; }
  | header_imports import_declaration
    { $$=$1?veri_parser->append_mod_item_list($1,$2):veri_parser->gen_mod_item_list($2); }
  ;

// Set the lexical default before parsing header imports, ports and body.
// gen_*_decl records the resolved lifetime in each subroutine's owned AST.
module_keyword
  : vMODULE
    { $$=$1;veri_parser->set_default_subroutine_automatic(false); }
  | vMODULE subroutine_lifetime
    { if(!veri_parser->systemverilog())throw std::runtime_error("module lifetime requires SystemVerilog");
      $$=$1;veri_parser->set_default_subroutine_automatic($2.extra[0]==IS_TRUE); }
  ;
interface_keyword
  : vINTERFACE
    { $$=$1;veri_parser->set_default_subroutine_automatic(false); }
  | vINTERFACE subroutine_lifetime
    { $$=$1;veri_parser->set_default_subroutine_automatic($2.extra[0]==IS_TRUE); }
  ;

interface_declaration
  : interface_keyword vIDENT header_imports ';' package_items_opt vENDINTERFACE package_end_name
    { veri_parser->gen_mod($1.line,$1.col,$2.content,NULL,NULL,$5,true,$3);free($2.content);free($7.content);$$=NULL; }
  | interface_keyword vIDENT header_imports module_port_part ';' package_items_opt vENDINTERFACE package_end_name
    { veri_parser->gen_mod($1.line,$1.col,$2.content,$4.node[0],$4.node[1],$6,true,$3);free($2.content);free($8.content);$$=NULL; }
  ;

virtual_interface_type
  : vVIRTUAL vIDENT
    { $$=veri_parser->gen_virtual_interface_type($1.line,$1.col,$2.content,"");free($2.content); }
  | vVIRTUAL vINTERFACE vIDENT
    { $$=veri_parser->gen_virtual_interface_type($1.line,$1.col,$3.content,"");free($3.content); }
  | vVIRTUAL vIDENT '.' vIDENT
    { $$=veri_parser->gen_virtual_interface_type($1.line,$1.col,$2.content,$4.content);free($2.content);free($4.content); }
  | vVIRTUAL vINTERFACE vIDENT '.' vIDENT
    { $$=veri_parser->gen_virtual_interface_type($1.line,$1.col,$3.content,$5.content);free($3.content);free($5.content); }
  ;
interface_port_declaration
  : vIDENT vIDENT
    { $$=veri_parser->gen_interface_port($1.line,$1.col,$1.content,"",$2.content);free($1.content);free($2.content); }
  | vIDENT '.' vIDENT vIDENT
    { $$=veri_parser->gen_interface_port($1.line,$1.col,$1.content,$3.content,$4.content);free($1.content);free($3.content);free($4.content); }
  | vINTERFACE vIDENT
    { $$=veri_parser->gen_interface_port($1.line,$1.col,"*","",$2.content);free($2.content); }
  ;
modport_start : vIDENT { veri_parser->begin_modport($1.content);free($1.content);$$.content=NULL; } ;
modport_ports
  : vIMPORT vIDENT { veri_parser->modport_member($2.content,vpIMPORT);free($2.content);$$=NULL; }
  | vIMPORT modport_prototype { $$=veri_parser->modport_prototype($2,true); }
  | modport_ports ',' vIMPORT vIDENT { veri_parser->modport_member($4.content,vpIMPORT);free($4.content);$$=$1; }
  | modport_ports ',' vIMPORT modport_prototype { $$=modport_join($1,veri_parser->modport_prototype($4,true)); }
  | modport_ports ',' modport_prototype { $$=modport_join($1,veri_parser->modport_prototype($3,false)); }
  | in_or_out vIDENT { veri_parser->modport_member($2.content,$1.extra[0]);free($2.content);$$=NULL; }
  | modport_ports ',' vIDENT { veri_parser->modport_member($3.content);free($3.content);$$=$1; }
  | modport_ports vPORT_DELIM in_or_out vIDENT { veri_parser->modport_member($4.content,$3.extra[0]);free($4.content);$$=$1; }
  ;
modport_items
  : modport_start '(' modport_ports ')' {$$=$3;}
  | modport_items ',' modport_start '(' modport_ports ')' {$$=modport_join($1,$5);}
  ;
modport_declaration : vMODPORT modport_items ';' {$$=$2?$2:veri_parser->gen_dummy_stmt($1.line,$1.col);} ;
modport_func_ports : %empty {$$=NULL;} | '(' func_port_list_opt ')' {$$=$2;} ;
modport_task_ports : %empty {$$=NULL;} | '(' task_port_list_opt ')' {$$=$2;} ;
modport_prototype
  : vTASK vIDENT modport_task_ports
    { $$=veri_parser->gen_task_decl($1.line,$1.col,IS_FALSE,$2.content,$3,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));free($2.content); }
  | vFUNC vIDENT modport_func_ports
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$2.content,$3,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));free($2.content); }
  | vFUNC func_declarator vIDENT modport_func_ports
    { if($2.extra[0]==IS_TRUE)throw std::runtime_error("modport prototype cannot declare a lifetime");
      $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,$2.extra[1],$2.extra[2],NULL,$3.content,$4,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));free($3.content); }
  | vFUNC packed_range vIDENT modport_func_ports
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,$2,$3.content,$4,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));free($3.content); }
  | vFUNC func_declarator packed_range vIDENT modport_func_ports
    { if($2.extra[0]==IS_TRUE)throw std::runtime_error("modport prototype cannot declare a lifetime");
      $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,$2.extra[1],$2.extra[2],$3,$4.content,$5,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));free($4.content); }
  | vFUNC vIDENT vIDENT modport_func_ports
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,$4,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));
      static_cast<VeriFuncDecl*>($$)->set_type_name($2.content);free($2.content);free($3.content); }
  | vFUNC class_application vIDENT modport_func_ports
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,$4,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col));
      static_cast<VeriFuncDecl*>($$)->set_type_expression($2);free($3.content); }
  ;

/* module and endmodule status added to ignore # */
module_declaration
  : module_keyword vIDENT header_imports ';' vENDMODULE
    { veri_parser->gen_mod($1.line,$1.col,$2.content,NULL,NULL,NULL,false,$3);free($2.content); }
  | module_keyword vIDENT header_imports module_port_part ';' vENDMODULE
    { veri_parser->gen_mod($1.line,$1.col,$2.content,$4.node[0],$4.node[1],NULL,false,$3);free($2.content); }
  | module_keyword vIDENT header_imports ';' module_item_list vENDMODULE
    { veri_parser->gen_mod($1.line,$1.col,$2.content,NULL,NULL,$5,false,$3);free($2.content); }
  | module_keyword vIDENT header_imports module_port_part ';' module_item_list vENDMODULE
    { veri_parser->gen_mod($1.line,$1.col,$2.content,$4.node[0],$4.node[1],$6,false,$3);free($2.content); }
  | attr_inst_list module_keyword vIDENT header_imports ';' vENDMODULE
    { veri_parser->gen_mod($2.line,$2.col,$3.content,NULL,NULL,NULL,false,$4);free($3.content); }
  | attr_inst_list module_keyword vIDENT header_imports module_port_part ';' vENDMODULE
    { veri_parser->gen_mod($2.line,$2.col,$3.content,$5.node[0],$5.node[1],NULL,false,$4);free($3.content); }
  | attr_inst_list module_keyword vIDENT header_imports ';' module_item_list vENDMODULE
    { veri_parser->gen_mod($2.line,$2.col,$3.content,NULL,NULL,$6,false,$4);free($3.content); }
  | attr_inst_list module_keyword vIDENT header_imports module_port_part ';' module_item_list vENDMODULE
    { veri_parser->gen_mod($2.line,$2.col,$3.content,$5.node[0],$5.node[1],$7,false,$4);free($3.content); }
  ;

module_port_part
  : '(' ')'
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = NULL;
      $$.node[1] = NULL;
    }
  | '(' expression ')'
    {
      /* arg-list or .arg()-list */
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = NULL;
      $$.node[1] = $2;
    }
  | '(' port_decl_list ')'
    {
      /* arg-list or .arg()-list */
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = NULL;
      $$.node[1] = $2;
    }
  | '#' '(' param_decl_list ')'
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = $3;
      $$.node[1] = NULL;
    }
  | '#' '(' param_decl_list ')' '(' ')'
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = $3;
      $$.node[1] = NULL;
    }
  | '#' '(' param_decl_list ')' '(' expression ')'
    {
      /* arg-list or .arg()-list */
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = $3;
      $$.node[1] = $6;
    }
  | '#' '(' param_decl_list ')' '(' port_decl_list ')'
    {
      /* arg-list or .arg()-list */
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.node[0] = $3;
      $$.node[1] = $6;
    }
  ;

module_item_list
  : module_item
    {
      $$ = veri_parser->gen_mod_item_list( $1 );
    }
  | module_item_list module_item
    {
      $$ = veri_parser->append_mod_item_list( $1, $2 );
    }
  ;

/* A.1.4 Module parameters and ports */
param_decl_list
  : param_decl_item
    {
      $$ = veri_parser->gen_param_decl_list( $1 );
    }
  | param_decl_list ',' param_decl_item
    {
      $$ = veri_parser->append_param_decl_list( $1, $3 );
    }
  | param_decl_list vPARAM_DELIM param_decl_item
    {
      $$ = veri_parser->append_param_decl_list( $1, $3 );
    }
  ;


port_decl_list
  : interface_port_declaration { $$=veri_parser->gen_port_decl_list($1); }
  | port_decl_list ',' vIDENT {
      auto& ports=static_cast<rtl::VeriPortDeclList*>($1)->port_list();
      auto* decl=static_cast<rtl::VeriVarDecl*>(ports.back());
      if(!decl->interface_port())throw std::runtime_error("missing interface port type");
      auto* id=veri_parser->gen_primary($3.content,$3.line,$3.col,veVAR);free($3.content);
      decl->append_var(id);id->set_father(decl);$$=$1;
    }
  | port_decl_list vPORT_DELIM interface_port_declaration { $$=veri_parser->append_port_decl_list($1,$3); }
  | port_declaration
    {
      $$ = veri_parser->gen_port_decl_list( $1 );
    }
  | port_decl_list vPORT_DELIM port_declaration
    {
      $$ = veri_parser->append_port_decl_list( $1, $3 );
    }
  ;


port_declaration
  : in_or_out expression port_term
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, $1.extra[0],
                                           vvWIRE, IS_FALSE, vpSCALAR, NULL,
                                           NULL, NULL, $2 );
    }
  | in_or_out vIDENT named_variable_list port_term
    { $$=veri_parser->gen_var_decl($1.line,$1.col,$1.extra[0],vvLOGIC,IS_FALSE,vpSCALAR,NULL,NULL,NULL,$3);
      static_cast<rtl::VeriVarDecl*>($$)->set_type_name($2.content);free($2.content); }
  | attr_inst_list in_or_out vIDENT named_variable_list port_term
    { $$=veri_parser->gen_var_decl($2.line,$2.col,$2.extra[0],vvLOGIC,IS_FALSE,vpSCALAR,NULL,NULL,NULL,$4);
      static_cast<rtl::VeriVarDecl*>($$)->set_type_name($3.content);free($3.content); }
  | in_or_out vVAR_PORT vIDENT named_variable_list port_term
    { $$=veri_parser->gen_var_decl($1.line,$1.col,$1.extra[0],vvLOGIC,IS_FALSE,vpSCALAR,NULL,NULL,NULL,$4);
      static_cast<rtl::VeriVarDecl*>($$)->set_type_name($3.content);free($3.content); }
  | attr_inst_list in_or_out vVAR_PORT vIDENT named_variable_list port_term
    { $$=veri_parser->gen_var_decl($2.line,$2.col,$2.extra[0],vvLOGIC,IS_FALSE,vpSCALAR,NULL,NULL,NULL,$5);
      static_cast<rtl::VeriVarDecl*>($$)->set_type_name($4.content);free($4.content); }
  | in_or_out port_type expression port_term
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, $1.extra[0],
                                           $2.extra[0], $2.extra[1], vpSCALAR,
                                           NULL, NULL, NULL,
                                           $3 );
    }
  | attr_inst_list in_or_out expression port_term
    {
      $$ = veri_parser->gen_var_decl( $2.line, $2.col, $2.extra[0],
                                           vvWIRE, IS_FALSE, vpSCALAR, NULL,
                                           NULL, NULL, $3 );
    }
  | attr_inst_list in_or_out port_type expression port_term
    {
      $$ = veri_parser->gen_var_decl( $2.line, $2.col, $2.extra[0],
                                           $3.extra[0], $3.extra[1], vpSCALAR,
                                           NULL, NULL, NULL,
                                           $4 );
    }
  | in_or_out packed_range expression port_term
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, $1.extra[0],
                                           vvWIRE, IS_FALSE, vpSCALAR, NULL,
                                           $2, NULL, $3 );
    }
  | in_or_out port_type packed_range expression port_term
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, $1.extra[0],
                                           $2.extra[0], $2.extra[1], vpSCALAR,
                                           NULL, $3, NULL,
                                           $4 );
    }
  | attr_inst_list in_or_out packed_range expression port_term
    {
      $$ = veri_parser->gen_var_decl( $2.line, $2.col, $2.extra[0],
                                           vvWIRE, IS_FALSE, vpSCALAR, NULL,
                                           $3, NULL, $4 );
    }
  | attr_inst_list in_or_out port_type packed_range expression port_term
    {
      $$ = veri_parser->gen_var_decl( $2.line, $2.col, $2.extra[0],
                                           $3.extra[0], $3.extra[1], vpSCALAR,
                                           NULL, $4, NULL,
                                           $5 );
    }
  | in_or_out vVAR_PORT port_type expression port_term
    { if($3.extra[0]==vvWIRE||$3.extra[0]==vvTRI)throw std::runtime_error("var port requires an explicit variable data type");
      $$=veri_parser->gen_var_decl($1.line,$1.col,$1.extra[0],$3.extra[0],$3.extra[1],vpSCALAR,NULL,NULL,NULL,$4); }
  | in_or_out vVAR_PORT port_type packed_range expression port_term
    { if($3.extra[0]==vvWIRE||$3.extra[0]==vvTRI)throw std::runtime_error("var port requires an explicit variable data type");
      $$=veri_parser->gen_var_decl($1.line,$1.col,$1.extra[0],$3.extra[0],$3.extra[1],vpSCALAR,NULL,$4,NULL,$5); }
  | attr_inst_list in_or_out vVAR_PORT port_type expression port_term
    { if($4.extra[0]==vvWIRE||$4.extra[0]==vvTRI)throw std::runtime_error("var port requires an explicit variable data type");
      $$=veri_parser->gen_var_decl($2.line,$2.col,$2.extra[0],$4.extra[0],$4.extra[1],vpSCALAR,NULL,NULL,NULL,$5); }
  | attr_inst_list in_or_out vVAR_PORT port_type packed_range expression port_term
    { if($4.extra[0]==vvWIRE||$4.extra[0]==vvTRI)throw std::runtime_error("var port requires an explicit variable data type");
      $$=veri_parser->gen_var_decl($2.line,$2.col,$2.extra[0],$4.extra[0],$4.extra[1],vpSCALAR,NULL,$5,NULL,$6); }
  ;

port_term
  : ';'
  |
  ;

in_or_out
  : vINPUT
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpIN;
    }
  | vOUTPUT
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpOUT;
    }
  | vINOUT
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpINOUT;
    }
  ;

port_type
  : vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvWIRE;
      $$.extra[1] = IS_TRUE;
    }
  | net_type
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = $1.extra[0];
      $$.extra[1] = IS_FALSE;
    }
  | net_type vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = $1.extra[0];
      $$.extra[1] = IS_TRUE;
    }
  | vREG
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvREG;
      $$.extra[1] = IS_FALSE;
    }
  | vREG vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvREG;
      $$.extra[1] = IS_TRUE;
    }
  | integral_type { $$=$1; }
  | vUNSIGNED
    {
      /* NOTE: Standalone "unsigned" in a port declaration is accepted
         as "wire unsigned". Strict SystemVerilog requires unsigned
         to modify a concrete type (e.g. "logic unsigned"). This is an
         accepted superset behavior. */
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvWIRE;
      $$.extra[1] = IS_FALSE;
    }
  | net_type vUNSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = $1.extra[0];
      $$.extra[1] = IS_FALSE;
    }
  | vREG vUNSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvREG;
      $$.extra[1] = IS_FALSE;
    }
  | vLOGIC
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvLOGIC;
      $$.extra[1] = IS_FALSE;
    }
  | vLOGIC vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvLOGIC;
      $$.extra[1] = IS_TRUE;
    }
  | vLOGIC vUNSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvLOGIC;
      $$.extra[1] = IS_FALSE;
    }
  | vBIT
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvBIT;
      $$.extra[1] = IS_FALSE;
    }
  | vBIT vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvBIT;
      $$.extra[1] = IS_TRUE;
    }
  | vBIT vUNSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvBIT;
      $$.extra[1] = IS_FALSE;
    }

  ;

/* A.1.5 Module items */
/* compress module_item and non_module_item here */
class_access_prototype
  : modport_prototype { $$=$1; }
  | vFUNC vNEW modport_func_ports
    { $$=veri_parser->gen_constructor($1.line,$1.col,$3,NULL,veri_parser->gen_dummy_stmt($1.line,$1.col)); }
  | vSTATIC class_access_prototype { $$=veri_parser->qualify_static_method($2); }
  | vVIRTUAL class_access_prototype { $$=veri_parser->qualify_virtual($2); }
  | vLOCAL class_access_prototype { $$=veri_parser->qualify_class_access($2,true); }
  | vPROTECTED class_access_prototype { $$=veri_parser->qualify_class_access($2,false); }
  ;

class_access_item
  : vLOCAL module_item { $$=veri_parser->qualify_class_access($2,true); }
  | vPROTECTED module_item { $$=veri_parser->qualify_class_access($2,false); }
  ;

time_declaration
  : vTIMEUNIT time_scale_value ';'
    { $$=veri_parser->gen_time_declaration($1.line,$1.col,$2.content,nullptr);free($2.content); }
  | vTIMEUNIT time_scale_value '/' time_scale_value ';'
    { $$=veri_parser->gen_time_declaration($1.line,$1.col,$2.content,$4.content);free($2.content);free($4.content); }
  | vTIMEPRECISION time_scale_value ';'
    { $$=veri_parser->gen_time_declaration($1.line,$1.col,nullptr,$2.content);free($2.content); }
  ;
time_scale_value
  : vTIME_LITERAL { $$=$1; }
  | vNUMBER vIDENT {
      const std::string spelling=std::string($1.content)+$2.content;
      $$=$1;free($1.content);free($2.content);$$.content=strdup(spelling.c_str());
    }
  ;

module_item
  : virtual_interface_type named_variable_list ';'
    { $$=veri_parser->gen_named_var_decl($1->line(),$1->col(),"$virtual_interface",$2);static_cast<rtl::VeriVarDecl*>($$)->set_type_expression($1); }
  | time_declaration { $$=$1; }
  | vEXTERN class_access_prototype ';' { $$=veri_parser->qualify_extern($2); }
  | vRAND module_item { $$=veri_parser->qualify_rand_property($2); }
  | vRANDC module_item { $$=veri_parser->qualify_rand_property($2,true); }
  | vCONSTRAINT vIDENT constraint_block { $$=veri_parser->gen_constraint($2.content,$1.line,$1.col,$3);free($2.content); }
  | vCONST module_item { $$=veri_parser->qualify_const_property($2); }
  | vSTATIC vCONST module_item { $$=veri_parser->qualify_static_method(veri_parser->qualify_const_property($3)); }
  | class_access_item { $$=$1; }
  | vSTATIC class_access_item { $$=veri_parser->qualify_static_method($2); }
  | vVIRTUAL class_access_item { $$=veri_parser->qualify_virtual($2); }
  | vVIRTUAL func_declaration { $$=veri_parser->qualify_virtual($2); }
  | vVIRTUAL task_declaration { $$=veri_parser->qualify_virtual($2); }
  | vSTATIC module_or_gen_item_declaration { $$=veri_parser->qualify_static_method($2); }
  | vSTATIC named_declaration { $$=veri_parser->qualify_static_method($2); }
  | vPURE vVIRTUAL class_access_prototype ';'
    { $$=veri_parser->qualify_virtual($3);static_cast<rtl::VeriDecl*>($$)->set_pure_virtual(); }
  | port_declaration
    {
      $$ = $1;
    }
  | module_or_gen_item
    {
      $$ = $1;
    }
  | generated_instantiation
    {
      $$ = $1;
    }
  | gen_cond_statement { $$ = $1; }
  | gen_case_statement { $$ = $1; }
  | gen_loop_statement { $$ = $1; }
  | gen_block { $$ = $1; }
  | param_declaration
    {
      $$ = $1;
    }
  | specparam_declaration
    {
      $$ = $1;
    }
  | attr_inst_list module_or_gen_item
    {
      $$ = $2;
    }
  | attr_inst_list generated_instantiation
    {
      $$ = $2;
    }
  | attr_inst_list param_declaration
    {
      $$ = $2;
    }
  | attr_inst_list specparam_declaration
    {
      $$ = $2;
    }
  | error ';'
    {
      // The public parse is already a failure. Stop before recovery can
      // reduce incomplete class/generate constructs into executable ASTs.
      $$ = NULL;
      YYABORT;
    }
  ;

module_or_gen_item
  : clocking_declaration { $$=$1; }
  | coverage_declaration { $$=$1; }
  | modport_declaration { $$=$1; }
  | sva_assertion { $$=veri_parser->gen_always_stmt($1->line(),$1->col(),$1,akALWAYS); }
  | vIDENT ':' sva_assertion
    { sva_body($3)->set_assertion_label($1.content);free($1.content);$$=veri_parser->gen_always_stmt($3->line(),$3->col(),$3,akALWAYS); }
  | sva_declaration { $$=veri_parser->gen_always_stmt($1->line(),$1->col(),$1,akALWAYS); }
  | module_or_gen_item_declaration
    {
      $$ = $1;
    }
  | continuous_assign
    {
      $$ = $1;
    }
  | gate_instantiation
    {
      $$ = $1;
    }
  | module_instantiation
    {
      $$ = $1;
    }
  | vINIT statement
    {
      $$ = veri_parser->gen_init_stmt( $1.line, $1.col, $2 );
    }
  | vFINAL statement
    {
      $$ = veri_parser->gen_init_stmt($1.line,$1.col,$2);
      static_cast<rtl::VeriInitStmt*>($$)->set_final_process();
    }
  | vALWAYS statement
    {
      $$ = veri_parser->gen_always_stmt( $1.line, $1.col, $2, akALWAYS );
    }
  | vALWAYS_COMB statement
    {
      $$ = veri_parser->gen_always_stmt( $1.line, $1.col, $2, akALWAYS_COMB );
    }
  | vALWAYS_FF statement
    {
      $$ = veri_parser->gen_always_stmt( $1.line, $1.col, $2, akALWAYS_FF );
    }
  | vALWAYS_LATCH statement
    {
      $$ = veri_parser->gen_always_stmt( $1.line, $1.col, $2, akALWAYS_LATCH );
    }
  ;

module_or_gen_item_declaration
  : class_declaration { $$=$1; }
  | import_declaration { $$=$1; }
  | dpi_export_declaration { $$=$1; }
  | typedef_declaration { $$=$1; }
  | net_declaration
    {
      $$ = $1;
    }
  | reg_declaration
    {
      $$ = $1;
    }
  | int_declaration
    {
      $$ = $1;
    }
  | genvar_declaration
    {
      $$ = $1;
    }
  | task_declaration
    {
      $$ = $1;
    }
  | func_declaration
    {
      $$ = $1;
    }
  ;

/* A.2 Declaration */

/* A.2.1 Declaration types */

/* A.2.1.1 Module parameter declarations */
param_declarator
  : vLOCAL_PARAM
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = IS_FALSE;
      $$.extra[2] = IS_TRUE;
    }
  | vPARAMETER
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = IS_FALSE;
      $$.extra[2] = IS_FALSE;
    }
  | vLOCAL_PARAM vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_TRUE;
      $$.extra[1] = IS_FALSE;
      $$.extra[2] = IS_TRUE;
    }
  | vPARAMETER vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_TRUE;
      $$.extra[1] = IS_FALSE;
      $$.extra[2] = IS_FALSE;
    }
  | vPARAMETER parameter_type
    { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=$2.extra[1];$$.extra[1]=100+$2.extra[0];$$.extra[2]=IS_FALSE; }
  | vLOCAL_PARAM parameter_type
    { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=$2.extra[1];$$.extra[1]=100+$2.extra[0];$$.extra[2]=IS_TRUE; }

  ;

parameter_type
  : integral_type { $$=$1; }
  | vBIT %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_FALSE; }
  | vBIT vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_TRUE; }
  | vBIT vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_FALSE; }
  | vLOGIC %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_FALSE; }
  | vLOGIC vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_TRUE; }
  | vLOGIC vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_FALSE; }
  | vREG %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREG;$$.extra[1]=IS_FALSE; }
  | vREG vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREG;$$.extra[1]=IS_TRUE; }
  | vREG vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREG;$$.extra[1]=IS_FALSE; }
  ;

param_decl_item
  : param_declarator vIDENT named_variable_list
    { if($1.extra[0]!=IS_FALSE||$1.extra[1]!=IS_FALSE) throw std::runtime_error("named parameter type cannot follow a signing or built-in type");
      $$=veri_parser->gen_param_decl($1.line,$1.col,IS_FALSE,IS_FALSE,$1.extra[2],NULL,$3);
      static_cast<VeriParamDecl*>($$)->set_type_name($2.content);free($2.content); }
  | param_declarator expression
    {
      /* expression-list or .arg()-list */
      $$ = veri_parser->gen_param_decl( $1.line, $1.col, $1.extra[0],
                                             $1.extra[1], $1.extra[2],
                                             NULL, $2 );
    }
  | param_declarator packed_range expression
    {
      /* expression-list or .arg()-list */
      $$ = veri_parser->gen_param_decl( $1.line, $1.col, $1.extra[0],
                                             $1.extra[1], $1.extra[2],
                                             $2, $3 );
    }
  ;

param_declaration
  : param_decl_item ';'
    {
      $$ = $1;
    }
  ;

specparam_declaration
  : vSPEC_PARAM expression ';'
    {
      // vIDENT = mintypmax-or-range-expression
      // const-mintypmax-expression
    }
  | vSPEC_PARAM specparam_assignment_list ';'
    {
      // first could be range[a:b]
    }
  | vSPEC_PARAM packed_range expression ';'
    {
      // vIDENT = mintypmax-or-range-expression
      // const-mintypmax-expression
    }
  | vSPEC_PARAM packed_range specparam_assignment_list ';'
    {
      // first could be range[a:b]
    }
  ;

/* A.2.1.2 Port declarations */
/* A.2.1.3 Type declaratioins */
genvar_declaration
  : vGENVAR expression ';'
    {
      // genvar-identifier-list
      $$ = veri_parser->gen_genvar_decl( $1.line, $1.col, $2 );
    }
  ;

integral_type
  : vINT %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT;$$.extra[1]=IS_TRUE; }
  | qualified_integral_type { $$=$1; }
  ;
qualified_integral_type
  : vINT vSIGNED { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT;$$.extra[1]=IS_TRUE; }
  | vREAL %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREAL;$$.extra[1]=IS_TRUE; }
  | vSHORTREAL %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSHORTREAL;$$.extra[1]=IS_TRUE; }
  | vREALTIME %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREAL;$$.extra[1]=IS_TRUE; }
  | vINT vUNSIGNED { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT;$$.extra[1]=IS_FALSE; }
  | vSTRING_TYPE { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSTRING;$$.extra[1]=IS_FALSE; }
  | vCHANDLE { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvCHANDLE;$$.extra[1]=IS_FALSE; }
  | vTIME { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvTIME;$$.extra[1]=IS_FALSE; }
  | vINT2 %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT2;$$.extra[1]=IS_TRUE; }
  | vINT2 vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT2;$$.extra[1]=IS_TRUE; }
  | vINT2 vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT2;$$.extra[1]=IS_FALSE; }
  | vBYTE %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBYTE;$$.extra[1]=IS_TRUE; }
  | vBYTE vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBYTE;$$.extra[1]=IS_TRUE; }
  | vBYTE vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBYTE;$$.extra[1]=IS_FALSE; }
  | vSHORTINT %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSHORTINT;$$.extra[1]=IS_TRUE; }
  | vSHORTINT vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSHORTINT;$$.extra[1]=IS_TRUE; }
  | vSHORTINT vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSHORTINT;$$.extra[1]=IS_FALSE; }
  | vLONGINT %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLONGINT;$$.extra[1]=IS_TRUE; }
  | vLONGINT vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLONGINT;$$.extra[1]=IS_TRUE; }
  | vLONGINT vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLONGINT;$$.extra[1]=IS_FALSE; }
  ;

int_declaration
  : vINT named_variable_list ';'
    {
      // var-identifier-list -> named_variable_list
      $$ = veri_parser->gen_int_decl( $1.line, $1.col, $2 );
    }
  | qualified_integral_type named_variable_list ';'
    { $$=veri_parser->gen_var_decl($1.line,$1.col,vpNO_IO,$1.extra[0],$1.extra[1],vpSCALAR,NULL,NULL,NULL,$2); }
  ;

net_declaration
  : net_type expression ';'
    {
      // { vIDENT + dimension_list } _list
      // or .id() -list
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           IS_FALSE, vpSCALAR, NULL, NULL,
                                           NULL, $2  );
    }
  | net_type net_decl_a expression ';'
    {
      // { vIDENT + dimension_list } _list
      // or .id() -list
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           $2.extra[0], $2.extra[1],
                                           NULL, $2.node[0],
                                           $2.node[1], $3  );
    }
  | net_type net_decl_b expression ';'
    {
      // const-assignment-exp, type-1
      // or .id() -list
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           $2.extra[0], $2.extra[1],
                                           $2.node[2], $2.node[0],
                                           $2.node[1], $3  );
    }
  ;

net_decl_a
  : packed_range
    {
      $$.line = $1->line();
      $$.col  = $1->col();
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = $1;
      $$.node[1] = NULL;
    }
  | packed_range delay3
    {
      $$.line = $1->line();
      $$.col  = $1->col();
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = $1;
      $$.node[1] = $2;
    }
  | vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_TRUE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = NULL;
      $$.node[1] = NULL;
    }
  | vector_or_scalar
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = $1.extra[0];
      $$.node[0] = NULL;
      $$.node[1] = NULL;
    }
  | delay3
    {
      $$.line = $1->line();
      $$.col  = $1->col();
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = NULL;
      $$.node[1] = $1;
    }
  | vSIGNED packed_range
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_TRUE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = $2;
      $$.node[1] = NULL;
    }
  | vector_or_scalar packed_range
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = $1.extra[0];
      $$.node[0] = $2;
      $$.node[1] = NULL;
    }
  | vSIGNED delay3
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_TRUE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = NULL;
      $$.node[1] = $2;
    }
  | vector_or_scalar delay3
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = $1.extra[0];
      $$.node[0] = NULL;
      $$.node[1] = $2;
    }
  | vSIGNED packed_range delay3
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_TRUE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = $2;
      $$.node[1] = $3;
    }
  | vector_or_scalar packed_range delay3
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = $1.extra[0];
      $$.node[0] = $2;
      $$.node[1] = $3;
    }
  ;

net_decl_b
  : drive_strength
    {
      $$.line = $1->line();
      $$.col  = $1->col();
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = vpSCALAR;
      $$.node[0] = NULL;
      $$.node[1] = NULL;
      $$.node[2] = $1;
    }
  | drive_strength net_decl_a
    {
      $$.line = $1->line();
      $$.col  = $1->col();
      $$.extra[0] = $2.extra[0];
      $$.extra[1] = $2.extra[1];
      $$.node[0] = $2.node[0];
      $$.node[1] = $2.node[1];
      $$.node[2] = $1;
    }
  ;

vector_or_scalar
  : vVECTORED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpVECTOR;
    }
  | vSCALARED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpSCALAR;
    }
  ;

variable_type
  : vREG
    { $$.line = $1.line; $$.col = $1.col; $$.extra[0] = vvREG; }
  | vLOGIC
    { $$.line = $1.line; $$.col = $1.col; $$.extra[0] = vvLOGIC; }
  | vBIT
    { $$.line = $1.line; $$.col = $1.col; $$.extra[0] = vvBIT; }

  ;

reg_declaration
  : enum_variable_declaration { $$=$1; }
  | vEVENT named_variable_list ';'
    { $$=veri_parser->gen_var_decl($1.line,$1.col,vpNO_IO,vvEVENT,IS_FALSE,vpSCALAR,NULL,NULL,NULL,$2); }
  | variable_type named_variable_list ';'
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                      IS_FALSE, vpSCALAR, NULL, NULL,
                                      NULL, $2  );
    }
  | variable_type vSIGNED named_variable_list ';'
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           IS_TRUE, vpSCALAR, NULL, NULL,
                                           NULL, $3 );
    }
  | variable_type packed_range named_variable_list ';'
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           IS_FALSE, vpSCALAR, NULL, $2,
                                           NULL, $3  );
    }
  | variable_type vSIGNED packed_range named_variable_list ';'
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           IS_TRUE, vpSCALAR, NULL, $3,
                                           NULL, $4  );
    }
  | variable_type vUNSIGNED named_variable_list ';'
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           IS_FALSE, vpSCALAR, NULL, NULL,
                                           NULL, $3 );
    }
  | variable_type vUNSIGNED packed_range named_variable_list ';'
    {
      $$ = veri_parser->gen_var_decl( $1.line, $1.col, vpNO_IO, $1.extra[0],
                                           IS_FALSE, vpSCALAR, NULL, $3,
                                           NULL, $4  );
    }
  ;

enum_variable_declaration
  : vENUM enum_body named_variable_list ';'
    { $$=veri_parser->gen_enum_variables($1.line,$1.col,vvINT2,IS_TRUE,NULL,$2,$3); }
  | vENUM parameter_type enum_body named_variable_list ';'
    { $$=veri_parser->gen_enum_variables($1.line,$1.col,$2.extra[0],$2.extra[1],NULL,$3,$4); }
  | vENUM parameter_type packed_range enum_body named_variable_list ';'
    { $$=veri_parser->gen_enum_variables($1.line,$1.col,$2.extra[0],$2.extra[1],$3,$4,$5); }
  | vENUM vIDENT enum_body named_variable_list ';'
    { $$=veri_parser->gen_enum_variables($1.line,$1.col,vvLOGIC,IS_FALSE,NULL,$3,$4,$2.content);free($2.content); }
  ;

/* Integral typedefs retain type identity and bind in each elaborated scope. */
typedef_declaration
  : vTYPEDEF vCLASS vIDENT ';'
    { $$=veri_parser->gen_typedef($1.line,$1.col,vvCLASS,IS_FALSE,NULL,$3.content);static_cast<rtl::VeriVarDecl*>($$)->set_forward_class();free($3.content); }
  | vTYPEDEF parameter_type named_declarator ';'
    { $$=veri_parser->gen_typedef_declarator($1.line,$1.col,$2.extra[0],$2.extra[1],NULL,$3); }
  | vTYPEDEF parameter_type packed_range named_declarator ';'
    { $$=veri_parser->gen_typedef_declarator($1.line,$1.col,$2.extra[0],$2.extra[1],$3,$4); }
  | vTYPEDEF vIDENT named_declarator ';'
    { $$=veri_parser->gen_typedef_declarator($1.line,$1.col,vvLOGIC,IS_FALSE,NULL,$3,$2.content);free($2.content); }
  | vTYPEDEF virtual_interface_type named_declarator ';'
    { $$=veri_parser->gen_typedef_declarator($1.line,$1.col,vvLONGINT,IS_FALSE,NULL,$3);static_cast<rtl::VeriVarDecl*>($$)->set_type_expression($2); }
  | vTYPEDEF class_application named_declarator ';'
    { $$=veri_parser->gen_typedef_declarator($1.line,$1.col,vvCLASS,IS_FALSE,NULL,$3);static_cast<rtl::VeriVarDecl*>($$)->set_type_expression($2); }
  | vTYPEDEF vSTRUCT '{' packed_members '}' vIDENT ';'
    { $$=veri_parser->gen_packed_type($1.line,$1.col,3,IS_FALSE,$4,$6.content);free($6.content); }
  | vTYPEDEF packed_kind vPACKED packed_sign '{' packed_members '}' vIDENT ';'
    { $$=veri_parser->gen_packed_type($1.line,$1.col,$2.extra[0],$4.extra[0],$6,$8.content);free($8.content); }
  | vTYPEDEF vENUM enum_body vIDENT ';'
    { $$=veri_parser->gen_enum($1.line,$1.col,vvINT2,IS_TRUE,NULL,$4.content,$3);free($4.content); }
  | vTYPEDEF vENUM parameter_type enum_body vIDENT ';'
    { $$=veri_parser->gen_enum($1.line,$1.col,$3.extra[0],$3.extra[1],NULL,$5.content,$4);free($5.content); }
  | vTYPEDEF vENUM parameter_type packed_range enum_body vIDENT ';'
    { $$=veri_parser->gen_enum($1.line,$1.col,$3.extra[0],$3.extra[1],$4,$6.content,$5);free($6.content); }
  | vTYPEDEF vENUM vIDENT enum_body vIDENT ';'
    { $$=veri_parser->gen_enum($1.line,$1.col,vvLOGIC,IS_FALSE,NULL,$5.content,$4,$3.content);free($3.content);free($5.content); }
  ;
packed_kind
  : vSTRUCT { $$.extra[0]=1; }
  | vUNION { $$.extra[0]=2; }
  ;
packed_sign
  : %empty { $$.extra[0]=IS_FALSE; }
  | vSIGNED { $$.extra[0]=IS_TRUE; }
  | vUNSIGNED { $$.extra[0]=IS_FALSE; }
  ;
packed_members
  : packed_member { $$=veri_parser->gen_block_item_list($1); }
  | packed_members packed_member { $$=veri_parser->append_block_item_list($1,$2); }
  ;
packed_member
  : parameter_type named_variable_list ';'
    { $$=veri_parser->gen_var_decl($1.line,$1.col,vpNO_IO,$1.extra[0],$1.extra[1],vpSCALAR,NULL,NULL,NULL,$2); }
  | parameter_type packed_range named_variable_list ';'
    { $$=veri_parser->gen_var_decl($1.line,$1.col,vpNO_IO,$1.extra[0],$1.extra[1],vpVECTOR,NULL,$2,NULL,$3); }
  | named_declaration { $$=$1; }
  | enum_variable_declaration { $$=$1; }
  ;
enum_body
  : '{' enum_members '}' { $$=$2; }
  ;
enum_members
  : enum_member { $$=$1; }
  | enum_members ',' enum_member { $$=veri_parser->gen_multi($1,$3,vemCOMMA_EXP,$2.line,$2.col); }
  ;
enum_member
  : vIDENT { $$=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content); }
  | vIDENT '=' assignment_expression
    { auto* id=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content);$$=veri_parser->gen_binary(id,vtASSIGN,$2.line,$2.col,$3); }
  ;
named_declaration
  : virtual_interface_type named_variable_list ';'
    { $$=veri_parser->gen_named_var_decl($1->line(),$1->col(),"$virtual_interface",$2);static_cast<rtl::VeriVarDecl*>($$)->set_type_expression($1); }
  | vIDENT named_variable_list ';'
    { $$=veri_parser->gen_named_var_decl($1.line,$1.col,$1.content,$2);free($1.content); }
  | class_application named_variable_list ';'
    { $$=veri_parser->gen_named_var_decl($1->line(),$1->col(),"$parameterized",$2);static_cast<rtl::VeriVarDecl*>($$)->set_type_expression($1); }

  ;
named_variable_list
  : named_variable_init { $$=$1; }
  | named_variable_list ',' named_variable_init
    { $$=veri_parser->gen_multi($1,$3,vemCOMMA_EXP,$2.line,$2.col); }
  ;
named_variable_init
  : named_declarator { $$=$1; }
  | named_declarator '=' assignment_expression { $$=veri_parser->gen_binary($1,vtASSIGN,$2.line,$2.col,$3,true); }
  ;
named_declarator
  : vIDENT { $$=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content); }
  | named_declarator range { $$=veri_parser->gen_array($1,$2); }
  | named_declarator '[' ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrOPEN,NULL)); }
  | named_declarator '[' '$' ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrQUEUE,NULL)); }
  | named_declarator '[' '$' ':' assignment_expression ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrQUEUE,$5)); }
  | named_declarator '[' vINT2 ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_INT,NULL)); }
  | named_declarator '[' vINT2 vSIGNED ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_INT,NULL)); }
  | named_declarator '[' vINT2 vUNSIGNED ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_UINT,NULL)); }
  | named_declarator '[' vSTRING_TYPE ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_STRING,NULL)); }
  ;

query_type
  : cast_type { $$=$1; }
  | cast_type vSIGNED { $$=$1;$$.extra[1]=IS_TRUE; }
  | cast_type vUNSIGNED { $$=$1;$$.extra[1]=IS_FALSE; }
  ;

cast_type
  : vINT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT;$$.extra[1]=IS_TRUE; }
  | vREAL %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREAL;$$.extra[1]=IS_TRUE; }
  | vSHORTREAL %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSHORTREAL;$$.extra[1]=IS_TRUE; }
  | vREALTIME %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREAL;$$.extra[1]=IS_TRUE; }
  | vINT2 { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvINT2;$$.extra[1]=IS_TRUE; }
  | vBYTE { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBYTE;$$.extra[1]=IS_TRUE; }
  | vSHORTINT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvSHORTINT;$$.extra[1]=IS_TRUE; }
  | vLONGINT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLONGINT;$$.extra[1]=IS_TRUE; }
  | vTIME { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvTIME;$$.extra[1]=IS_FALSE; }
  | vBIT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_FALSE; }
  | vLOGIC { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_FALSE; }
  | vREG { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvREG;$$.extra[1]=IS_FALSE; }
  ;

/* A.2.2 Declaration data types */

/* A.2.2.1 Net and variable types */
net_type
  : vSUPPLY_A
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvSUPPLY0;
    }
  | vSUPPLY_B
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvSUPPLY1;
    }
  | vTRI
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvTRI;
    }
  | vTRIAND
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvTRIAND;
    }
  | vTRIOR
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvTRIOR;
    }
  | vWIRE
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvWIRE;
    }
  | vWAND
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvWAND;
    }
  | vWOR
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvWOR;
    }
  ;

/* A.2.2.2 Strengths */
drive_strength
  : '(' strength0 ',' strength1 ')'
    {
      $$ = veri_parser->gen_drive_exp( $1.line, $1.col, $2.extra[0],
                                            $4.extra[0] );
    }
  | '(' strength1 ',' strength0 ')'
    {
      $$ = veri_parser->gen_drive_exp( $1.line, $1.col, $2.extra[0],
                                            $4.extra[0] );
    }
  | '(' strength0 ',' vHIGHZ_A ')'
    {
      $$ = veri_parser->gen_drive_exp( $1.line, $1.col, $2.extra[0],
                                            vpHIGHZ0 );
    }
  | '(' strength1 ',' vHIGHZ_B ')'
    {
      $$ = veri_parser->gen_drive_exp( $1.line, $1.col, $2.extra[0],
                                            vpHIGHZ1 );
    }
  | '(' vHIGHZ_A ',' strength1 ')'
    {
      $$ = veri_parser->gen_drive_exp( $1.line, $1.col, vpHIGHZ0,
                                            $4.extra[0] );
    }
  | '(' vHIGHZ_B ',' strength0 ')'
    {
      $$ = veri_parser->gen_drive_exp( $1.line, $1.col, vpHIGHZ1,
                                            $4.extra[0] );
    }
  ;

strength0
  : vSUPPLY_A
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpSUPPLY0;
    }
  | vSTRONG_A
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpSTRONG0;
    }
  | vPULL_A
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpPULL0;
    }
  | vWEAK_A
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpWEAK0;
    }
  ;

strength1
  : vSUPPLY_B
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpSUPPLY1;
    }
  | vSTRONG_B
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpSTRONG1;
    }
  | vPULL_B
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpPULL1;
    }
  | vWEAK_B
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vpWEAK1;
    }
  ;

/* A.2.2.3 Delays */
delay3
  : '#' expression
    {
      $$ = veri_parser->gen_delay_exp( $1.line, $1.col, $2, NULL );
    }
  ;

/* A.2.3 Declaration lists */
specparam_assignment_list
  : specparam_assignment
    {
    }
  | specparam_assignment_list ',' specparam_assignment
    {
    }
  ;

/* A.2.4 Declaration assignments */
specparam_assignment
  : vPATHPULSE ';'
    {
    }
  ;

/* A.2.5 Declaration ranges */
subroutine_lifetime
  : vAUTO { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_TRUE; }
  | vSTATIC { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=rtl::VeriParser::explicit_static_lifetime; }
  ;

/* A.2.6 Function declarations */
class_header
  : vCLASS vIDENT { $$.content=$2.content;$$.line=$1.line;$$.col=$1.col;$$.abstract_class=false;veri_parser->begin_class(); }
  | vVIRTUAL vCLASS vIDENT { $$.content=$3.content;$$.line=$1.line;$$.col=$1.col;$$.abstract_class=true;veri_parser->begin_class(); }
  ;
class_parameters_opt
  : %empty { $$=NULL; }
  | '#' '(' class_parameter_list ')' { $$=$3; }
  ;
class_parameter_list
  : class_parameter { $$=veri_parser->append_class_parameter(NULL,$1); }
  | class_parameter_list vPARAM_DELIM class_parameter { $$=veri_parser->append_class_parameter($1,$3); }
  | class_parameter_list vPORT_DELIM class_parameter { $$=veri_parser->append_class_parameter($1,$3); }
  | class_parameter_list ',' class_parameter { $$=veri_parser->append_class_parameter($1,$3); }
  ;
class_value_declarator
  : vPARAMETER { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE; }
  | vPARAMETER vSIGNED { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_TRUE;$$.extra[1]=IS_FALSE; }
  | vPARAMETER parameter_type { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=$2.extra[1];$$.extra[1]=100+$2.extra[0]; }
  | parameter_type { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=$1.extra[1];$$.extra[1]=100+$1.extra[0]; }
  ;
class_parameter
  : class_value_declarator vIDENT '=' assignment_expression
    { auto* id=veri_parser->gen_primary($2.content,$2.line,$2.col,veVAR);free($2.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,$1.extra[0],$1.extra[1],NULL,veri_parser->gen_binary(id,vtASSIGN,$3.line,$3.col,$4)); }
  | class_value_declarator vIDENT
    { auto* id=veri_parser->gen_primary($2.content,$2.line,$2.col,veVAR);free($2.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,$1.extra[0],$1.extra[1],NULL,id); }
  | class_value_declarator packed_range vIDENT '=' assignment_expression
    { auto* id=veri_parser->gen_primary($3.content,$3.line,$3.col,veVAR);free($3.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,$1.extra[0],$1.extra[1],$2,veri_parser->gen_binary(id,vtASSIGN,$4.line,$4.col,$5)); }
  | class_value_declarator packed_range vIDENT
    { auto* id=veri_parser->gen_primary($3.content,$3.line,$3.col,veVAR);free($3.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,$1.extra[0],$1.extra[1],$2,id); }
  | vPARAMETER vIDENT vIDENT '=' assignment_expression
    { auto* id=veri_parser->gen_primary($3.content,$3.line,$3.col,veVAR);free($3.content);
      $$=veri_parser->gen_param_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,veri_parser->gen_binary(id,vtASSIGN,$4.line,$4.col,$5));
      static_cast<VeriParamDecl*>($$)->set_type_name($2.content);free($2.content); }
  | vPARAMETER vIDENT vIDENT
    { auto* id=veri_parser->gen_primary($3.content,$3.line,$3.col,veVAR);free($3.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,IS_FALSE,IS_FALSE,NULL,id);
      static_cast<VeriParamDecl*>($$)->set_type_name($2.content);free($2.content); }
  | vIDENT vIDENT '=' assignment_expression
    { auto* id=veri_parser->gen_primary($2.content,$2.line,$2.col,veVAR);free($2.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,IS_FALSE,IS_FALSE,NULL,veri_parser->gen_binary(id,vtASSIGN,$3.line,$3.col,$4));
      static_cast<VeriParamDecl*>($$)->set_type_name($1.content);free($1.content); }
  | vIDENT vIDENT
    { auto* id=veri_parser->gen_primary($2.content,$2.line,$2.col,veVAR);free($2.content);
      $$=veri_parser->gen_class_value_parameter($1.line,$1.col,IS_FALSE,IS_FALSE,NULL,id);
      static_cast<VeriParamDecl*>($$)->set_type_name($1.content);free($1.content); }
  | vIDENT '=' class_argument
    { auto* id=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content);
      $$=veri_parser->gen_binary(id,vtASSIGN,$2.line,$2.col,$3); }
  | vIDENT { $$=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content); }
  | vPARAMETER vTYPE vIDENT '=' class_type_spec
    { $$=veri_parser->gen_type_parameter($1.line,$1.col,$3.content,$5);free($3.content); }
  | vTYPE vIDENT '=' class_type_spec
    { $$=veri_parser->gen_type_parameter($1.line,$1.col,$2.content,$4);free($2.content); }
  | vPARAMETER vTYPE vIDENT
    { $$=veri_parser->gen_type_parameter($1.line,$1.col,$3.content,NULL);free($3.content); }
  | vTYPE vIDENT
    { $$=veri_parser->gen_type_parameter($1.line,$1.col,$2.content,NULL);free($2.content); }
  ;
class_extends_opt
  : %empty { $$=NULL; }
  | vEXTENDS class_type_spec { $$=$2; }
  ;
class_declaration
  : class_header class_parameters_opt class_extends_opt ';' package_items_opt vENDCLASS package_end_name
    { $$=veri_parser->gen_class($1.line,$1.col,$1.content,$5,$7.content);auto* cls=static_cast<rtl::VeriSeqBlock*>($$);
      cls->set_class_parameters($2);cls->set_base_type($3);cls->set_abstract_class($1.abstract_class);free($1.content);free($7.content); }
  ;
class_type_spec
  : vIDENT { $$=veri_parser->gen_type_expression($1.line,$1.col,$1.content,-1,0);free($1.content); }
  | class_nonexpr_type { $$=$1; }
  ;
class_nonexpr_type
  : virtual_interface_type { $$=$1; }
  | parameter_type { $$=veri_parser->gen_type_expression($1.line,$1.col,NULL,$1.extra[0],$1.extra[1]); }
  | parameter_type packed_range { $$=veri_parser->gen_type_expression($1.line,$1.col,NULL,$1.extra[0],$1.extra[1],$2); }
  | class_application { $$=$1; }
  ;
class_application
  : vIDENT '#' '(' class_arguments_opt ')'
    { $$=veri_parser->gen_type_expression($1.line,$1.col,$1.content,-1,0,NULL,$4);free($1.content); }
  ;
class_arguments_opt
  : %empty { auto* list=new rtl::VeriMultiExp(veri_parser->next_id(),vemCOMMA_EXP,veri_lno,veri_col,NULL);veri_parser->insert_node(list);$$=list; }
  | class_arguments { $$=$1; }
  ;
class_arguments
  : class_argument { $$=$1; }
  | class_arguments ',' class_argument { $$=veri_parser->gen_multi($1,$3,vemCOMMA_EXP,$2.line,$2.col); }
  | class_arguments vPORT_DELIM class_argument { $$=veri_parser->gen_multi($1,$3,vemCOMMA_EXP,$2.line,$2.col); }
  ;
class_argument
  : assignment_expression { $$=$1; }
  | class_nonexpr_type { $$=$1; }
  | '.' vIDENT '(' class_nonexpr_type ')'
    { auto* port=veri_parser->gen_port_ref($1.line,$1.col,$2.content);free($2.content);$$=veri_parser->gen_caller(port,$4); }
  ;
// End labels name the declaration, including constructors (the new keyword).
// Validate before the declaration is installed; labels do not create a scope.
subroutine_end_name
  : package_end_name { $$=$1; }
  | ':' vNEW { $$=$2;$$.content=strdup("new"); }
  ;
func_declaration
  : func_declaration_body subroutine_end_name
    {
      std::string closing=$2.content?$2.content:"";free($2.content);
      auto declared=static_cast<VeriFuncDecl*>($1)->func_name();auto split=declared.front()=='\\'?std::string::npos:declared.rfind("::");
      if(!closing.empty()&&closing!=declared.substr(split==std::string::npos?0:split+2))
        { std::string error="function closing label does not match: "+static_cast<VeriFuncDecl*>($1)->func_name();yyerror(error.c_str());YYERROR; }
      $$=$1;
    }
  ;
func_declaration_body
  : vFUNC vNEW '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_constructor($1.line,$1.col,$4,NULL,$7); }
  | vFUNC class_application vIDENT '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,$5,NULL,$8);static_cast<VeriFuncDecl*>($$)->set_type_expression($2);free($3.content); }
  | vFUNC class_application vIDENT '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,$5,$8,$9);static_cast<VeriFuncDecl*>($$)->set_type_expression($2);free($3.content); }
  | vFUNC class_application vIDENT ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,NULL,$5,$6);static_cast<VeriFuncDecl*>($$)->set_type_expression($2);free($3.content); }
  | vFUNC class_application vIDENT ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,NULL,NULL,$5);static_cast<VeriFuncDecl*>($$)->set_type_expression($2);free($3.content); }
  | vFUNC subroutine_lifetime class_application vIDENT '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,$6,NULL,$9);static_cast<VeriFuncDecl*>($$)->set_type_expression($3);free($4.content); }
  | vFUNC subroutine_lifetime class_application vIDENT '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,$6,$9,$10);static_cast<VeriFuncDecl*>($$)->set_type_expression($3);free($4.content); }
  | vFUNC subroutine_lifetime class_application vIDENT ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,NULL,NULL,$6);static_cast<VeriFuncDecl*>($$)->set_type_expression($3);free($4.content); }
  | vFUNC subroutine_lifetime class_application vIDENT ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,NULL,$6,$7);static_cast<VeriFuncDecl*>($$)->set_type_expression($3);free($4.content); }

  | vFUNC vNEW '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_constructor($1.line,$1.col,$4,$7,$8); }
  | vFUNC vNEW ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_constructor($1.line,$1.col,NULL,$4,$5); }
  | vFUNC vNEW ';' func_statement vENDFUNC
    { $$=veri_parser->gen_constructor($1.line,$1.col,NULL,NULL,$4); }
  | vFUNC subroutine_lifetime vIDENT ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$3.content,NULL,$5,$6);free($3.content); }
  | vFUNC subroutine_lifetime vIDENT ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$3.content,NULL,NULL,$5);free($3.content); }
  | vFUNC subroutine_lifetime vIDENT '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$3.content,$5,NULL,$8);free($3.content); }
  | vFUNC subroutine_lifetime vIDENT '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$3.content,$5,$8,$9);free($3.content); }
  | vFUNC subroutine_lifetime packed_range vIDENT ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,$3,$4.content,NULL,$6,$7);free($4.content); }
  | vFUNC subroutine_lifetime packed_range vIDENT ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,$3,$4.content,NULL,NULL,$6);free($4.content); }
  | vFUNC subroutine_lifetime packed_range vIDENT '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,$3,$4.content,$6,NULL,$9);free($4.content); }
  | vFUNC subroutine_lifetime packed_range vIDENT '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,$3,$4.content,$6,$9,$10);free($4.content); }
  | vFUNC subroutine_lifetime vIDENT vIDENT ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,NULL,$6,$7);
      static_cast<VeriFuncDecl*>($$)->set_type_name($3.content);free($3.content);free($4.content); }
  | vFUNC subroutine_lifetime vIDENT vIDENT ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,NULL,NULL,$6);
      static_cast<VeriFuncDecl*>($$)->set_type_name($3.content);free($3.content);free($4.content); }
  | vFUNC subroutine_lifetime vIDENT vIDENT '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,$6,NULL,$9);
      static_cast<VeriFuncDecl*>($$)->set_type_name($3.content);free($3.content);free($4.content); }
  | vFUNC subroutine_lifetime vIDENT vIDENT '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,$2.extra[0],IS_FALSE,IS_FALSE,NULL,$4.content,$6,$9,$10);
      static_cast<VeriFuncDecl*>($$)->set_type_name($3.content);free($3.content);free($4.content); }
  | vFUNC vIDENT vIDENT ';' func_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,NULL,$5,$6);
      static_cast<VeriFuncDecl*>($$)->set_type_name($2.content);free($2.content);free($3.content); }
  | vFUNC vIDENT vIDENT ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,NULL,NULL,$5);
      static_cast<VeriFuncDecl*>($$)->set_type_name($2.content);free($2.content);free($3.content); }
  | vFUNC vIDENT vIDENT '(' func_port_list_opt ')' ';' func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,$5,NULL,$8);
      static_cast<VeriFuncDecl*>($$)->set_type_name($2.content);free($2.content);free($3.content); }
  | vFUNC vIDENT vIDENT '(' func_port_list_opt ')' ';' block_item_decl_list func_statement vENDFUNC
    { $$=veri_parser->gen_func_decl($1.line,$1.col,IS_FALSE,IS_FALSE,IS_FALSE,NULL,$3.content,$5,$8,$9);
      static_cast<VeriFuncDecl*>($$)->set_type_name($2.content);free($2.content);free($3.content); }
  | vFUNC vIDENT ';'
    func_item_decl_list func_statement vENDFUNC
    {
      // expression is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, NULL, $2.content,
                                  NULL, $4, $5 );
      free( $2.content );
    }
  | vFUNC vIDENT ';'
    func_statement vENDFUNC
    {
      // expression is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, NULL, $2.content,
                                  NULL, NULL, $4 );
      free( $2.content );
    }
  | vFUNC vIDENT '(' func_port_list_opt ')' ';'
    func_statement vENDFUNC
    {
      // ANSI-style function port list with no separate item declarations.
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, NULL, $2.content,
                                  $4, NULL, $7 );
      free( $2.content );
    }
  | vFUNC vIDENT '(' func_port_list_opt ')' ';'
    block_item_decl_list func_statement vENDFUNC
    {
      // expression is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, NULL, $2.content,
                                  $4, $7, $8 );
      free( $2.content );
    }
  | vFUNC packed_range vIDENT ';'
    func_item_decl_list func_statement vENDFUNC
    {
      // last exp is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, $2, $3.content,
                                  NULL, $5, $6 );
      free( $3.content );
    }
  | vFUNC packed_range vIDENT ';'
    func_statement vENDFUNC
    {
      // last exp is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, $2, $3.content,
                                  NULL, NULL, $5 );
      free( $3.content );
    }
  | vFUNC packed_range vIDENT '(' func_port_list_opt ')' ';'
    func_statement vENDFUNC
    {
      // ANSI-style function port list with no separate item declarations.
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, $2, $3.content,
                                  $5, NULL, $8 );
      free( $3.content );
    }
  | vFUNC packed_range vIDENT '(' func_port_list_opt ')' ';'
    block_item_decl_list func_statement vENDFUNC
    {
      // last exp is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, IS_FALSE,
                                  IS_FALSE, IS_FALSE, $2, $3.content,
                                  $5, $8, $9 );
      free( $3.content );
    }
  | vFUNC func_declarator vIDENT ';'
    func_item_decl_list func_statement vENDFUNC
    {
      // expression is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], NULL, $3.content,
                                  NULL, $5, $6 );
      free( $3.content );
    }
  | vFUNC func_declarator vIDENT ';'
    func_statement vENDFUNC
    {
      // expression is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], NULL, $3.content,
                                  NULL, NULL, $5 );
      free( $3.content );
    }
  | vFUNC func_declarator vIDENT '(' func_port_list_opt ')' ';'
    func_statement vENDFUNC
    {
      // ANSI-style function port list with no separate item declarations.
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], NULL, $3.content,
                                  $5, NULL, $8 );
      free( $3.content );
    }
  | vFUNC func_declarator vIDENT '(' func_port_list_opt ')' ';'
    block_item_decl_list func_statement vENDFUNC
    {
      // expression is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], NULL, $3.content,
                                  $5, $8, $9 );
      free( $3.content );
    }
  | vFUNC func_declarator packed_range vIDENT ';'
    func_item_decl_list func_statement vENDFUNC
    {
      // last exp is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], $3, $4.content,
                                  NULL, $6, $7 );
      free( $4.content );
    }
  | vFUNC func_declarator packed_range vIDENT ';'
    func_statement vENDFUNC
    {
      // last exp is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], $3, $4.content,
                                  NULL, NULL, $6 );
      free( $4.content );
    }
  | vFUNC func_declarator packed_range vIDENT '(' func_port_list_opt ')' ';'
    func_statement vENDFUNC
    {
      // ANSI-style function port list with no separate item declarations.
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], $3, $4.content,
                                  $6, NULL, $9 );
      free( $4.content );
    }
  | vFUNC func_declarator packed_range vIDENT '(' func_port_list_opt ')' ';'
    block_item_decl_list func_statement vENDFUNC
    {
      // last exp is id
      $$ = veri_parser->gen_func_decl( $1.line, $1.col, $2.extra[0],
                                  $2.extra[1], $2.extra[2], $3, $4.content,
                                  $6, $9, $10 );
      free( $4.content );
    }
  ;

func_declarator
  : vVOID { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=-1; }
  | integral_type
    { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=$1.extra[1];$$.extra[2]=$1.extra[0]==vvINT?IS_TRUE:$1.extra[0]==vvTIME?2:100+$1.extra[0]; }
  | vBIT %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=100+vvBIT; }
  | vBIT vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_TRUE;$$.extra[2]=100+vvBIT; }
  | vBIT vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=100+vvBIT; }
  | vLOGIC %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=100+vvLOGIC; }
  | vLOGIC vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_TRUE;$$.extra[2]=100+vvLOGIC; }
  | vLOGIC vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=100+vvLOGIC; }
  | vREG %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=100+vvREG; }
  | vREG vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_TRUE;$$.extra[2]=100+vvREG; }
  | vREG vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;$$.extra[1]=IS_FALSE;$$.extra[2]=100+vvREG; }
  | vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = IS_TRUE;
      $$.extra[2] = IS_FALSE;
    }
  | vUNSIGNED
    {
      $$.line=$1.line;$$.col=$1.col;$$.extra[0]=IS_FALSE;
      $$.extra[1]=IS_FALSE;$$.extra[2]=IS_FALSE;
    }
  | vSIGNED vINT
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = IS_FALSE;
      $$.extra[1] = IS_TRUE;
      $$.extra[2] = IS_TRUE;
    }
  | subroutine_lifetime func_declarator
    { if($2.extra[0]!=IS_FALSE) {
        if($1.extra[0]==$2.extra[0])throw std::runtime_error($1.extra[0]==IS_TRUE?"duplicate automatic lifetime qualifier":"duplicate static lifetime qualifier");
        throw std::runtime_error("conflicting subroutine lifetime qualifiers");
      } $$=$2;$$.extra[0]=$1.extra[0]; }

  ;

func_item_decl_list
  : func_item_declaration
    {
      $$ = veri_parser->gen_func_item_list( $1 );
    }
  | func_item_decl_list func_item_declaration
    {
      $$ = veri_parser->append_func_item_list( $1, $2 );
    }
  ;

block_item_decl_list
  : block_item_declaration
    {
      $$ = veri_parser->gen_block_item_list( $1 );
    }
  | block_item_decl_list block_item_declaration
    {
      $$ = veri_parser->append_block_item_list( $1, $2 );
    }
  ;

func_item_declaration
  : block_item_declaration
    {
      $$ = $1;
    }
  | tf_declaration ';'
    {
      $$ = $1;
    }
  ;

func_port_list_opt
  : %empty { $$=NULL; }
  | func_port_list { $$=$1; }
  ;

func_port_list
  : implicit_tf_declaration { $$=veri_parser->gen_fp_list($1); }
  | tf_declaration
    {
      $$ = veri_parser->gen_fp_list( $1 );
    }
  | func_port_list vPORT_DELIM tf_declaration
    {
      $$ = veri_parser->append_fp_list( $1, $3 );
    }
  | func_port_list vPORT_DELIM implicit_tf_declaration
    { static_cast<VeriTfDecl*>($3)->set_inout(static_cast<VeriTfDecl*>(static_cast<rtl::VeriFuncPortList*>($1)->func_port().back())->inout());
      $$=veri_parser->append_fp_list($1,$3); }
  ;

/* A.2.7 Task declarations */
task_declaration
  : task_declaration_body subroutine_end_name
    {
      std::string closing=$2.content?$2.content:"";free($2.content);
      auto declared=static_cast<rtl::VeriTaskDecl*>($1)->task_name();auto split=declared.front()=='\\'?std::string::npos:declared.rfind("::");
      if(!closing.empty()&&closing!=declared.substr(split==std::string::npos?0:split+2))
        { std::string error="task closing label does not match: "+static_cast<rtl::VeriTaskDecl*>($1)->task_name();yyerror(error.c_str());YYERROR; }
      $$=$1;
    }
  ;
task_declaration_body
  : vTASK vIDENT ';' subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, IS_FALSE,
                                  $2.content, NULL, NULL, $4 );
      free($2.content);
    }
  | vTASK vIDENT ';' task_item_decl_list subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, IS_FALSE,
                                  $2.content, NULL, $4, $5 );
      free($2.content);
    }
  | vTASK subroutine_lifetime vIDENT ';' subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, $2.extra[0],
                                  $3.content, NULL, NULL, $5 );
      free($3.content);
    }
  | vTASK subroutine_lifetime vIDENT ';' task_item_decl_list subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, $2.extra[0],
                                  $3.content, NULL, $5, $6 );
      free($3.content);
    }
  | vTASK vIDENT '(' task_port_list_opt ')' ';' subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, IS_FALSE,
                                  $2.content, $4, NULL, $7 );
      free($2.content);
    }
  | vTASK vIDENT '(' task_port_list_opt ')' ';'
    block_item_decl_list subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, IS_FALSE,
                                  $2.content, $4, $7, $8 );
      free($2.content);
    }
  | vTASK subroutine_lifetime vIDENT '(' task_port_list_opt ')' ';'
    subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, $2.extra[0],
                                  $3.content, $5, NULL, $8 );
      free($3.content);
    }
  | vTASK subroutine_lifetime vIDENT '(' task_port_list_opt ')' ';'
    block_item_decl_list subroutine_body vENDTASK
    {
      $$ = veri_parser->gen_task_decl( $1.line, $1.col, $2.extra[0],
                                  $3.content, $5, $8, $9 );
      free($3.content);
    }
  ;

task_item_decl_list
  : task_item_declaration
    {
      $$ = veri_parser->gen_task_item_list( $1 );
    }
  | task_item_decl_list task_item_declaration
    {
      $$ = veri_parser->append_task_item_list( $1, $2 );
    }
  ;

task_item_declaration
  : block_item_declaration
    {
      $$ = $1;
    }
  | tf_declaration ';'
    {
      $$ = $1;
    }
  ;

task_port_list_opt
  : %empty { $$=NULL; }
  | task_port_list { $$=$1; }
  ;

task_port_list
  : implicit_tf_declaration { $$=veri_parser->gen_tp_list($1); }
  | tf_declaration
    {
      $$ = veri_parser->gen_tp_list( $1 );
    }
  | task_port_list vPORT_DELIM tf_declaration
    {
      $$ = veri_parser->append_tp_list( $1, $3 );
    }
  | task_port_list vPORT_DELIM implicit_tf_declaration
    { static_cast<VeriTfDecl*>($3)->set_inout(static_cast<VeriTfDecl*>(static_cast<rtl::VeriTaskPortList*>($1)->task_port().back())->inout());
      $$=veri_parser->append_tp_list($1,$3); }
  ;

tf_port_declarator
  : vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvWIRE;
      $$.extra[1] = IS_TRUE;
    }
  | vREG
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvREG;
      $$.extra[1] = IS_FALSE;
    }
  | vREG vSIGNED
    {
      $$.line = $1.line;
      $$.col  = $1.col;
      $$.extra[0] = vvREG;
      $$.extra[1] = IS_TRUE;
    }
  | vLOGIC %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_FALSE; }
  | vLOGIC vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_TRUE; }
  | vLOGIC vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvLOGIC;$$.extra[1]=IS_FALSE; }
  | vBIT %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_FALSE; }
  | vBIT vSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_TRUE; }
  | vBIT vUNSIGNED %prec INTEGRAL_DEFAULT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vvBIT;$$.extra[1]=IS_FALSE; }
  | integral_type { $$=$1; }
  ;

named_port_ids
  : named_declarator { $$=$1; }
  | named_declarator '=' assignment_expression
    { $$=veri_parser->gen_binary($1,vtASSIGN,$2.line,$2.col,$3); }
  | named_port_ids ',' named_declarator '=' assignment_expression
    { auto* value=veri_parser->gen_binary($3,vtASSIGN,$4.line,$4.col,$5);
      $$=veri_parser->gen_multi($1,value,vemCOMMA_EXP,$2.line,$2.col); }
  | named_port_ids ',' named_declarator
    { $$=veri_parser->gen_multi($1,$3,vemCOMMA_EXP,$2.line,$2.col); }
  ;

tf_direction
  : in_or_out { $$=$1; }
  | vREF { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vpREF; }
  | vCONST vREF { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=vpCONST_REF; }
  ;

implicit_tf_declaration
  : virtual_interface_type named_port_ids
    { $$=veri_parser->gen_tf_declaration($1->line(),$1->col(),vpIN,vvLONGINT,IS_FALSE,NULL,$2);static_cast<VeriTfDecl*>($$)->set_type_expression($1); }
  | tf_port_declarator named_port_ids
    { if(!veri_parser->systemverilog())throw std::runtime_error("implicit typed formal direction requires SystemVerilog mode");
      $$=veri_parser->gen_tf_declaration($1.line,$1.col,vpIN,$1.extra[0],$1.extra[1],NULL,$2); }

  | class_application named_port_ids
    { $$=veri_parser->gen_tf_declaration($1->line(),$1->col(),vpIN,vvCLASS,IS_FALSE,NULL,$2);static_cast<VeriTfDecl*>($$)->set_type_expression($1); }

  | tf_port_declarator packed_range named_port_ids
    { if(!veri_parser->systemverilog())throw std::runtime_error("implicit typed formal direction requires SystemVerilog mode");
      $$=veri_parser->gen_tf_declaration($1.line,$1.col,vpIN,$1.extra[0],$1.extra[1],$2,$3); }
  | vIDENT named_port_ids
    {
      if(!veri_parser->systemverilog())throw std::runtime_error("implicit typed formal direction requires SystemVerilog mode");
      $$=veri_parser->gen_tf_declaration($1.line,$1.col,vpIN,vvLOGIC,IS_FALSE,NULL,$2);
      static_cast<VeriTfDecl*>($$)->set_type_name($1.content);free($1.content);
    }
  ;

tf_declaration
  : tf_direction virtual_interface_type named_port_ids
    { $$=veri_parser->gen_tf_declaration($1.line,$1.col,$1.extra[0],vvLONGINT,IS_FALSE,NULL,$3);static_cast<VeriTfDecl*>($$)->set_type_expression($2); }
  | tf_direction vIDENT named_port_ids
    { $$=veri_parser->gen_tf_declaration($1.line,$1.col,$1.extra[0],vvLOGIC,IS_FALSE,NULL,$3);
      static_cast<VeriTfDecl*>($$)->set_type_name($2.content);free($2.content); }
  | tf_direction class_application named_port_ids
    { $$=veri_parser->gen_tf_declaration($1.line,$1.col,$1.extra[0],vvCLASS,IS_FALSE,NULL,$3);static_cast<VeriTfDecl*>($$)->set_type_expression($2); }

  | tf_direction named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $1.line, $1.col, $1.extra[0],
                                           vvWIRE, IS_FALSE, NULL, $2 );
    }
  | tf_direction tf_port_declarator named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $1.line, $1.col, $1.extra[0],
                                           $2.extra[0], $2.extra[1], NULL,
                                           $3 );
    }
  | attr_inst_list tf_direction named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $2.line, $2.col, $2.extra[0],
                                           vvWIRE, IS_FALSE, NULL, $3 );
    }
  | attr_inst_list tf_direction tf_port_declarator named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $2.line, $2.col, $2.extra[0],
                                           $3.extra[0], $3.extra[1], NULL,
                                           $4 );
    }
  | tf_direction packed_range named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $1.line, $1.col, $1.extra[0],
                                           vvWIRE, IS_FALSE, $2, $3 );
    }
  | tf_direction tf_port_declarator packed_range named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $1.line, $1.col, $1.extra[0],
                                           $2.extra[0], $2.extra[1], $3,
                                           $4 );
    }
  | attr_inst_list tf_direction packed_range named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $2.line, $2.col, $2.extra[0],
                                           vvWIRE, IS_FALSE, $3,
                                           $4 );
    }
  | attr_inst_list tf_direction tf_port_declarator packed_range named_port_ids
    {
      // port-identifier-list
      $$ = veri_parser->gen_tf_declaration( $2.line, $2.col, $2.extra[0],
                                           $3.extra[0], $3.extra[1], $4,
                                           $5 );
    }
  ;

/* A.2.8 Block item declarations */
block_item_declaration
  : import_declaration { $$=$1; }
  | vCONST block_item_declaration { $$=veri_parser->qualify_const_property($2); }
  | typedef_declaration { $$=$1; }
  | vAUTO block_item_declaration
    {
      if($2->detail_type()!=vsDECL_VAR && $2->detail_type()!=vsDECL_INT)
        throw std::runtime_error("automatic requires a local variable declaration");
      auto* decl=static_cast<rtl::VeriDecl*>($2);
      if(decl->explicit_automatic())throw std::runtime_error("duplicate automatic lifetime qualifier");
      if(decl->explicit_static())throw std::runtime_error("conflicting lifetime qualifiers");
      if($2->detail_type()==vsDECL_VAR && static_cast<rtl::VeriVarDecl*>($2)->is_typedef())
        throw std::runtime_error("automatic requires a local variable declaration");
      decl->set_explicit_automatic();$$=$2;
    }
  | vSTATIC block_item_declaration
    {
      if($2->detail_type()!=vsDECL_VAR && $2->detail_type()!=vsDECL_INT)
        throw std::runtime_error("static requires a local variable declaration");
      auto* decl=static_cast<rtl::VeriDecl*>($2);
      if(decl->explicit_static())throw std::runtime_error("duplicate static lifetime qualifier");
      if(decl->explicit_automatic())throw std::runtime_error("conflicting lifetime qualifiers");
      if($2->detail_type()==vsDECL_VAR && static_cast<rtl::VeriVarDecl*>($2)->is_typedef())
        throw std::runtime_error("static requires a local variable declaration");
      decl->set_explicit_static();$$=$2;
    }
  | named_declaration { $$=$1; }
  | reg_declaration
    {
      $$ = $1;
    }
  | int_declaration
    {
      $$ = $1;
    }
  | param_declaration
    {
      $$ = $1;
    }
  | attr_inst_list reg_declaration
    {
      $$ = $2;
    }

  | attr_inst_list param_declaration
    {
      $$ = $2;
    }
  | attr_inst_list int_declaration
    {
      $$ = $2;
    }
  ;

/* A.3 Primitive instances */
/* A.3.1 Primitive instantiation and instances */

/* Keep terminal commas inside an instance separate from commas between
 * instances. The old expression production flattened unnamed port groups. */
gate_instantiation
  : gatetype gate_instance_list ';'
    {
      $$ = veri_parser->gen_gate_instantiation( $1.line, $1.col,
                               $1.extra[0], NULL, NULL, $2 );
    }
  | gatetype drive_strength gate_instance_list ';'
    {
      $$ = veri_parser->gen_gate_instantiation( $1.line, $1.col,
                               $1.extra[0], $2, NULL, $3 );
    }
  | gatetype procedural_delay gate_instance_list ';'
    {
      $$ = veri_parser->gen_gate_instantiation( $1.line, $1.col,
                               $1.extra[0], NULL, $2, $3 );
    }
  | gatetype drive_strength procedural_delay gate_instance_list ';'
    {
      $$ = veri_parser->gen_gate_instantiation( $1.line, $1.col,
                               $1.extra[0], $2, $3, $4 );
    }
  ;

gate_instance_list
  : gate_instance
    {
      $$ = veri_parser->gen_mod_item_list($1);
    }
  | gate_instance_list ',' gate_instance
    {
      $$ = veri_parser->append_mod_item_list($1, $3);
    }
  ;

gate_instance
  : '(' expression ')'
    {
      $$ = veri_parser->gen_gate_instance($2, true);
    }
  | vIDENT '(' expression ')'
    {
      VeriNode *name = veri_parser->gen_primary($1.content, $1.line, $1.col, veVAR);
      free($1.content);
      $$ = veri_parser->gen_gate_instance(veri_parser->gen_caller(name, $3));
    }
  | vIDENT range '(' expression ')'
    {
      VeriNode *name = veri_parser->gen_primary($1.content, $1.line, $1.col, veVAR);
      free($1.content);
      $$ = veri_parser->gen_gate_instance(veri_parser->gen_caller(veri_parser->gen_array(name, $2), $4));
    }
  ;

/* A.3.2 Primitive strengths */
/* A.3.3 Primitive terminals */

/* A.3.4 Primitive gate and switch types */
gatetype
  : vBUFIF_A
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpBUFFIF0;
    }
  | vBUFIF_B
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpBUFFIF1;
    }
  | vNOTIF_A
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpNOTIF0;
    }
  | vNOTIF_B
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpNOTIF1;
    }
  | vAND_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpAND;
    }
  | vNAND_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpNAND;
    }
  | vOR_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpOR;
    }
  | vNOR_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpNOR;
    }
  | vXOR_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpXOR;
    }
  | vXNOR_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpXNOR;
    }
  | vBUF_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpBUF;
    }
  | vNOT_ASCII
    {
      $$.line  = $1.line;
      $$.col   = $1.col;
      $$.extra[0] = vpNOT;
    }
  ;

/* A.4 Module and generated instantiation */

/* A.4.1 Module instantiation */
/* module-instantiation status added for ignoring # */
module_instantiation
  : vIDENT expression ';'
    {
      $$ = veri_parser->gen_mod_instantiation( $1.line, $1.col,
                                   $1.content, NULL, $2 );
      free($1.content);
    }
  | vIDENT '#' '(' class_arguments_opt ')' expression ';'
    {
      /* second is param-val-assignment */
      /* third is module-instance-list */
      $$ = veri_parser->gen_mod_instantiation( $1.line, $1.col,
                                   $1.content, $4, $6 );
      free($1.content);
    }
  ;

/* A.4.2 Generated instantiation */
generated_instantiation
  : vGEN vENDGEN
    {
      $$ = veri_parser->gen_dummy_inst( $1.line, $1.col );
    }
  | vGEN gen_item_list vENDGEN
    {
      $$ = $2;
    }
  ;

gen_item_list
  : gen_item
    {
      $$ = veri_parser->gen_gen_item_list( $1 );
    }
  | gen_item_list gen_item
    {
      $$ = veri_parser->append_gen_item_list( $1, $2 );
    }
  ;

gen_item_or_null
  : gen_item
    {
      $$ = $1;
    }
  | ';'
    {
      $$ = veri_parser->gen_dummy_inst( $1.line, $1.col );
    }
  ;

gen_item
  : gen_cond_statement
    {
      $$ = $1;
    }
  | gen_case_statement
    {
      $$ = $1;
    }
  | gen_loop_statement
    {
      $$ = $1;
    }
  | gen_block
    {
      $$ = $1;
    }
  | param_declaration
    { $$ = $1; }
  | module_or_gen_item
    {
      $$ = $1;
    }
  ;

gen_cond_statement
  : vIF '(' expression ')' gen_item_or_null %prec LOWER_THAN_ELSE
    {
      // const-expression
      // 1 expression only
      $$ = veri_parser->gen_gen_cond_stmt( $1.line, $1.col, $3,
                                                $5, NULL );
    }
  | vIF '(' expression ')' gen_item_or_null vELSE gen_item_or_null
    {
      // const-expression
      // 1 expression only
      $$ = veri_parser->gen_gen_cond_stmt( $1.line, $1.col, $3,
                                                $5, $7 );
    }
  ;

gen_case_statement
  : vCASE '(' expression ')' genvar_case_item_list vENDCASE
    {
      // const-expression
      // 1 expression only
      $$ = veri_parser->gen_gen_case_stmt( $1.line, $1.col,
                                                $3, $5 );
    }
  ;

genvar_case_item_list
  : genvar_case_item
    {
      $$ = veri_parser->gen_gen_case_item_list( $1 );
    }
  | genvar_case_item_list genvar_case_item
    {
      $$ = veri_parser->append_gen_case_item_list( $1, $2 );
    }
  ;

genvar_case_item
  : expression ':' gen_item_or_null
    {
      // const-exp-list
      $$ = veri_parser->gen_gen_case_item( $1, $3 );
    }
  | vDEFAULT gen_item_or_null
    {
      $$ = veri_parser->gen_default_gen_case_item( $1.line, $1.col,
                                                        $2 );
    }
  | vDEFAULT ':' gen_item_or_null
    {
      $$ = veri_parser->gen_default_gen_case_item( $1.line, $1.col,
                                                        $3 );
    }
  ;

gen_loop_statement
  : vFOR '(' expression ';' expression ';' expression ')'
    vBEGIN ':' vIDENT vEND
    {
      // const-expression
      // 1 expression only
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, $3, $5,
                                $7, $11.content, $11.line, $11.col, NULL );
      free($11.content);
    }
  | vFOR '(' expression ';' expression ';' expression ')'
    vBEGIN ':' vIDENT gen_item_list vEND
    {
      // const-expression
      // 1 expression only
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, $3, $5,
                                $7, $11.content, $11.line, $11.col, $12 );
      free($11.content);
    }
  | vFOR '(' expression ';' expression ';' expression ')'
    vBEGIN vEND
    {
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, $3, $5,
                                $7, NULL, -1, -1, NULL );
    }
  | vFOR '(' expression ';' expression ';' expression ')'
    vBEGIN gen_item_list vEND
    {
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, $3, $5,
                                $7, NULL, -1, -1, $10 );
    }
  | vFOR '(' vGENVAR vIDENT '=' expression ';' expression ';' expression ')'
    vBEGIN ':' vIDENT vEND
    {
      /* build: genvar_i = init_expr as assignment */
      VeriNode * init_assign = veri_parser->gen_binary(
        veri_parser->gen_primary( $4.content, $4.line, $4.col, veVAR ),
        vtASSIGN, $5.line, $5.col, $6 );
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, init_assign, $8,
                                $10, $14.content, $14.line, $14.col, NULL );
      free($14.content);
      static_cast<rtl::VeriGenLoop*>($$)->set_inline_genvar(true);
    }
  | vFOR '(' vGENVAR vIDENT '=' expression ';' expression ';' expression ')'
    vBEGIN ':' vIDENT gen_item_list vEND
    {
      VeriNode * init_assign = veri_parser->gen_binary(
        veri_parser->gen_primary( $4.content, $4.line, $4.col, veVAR ),
        vtASSIGN, $5.line, $5.col, $6 );
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, init_assign, $8,
                                $10, $14.content, $14.line, $14.col, $15 );
      free($14.content);
      static_cast<rtl::VeriGenLoop*>($$)->set_inline_genvar(true);
    }
  | vFOR '(' vGENVAR vIDENT '=' expression ';' expression ';' expression ')'
    vBEGIN vEND
    {
      VeriNode * init_assign = veri_parser->gen_binary(
        veri_parser->gen_primary( $4.content, $4.line, $4.col, veVAR ),
        vtASSIGN, $5.line, $5.col, $6 );
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, init_assign, $8,
                                $10, NULL, -1, -1, NULL );
      static_cast<rtl::VeriGenLoop*>($$)->set_inline_genvar(true);
    }
  | vFOR '(' vGENVAR vIDENT '=' expression ';' expression ';' expression ')'
    vBEGIN gen_item_list vEND
    {
      VeriNode * init_assign = veri_parser->gen_binary(
        veri_parser->gen_primary( $4.content, $4.line, $4.col, veVAR ),
        vtASSIGN, $5.line, $5.col, $6 );
      $$ = veri_parser->gen_gen_loop_stmt( $1.line, $1.col, init_assign, $8,
                                $10, NULL, -1, -1, $13 );
      static_cast<rtl::VeriGenLoop*>($$)->set_inline_genvar(true);
    }
  ;

gen_block
  : vBEGIN vEND
    {
      $$ = veri_parser->gen_gen_block_stmt( $1.line, $1.col, NULL, -1, -1,
                                            NULL );
    }
  | vBEGIN gen_item_list vEND
    {
      $$ = veri_parser->gen_gen_block_stmt( $1.line, $1.col, NULL, -1, -1,
                                            $2 );
    }
  | vBEGIN ':' vIDENT vEND
    {
      $$ = veri_parser->gen_gen_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, NULL );
      free($3.content);
    }
  | vBEGIN ':' vIDENT gen_item_list vEND
    {
      $$ = veri_parser->gen_gen_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, $4 );
      free($3.content);
    }
  ;

/* A.5 UDP declaration and instantiation */
/* A.5.1 UDP declaration */
udp_declaration
  : vPRIMITIVE vENDPRI
    {
    }
  | attr_inst_list vPRIMITIVE vENDPRI
    {
    }
  ;

/* A.5.2 UDP ports */
/* A.5.3 UDP body */
/* A.5.4 UDP instantiation */

/* A.6 Behavioral statements */

/* A.6.1 Continuous assignment statements */
continuous_assign
  : vASSIGN expression ';'
    {
      $$ = veri_parser->gen_continuous_assign_stmt( $1.line, $1.col,
                                    NULL, NULL, $2 );
    }
  | vASSIGN drive_strength expression ';'
    {
      $$ = veri_parser->gen_continuous_assign_stmt( $1.line, $1.col,
                                    NULL, $2, $3 );
    }
  | vASSIGN delay3 expression ';'
    {
      $$ = veri_parser->gen_continuous_assign_stmt( $1.line, $1.col,
                                    $2, NULL, $3 );
    }
  | vASSIGN drive_strength delay3 expression ';'
    {
      $$ = veri_parser->gen_continuous_assign_stmt( $1.line, $1.col,
                                    $2, $3, $4 );
    }
  ;

/* A.6.2 Procedural blocks and assignments */
assignment_event_control
  : event_control { $$=$1; }
  | vREPEAT '(' expression ')' event_control
    {
      auto* body=veri_parser->gen_proc_timing_control_stmt($5,veri_parser->gen_dummy_stmt($1.line,$1.col));
      $$=veri_parser->gen_loop_stmt($1.line,$1.col,NULL,$3,NULL,body,rtl::VeriLoopStmt::REPEAT);
    }
  ;

blocking_assignment
  : unary_expression '=' assignment_event_control expression
    {
      // 1 expression only
      $$ = veri_parser->gen_blocking_stmt( $1, $3, $4 );
    }
  | unary_expression '=' procedural_delay expression
    {
      $$ = veri_parser->gen_blocking_stmt( $1, $3, $4 );
    }
  | expression '=' expression
    {
      // blocking assignment without timing control
      $$ = veri_parser->gen_blocking_stmt( $1, NULL, $3 );
    }
  ;

nonblocking_assignment
  : unary_expression vLE assignment_event_control expression
    {
      // 1 expression only
      $$ = veri_parser->gen_non_blocking_stmt( $1, $3, $4);
    }
  | unary_expression vLE procedural_delay expression
    {
      $$ = veri_parser->gen_non_blocking_stmt( $1, $3, $4 );
    }
  | unary_expression vLE expression %prec LOWER_THAN_C
    {
      // nonblocking assignment without timing control
      $$ = veri_parser->gen_non_blocking_stmt( $1, NULL, $3 );
    }
  ;


/* A.6.3 Parallel and sequential blocks */


stmt_list
  : stmt_or_null
    {
      $$ = veri_parser->gen_stmt_list( $1 );
    }
  | stmt_list stmt_or_null
    {
      $$ = veri_parser->append_stmt_list( $1, $2 );
    }
  ;

seq_block
  : seq_block_body { $$=$1; }
  | seq_block_body ':' vIDENT
    {
      std::string closing($3.content);free($3.content);
      if(static_cast<rtl::VeriSeqBlock*>($1)->label().empty()||static_cast<rtl::VeriSeqBlock*>($1)->label()!=closing)
        { yyerror("block closing label does not match opening label");YYERROR; }
      $$=$1;
    }
  ;

seq_block_body
  : vBEGIN vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, NULL, NULL );
    }
  | vBEGIN stmt_list vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, NULL, $2 );
    }
  | vBEGIN block_item_decl_list vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, $2, NULL );
    }
  | vBEGIN block_item_decl_list stmt_list vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, $2, $3 );
    }
  | vBEGIN ':' vIDENT vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, NULL, NULL );
      free($3.content);
    }
  | vBEGIN ':' vIDENT stmt_list vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, NULL, $4 );
      free($3.content);
    }
  | vBEGIN ':' vIDENT block_item_decl_list vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, $4, NULL );
      free($3.content);
    }
  | vBEGIN ':' vIDENT block_item_decl_list stmt_list vEND
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, $4, $5 );
      free($3.content);
    }
  ;

parallel_block
  : parallel_block_body { $$=$1; }
  | parallel_block_body ':' vIDENT
    {
      std::string closing($3.content);free($3.content);
      if(static_cast<rtl::VeriSeqBlock*>($1)->label().empty()||static_cast<rtl::VeriSeqBlock*>($1)->label()!=closing)
        { yyerror("block closing label does not match opening label");YYERROR; }
      $$=$1;
    }
  ;

parallel_block_body
  : vFORK fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, NULL, NULL );
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($2);
    }
  | vFORK stmt_list fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, NULL, $2 );
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($3);
    }
  | vFORK block_item_decl_list fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, $2, NULL );
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($3);
    }
  | vFORK block_item_decl_list stmt_list fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, NULL,
                                            -1, -1, $2, $3 );
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($4);
    }
  | vFORK ':' vIDENT fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, NULL, NULL );
      free($3.content);
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($4);
    }
  | vFORK ':' vIDENT stmt_list fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, NULL, $4 );
      free($3.content);
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($5);
    }
  | vFORK ':' vIDENT block_item_decl_list fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, $4, NULL );
      free($3.content);
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($5);
    }
  | vFORK ':' vIDENT block_item_decl_list stmt_list fork_join_keyword
    {
      $$ = veri_parser->gen_seq_block_stmt( $1.line, $1.col, $3.content,
                                            $3.line, $3.col, $4, $5 );
      free($3.content);
      static_cast<rtl::VeriSeqBlock*>($$)->set_parallel_kind($6);
    }
  ;

fork_join_keyword
  : vJOIN { $$=1; }
  | vJOIN_ANY { $$=2; }
  | vJOIN_NONE { $$=3; }
  ;

/* A.6.4 Statements */
statement
  : expression ';'
    {
      /* '=' is blocking, '<=' is non-blocking */
      $$ = veri_parser->gen_block_or_non_or_caller_stmt( $1 );
    }
  | vFORCE unary_expression '=' assignment_expression ';'
    { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_FORCE,$2,$4,0); }
  | vRELEASE unary_expression ';'
    { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_RELEASE,$2,NULL,0); }
  | vVOID '\'' '(' expression ')' ';'
    {
      if($4->detail_type()!=veEXP_CALLER&&$4->detail_type()!=veEXP_MEMBER&& !($4->detail_type()==veEXP_UNA&&(static_cast<rtl::VeriUnaryExp*>($4)->op()==vtSYS_CAST||veri_is_random(static_cast<rtl::VeriUnaryExp*>($4)->op())||veri_is_testbench_function(static_cast<rtl::VeriUnaryExp*>($4)->op()))))throw std::runtime_error("void discard requires a function call");
      $$=veri_parser->gen_block_or_non_or_caller_stmt($4);
      static_cast<rtl::VeriCallerStmt*>($$)->set_discard();
    }
  | blocking_assignment ';'
    {
      $$ = $1;
    }
  | case_statement
    {
      $$ = $1;
    }
  | cond_statement
    {
      $$ = $1;
    }
  | immediate_assertion_statement { $$=$1; }
  | wait_order_statement { $$=$1; }
  | vIDENT ':' immediate_assertion_statement
    { static_cast<rtl::VeriCondStmt*>($3)->set_assertion_label($1.content);free($1.content);$$=$3; }
  | disable_statement
    {
      $$ = $1;
    }
  | loop_statement
    {
      $$ = $1;
    }
  | nonblocking_assignment ';'
    {
      $$ = $1;
    }
  | procedural_timing_control_statement
    {
      $$ = $1;
    }
  | vTRIGGER unary_expression ';'
    { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_EVENT_TRIGGER,$2,NULL,0); }
  | vNBA_TRIGGER unary_expression ';'
    { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_EVENT_TRIGGER,$2,NULL,1); }
  | vNBA_TRIGGER delay3 unary_expression ';'
    { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_EVENT_TRIGGER,$3,$2,1); }
  | vWAIT vFORK ';' { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_WAIT_FORK,NULL,NULL,0); }
  | vWAIT '(' expression ')' stmt_or_null
    {
      $$ = veri_parser->gen_proc_timing_control_stmt($3, $5, true);
    }
  | parallel_block { $$=$1; }
  | seq_block
    {
      $$ = $1;
    }
  | sys_caller
    {
      $$ = $1;
    }
  | attr_inst_list blocking_assignment ';'
    {
      $$ = $2;
    }
  | attr_inst_list case_statement
    {
      $$ = $2;
    }
  | attr_inst_list cond_statement
    {
      $$ = $2;
    }
  | attr_inst_list disable_statement
    {
      $$ = $2;
    }
  | attr_inst_list loop_statement
    {
      $$ = $2;
    }
  | attr_inst_list nonblocking_assignment ';'
    {
      $$ = $2;
    }
  | attr_inst_list procedural_timing_control_statement
    {
      $$ = $2;
    }
  | attr_inst_list parallel_block { $$=$2; }
  | attr_inst_list seq_block
    {
      $$ = $2;
    }
  | attr_inst_list sys_caller
    {
      $$ = $2;
    }
  | compound_assignment ';' { $$=$1; }
  | vRETURN ';' { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_RETURN,NULL,NULL,0); }
  | vRETURN expression ';' { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_RETURN,NULL,$2,0); }
  | vBREAK ';' { $$=veri_parser->gen_loop_jump($1.line,$1.col,false); }
  | vCONTINUE ';' { $$=veri_parser->gen_loop_jump($1.line,$1.col,true); }
  ;

compound_operator
  : vADD_EQ { $$=vtBADD; } | vSUB_EQ { $$=vtBSUB; }
  | vMUL_EQ { $$=vtBMUL; } | vDIV_EQ { $$=vtBDIV; } | vMOD_EQ { $$=vtBMOD; }
  | vAND_EQ { $$=vtBSAND; } | vOR_EQ { $$=vtBSOR; } | vXOR_EQ { $$=vtBSXOR; }
  | vLS_EQ { $$=vtBLLS; } | vRS_EQ { $$=vtBLRS; }
  | vALS_EQ { $$=vtBALS; } | vARS_EQ { $$=vtBARS; }
  ;
compound_assignment
  : unary_expression compound_operator assignment_expression {
      $$=veri_parser->gen_action_stmt($1->line(),$1->col(),vsSTMT_COMPOUND,$1,$3,$2);
    }
  ;

for_step
  : assignment_expression { $$=veri_parser->gen_block_or_non_or_caller_stmt($1); }
  | compound_assignment { $$=$1; }
  ;
for_steps
  : for_step { $$=veri_parser->gen_stmt_list($1); }
  | for_steps ',' for_step { $$=veri_parser->append_stmt_list($1,$3); }
  ;
for_steps_opt
  : %empty { $$=NULL; }
  | for_steps { $$=$1; }
  ;
for_condition
  : %empty { $$=NULL; }
  | expression { $$=$1; }
  ;

stmt_or_null
  : statement
    {
      $$ = $1;
    }
  | ';'
    {
      $$ = veri_parser->gen_dummy_stmt( $1.line, $1.col );
    }
  | attr_inst_list ';'
    {
      $$ = veri_parser->gen_dummy_stmt( $2.line, $2.col );
    }
  ;

subroutine_body
  : stmt_list { $$=$1; }
  | %empty { $$=veri_parser->gen_seq_block_stmt(0,0,NULL,0,0,NULL,NULL); }
  ;

func_statement
  : subroutine_body { $$=$1; }
  ;

coverage_declaration
  : vCOVERGROUP vIDENT coverage_event ';' coverage_items vENDGROUP package_end_name
    { $$=veri_parser->gen_covergroup($1.line,$1.col,$2.content,$3,$5,$7.content);free($2.content);free($7.content); }
  | vCOVERGROUP vIDENT '(' ')' coverage_event ';' coverage_items vENDGROUP package_end_name
    { $$=veri_parser->gen_covergroup($1.line,$1.col,$2.content,$5,$7,$9.content);free($2.content);free($9.content); }
  ;
coverage_event
  : %empty { $$=nullptr; }
  | event_control { $$=$1; }
  ;
coverage_items
  : %empty { $$=nullptr; }
  | coverage_items coverage_item { $$=$1?veri_parser->append_mod_item_list($1,$2):veri_parser->gen_mod_item_list($2); }
  ;
coverage_item
  : vIDENT ':' vCOVERPOINT expression coverage_iff coverage_body
    { $$=clocking_node(vsDECL_COVERPOINT,$1.content,{$4,$5,$6});free($1.content); }
  | vCOVERPOINT expression coverage_iff coverage_body
    { $$=clocking_node(vsDECL_COVERPOINT,"",{$2,$3,$4}); }
  | vIDENT ':' vCROSS coverage_cross_names coverage_iff coverage_body
    { $$=clocking_node(vsDECL_COVER_CROSS,$1.content,{$4,$5,$6});free($1.content); }
  | vCROSS coverage_cross_names coverage_iff coverage_body
    { $$=clocking_node(vsDECL_COVER_CROSS,"",{$2,$3,$4}); }
  | coverage_option { $$=$1; }
  ;
coverage_cross_names
  : vIDENT ',' vIDENT
    { auto* a=clocking_node(vsDECL_COVER_RANGE,$1.content);auto* b=clocking_node(vsDECL_COVER_RANGE,$3.content);free($1.content);free($3.content);$$=veri_parser->append_mod_item_list(veri_parser->gen_mod_item_list(a),b); }
  | coverage_cross_names ',' vIDENT
    { auto* item=clocking_node(vsDECL_COVER_RANGE,$3.content);free($3.content);$$=veri_parser->append_mod_item_list($1,item); }
  ;
coverage_iff
  : %empty { $$=nullptr; }
  | vIFF '(' expression ')' { $$=$3; }
  ;
coverage_body
  : ';' { $$=nullptr; }
  | '{' coverage_bins '}' { $$=$2; }
  ;
coverage_bins
  : %empty { $$=nullptr; }
  | coverage_bins coverage_bin { $$=$1?veri_parser->append_mod_item_list($1,$2):veri_parser->gen_mod_item_list($2); }
  | coverage_bins coverage_option { $$=$1?veri_parser->append_mod_item_list($1,$2):veri_parser->gen_mod_item_list($2); }
  ;
coverage_option
  : vIDENT '.' vIDENT '=' assignment_expression ';'
    { const auto name=std::string($1.content)+"."+$3.content;free($1.content);free($3.content);$$=clocking_node(vsDECL_COVER_OPTION,name,{$5}); }
  ;
coverage_bin_kind
  : vBINS { $$=0; }
  | vIGNORE_BINS { $$=1; }
  | vILLEGAL_BINS { $$=2; }
  ;
coverage_bin
  : coverage_bin_kind vIDENT '=' '{' coverage_values '}' coverage_iff ';'
    { $$=clocking_node(vsDECL_COVER_BIN,$2.content,{$5,$7},$1);free($2.content); }
  | coverage_bin_kind vIDENT '[' ']' '=' '{' coverage_values '}' coverage_iff ';'
    { $$=clocking_node(vsDECL_COVER_BIN,$2.content,{$7,$9},$1,true);free($2.content); }
  | coverage_bin_kind vIDENT '=' vDEFAULT ';'
    { $$=clocking_node(vsDECL_COVER_BIN,$2.content,{nullptr,nullptr},$1);free($2.content); }
  ;
coverage_values
  : coverage_value { $$=veri_parser->gen_mod_item_list($1); }
  | coverage_values ',' coverage_value { $$=veri_parser->append_mod_item_list($1,$3); }
  ;
coverage_value
  : assignment_expression { $$=clocking_node(vsDECL_COVER_RANGE,"",{$1,nullptr}); }
  | '[' assignment_expression ':' assignment_expression ']' { $$=clocking_node(vsDECL_COVER_RANGE,"",{$2,$4}); }
  ;

clocking_declaration
  : vCLOCKING vIDENT event_control ';' clocking_items vENDCLOCKING package_end_name
    {
      if($7.content&&std::string($7.content)!=$2.content)throw std::runtime_error("clocking closing label does not match");
      $$=clocking_node(vsDECL_CLOCKING,$2.content,{$3,$5});free($2.content);free($7.content);
    }
  | vDEFAULT clocking_declaration
    {
      if($2->detail_type()!=vsDECL_CLOCKING)throw std::runtime_error("invalid default clocking declaration");
      static_cast<rtl::VeriClocking*>($2)->default_clock=true;$$=$2;
    }
  | vDEFAULT vCLOCKING vIDENT ';'
    { $$=clocking_node(vsDECL_DEFAULT_CLOCKING,$3.content);free($3.content); }
  ;
clocking_items
  : %empty { $$=NULL; }
  | clocking_items clocking_item
    { $$=$1?veri_parser->append_mod_item_list($1,$2):veri_parser->gen_mod_item_list($2); }
  ;
clocking_item
  : vINPUT clocking_skew_opt clocking_signals ';' { $$=clocking_ports($3,vpIN,$2); }
  | vOUTPUT clocking_skew_opt clocking_signals ';' { $$=clocking_ports($3,vpOUT,$2); }
  | vDEFAULT vINPUT clocking_skew ';' { $$=clocking_default(vpIN,$3); }
  | vDEFAULT vOUTPUT clocking_skew ';' { $$=clocking_default(vpOUT,$3); }
  | vDEFAULT vINPUT clocking_skew vOUTPUT clocking_skew ';'
    { $$=veri_parser->append_mod_item_list(veri_parser->gen_mod_item_list(clocking_default(vpIN,$3)),clocking_default(vpOUT,$5)); }
  ;
clocking_signals
  : clocking_signal { $$=veri_parser->gen_mod_item_list($1); }
  | clocking_signals ',' clocking_signal { $$=veri_parser->append_mod_item_list($1,$3); }
  ;
clocking_signal
  : vIDENT
    { auto* source=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);$$=clocking_node(vsDECL_CLOCKING_ITEM,$1.content,{source});free($1.content); }
  | vIDENT '=' assignment_expression { $$=clocking_node(vsDECL_CLOCKING_ITEM,$1.content,{$3});free($1.content); }
  ;
clocking_skew_opt
  : %empty { $$=NULL; }
  | clocking_skew { $$=$1; }
  ;
clocking_skew
  : '#' vSTEP { $$=clocking_node(vsDECL_CLOCKING_ITEM,"",{},0,true); }
  | procedural_delay { $$=clocking_node(vsDECL_CLOCKING_ITEM,"",{$1}); }
  ;

/* A.6.5 Timing control statements */
event_control
  : '@' vIDENT %prec LOWER_THAN_A
    {
      $$ = veri_parser->gen_event_stmt( $1.line, $1.col, IS_FALSE,
                         veri_parser->gen_primary( $2.content, $2.line,
                                                   $2.col, veVAR ));
      free($2.content);
    }
  | '@' vIDENT '.' vIDENT
    {
      $$=veri_parser->gen_event_stmt($1.line,$1.col,IS_FALSE,
        veri_parser->gen_member(veri_parser->gen_primary($2.content,$2.line,$2.col,veVAR),$4.content,$4.line,$4.col));
      free($2.content);free($4.content);
    }
  | '@' '(' expression ')'
    {
      /* event expression check, only id or event expression list */
      $$ = veri_parser->gen_event_stmt( $1.line, $1.col,
                                             IS_FALSE, $3 );
    }
  | '@' '*'
    {
      $$ = veri_parser->gen_event_stmt( $1.line, $1.col, IS_TRUE, NULL );
    }
  | '@' vEVENT_ALL
    {
      $$ = veri_parser->gen_event_stmt( $1.line, $1.col, IS_TRUE, NULL );
    }
  ;

disable_statement
  : vDISABLE vFORK ';' { $$=veri_parser->gen_action_stmt($1.line,$1.col,vsSTMT_DISABLE_FORK,NULL,NULL,0); }
  | vDISABLE vIDENT ';'
    {
      // hier_block_identifier
      // original --> hier-block-identifier or hier-task-identifier
      // ori --> hier identifier
      $$ = veri_parser->gen_disable_stmt( $2.content, $1.line, $1.col );
      free($2.content);
    }
  ;

// Procedural delay uses a delay_value, not a free unparenthesized expression.
// This avoids ambiguities between the delay expression and the next statement.
procedural_delay
  : '#' vNUMBER
    {
      $$ = veri_parser->gen_delay_exp($1.line, $1.col,
          veri_parser->gen_primary($2.content, $2.line, $2.col, veNUM), NULL);
      free($2.content);
    }
  | '#' vTIME_LITERAL
    {
      $$ = veri_parser->gen_delay_exp($1.line,$1.col,
          veri_parser->gen_time_literal($2.content,$2.line,$2.col),NULL);
      free($2.content);
    }
  | '#' vIDENT
    {
      $$ = veri_parser->gen_delay_exp($1.line, $1.col,
          veri_parser->gen_primary($2.content, $2.line, $2.col, veVAR), NULL);
      free($2.content);
    }
  | '#' '(' expression ')'
    {
      $$ = veri_parser->gen_delay_exp($1.line, $1.col, $3, NULL);
    }
  ;

procedural_timing_control_statement
  : vCYCLEDELAY sva_cycle_count stmt_or_null { $$=clocking_node(vsSTMT_CYCLE_CONTROL,"",{$2,$3}); }
  | event_control stmt_or_null
    {
      $$ = veri_parser->gen_proc_timing_control_stmt( $1, $2 );
    }
  | procedural_delay stmt_or_null
    {
      $$ = veri_parser->gen_proc_timing_control_stmt( $1, $2 );
    }
  ;

/* A.6.6 Conditional statements */
unique_priority
  : vUNIQUE { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=1; }
  | vUNIQUE0 { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=2; }
  | vPRIORITY { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=3; }
  ;
cond_head
  : vIF { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=0; }
  | unique_priority vIF { $$=$1; }
  ;
cond_statement
  : cond_head '(' expression ')' stmt_or_null %prec LOWER_THAN_ELSE
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,NULL);
      static_cast<rtl::VeriCondStmt*>($$)->set_selection_qualifier($1.extra[0]); }
  | cond_head '(' expression ')' stmt_or_null vELSE stmt_or_null
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,$7);
      static_cast<rtl::VeriCondStmt*>($$)->set_selection_qualifier($1.extra[0]); }
  ;


/* A.6.7 Case statements */
/* Bounded single-clock concurrent properties. Unsupported temporal operators
 * are deliberately absent rather than silently reduced to expressions. */
sva_kind
  : simple_assertion_kind { $$=$1; }
  | vCOVER { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=3; }
  ;
sva_disable
  : %empty { $$=sva_number("0"); }
  | vDISABLE vIFF '(' expression ')' { $$=$4; }
  ;
sva_cycle_count
  : vNUMBER { $$=veri_parser->gen_primary($1.content,$1.line,$1.col,veNUM);free($1.content); }
  | vIDENT { $$=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content); }
  | '(' expression ')' { $$=$2; }
  ;
sva_sequence
  : expression { $$=sva_term($1); }
  | sva_temporal_sequence { $$=$1; }
  ;
/* A group must contain a temporal operator. Ordinary (boolean expressions)
 * remain in the expression grammar, avoiding two parses of every '(expr)'. */
sva_temporal_sequence
  : expression vCYCLEDELAY sva_cycle_count sva_sequence { $$=sva_term($1,sva_cycle($3,$4)); }
  | expression vSVA_REPEAT expression ']' { $$=sva_repeat($1,$3); }
  | expression vSVA_REPEAT expression ']' vCYCLEDELAY sva_cycle_count sva_sequence { $$=sva_repeat($1,$3,sva_cycle($6,$7)); }
  | '(' sva_temporal_sequence ')' { $$=sva_group($2); }
  | '(' sva_temporal_sequence ')' vCYCLEDELAY sva_cycle_count sva_sequence { $$=sva_group($2,nullptr,sva_cycle($5,$6)); }
  | '(' sva_temporal_sequence ')' vSVA_REPEAT expression ']' { $$=sva_group($2,$5); }
  | '(' sva_temporal_sequence ')' vSVA_REPEAT expression ']' vCYCLEDELAY sva_cycle_count sva_sequence { $$=sva_group($2,$5,sva_cycle($8,$9)); }
  ;
sva_consequent
  : sva_sequence { $$=$1; }
  | vCYCLEDELAY sva_cycle_count sva_sequence { $$=sva_cycle($2,$3); }
  ;
sva_spec
  : event_control sva_disable sva_sequence
    { $$=sva_specification($1,$2,sva_term(sva_number("1")),$3,0); }
  | event_control sva_disable sva_sequence vOVERLAP sva_consequent
    { $$=sva_specification($1,$2,$3,$5,0); }
  | event_control sva_disable sva_sequence vNONOVERLAP sva_consequent
    { $$=sva_specification($1,$2,$3,$5,1); }
  | vIDENT
    { auto* spec=sva_condition(sva_number("0"),veri_parser->gen_dummy_stmt($1.line,$1.col));
      spec->set_property_name($1.content);free($1.content);$$=spec; }
  ;
sva_actions
  : statement %prec LOWER_THAN_ELSE { $$=sva_condition(sva_number("1"),$1); }
  | ';' { $$=sva_condition(sva_number("1"),veri_parser->gen_dummy_stmt($1.line,$1.col)); }
  | statement vELSE stmt_or_null { $$=sva_condition(sva_number("1"),$1,$3); }
  | vELSE stmt_or_null { $$=sva_condition(sva_number("1"),veri_parser->gen_dummy_stmt($1.line,$1.col),$2); }
  ;
sva_assertion
  : sva_kind vPROPERTY '(' sva_spec ')' sva_actions
    { sva_body($4)->set_assertion_kind($1.extra[0]+3);sva_body($4)->set_else_stmt($6);$$=$4; }
  ;
sva_declaration
  : vPROPERTY vIDENT ';' sva_spec ';' vENDPROPERTY
    { sva_body($4)->set_assertion_kind(7);sva_body($4)->set_property_name($2.content);free($2.content);$$=$4; }
  | vSEQUENCE vIDENT ';' sva_sequence ';' sva_sequence_end
    { $$=sva_declare_sequence($2.content,$4,$6.content); }
  | vSEQUENCE vIDENT '(' ')' ';' sva_sequence ';' sva_sequence_end
    { $$=sva_declare_sequence($2.content,$6,$8.content); }
  ;
sva_sequence_end
  : vENDSEQUENCE { $$=$1;$$.content=nullptr; }
  | vENDSEQUENCE ':' vIDENT { $$=$3; }
  ;

/* Ordinary immediate assertions (deferred and concurrent forms remain separate). */
simple_assertion_kind
  : vASSERT { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=1; }
  | vASSUME { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=2; }
  ;
immediate_assertion_statement
  : simple_assertion_kind '(' expression ')' stmt_or_null %prec LOWER_THAN_ELSE
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,NULL);
      static_cast<rtl::VeriCondStmt*>($$)->set_assertion_kind($1.extra[0]); }
  | simple_assertion_kind '(' expression ')' statement vELSE stmt_or_null
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,$7);
      static_cast<rtl::VeriCondStmt*>($$)->set_assertion_kind($1.extra[0]); }
  | simple_assertion_kind '(' expression ')' vELSE stmt_or_null
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,veri_parser->gen_dummy_stmt($3->line(),$3->col()),$6);
      static_cast<rtl::VeriCondStmt*>($$)->set_assertion_kind($1.extra[0]); }
  | vCOVER '(' expression ')' stmt_or_null %prec LOWER_THAN_ELSE
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,NULL);
      static_cast<rtl::VeriCondStmt*>($$)->set_assertion_kind(3); }
  ;


/* Ordered static named-event waits retain branch and clone traversal. */
wait_order_statement
  : vWAIT_ORDER '(' expression ')' stmt_or_null %prec LOWER_THAN_ELSE
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,NULL,true);
      static_cast<rtl::VeriCondStmt*>($$)->set_wait_order(); }
  | vWAIT_ORDER '(' expression ')' stmt_or_null vELSE stmt_or_null
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,$5,$7,true);
      static_cast<rtl::VeriCondStmt*>($$)->set_wait_order(); }
  | vWAIT_ORDER '(' expression ')' vELSE stmt_or_null
    { $$=veri_parser->gen_cond_stmt($1.line,$1.col,$3,veri_parser->gen_dummy_stmt($1.line,$1.col),$6,true);
      static_cast<rtl::VeriCondStmt*>($$)->set_wait_order(); }
  ;

case_keyword
  : vCASE { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=0;$$.extra[1]=vcCASE; }
  | vCASEZ { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=0;$$.extra[1]=vcCASEZ; }
  | vCASEX { $$.line=$1.line;$$.col=$1.col;$$.extra[0]=0;$$.extra[1]=vcCASEX; }
  ;
case_head
  : case_keyword { $$=$1; }
  | unique_priority case_keyword { $$=$2;$$.line=$1.line;$$.col=$1.col;$$.extra[0]=$1.extra[0]; }
  ;
case_statement
  : case_head '(' expression ')' case_item_list vENDCASE
    { $$=veri_parser->gen_case_stmt($1.line,$1.col,$1.extra[1],$3,$5);
      static_cast<rtl::VeriCaseStmt*>($$)->set_selection_qualifier($1.extra[0]); }
  | case_head '(' expression ')' vINSIDE inside_case_list vENDCASE
    { if($1.extra[1]!=vcCASE)throw std::runtime_error("inside requires case, not casez/casex");
      $$=veri_parser->gen_case_stmt($1.line,$1.col,vcINSIDE,$3,$6);
      static_cast<rtl::VeriCaseStmt*>($$)->set_selection_qualifier($1.extra[0]); }
  ;

inside_item
  : conditional_expression { $$=$1; }
  | '[' conditional_expression ':' conditional_expression ']'
    { $$=veri_parser->gen_multi($2,$4,vemINSIDE_RANGE,$1.line,$1.col); }
  ;
inside_list
  : inside_item { $$=veri_parser->gen_inside_set($1); }
  | inside_list ',' inside_item { $$=veri_parser->gen_multi($1,$3,vemINSIDE_SET,$2.line,$2.col); }
  ;
inside_case_list
  : inside_case_item { $$=veri_parser->gen_case_item_list($1); }
  | inside_case_list inside_case_item { $$=veri_parser->append_case_item_list($1,$2); }
  ;
inside_case_item
  : inside_list ':' stmt_or_null { $$=veri_parser->gen_case_item($1,$3); }
  | vDEFAULT stmt_or_null { $$=veri_parser->gen_default_case_item($1.line,$1.col,$2); }
  | vDEFAULT ':' stmt_or_null { $$=veri_parser->gen_default_case_item($1.line,$1.col,$3); }
  ;

case_item_list
  : case_item
    {
      $$ = veri_parser->gen_case_item_list( $1 );
    }
  | case_item_list case_item
    {
      $$ = veri_parser->append_case_item_list( $1, $2 );
    }
  ;

case_item
  : expression ':' stmt_or_null
    {
      $$ = veri_parser->gen_case_item( $1, $3 );
    }
  | vDEFAULT stmt_or_null
    {
      $$ = veri_parser->gen_default_case_item( $1.line, $1.col, $2 );
    }
  | vDEFAULT ':' stmt_or_null
    {
      $$ = veri_parser->gen_default_case_item( $1.line, $1.col, $3 );
    }
  ;




/* A.6.8 Looping statements */

foreach_index
  : conditional_expression { $$=$1; }
  | %empty { $$=veri_parser->gen_primary("",0,0,veVAR); }
  ;
foreach_indices
  : foreach_index { $$=$1; }
  | foreach_indices ',' foreach_index { $$=veri_parser->gen_multi($1,$3,vemCOMMA_EXP,0,0); }
  ;

foreach_array
  : vIDENT { $$={};$$.node[0]=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);free($1.content); }
  | vTHIS { $$={};$$.node[0]=veri_parser->gen_primary("this",$1.line,$1.col,veVAR); }
  | vSUPER { $$={};$$.node[0]=veri_parser->gen_primary("super",$1.line,$1.col,veVAR); }
  | foreach_array '.' vIDENT
    { $$={};$$.node[0]=veri_parser->gen_member(foreach_receiver($1.node[0],$1.node[1]),$3.content,$3.line,$3.col);free($3.content); }
  | foreach_array '[' foreach_indices ']'
    { $$={};$$.node[0]=foreach_receiver($1.node[0],$1.node[1]);$$.node[1]=$3; }
  ;
loop_statement
  : vFOREACH '(' foreach_array ')' stmt_or_null
    { if(!$3.node[1])throw std::runtime_error("foreach requires an iterator list");
      $$=veri_parser->gen_foreach($1.line,$1.col,$3.node[0],$3.node[1],$5); }
  | vFOR '(' for_steps_opt ';' for_condition ';' for_steps_opt ')' stmt_or_null
    {
      $$=veri_parser->gen_loop_stmt($1.line,$1.col,$3,$5,$7,$9);
    }
  | vFOR '(' vINT expression ';' for_condition ';' for_steps_opt ')' stmt_or_null
    {
      $$=veri_parser->gen_inline_for($1.line,$1.col,$4,$6,$8,$10);
    }
  | vFOR '(' qualified_integral_type expression ';' for_condition ';' for_steps_opt ')' stmt_or_null
    { $$=veri_parser->gen_inline_for($1.line,$1.col,$4,$6,$8,$10,$3.extra[0],$3.extra[1]); }
  | vFOR '(' vIDENT named_variable_list ';' for_condition ';' for_steps_opt ')' stmt_or_null
    { $$=veri_parser->gen_inline_for($1.line,$1.col,$4,$6,$8,$10,0,IS_TRUE,$3.content);free($3.content); }
  | vFOR '(' class_application named_variable_list ';' for_condition ';' for_steps_opt ')' stmt_or_null
    { $$=veri_parser->gen_inline_for($1.line,$1.col,$4,$6,$8,$10,0,IS_TRUE,"$parameterized",$3); }
  | vWHILE '(' expression ')'
    stmt_or_null
    {
      $$ = veri_parser->gen_loop_stmt( $1.line, $1.col, NULL,
                                    $3, NULL, $5, rtl::VeriLoopStmt::WHILE );
    }
  | vDO stmt_or_null vWHILE '(' expression ')' ';'
    {
      $$ = veri_parser->gen_loop_stmt( $1.line, $1.col, NULL,
                                    $5, NULL, $2, rtl::VeriLoopStmt::DO_WHILE );
    }
  | vREPEAT '(' expression ')' stmt_or_null
    {
      $$ = veri_parser->gen_loop_stmt( $1.line, $1.col, NULL,
                                    $3, NULL, $5, rtl::VeriLoopStmt::REPEAT );
    }
  | vFOREVER stmt_or_null
    {
      $$ = veri_parser->gen_loop_stmt( $1.line, $1.col, NULL,
                                    NULL, NULL, $2, rtl::VeriLoopStmt::FOREVER );
    }
  ;

/* A.6.9 Task enable statements */
  /* combined by caller */

/* A.7 Specify section */
/* specify block is ignored */
/* A.7.1 Specify block declaration */
/* A.7.2 Specify path declaration */
/* A.7.3 Specify block terminals */
/* A.7.4 Specify path delays */
/* A.7.5 System timing checks  */
/* A.7.5.1 System timing check commands  */
/* A.7.5.2 System timing check command arguments  */
/* A.7.5.3 System timing check event definitions */

/* A.8 Expressions */

/* A.8.1 Concatenations */
concat
  : '{' expression '}'
    {
      // could be const
      $$ = veri_parser->gen_concat_exp( $2 );
    }
  ;

stream_concat
  : '{' vLOGIC_LS concat '}'
    { $$=veri_parser->gen_binary(veri_parser->gen_primary("1",$1.line,$1.col,veNUM),vtSTREAM_LEFT,$1.line,$1.col,$3); }
  | '{' vLOGIC_RS concat '}'
    { $$=veri_parser->gen_binary(veri_parser->gen_primary("1",$1.line,$1.col,veNUM),vtSTREAM_RIGHT,$1.line,$1.col,$3); }
  | '{' vLOGIC_LS assignment_expression concat '}'
    { $$=veri_parser->gen_binary($3,vtSTREAM_LEFT,$1.line,$1.col,$4); }
  | '{' vLOGIC_RS assignment_expression concat '}'
    { $$=veri_parser->gen_binary($3,vtSTREAM_RIGHT,$1.line,$1.col,$4); }
  | '{' vLOGIC_LS cast_type concat '}'
    { if(veri_real($3.extra[0]))throw std::runtime_error("stream slice type must be integral");auto text=std::to_string(veri_type_width($3.extra[0]));$$=veri_parser->gen_binary(veri_parser->gen_primary(text.c_str(),$1.line,$1.col,veNUM),vtSTREAM_LEFT,$1.line,$1.col,$4); }
  | '{' vLOGIC_RS cast_type concat '}'
    { if(veri_real($3.extra[0]))throw std::runtime_error("stream slice type must be integral");auto text=std::to_string(veri_type_width($3.extra[0]));$$=veri_parser->gen_binary(veri_parser->gen_primary(text.c_str(),$1.line,$1.col,veNUM),vtSTREAM_RIGHT,$1.line,$1.col,$4); }
  ;

multi_concat
  : '{' expression concat '}'
    {
      // const + non-const, two structures
      // 1 const-expression only
      $$ = veri_parser->gen_binary( $2, vtMULTI_CONCAT, $1.line,
                                         $1.col, $3 );
    }
  ;

/* A.8.2 Function calls */
/* combined by caller */
sys_caller
  : vSYS_IDENT ';'
    {
      $$ = veri_parser->gen_sys_caller_stmt( $1.line, $1.col, $1.content, NULL );
    }
  | vSYS_IDENT '(' expression ')' ';'
    {
      $$ = veri_parser->gen_sys_caller_stmt( $1.line, $1.col,
                                             $1.content, $3 );
    }
  | vSYS_IDENT '(' ')' ';'
    {
      $$ = veri_parser->gen_sys_caller_stmt($1.line, $1.col, $1.content, NULL);
      free($1.content);
    }
  | vDUMPVARS ';'
    {
      $$ = veri_parser->gen_sys_caller_stmt($1.line, $1.col, $1.content, NULL);
      free($1.content);
    }
  | vDUMPVARS '(' ')' ';'
    {
      $$ = veri_parser->gen_sys_caller_stmt($1.line, $1.col, $1.content, NULL);
      free($1.content);
    }
  | vDUMPVARS '(' conditional_expression ')' ';'
    {
      $$ = veri_parser->gen_sys_caller_stmt($1.line, $1.col, $1.content, $3);
      free($1.content);
    }
  | vDUMPVARS '(' conditional_expression ',' dump_targets ')' ';'
    {
      // gen_multi appends its right operand as one child. Append each target
      // separately so the task's argument list has one depth followed by names.
      VeriNode *args = $3;
      if($5->detail_type() == veEXP_MULTI)
      {
        for(VeriNode *target : static_cast<rtl::VeriMultiExp *>($5)->exp())
          args = veri_parser->gen_multi(args, target, vemCOMMA_EXP, $4.line, $4.col);
      }
      else
        args = veri_parser->gen_multi(args, $5, vemCOMMA_EXP, $4.line, $4.col);
      $$ = veri_parser->gen_sys_caller_stmt($1.line, $1.col, $1.content, args);
      free($1.content);
    }
  ;

dump_targets
  : dump_target { $$ = $1; }
  | dump_targets ',' dump_target
    { $$ = veri_parser->gen_multi($1, $3, vemCOMMA_EXP, $2.line, $2.col); }
  ;

dump_target
  : vIDENT
    {
      $$ = veri_parser->gen_dump_target(NULL, $1.content, $1.line, $1.col);
      free($1.content);
    }
  | dump_target '.' vIDENT
    {
      $$ = veri_parser->gen_dump_target($1, $3.content, $1->line(), $1->col());
      free($3.content);
    }
  ;

/* A.8.3 Expressions */
expression
  : assignment_expression
    {
      $$ = $1;
    }
  | vDUMMY_PORT
    {
      $$ = veri_parser->gen_dummy_port( $1.line, $1.col );
    }
  | expression ',' expression
    {
      $$ = veri_parser->gen_multi( $1, $3, vemCOMMA_EXP, $2.line, $2.col );
    }
  | expression vOR_ASCII expression
    {
      /* for event only */
      $$ = veri_parser->gen_multi( $1, $3, vemEVENT_EXP, $2.line, $2.col );
    }
  | expression vIFF expression
    { $$ = veri_parser->gen_conditional_event($1,$3,$2.line,$2.col); }
  ;

postfix_expression
  : primary
    {
      $$ = $1;
    }
  | postfix_expression '(' ')'
    {
      $$ = veri_parser->gen_caller( $1, NULL );
    }
  | postfix_expression '(' expression ')'
    {
      /* could be const */
      $$ = veri_parser->gen_caller( $1, $3 );
    }
  | postfix_expression range
    {
      /* could be range or array or dimension ... */
      $$ = veri_parser->gen_array( $1, $2 );
    }
  | postfix_expression '[' ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrOPEN,NULL)); }
  | postfix_expression '[' '$' ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrQUEUE,NULL)); }
  | postfix_expression '[' '$' ':' assignment_expression ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrQUEUE,$5)); }
  | postfix_expression '[' vINT2 ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_INT,NULL)); }
  | postfix_expression '[' vINT2 vSIGNED ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_INT,NULL)); }
  | postfix_expression '[' vINT2 vUNSIGNED ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_UINT,NULL)); }
  | postfix_expression '[' vSTRING_TYPE ']'
    { auto* zero=veri_parser->gen_primary("0",$2.line,$2.col,veNUM);
      $$=veri_parser->gen_array($1,veri_parser->gen_range(zero,vrASSOC_STRING,NULL)); }
  | postfix_expression '.' vIDENT
    { $$=veri_parser->gen_member($1,$3.content,$3.line,$3.col);free($3.content); }
  | class_application vSCOPE vIDENT
    { $$=veri_parser->gen_member($1,$3.content,$3.line,$3.col);static_cast<rtl::VeriMemberExp*>($$)->set_scope_reference();free($3.content); }
  | postfix_expression '.' vNEW { $$=veri_parser->gen_member($1,"new",$3.line,$3.col); }
  | postfix_expression '.' vUNIQUE { $$=veri_parser->gen_member($1,"unique",$3.line,$3.col); }
  | postfix_expression '.' vAND_ASCII { $$=veri_parser->gen_member($1,"and",$3.line,$3.col); }
  | postfix_expression '.' vOR_ASCII { $$=veri_parser->gen_member($1,"or",$3.line,$3.col); }
  | postfix_expression '.' vXOR_ASCII { $$=veri_parser->gen_member($1,"xor",$3.line,$3.col); }
  | postfix_expression vWITH '(' expression ')'
    { if($1->detail_type()!=veEXP_MEMBER)throw std::runtime_error("with clause requires an array method");static_cast<rtl::VeriMemberExp*>($1)->set_with($4);$$=$1; }
  | postfix_expression vWITH constraint_block
    { if($1->detail_type()!=veEXP_MEMBER||static_cast<rtl::VeriMemberExp*>($1)->member()!="randomize")throw std::runtime_error("constraint with clause requires randomize()");static_cast<rtl::VeriMemberExp*>($1)->set_with_constraint($3);$$=$1; }
  | postfix_expression vINCR { $$=veri_parser->gen_unary(vtUPOSTINC,$2.line,$2.col,$1); }
  | postfix_expression vDECR { $$=veri_parser->gen_unary(vtUPOSTDEC,$2.line,$2.col,$1); }
  | postfix_expression '\'' '(' expression ')'
    { $$=veri_parser->gen_binary($1,vtCAST_SIZE,$1->line(),$1->col(),$4); }
  ;

constraint_block
  : '{' constraint_items '}' { $$=$2; }
  | '{' '}' { $$=veri_parser->gen_primary("1'b1",$1.line,$1.col,veNUM); }
  ;
constraint_items
  : constraint_item { $$=$1; }
  | constraint_items constraint_item { $$=veri_parser->gen_binary($1,vtBDAND,$1->line(),$1->col(),$2); }
  ;
constraint_set
  : constraint_item { $$=$1; }
  | constraint_block { $$=$1; }
  ;
constraint_item
  : expression ';' { $$=$1; }
  | vFOREACH '(' foreach_array ')' constraint_set
    { if(!$3.node[1])throw std::runtime_error("constraint foreach requires an iterator list");
      $$=veri_parser->gen_constraint_foreach($1.line,$1.col,$3.node[0],$3.node[1],$5); }
  | expression vTRIGGER constraint_set { $$=veri_parser->gen_binary(veri_parser->gen_unary(vtUNOT,$1->line(),$1->col(),$1),vtBDOR,$1->line(),$1->col(),$3); }
  | vIF '(' expression ')' constraint_set %prec LOWER_THAN_ELSE { $$=veri_parser->gen_ques_exp($3,$1.line,$1.col,$5,veri_parser->gen_primary("1'b1",$1.line,$1.col,veNUM)); }
  | vIF '(' expression ')' constraint_set vELSE constraint_set { $$=veri_parser->gen_ques_exp($3,$1.line,$1.col,$5,$7); }
  ;

packed_range
  : range { $$=$1; }
  | packed_range range
    { static_cast<rtl::VeriRangeExp*>($1)->append_packed(static_cast<rtl::VeriRangeExp*>($2));$$=$1; }
  ;

range
  : '[' expression ']'
    {
      $$ = veri_parser->gen_range( $2, vrSINGLE, NULL );
    }
  | '[' expression ':' expression ']'
    {
      $$ = veri_parser->gen_range( $2, vrSEMI, $4 );
    }
  | '[' expression vRANGE_ADD expression ']'
    {
      $$ = veri_parser->gen_range( $2, vrRAN_ADD, $4 );
    }
  | '[' expression vRANGE_SUB expression ']'
    {
      $$ = veri_parser->gen_range( $2, vrRAN_SUB, $4 );
    }
  ;

unary_expression
  : postfix_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | vINCR unary_expression %prec UADD { $$=veri_parser->gen_unary(vtUPREINC,$1.line,$1.col,$2); }
  | vDECR unary_expression %prec UMINUS { $$=veri_parser->gen_unary(vtUPREDEC,$1.line,$1.col,$2); }
  | '+'   unary_expression %prec UADD
    {
      $$ = veri_parser->gen_unary( vtUADD, $1.line, $1.col, $2 );
    }
  | '-'   unary_expression %prec UMINUS
    {
      $$ = veri_parser->gen_unary( vtUSUB, $1.line, $1.col, $2 );
    }
  | '~'   unary_expression %prec UNEG
    {
      $$ = veri_parser->gen_unary( vtUNEG, $1.line, $1.col, $2 );
    }
  | '&'   unary_expression %prec UAND
    {
      $$ = veri_parser->gen_unary( vtUAND, $1.line, $1.col, $2 );
    }
  | '|'   unary_expression %prec UOR
    {
      $$ = veri_parser->gen_unary( vtUOR, $1.line, $1.col, $2 );
    }
  | vNAND unary_expression %prec UNAND
    {
      $$ = veri_parser->gen_unary( vtUNAND, $1.line, $1.col, $2 );
    }
  | vNOR  unary_expression %prec UNOR
    {
      $$ = veri_parser->gen_unary( vtUNOR, $1.line, $1.col, $2 );
    }
  | vXNOR unary_expression %prec UXNOR
    {
      $$ = veri_parser->gen_unary( vtUXNOR, $1.line, $1.col, $2 );
    }
  | '!'   unary_expression %prec ULNOT
    {
      $$ = veri_parser->gen_unary( vtUNOT, $1.line, $1.col, $2 );
    }
  | '^'   unary_expression %prec UXOR
    {
      $$ = veri_parser->gen_unary( vtUXOR, $1.line, $1.col, $2 );
    }
  | vPOSEDGE unary_expression
    {
      /* event */
      $$ = veri_parser->gen_unary( vtUPOSE, $1.line, $1.col, $2 );
    }
  | vNEGEDGE unary_expression
    {
      /* event */
      $$ = veri_parser->gen_unary( vtUNEGE, $1.line, $1.col, $2 );
    }
  | vSIGN_FUNC '(' expression ')'
    {
      $$ = veri_parser->gen_signed_exp( $1.line, $1.col, $3 );
    }
  | vUNSIGN_FUNC '(' expression ')'
    {
      $$ = veri_parser->gen_unsigned_exp( $1.line, $1.col, $3 );
    }
  ;

pow_expression
  : unary_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | pow_expression vPOW  unary_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBPOW, $2.line,
                                         $2.col, $3 );
    }
  | pow_expression vNAND unary_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBNAND, $2.line,
                                         $2.col, $3 );
    }
  | pow_expression vNOR  unary_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBNOR, $2.line,
                                         $2.col, $3 );
    }
  | pow_expression vXNOR unary_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBXNOR, $2.line,
                                         $2.col, $3 );
    }
  ;

multiplicative_expression
  : pow_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | multiplicative_expression '%' pow_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBMOD, $2.line,
                                         $2.col, $3 );
    }
  | multiplicative_expression '*' pow_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBMUL, $2.line,
                                         $2.col, $3 );
    }
  | multiplicative_expression '/' pow_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBDIV, $2.line,
                                         $2.col, $3 );
    }
  ;

additive_expression
  : multiplicative_expression
    {
      $$ = $1;
    }
  | additive_expression '+' multiplicative_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBADD, $2.line,
                                         $2.col, $3 );
    }
  | additive_expression '-' multiplicative_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBSUB, $2.line,
                                         $2.col, $3 );
    }
  ;

shift_expression
  : additive_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | shift_expression vLOGIC_RS additive_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBLRS, $2.line,
                                         $2.col, $3 );
    }
  | shift_expression vLOGIC_LS additive_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBLLS, $2.line,
                                         $2.col, $3 );
    }
  | shift_expression vARITH_RS additive_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBARS, $2.line,
                                         $2.col, $3 );
    }
  | shift_expression vARITH_LS additive_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBALS, $2.line,
                                         $2.col, $3 );
    }
  ;

relational_expression
  : shift_expression
    {
      $$ = $1;
    }
  | relational_expression vINSIDE '{' inside_list '}'
    { $$=veri_parser->gen_binary($1,vtBINSIDE,$2.line,$2.col,$4); }
  | relational_expression '<' shift_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBLT, $2.line,
                                         $2.col, $3 );
    }
  | relational_expression '>' shift_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBGT, $2.line,
                                         $2.col, $3 );
    }
  | relational_expression vLE shift_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBLE, $2.line,
                                         $2.col, $3 );
    }
  | relational_expression vGE shift_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBGE, $2.line,
                                         $2.col, $3 );
    }
  ;

equality_expression
  : relational_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | equality_expression vWILD_EQ relational_expression
    { $$=veri_parser->gen_binary($1,vtBWLEQ,$2.line,$2.col,$3); }
  | equality_expression vWILD_NE relational_expression
    { $$=veri_parser->gen_binary($1,vtBWLNEQ,$2.line,$2.col,$3); }
  | equality_expression vLOGIC_EQ   relational_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBLEQ, $2.line,
                                         $2.col, $3 );
    }
  | equality_expression vLOGIC_INEQ relational_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBLIEQ, $2.line,
                                         $2.col, $3 );
    }
  | equality_expression vCASE_EQ   relational_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBCEQ, $2.line,
                                         $2.col, $3 );
    }
  | equality_expression vCASE_INEQ relational_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBCIEQ, $2.line,
                                         $2.col, $3 );
    }
  ;

and_expression
  : equality_expression
    {
      $$ = $1;
    }
  | and_expression '&' equality_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBSAND, $2.line,
                                         $2.col, $3 );
    }
  ;

xor_expression
  : and_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | xor_expression '^' and_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBSXOR, $2.line,
                                         $2.col, $3 );
    }
  ;

bit_or_expression
  : xor_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | bit_or_expression '|' xor_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBSOR, $2.line,
                                         $2.col, $3 );
    }
  ;

logical_and_expression
  : bit_or_expression %prec LOWER_THAN_A
    {
      $$ = $1;
    }
  | logical_and_expression vANDAND bit_or_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBDAND, $2.line,
                                         $2.col, $3 );
    }
  ;

logical_or_expression
  : logical_and_expression
    {
      $$ = $1;
    }
  | logical_or_expression vOROR logical_and_expression
    {
      $$ = veri_parser->gen_binary( $1, vtBDOR, $2.line, $2.col, $3);
    }
  ;

conditional_expression
  : logical_or_expression
    {
      $$ = $1;
    }
  | logical_or_expression '?' expression ':' conditional_expression
    {
      $$ = veri_parser->gen_ques_exp( $1, $2.line, $2.col, $3, $5 );
    }
  ;

assignment_expression
  : conditional_expression
    {
      $$ = $1;
    }
  | '{' '}' { $$=veri_parser->gen_empty_concat($1.line,$1.col); }
  | unary_expression '=' assignment_expression
    {
      /* first expression should be id */
      $$ = veri_parser->gen_binary( $1, vtASSIGN, $2.line,
                                         $2.col, $3 );
    }
  ;

mintypmax_expression
  : expression ':' expression ':' expression
    {
      $$ = veri_parser->gen_mintypmax( $1, $2.line, $2.col, $3, $5 );
    }
  ;

/* Context-determined assignment patterns stay distinct from concatenations. */
assignment_pattern
  : vPATTERN_OPEN pattern_items '}' { $$=$2; }
  | vPATTERN_OPEN '}' { $$=veri_parser->gen_empty_pattern($1.line,$1.col); }
  ;
pattern_items
  : pattern_item { $$=veri_parser->gen_pattern(vemASSIGN_PATTERN,$1); }
  | pattern_items ',' pattern_item { $$=veri_parser->gen_multi($1,$3,vemASSIGN_PATTERN,$2.line,$2.col); }
  ;
pattern_item
  : assignment_expression { $$=$1; }
  | vDEFAULT ':' assignment_expression { $$=veri_parser->gen_pattern(vemPATTERN_DEFAULT,$3); }
  | vIDENT ':' assignment_expression {
      $$=veri_parser->gen_pattern_field($1.content,$3,$1.line,$1.col);free($1.content);
    }
  | vNUMBER ':' assignment_expression {
      auto* key=veri_parser->gen_primary($1.content,$1.line,$1.col,veNUM);free($1.content);
      $$=veri_parser->gen_pattern(vemPATTERN_INDEX,key,$3);
    }
  | '-' vNUMBER ':' assignment_expression {
      auto* key=veri_parser->gen_primary($2.content,$2.line,$2.col,veNUM);free($2.content);
      key=veri_parser->gen_unary(vtUSUB,$1.line,$1.col,key);
      $$=veri_parser->gen_pattern(vemPATTERN_INDEX,key,$4);
    }
  | assignment_expression '{' pattern_items '}' { $$=veri_parser->gen_pattern(vemPATTERN_REPEAT,$1,$3); }
  ;

/* A.8.4 Primaries */

/* concat hier_identifier-exp-bracket-list due to r/s conflicts */
primary
  : assignment_pattern { $$=$1; }
  | '$' %prec LOWER_THAN_A { $$=veri_parser->gen_primary("$",veri_lno,veri_col,veQUEUE_LAST); }
  | vTIME_LITERAL { $$=veri_parser->gen_time_literal($1.content,$1.line,$1.col);free($1.content); }
  | stream_concat { $$=$1; }
  | vNULL { $$=veri_parser->gen_multi(NULL,NULL,vemNULL,$1.line,$1.col); }
  | vTHIS { $$=veri_parser->gen_primary("this",$1.line,$1.col,veVAR); }
  | vSUPER { $$=veri_parser->gen_primary("super",$1.line,$1.col,veVAR); }
  | vNEW { $$=veri_parser->gen_multi(NULL,NULL,vemOBJECT_NEW,$1.line,$1.col); }
  | vNEW '(' ')' { $$=veri_parser->gen_multi(NULL,NULL,vemOBJECT_NEW,$1.line,$1.col); }
  | vNEW '(' expression ')' { $$=veri_parser->gen_multi($3,NULL,vemOBJECT_NEW,$1.line,$1.col); }
  | vNEW '[' expression ']'
    { $$=veri_parser->gen_multi($3,NULL,vemDYNAMIC_NEW,$1.line,$1.col); }
  | vNUMBER
    {
      /* could be const */
      $$ = veri_parser->gen_primary( $1.content, $1.line, $1.col, veNUM );
      free( $1.content );
    }
  | vSTR
    {
      /* could be const */
      $$ = veri_parser->gen_primary( $1.content, $1.line, $1.col, veSTR );
      free( $1.content );
    }
  | vIDENT
    {
      /* could be const */
      $$ = veri_parser->gen_primary( $1.content, $1.line, $1.col, veVAR );
      free($1.content);
    }
  | cast_type '\'' '(' expression ')'
    { $$=veri_parser->gen_type_cast($1.extra[0],$1.extra[1],$1.line,$1.col,$4); }
  | vSTRING_TYPE '\'' '(' expression ')'
    { $$=veri_parser->gen_type_cast(vvSTRING,IS_FALSE,$1.line,$1.col,$4); }
  | vSIGNED '\'' '(' expression ')'
    { $$=veri_parser->gen_signed_exp($1.line,$1.col,$4); }
  | vUNSIGNED '\'' '(' expression ')'
    { $$=veri_parser->gen_unsigned_exp($1.line,$1.col,$4); }
  | vRANDOM_FUNC
    {
      auto* name=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);
      free($1.content);$$=veri_parser->gen_caller(name,NULL);
    }
  | vRANDOM_FUNC '(' ')'
    {
      auto* name=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);
      free($1.content);$$=veri_parser->gen_caller(name,NULL);
    }
  | vRANDOM_FUNC '(' expression ')'
    {
      auto* name=veri_parser->gen_primary($1.content,$1.line,$1.col,veVAR);
      free($1.content);$$=veri_parser->gen_caller(name,$3);
    }
  | vSYS_IDENT
    {
      /* system function identifier (e.g. $clog2) */
      $$ = veri_parser->gen_primary( $1.content, $1.line, $1.col, veVAR );
      free($1.content);
    }
  | vSYS_IDENT '(' expression ')'
    {
      /* system function call (e.g. $clog2(expr)) */
      VeriNode * name = veri_parser->gen_primary( $1.content, $1.line, $1.col, veVAR );
      free($1.content);
      $$ = veri_parser->gen_caller( name, $3 );
    }
  | vSYS_IDENT '(' vCHANDLE ')'
    {
      if(std::string($1.content)!="$typename")throw std::runtime_error("only $typename accepts chandle type here");
      $$=veri_parser->gen_unary(vtSYS_TYPENAME,$1.line,$1.col,veri_parser->gen_type_expression($1.line,$1.col,"",vvCHANDLE,IS_FALSE));free($1.content);
    }
  | vSYS_IDENT '(' vSTRING_TYPE ')'
    {
      if(std::string($1.content)!="$typename")throw std::runtime_error("only $typename accepts string type here");
      $$=veri_parser->gen_unary(vtSYS_TYPENAME,$1.line,$1.col,veri_parser->gen_type_expression($1.line,$1.col,"",vvSTRING,IS_FALSE));free($1.content);
    }
  | vSYS_IDENT '(' query_type ')'
    {
      if(std::string($1.content)=="$bits") {
        if(veri_real($3.extra[0]))throw std::runtime_error("size/range query requires a bit-stream or array type");
        const auto width=std::to_string(veri_type_width($3.extra[0]));
        $$=veri_parser->gen_primary(width.c_str(),$1.line,$1.col,veNUM);
      } else if(std::string($1.content)=="$typename") {
        $$=veri_parser->gen_unary(vtSYS_TYPENAME,$1.line,$1.col,veri_parser->gen_type_expression($1.line,$1.col,"",$3.extra[0],$3.extra[1]));
      } else $$=veri_parser->gen_array_type_query($1.content,$3.extra[0],$1.line,$1.col,NULL);
      free($1.content);
    }
  | vSYS_IDENT '(' query_type range ')'
    {
      if(std::string($1.content)!="$bits") {
        if(std::string($1.content)=="$typename")
          $$=veri_parser->gen_unary(vtSYS_TYPENAME,$1.line,$1.col,veri_parser->gen_type_expression($1.line,$1.col,"",$3.extra[0],$3.extra[1],$4));
        else $$=veri_parser->gen_array_type_query($1.content,$3.extra[0],$1.line,$1.col,$4);
      } else {
      if(veri_real($3.extra[0]))throw std::runtime_error("size/range query requires a bit-stream or array type");
      if(veri_integral_atom($3.extra[0]))throw std::runtime_error("packed dimensions require bit/logic/reg data type");
      auto* count=veri_parser->gen_unary(vtSYS_RANGE_BITS,$1.line,$1.col,$4);
      const auto width=std::to_string(veri_type_width($3.extra[0]));
      auto* base=veri_parser->gen_primary(width.c_str(),$1.line,$1.col,veNUM);
      $$=veri_parser->gen_binary(count,vtBMUL,$1.line,$1.col,base);
      }
      free($1.content);
    }
  | vSYS_IDENT '(' query_type ',' expression ')'
    {
      $$=veri_parser->gen_array_type_query($1.content,$3.extra[0],$1.line,$1.col,NULL,$5);free($1.content);
    }
  | vSYS_IDENT '(' query_type range ',' expression ')'
    {
      $$=veri_parser->gen_array_type_query($1.content,$3.extra[0],$1.line,$1.col,$4,$6);free($1.content);
    }
  | '.' vIDENT
    {
      /* Implicit named connection keeps its port identity and same-name actual. */
      VeriNode * port = veri_parser->gen_port_ref( $1.line, $1.col, $2.content );
      VeriNode * signal = veri_parser->gen_primary( $2.content, $2.line, $2.col, veVAR );
      $$ = veri_parser->gen_caller( port, signal );
      static_cast<rtl::VeriNamedParamExp*>($$)->set_implicit();
      free( $2.content );
    }
  | '.' vIDENT '(' expression ')'
    {
      /* named port connection with signal: .port_name(signal) */
      VeriNode * port = veri_parser->gen_port_ref( $1.line, $1.col, $2.content );
      free( $2.content );
      $$ = veri_parser->gen_caller( port, $4 );
    }
  | '.' vIDENT '(' ')'
    {
      /* named port connection with no signal (open): .port_name() */
      VeriNode * port = veri_parser->gen_port_ref( $1.line, $1.col, $2.content );
      free( $2.content );
      $$ = veri_parser->gen_caller( port, NULL );
    }
  | concat
    {
      /* could be const */
      $$ = $1;
    }
  | multi_concat
    {
      /* could be const */
      $$ = $1;
    }
  | '(' expression ')'
    {
      $$ = $2;
    }
  | '(' mintypmax_expression ')'
    {
      /* could be const */
      $$ = $2;
    }
  ;

/* A.8.5 Expression left_side values */
/* A.8.6 Operators */
/* A.8.7 Numbers */

/* A.9 General */
/* A.9.l Attributes */

attr_inst_list
  : attr_instance
    {
    }
  | attr_inst_list attr_instance
    {
    }
  ;

attr_instance
  : vATTR_L expression vATTR_R
    {
    }
  ;

/* A.9.2 Comments */

/* A.9.3 Identifiers */
%%
