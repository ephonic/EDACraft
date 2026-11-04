/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_node.hpp
 * Summary  : verilog syntax analyzer true node class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PARSER_VERILOG_VERI_NODE_HPP_
#define PARSER_VERILOG_VERI_NODE_HPP_

#include "general_err.hpp"
#include "verilog_token.hpp"
#include "veri_err.hpp"

#include <vector>
#include <queue>
#include <string>
#include <fstream>
#include <sstream>

namespace rtl
{

class VeriMod;
class VeriSymbolTable;

/*
 * class VeriNode :
 *     Verilog syntax analyzer true node
 */
class VeriNode
{
  public:
    typedef unsigned int  Uint;
    typedef std::string   String;
    typedef const String  CString;
    typedef std::ofstream Ofstream;
    typedef std::vector< VeriNode * > NodeVec;
    typedef std::queue< VeriNode * >  NodeQueue;
    typedef std::queue< int >         IQueue;
    typedef std::list<VeriNode *>     NodeList;
    typedef std::list< int >          IList;
    typedef VeriSymbolTable           SymbolTable;

  public:
    VeriNode( Uint idx, short tok_type, short detail_type,
              int line, int col, VeriMod *mod )
      : _idx( idx )
      , _tok_type( tok_type )
      , _detail_type( detail_type )
        \
      , _is_decl( IS_FALSE )
      , _is_trash( IS_FALSE )
      , _gen_flag( IS_FALSE )
      , _pstatus( vSTART_S )
      , _scope( NULL )
        \
      , _line( line )
      , _col( col )
        \
      , _birth_mod( mod )
      , _father( NULL )
    {}

    virtual ~VeriNode() {};

    // accessors
    Uint idx  ( void ) const { return _idx;   }
    int line ( void ) const { return _line;  }
    int col  ( void ) const { return _col;   }

    short tok_type( void ) const { return _tok_type; }
    short detail_type( void ) const { return _detail_type; }
    short is_decl( void ) const { return _is_decl; }
    short is_trash( void ) const { return _is_trash; }
    short gen_flag( void ) const { return _gen_flag; }
    short pstatus( void ) const { return _pstatus; }
    SymbolTable * scope( void ) { return _scope; }

    VeriMod  * birth_mod( void ) { return _birth_mod; }
    VeriNode * father   ( void ) { return _father;    }

    // mutators
    void set_line    ( int line ) { _line = line; }
    void set_col     ( int col  ) { _col  = col;  }
    void set_father( VeriNode *father ) { _father = father; }
    void set_birth_mod(VeriMod* mod) { _birth_mod=mod; }
    void set_is_decl( short is_decl ) { _is_decl = is_decl; }
    void set_is_trash( short is_trash ) { _is_trash = is_trash; }
    void set_gen_flag( short gen_flag ) { _gen_flag = gen_flag; }
    void set_pstatus( short pstatus ) { _pstatus = pstatus; }
    void set_scope( SymbolTable *t ) { _scope = t; }

    virtual void clear( void ) {};
    virtual void clean_up( void ) = 0;
    virtual int  check_child_validation( void ) = 0;

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue ) = 0;
    virtual int  pretty_dot_label( Ofstream& ofile, int depth ) = 0;

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info ) = 0;
    virtual int  push_for_replacement( NodeVec& mstack ) = 0;
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl ) = 0;

    // search-for-symbol additional round
    virtual int  search_for_symbol( NodeVec& /*seq*/, CString& /*symbol_name*/ )
    { return NOT_EXIST; }

  protected:
    VeriNode() {}

    VeriNode( Uint idx, const VeriNode *copy )
      : _idx( idx )
      , _tok_type( copy ? copy->_tok_type : 0 )
      , _detail_type( copy ? copy->_detail_type : 0 )
        \
      , _is_decl( IS_FALSE )
      , _is_trash( IS_FALSE )
      , _gen_flag( IS_FALSE )
      , _pstatus( vSTART_S )
      , _scope( NULL )
        \
      , _line( copy ? copy->_line : 0 )
      , _col( copy ? copy->_col : 0 )
        \
      , _birth_mod( copy ? copy->_birth_mod : NULL )
      , _father( NULL )
    {}

  private:
    // basic information
    Uint  _idx;
    short _tok_type;
    short _detail_type;

    short _is_decl;
    short _is_trash;
    short _gen_flag;
    short _pstatus;

    SymbolTable *_scope;

    // debug
    int _line;
    int _col;

    VeriMod  *_birth_mod;   // the original module, for err output
    VeriNode *_father;

   // static functions
  protected:
    static String int2string( int n )
    {
      std::stringstream f;
      f << n;
      return f.str();
    }

  protected:
    static String dot_str_head( Uint idx )
    { return ("  " + int2string( idx ) + " [ label = \""); }

    static String dot_str_var_head( Uint idx )
    { return ("  " + int2string( idx ) + " [ shape=box, label = \""); }

    static String dot_str_tail( int tok_type )
    { return ("\", " + dot_str_tail_color( tok_type ) + "];\n"); }

    static String dot_str_tail_color( int tok_type )
    {
      switch( tok_type )
      {
        case vtDECL    : return "fontcolor=red";
        case vtINST    : return "fontcolor=green";
        case vtSTMT    : return "fontcolor=blue";
        case vtEXP     : return "fontcolor=black";
        case vtSYS_VAR : return "fontcolor=brown";
        case vtVAR     : return "fontcolor=brown";
        case vtPARAM   : return "fontcolor=brown";
        case vtINT     : return "fontcolor=brown";
        case vtGENVAR  : return "fontcolor=brown";
        case vtTFVAR   : return "fontcolor=brown";
        case vtNUM     : return "fontcolor=brown";
        case vtSTR     : return "fontcolor=brown";
        case vtMOD     : return "";
        default        : return "";
      }
    }

    static String dot_str_scope( int depth )
    { return ( "SCOPE : [" + int2string(depth) + "]\\n" ); }

    static String dot_str_rank( Uint idx, int depth )
    {
      return (   "  { rank = same; -" + int2string( depth ) + "; "
               + int2string( idx ) + ";}\n" );
    }

    static String dot_str_conn( Uint idx, VeriNode *node )
    {
      if( node != NULL )
      {
        return (   "  " + int2string( idx ) + " -> "
               + int2string( node->idx() ) + ";\n" );
      }
      else
        return "";
    }

    static String dot_str_symbol_back_conn( Uint idx, VeriNode *decl )
    {
      return ( "  " + int2string( idx ) + " -> " + int2string( decl->idx() )
             + " [ style=dotted, constraint=false, color=orange ];\n" );
    }

    static String dot_str_symbol_conn( Uint idx, VeriNode *symbol )
    {
      return ( "  " + int2string( idx ) + " -> " + int2string( symbol->idx() )
             + " [ style=dotted, constraint=false, color=green ];\n" );
    }

    static String dot_str_var_conn( CString& conn, VeriNode *node )
    {
      if( node != NULL )
        return (conn + " :-> " + int2string(node->idx()));
      else
        return dot_str_name( conn );
    }

    static String dot_str_name( CString& name )
    {
      String tmp;
      for( unsigned int i = 0; i < name.size(); ++i )
      {
        if( name[i] != '\\' )
          tmp += name[i];
        else
          tmp += '|';
      }
      return ("NAME : \\\"" + tmp + "\\\"\\n");
    }

    static String dot_str_range( IList &from, IList& to )
    {
      String range = "RANGE : \\n";
      IList::iterator ifrom = from.begin();
      IList::iterator ito = to.begin();

      for( ; ifrom != from.end(); ++ifrom, ++ito )
        range += "[ "+int2string(*ifrom)+" : "+int2string(*ito)+" ]\\n";
      return range;
    }

    static String dot_str_is_tf( CString& prefix, int tf )
    {
      switch( tf )
      {
        case IS_TRUE  : return prefix + " : true\\n";
        case IS_FALSE : return prefix + " : false\\n";
        default       : return prefix + " : \\n";
      }
    }

    static String dot_str_tok_type( int t )
    {
      switch( t )
      {
        case vtDECL    : return "TOK : DECLARATION\\n";
        case vtINST    : return "TOK : INSTANTIATION\\n";
        case vtSTMT    : return "TOK : STATEMENT\\n";
        case vtEXP     : return "TOK : EXPRESSION\\n";

        case vtSYS_VAR : return "TOK : SYS_VAR\\n";
        case vtVAR     : return "TOK : VAR\\n";
        case vtTFVAR   : return "TOK : TFVAR\\n";
        case vtPARAM   : return "TOK : PARAM\\n";
        case vtINT     : return "TOK : INT\\n";
        case vtGENVAR  : return "TOK : GENVAR\\n";

        case vtNUM     : return "TOK : NUM\\n";
        case vtSTR     : return "TOK : STR\\n";
        case vtMOD     : return "TOK : MODULE\\n";

        case vtFUNC    : return "TOK : FUNC\\n";
        case vtTASK    : return "TOK : TASK\\n";
        case vtMOD_INST : return "TOK : MOD_INST\\n";
        case vtGATE_INST: return "TOK : GATE_INST\\n";
        default        : return "TOK : \\n";
      }
    }

    static String dot_str_primary_type( int t )
    {
      switch( t )
      {
        case veVAR : return "CONTENT : VAR\\n";
        case veSTR : return "CONTENT : STR\\n";
        case veNUM : return "CONTENT : NUM\\n";
        default:     return "CONTENT : \\n";
      }
    }

    static String dot_str_vector_scalar( int vs )
    {
      switch( vs )
      {
        case vpVECTOR : return "VS : vector\\n";
        case vpSCALAR : return "VS : scalar\\n";
        default       : return "VS : \\n";
      }
    }

    static String dot_str_in_out( int io )
    {
      switch( io )
      {
        case vpNO_IO : return "IO : NONE\\n";
        case vpIN    : return "IO : input\\n";
        case vpOUT   : return "IO : output\\n";
        case vpINOUT : return "IO : inout\\n";
        default      : return "IO : \\n";
      }
    }

    static String dot_str_drive_from( int s )
    {
      switch( s )
      {
        case vpSTRONG0 : return "FROM : strong0\\n";
        case vpSTRONG1 : return "FROM : strong1\\n";
        case vpPULL0   : return "FROM : pull0\\n";
        case vpPULL1   : return "FROM : pull1\\n";
        case vpWEAK0   : return "FROM : weak0\\n";
        case vpWEAK1   : return "FROM : weak1\\n";
        case vpHIGHZ0  : return "FROM : highz0\\n";
        case vpHIGHZ1  : return "FROM : highz1\\n";
        case vpSUPPLY0 : return "FROM : supply0\\n";
        case vpSUPPLY1 : return "FROM : supply1\\n";
        default        : return "FROM : \\n";
      }
    }

    static String dot_str_drive_to( int s )
    {
      switch( s )
      {
        case vpSTRONG0 : return " TO  : strong0\\n";
        case vpSTRONG1 : return " TO  : strong1\\n";
        case vpPULL0   : return " TO  : pull0\\n";
        case vpPULL1   : return " TO  : pull1\\n";
        case vpWEAK0   : return " TO  : weak0\\n";
        case vpWEAK1   : return " TO  : weak1\\n";
        case vpHIGHZ0  : return " TO  : highz0\\n";
        case vpHIGHZ1  : return " TO  : highz1\\n";
        case vpSUPPLY0 : return " TO  : supply0\\n";
        case vpSUPPLY1 : return " TO  : supply1\\n";
        default        : return " TO  : \\n";
      }
    }


    static String dot_str_gate_type( int t )
    {
      switch( t )
      {
        case vpBUFFIF0 : return "GATE : buffif0\\n";
        case vpBUFFIF1 : return "GATE : buffif1\\n";
        case vpNOTIF0  : return "GATE : notif0\\n";
        case vpNOTIF1  : return "GATE : notif1\\n";
        case vpAND     : return "GATE : and\\n";
        case vpNAND    : return "GATE : nand\\n";
        case vpOR      : return "GATE : or\\n";
        case vpNOR     : return "GATE : nor\\n";
        case vpXOR     : return "GATE : xor\\n";
        case vpXNOR    : return "GATE : xnor\\n";
        case vpBUF     : return "GATE : buf\\n";
        case vpNOT     : return "GATE : not\\n";
        default        : return "GATE : \\n";
      }
    }

    static String dot_str_range_type( int t )
    {
      switch( t )
      {
        case vrSINGLE  : return "RANGE : 1\\n";
        case vrSEMI    : return "RANGE : 2\\n";
        case vrRAN_ADD : return "RANGE : 3\\n";
        case vrRAN_SUB : return "RANGE : 4\\n";
        default        : return "RANGE : \\n";
      }
    }

    static String dot_str_var_type( int t )
    {
      switch( t )
      {
        case vvSUPPLY0 : return "VAR_TYPE : supply0\\n";
        case vvSUPPLY1 : return "VAR_TYPE : supply1\\n";
        case vvTRI     : return "VAR_TYPE : tri\\n";
        case vvTRIAND  : return "VAR_TYPE : triand\\n";
        case vvTRIOR   : return "VAR_TYPE : trior\\n";
        case vvTRI0    : return "VAR_TYPE : tri0\\n";
        case vvTRI1    : return "VAR_TYPE : tri1\\n";
        case vvWIRE    : return "VAR_TYPE : wire\\n";
        case vvWAND    : return "VAR_TYPE : wand\\n";
        case vvWOR     : return "VAR_TYPE : wor\\n";
        case vvREG     : return "VAR_TYPE : reg\\n";
        case vvINT2    : return "VAR_TYPE : int\\n";
        case vvINT     : return "VAR_TYPE : integer\\n";
        case vvTIME    : return "VAR_TYPE : time\\n";
        case vvTRIREG  : return "VAR_TYPE : trireg\\n";
        case vvPARAM   : return "VAR_TYPE : param\\n";
        case vvLOGIC   : return "VAR_TYPE : logic\\n";
        case vvBIT     : return "VAR_TYPE : bit\\n";
        case vvBYTE    : return "VAR_TYPE : byte\\n";
        case vvSHORTINT: return "VAR_TYPE : shortint\\n";
        case vvLONGINT : return "VAR_TYPE : longint\\n";
        case vvENUM    : return "VAR_TYPE : enum\\n";
        case vvSTRUCT  : return "VAR_TYPE : struct\\n";
        case vvTYPEDEF : return "VAR_TYPE : typedef\\n";
        default        : return "VAR_TYPE : \\n";
      }
    }

    static String dot_str_case_type( int t )
    {
      switch( t )
      {
        case vcCASE  : return "CASE : case\\n";
        case vcCASEZ : return "CASE : casez\\n";
        case vcCASEX : return "CASE : casex\\n";
        default      : return "CASE : \\n";
      }
    }

    static String dot_str_multi_exp_type( int t )
    {
      switch( t )
      {
        case vemCONCAT_EXP : return "MULTI : CONCAT\\n";
        case vemCOMMA_EXP  : return "MULTI : COMMA\\n";
        case vemEVENT_EXP  : return "MULTI : EVENT\\n";
        case vemPORT_EXP   : return "MULTI : PORT\\n";
        case vemPORT_INST_EXP  : return "MULTI : PORT_INST_EXP\\n";
        default            : return "MULTI : \\n";
      }
    }

    static String dot_str_op( int op )
    {
      switch( op )
      {
        case vtUADD   : return "OP : +\\n";
        case vtUSUB   : return "OP : -\\n";
        case vtUNEG   : return "OP : ~\\n";
        case vtUAND   : return "OP : &\\n";
        case vtUOR    : return "OP : |\\n";
        case vtUNAND  : return "OP : ~&\\n";
        case vtUNOR   : return "OP : ~|\\n";
        case vtUXNOR  : return "OP : ~^\\n";
        case vtUNOT   : return "OP : !\\n";
        case vtUXOR   : return "OP : ^\\n";
        case vtUPOSE  : return "OP : pos\\n";
        case vtUNEGE  : return "OP : neg\\n";

        /* binary */
        case vtBPOW   : return "OP : **\\n";
        case vtBNAND  : return "OP : ~&\\n";
        case vtBNOR   : return "OP : ~|\\n";
        case vtBXNOR  : return "OP : ~^\\n";
        case vtBMOD   : return "OP : %\\n";
        case vtBMUL   : return "OP : *\\n";
        case vtBDIV   : return "OP : /\\n";
        case vtBADD   : return "OP : +\\n";
        case vtBSUB   : return "OP : -\\n";
        case vtBLRS   : return "OP : >>\\n";
        case vtBLLS   : return "OP : <<\\n";
        case vtBARS   : return "OP : >>>\\n";
        case vtBALS   : return "OP : <<<\\n";
        case vtBLT    : return "OP : <\\n";
        case vtBGT    : return "OP : >\\n";
        case vtBLE    : return "OP : <=\\n";
        case vtBGE    : return "OP : >=\\n";
        case vtBLEQ   : return "OP : ==\\n";
        case vtBLIEQ  : return "OP : !=\\n";
        case vtBCEQ   : return "OP : ===\\n";
        case vtBCIEQ  : return "OP : !==\\n";
        case vtBSAND  : return "OP : &\\n";
        case vtBSXOR  : return "OP : ^\\n";
        case vtBSOR   : return "OP : |\\n";
        case vtBDAND  : return "OP : &&\\n";
        case vtBDOR   : return "OP : ||\\n";

        case vtASSIGN : return "OP : =\\n";

        /* ternery */
        case vtQUES   : return "OP : ?\\n";
        case vtSEMI   : return "OP : :\\n";

        default       : return "OP : \\n";
      }
    }

static String dot_str_detail_type( int t )
{
  switch( t )
  {
    case veEXP_PRI         : return "EXP : PRIMARY\\n";
    case veEXP_UNA         : return "EXP : UNARY\\n";
    case veEXP_BIN         : return "EXP : BINARY\\n";
    case veEXP_MINTY       : return "EXP : MINTYPMAX\\n";
    case veEXP_QUES        : return "EXP : QUESTION\\n";
    case veEXP_MULTI       : return "EXP : MULTIPLE\\n";
    case veEXP_RANGE       : return "EXP : RANGE\\n";
    case veEXP_CALLER      : return "EXP : CALLER\\n";
    case veEXP_ARRAY       : return "EXP : ARRAY\\n";
    case veEXP_EVENT       : return "EXP : EVENT\\n";
    case veEXP_ASSIGN      : return "EXP : ASSIGNMENT\\n";
    case veEXP_MCONCAT     : return "EXP : MULTI-CONTAT\\n";
    case veEXP_DELAY       : return "EXP : DELAY\\n";
    case veEXP_DRIVE       : return "EXP : DRIVE\\n";
    case veEXP_PORT_REF    : return "EXP : PORT-REFERENCE\\n";
    case veEXP_NAMED_PARAM : return "EXP : NAMED-PARAMETER\\n";
    case veEXP_SIGN        : return "EXP : SYS-$signed\\n";
    case veEXP_UNSIGN      : return "EXP : SYS-$unsigned\\n";
    case veEXP_DUMMY_PORT  : return "EXP : DUMMY_PORT\\n";

    case vsSTMT_DUMMY                 : return "STMT : DUMMY\\n";
    case vsSTMT_BLOCKING              : return "STMT : BLOCKING\\n";
    case vsSTMT_CASE                  : return "STMT : CASE\\n";
    case vsSTMT_COND                  : return "STMT : CONDITION\\n";
    case vsSTMT_DISABLE               : return "STMT : DISABLE\\n";
    case vsSTMT_EVENT                 : return "STMT : EVENT\\n";
    case vsSTMT_LOOP                  : return "STMT : LOOP\\n";
    case vsSTMT_NONBLOCKING           : return "STMT : NONBLOCKING\\n";
    case vsSTMT_PAR_BLOCK             : return "STMT : PAR_BLOCK\\n";
    case vsSTMT_PROC_CONT_ASSIGN      : return "STMT : PROC_CONT_ASSIGN\\n";
    case vsSTMT_PROC_TIME_CONTROL     : return "STMT : PROC_TIME_CONTROL\\n";
    case vsSTMT_SEQ_BLOCK             : return "STMT : SEQ_BLOCK\\n";
    case vsSTMT_EVENT_TRIGGER         : return "STMT : EVENT_TRIGGER\\n";
    case vsSTMT_WAIT_FORK                  : return "STMT : WAIT_FORK\\n";
    case vsSTMT_DISABLE_FORK                  : return "STMT : DISABLE_FORK\\n";
    case vsSTMT_WAIT                  : return "STMT : WAIT\\n";
    case vsSTMT_FUNC_BLOCKING         : return "STMT : FUNC_BLOCKING\\n";
    case vsSTMT_FUNC_CASE             : return "STMT : FUNC_CASE\\n";
    case vsSTMT_FUNC_COND             : return "STMT : FUNC_CONDITION\\n";
    case vsSTMT_FUNC_LOOP             : return "STMT : FUNC_LOOP\\n";
    case vsSTMT_FUNC_SEQ_BLOCK        : return "STMT : FUNC_SEQ_BLOCK\\n";
    case vsSTMT_FUNC_DEFAULT_CASE_ITEM: return "STMT : FUNC_DEFAULT_CASE_ITEM\\n";
    case vsSTMT_FUNC_CASE_ITEM        : return "STMT : FUNC_CASE_ITEM\\n";
    case vsSTMT_FUNC_CASE_ITEM_LIST   : return "STMT : FUNC_CASE_ITEM_LIST\\n";
    case vsSTMT_FUNC_CASE_STMT        : return "STMT : FUNC_CASE\\n";
    case vsSTMT_DEFAULT_CASE_ITEM     : return "STMT : DEFAULT_CASE_ITEM\\n";
    case vsSTMT_CASE_ITEM             : return "STMT : CASE_ITEM\\n";
    case vsSTMT_CASE_ITEM_LIST        : return "STMT : CASE_ITEM_LIST\\n";
    case vsSTMT_SYS_CALL              : return "STMT : SYS_CALL\\n";
    case vsSTMT_CALL                  : return "STMT : CALL\\n";
    case vsSTMT_STMT_LIST             : return "STMT : STMT_LIST\\n";
    case vsSTMT_FUNC_STMT_LIST        : return "STMT : FUNC_STMT_LIST\\n";
    case vsSTMT_CONT_ASSIGN           : return "STMT : CONT_ASSIGN\\n";
    case vsSTMT_INIT                  : return "STMT : INIT\\n";
    case vsSTMT_ALWAYS                : return "STMT : ALWAYS\\n";
    case vsSTMT_MOD_ITEM_LIST         : return "STMT : MODULE_ITEM_LIST\\n";
    case vsSTMT_BLOCK_ITEM_DECL_LIST  : return "STMT : BLOCK_ITEM_DECL_LIST\\n";

    case vsINST_DUMMY                 : return "INST : DUMMY\\n";
    case vsINST_GEN_DEFAULT_CASE_ITEM : return "INST : GEN_DEFAULT_CASE_ITEM\\n";
    case vsINST_GEN_CASE_ITEM         : return "INST : GEN_CASE_ITEM\\n";
    case vsINST_GEN_CASE_ITEM_LIST    : return "INST : GEN_CASE_ITEM_LIST\\n";
    case vsINST_GEN_ITEM_LIST         : return "INST : GEN_ITEM_LIST\\n";
    case vsINST_GEN_BLOCK             : return "INST : GEN_BLOCK\\n";
    case vsINST_GEN_COND              : return "INST : GEN_COND\\n";
    case vsINST_MOD_INSTANCE          : return "INST : MOD_INSTANCE\\n";
    case vsINST_GATE_INSTANCE         : return "INST : GATE_INSTANCE\\n";
    case vsINST_MOD_INSTANTIATION     : return "INST : MOD_INSTANTIATION\\n";
    case vsINST_GATE_INSTANTIATION    : return "INST : GATE_INSTANTIATION\\n";
    case vsINST_GEN_CASE              : return "INST : GEN_CASE\\n";
    case vsINST_GEN_LOOP              : return "INST : GEN_LOOP\\n";

    case vsDECL_TF_DECL              : return "DECL : TF_DECL\\n";
    case vsDECL_TASK_PORT_LIST       : return "DECL : TASK_PORT_LIST\\n";
    case vsDECL_FUNC_PORT_LIST       : return "DECL : FUNC_PORT_LIST\\n";
    case vsDECL_TASK_ITEM_DECL_LIST  : return "DECL : TASK_ITEM_DECL_LIST\\n";
    case vsDECL_BLOCK_ITEM_DECL_LIST : return "DECL : BLOCK_ITEM_DECL_LIST\\n";
    case vsDECL_FUNC_ITEM_DECL_LIST  : return "DECL : FUNC_ITEM_DECL_LIST\\n";
    case vsDECL_TASK_DECL            : return "DECL : TASK_DECL\\n";
    case vsDECL_FUNC_DECL            : return "DECL : FUNC_DECL\\n";
    case vsDECL_VAR                  : return "DECL : VAR\\n";
    case vsDECL_PARAM                : return "DECL : PARAM\\n";
    case vsDECL_INT                  : return "DECL : INT\\n";
    case vsDECL_GENVAR               : return "DECL : GENVAR\\n";
    case vsDECL_PARAM_DECL_LIST      : return "DECL : PARAM_DECL_LIST\\n";
    case vsDECL_PORT_DECL_LIST       : return "DECL : PORT_DECL_LIST\\n";
    default                          : return "DETAIL UNKNOWN\\n";
  }
}

};

};
#endif // PARSER_VERILOG_VERI_NODE_HPP_
