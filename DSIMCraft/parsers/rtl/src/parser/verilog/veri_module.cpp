/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_module.cpp
 * Summary  : verilog syntax analyzer :: module functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */

#ifdef DEBUG_PARSER
#include <iostream>
#endif

#include <algorithm>
#include "general_err.hpp"
#include "veri_err_token.hpp"

#include "veri_num.hpp"

#include "veri_var.hpp"
#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include "veri_inst.hpp"
#include "veri_tfmg.hpp"
#include "veri_stmt.hpp"

#include "veri_module.hpp"
#include "veri_parser.hpp"

namespace rtl
{

void
VeriMod::init( int symbol_table_size )
{
  _symbols = new SymbolTable;
  _symbols->init( symbol_table_size, _mod_name );
  set_scope( _symbols );
}

void
VeriMod::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( _symbols != NULL )
    delete _symbols;
  _symbols = NULL;
  set_scope( NULL );

  _act_ports.clear( );
  _act_port_num = 0;
  _modport_prototypes.clear();
}

void
VeriMod::clear( void )
{
  set_pstatus( vSTART_S );
  if( _symbols != NULL )
    delete _symbols;
  _symbols = NULL;
  set_scope( NULL );

  _act_ports.clear( );
  _act_port_num = 0;
  _modport_prototypes.clear();
}

int
VeriMod::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  if(_header_imports){mqueue.push(_header_imports);iqueue.push(depth);}

  if( _param != NULL )
  {
    mqueue.push( _param );
    iqueue.push( depth );
  }

  if( _port != NULL )
  {
    mqueue.push( _port );
    iqueue.push( depth );
  }

  if( _item != NULL )
  {
    mqueue.push( _item );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriMod::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _mod_name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _header_imports );
  ofile << dot_str_conn( idx(), _param );
  ofile << dot_str_conn( idx(), _port  );
  ofile << dot_str_conn( idx(), _item  );

  return OK;
}

int
VeriMod::check_child_validation( void )
{
  if( _port == NULL )
    return OK;
  if( _port->detail_type( ) == veEXP_MULTI )
  {
    VeriMultiExp *port_list = static_cast<VeriMultiExp *>(_port);
    NodeList& exp_list = port_list->exp();

    NodeList::iterator iport = exp_list.begin();

    for( ; iport != exp_list.end(); ++iport )
    {
      if( (*iport) == NULL )
      {
        veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_MODULE_PORT_ID );
        return vCHILD_TYPE_MODULE_PORT_ID;
      }

      if( (*iport)->detail_type( ) != veEXP_PRI )
      {
        veri_err->append_err( ERR_ERROR, (*iport)->line(), (*iport)->col(),
                          vCHILD_TYPE_MODULE_PORT_ID );
        return vCHILD_TYPE_MODULE_PORT_ID;
      }
    }
  }
  else if( _port->detail_type( ) == vsDECL_PORT_DECL_LIST )
  {
    VeriPortDeclList *port_list = static_cast<VeriPortDeclList *>(_port);
    NodeList & port_decl_list = port_list->port_list( );

    NodeList::iterator idecl = port_decl_list.begin( );
    NodeList::iterator iport;

    for( ; idecl != port_decl_list.end( ); ++idecl )
    {
      if( (*idecl) == NULL )
      {
        veri_err->append_err( ERR_ERROR, line(), col(),
                              vCHILD_TYPE_MODULE_PORT_ID );
        return vCHILD_TYPE_MODULE_PORT_ID;
      }
      
      if( (*idecl)->detail_type( ) != vsDECL_VAR )
      {
        veri_err->append_err( ERR_ERROR, (*idecl)->line(), (*idecl)->col(),
                          vCHILD_TYPE_MODULE_PORT_ID );
        return vCHILD_TYPE_MODULE_PORT_ID;
      }
    }
  }

  return OK;
}

int
VeriMod::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_everything( mstack );
      set_pstatus( has_interface_ports()?vSEARCH_DECL_S:vEND_S );
      return re;
      break;

    case vSEARCH_DECL_S:
      re=bind_interface_ports();
      if(re!=OK)return re;
      set_pstatus(vEND_S);mstack.push_back(this);
      if(_item){_item->set_scope(scope());mstack.push_back(_item);}
      return OK;
    default:
      return map_ports( );
      break;
  }
}

bool VeriMod::has_interface_ports() const {
  if(!_port||_port->detail_type()!=vsDECL_PORT_DECL_LIST)return false;
  for(auto* n:static_cast<VeriPortDeclList*>(_port)->port_list())
    if(static_cast<VeriVarDecl*>(n)->interface_port())return true;
  return false;
}
int VeriMod::bind_interface_ports() {
  if(!father()||father()->detail_type()!=vsINST_MOD_INSTANCE)
    throw std::runtime_error("top module cannot have unbound interface ports");
  int status=prep_ports_for_map();if(status!=OK)return status;
  std::vector<VeriVar*> formal;for(auto* n:_act_ports)formal.push_back(static_cast<VeriVar*>(n));
  std::vector<VeriNode*> actual(formal.size(),nullptr);std::vector<bool> seen(formal.size());
  auto* inst=static_cast<VeriModInstance*>(father());bool named=false,positional=false;size_t pos=0;
  if(inst->arg())for(auto* a:static_cast<VeriMultiExp*>(inst->arg())->exp()) {
    size_t i=pos;
    if(a->detail_type()==veEXP_NAMED_PARAM) {
      if(positional)throw std::runtime_error("module connections cannot mix positional and named ports");named=true;
      auto* arg=static_cast<VeriNamedParamExp*>(a);
      auto it=std::find_if(formal.begin(),formal.end(),[&](VeriVar* v){return v->name()==arg->ref();});
      if(it==formal.end())throw std::runtime_error("unknown port: "+arg->ref());i=it-formal.begin();a=arg->port_exp();
      if(a&&a->detail_type()==veEXP_MULTI){auto& values=static_cast<VeriMultiExp*>(a)->exp();if(values.size()!=1)throw std::runtime_error("interface port requires one argument");a=values.front();}
    } else {if(named)throw std::runtime_error("module connections cannot mix positional and named ports");positional=true;++pos;}
    if(i>=formal.size())throw std::runtime_error("too many positional ports");
    if(seen[i])throw std::runtime_error("duplicate module port: "+formal[i]->name());seen[i]=true;actual[i]=a;
  }
  for(size_t i=0;i<formal.size();++i)if(formal[i]->interface_port()) {
    auto* v=formal[i];auto* a=actual[i];VeriMod* target=nullptr;std::string view;
    if(a&&a->detail_type()==veEXP_PRI) {
      auto* symbol=static_cast<VeriPrimaryExp*>(a)->var();
      if(symbol&&symbol->tok_type()==vtMOD_INST)target=static_cast<VeriMod*>(static_cast<VeriModInstance*>(static_cast<VeriModInst*>(symbol)->instance())->hive());
      else if(symbol&&symbol->tok_type()==vtVAR) {auto* port=static_cast<VeriVar*>(symbol);target=port->interface_instance();view=port->interface_modport();}
    } else if(a&&a->detail_type()==veEXP_MEMBER) {
      auto* member=static_cast<VeriMemberExp*>(a);target=member->interface_view_instance();view=member->member();
    }
    if(!target||!target->is_interface())throw std::runtime_error("interface port "+v->name()+" requires an elaborated interface instance");
    if(v->interface_type()!="*"&&v->interface_type()!=target->name())throw std::runtime_error("interface type mismatch on port "+v->name());
    if(!v->interface_modport().empty()) {
      if(!view.empty()&&view!=v->interface_modport())throw std::runtime_error("incompatible modport view on port "+v->name());
      view=v->interface_modport();
    }
    if(!view.empty()&&!target->modports().count(view))throw std::runtime_error("unknown modport "+view+" on interface "+target->name());
    v->bind_interface(target,view);
  }
  return OK;
}

int
VeriMod::push_everything( NodeVec& mstack )
{
  if( father() != NULL )
    set_scope( scope()->append_scope( _mod_name, vMOD_SCOPE ) );

  scope()->set_compilation_scope(_compilation_scope);
  // Module definitions and local values have separate namespaces. A module
  // named counter may legally contain a register also named counter. The
  // selected root instance is resolved explicitly for hierarchical references.
  int re = prepare_parameter_overrides();
  if( re != OK )
    return re;
  // Run port mapping only after parameters, declarations and instances.
  mstack.push_back( this );

  if( _port == NULL || _port->detail_type( ) == vsDECL_PORT_DECL_LIST )
  {
    if( _item != NULL && !has_interface_ports() )
    {
      _item->set_scope( scope( ) );
      mstack.push_back( _item );
    }

    if( _port != NULL )
    {
      _port->set_is_decl( IS_TRUE );
      _port->set_is_trash( IS_TRUE );
      _port->set_scope( scope( ) );
      mstack.push_back( _port );
    }

    if( _param != NULL )
    {
      _param->set_is_decl( IS_TRUE );
      _param->set_is_trash( IS_TRUE );
      _param->set_scope( scope( ) );
      mstack.push_back( _param );
    }

  }
  else if( _port->detail_type( ) == veEXP_MULTI )
  {
    if( _port != NULL )
    {
      _port->set_is_trash( IS_TRUE );
      _port->set_scope( scope( ) );
      mstack.push_back( _port );
    }

    if( _item != NULL )
    {
      _item->set_scope( scope( ) );
      mstack.push_back( _item );
    }

    if( _param != NULL )
    {
      _param->set_is_decl( IS_TRUE );
      _param->set_is_trash( IS_TRUE );
      _param->set_scope( scope( ) );
      mstack.push_back( _param );
    }
  }

  // The work stack is LIFO: bind imports before any header defaults/types.
  if(_header_imports) {
    _header_imports->set_scope(scope());
    mstack.push_back(_header_imports);
  }

  return OK;
}

int
VeriMod::prepare_parameter_overrides( void )
{
  _parameter_overrides.clear();
  _parameter_override_expressions.clear();
  if( father() == NULL )
    return OK;
  auto* instance = static_cast<VeriModInstance *>(father());
  auto* declaration = static_cast<VeriModInstantiation *>(instance->father());
  if( declaration->param() == NULL )
    return OK;

  // Header parameters define the override order when a header is present.
  // Otherwise use module-level parameter declarations, excluding localparam.
  NodeList declarations;
  if( _param != NULL )
    declarations = static_cast<VeriParamDeclList *>(_param)->param_list();
  else if( _item != NULL )
    declarations = static_cast<VeriModuleItemList *>(_item)->item_list();
  std::vector<String> names;
  NodeMap formals;
  for( auto* node : declarations )
  {
    if( node->detail_type() != vsDECL_PARAM )
      continue;
    auto* param = static_cast<VeriParamDecl *>(node);
    if( param->is_local() == IS_TRUE )
      continue;
    for( auto* var : param->vars() )
    {
      auto* assignment = static_cast<VeriAssignExp *>(var);
      const String& name = static_cast<VeriPrimaryExp *>(assignment->lval())->str();
      names.push_back(name);
      formals[name] = assignment;
    }
  }
  bool named = false, positional = false;
  size_t position = 0;
  for( auto* node : static_cast<VeriMultiExp *>(declaration->param())->exp() )
  {
    String name;
    VeriExp* expression = static_cast<VeriExp *>(node);
    if( node->detail_type() == veEXP_NAMED_PARAM )
    {
      named = true;
      auto* argument = static_cast<VeriNamedParamExp *>(node);
      name = argument->ref();
      expression = static_cast<VeriExp *>(argument->port_exp());
      // Named arguments use the caller's comma-list wrapper. It supplies no
      // self-determined sizing boundary around the actual value expression.
      if(expression&&expression->detail_type()==veEXP_MULTI) {
        auto* list=static_cast<VeriMultiExp*>(expression);
        if(list->multi_type()==vemCOMMA_EXP)
          expression=list->exp().size()==1?static_cast<VeriExp*>(list->exp().front()):NULL;
      }
      if( positional || formals.find(name) == formals.end() )
        expression = NULL;
    }
    else
    {
      positional = true;
      if( named || position >= names.size() )
        expression = NULL;
      else
        name = names[position++];
    }
    if( expression == NULL || expression->calc_value() == NULL ||
        _parameter_overrides.count(name) )
    {
      veri_err->append_err(ERR_ERROR, node, vSEC_MOD_PARAM_MISMATCH);
      return vSEC_MOD_PARAM_MISMATCH;
    }
    _parameter_overrides[name] = expression->calc_value();
    _parameter_override_expressions[name] = expression;
  }
  return OK;
}

int
VeriMod::check_type_ref( VeriExp *exp, VeriVar *port )
{
  if(port->interface_port()) {
    if(exp->detail_type()==veEXP_NAMED_PARAM)static_cast<VeriNamedParamExp*>(exp)->set_port_ref(port);
    return OK;
  }
  int re = OK;

  IVec dummy_dimen;

  VeriVar    *var     = NULL;
  VeriInt    *int_var = NULL;

  switch( exp->detail_type( ) )
  {
    case veEXP_PRI :
    {
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(exp);
      if( pexp->var( ) == NULL )
      {
        if( pexp->pri_type( ) == veNUM && port->range_depth( ) != 0 )
        {
          veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
          return vSEC_MOD_PORT_MISMATCH;
        }
        return OK;
      }

      switch( pexp->var()->tok_type( ) )
      {
        case vtVAR :
          var = static_cast<VeriVar *>(pexp->var());
          if( var->range_depth() != port->range_depth() )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
            return vSEC_MOD_PORT_MISMATCH;
          }
          else
            return OK;
          break;

        case vtTFVAR :
          if( 0 != port->range_depth() )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
            return vSEC_MOD_PORT_MISMATCH;
          }
          else
            return OK;
          break;


        case vtPARAM :
          if( 0 != port->range_depth() )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
            return vSEC_MOD_PORT_MISMATCH;
          }
          else
            return OK;
          break;

        case vtINT :
          int_var = static_cast<VeriInt *>(pexp->var());
          if( int_var->range_depth() != port->range_depth() )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
            return vSEC_MOD_PORT_MISMATCH;
          }
          else
            return OK;
          break;

        case vtGENVAR :
          if( 0 != port->range_depth() )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
            return vSEC_MOD_PORT_MISMATCH;
          }
          else
            return OK;
          break;

        default:
          break;
      }
      break;
    
    }

    case veEXP_UNA :
    case veEXP_BIN :
    case veEXP_SIGN :
    case veEXP_UNSIGN :
      if( port->range_depth( ) != 0 )
      {
        veri_err->append_err( ERR_ERROR, exp, vSEC_MOD_PORT_MISMATCH );
        return vSEC_MOD_PORT_MISMATCH;
      }
      return OK;
      break;

    case veEXP_ARRAY :
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(exp);
      // Packed members already carry their elaborated result shape. Do not
      // reinterpret their receiver as a primary expression.
      if( aexp->id()->detail_type() != veEXP_PRI )
        return port->range_depth() == 0 ? OK : vSEC_MOD_PORT_MISMATCH;
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(aexp->id());

      if( pexp->var() == NULL )
        return vSEC_MOD_PORT_MISMATCH;

      // Array indexing consumes unpacked dimensions. A partial reference may
      // itself connect to an array port; a complete reference is a packed word.
      if( pexp->var()->tok_type() == vtVAR || pexp->var()->tok_type() == vtINT )
      {
        const int dimensions = pexp->var()->tok_type() == vtVAR
            ? static_cast<VeriVar *>(pexp->var())->range_depth()
            : static_cast<VeriInt *>(pexp->var())->range_depth();
        const int consumed = aexp->range_depth();
        if( dimensions > 0 && consumed <= dimensions + 1 )
        {
          auto it = aexp->range().begin();
          bool elements = true;
          for( int i = 0; i < std::min(consumed,dimensions); ++i, ++it )
            elements = elements && static_cast<VeriRangeExp *>(*it)->rtype() == vrSINGLE;
          if( elements && std::max(0,dimensions-consumed) == port->range_depth() )return OK;
          veri_err->append_err( ERR_ERROR, exp, vSEC_MOD_PORT_MISMATCH );
          return vSEC_MOD_PORT_MISMATCH;
        }
      }

      // A packed select does not add an unpacked array dimension.
      if( pexp->var()->tok_type() == vtVAR
          && static_cast<VeriVar *>(pexp->var())->range_depth() == 0
          && aexp->range_depth() == 1 && port->range_depth() == 0 )
        return OK;
      if( aexp->range_depth( ) != port->range_depth( ) )
      {
        veri_err->append_err( ERR_ERROR, exp, vSEC_MOD_PORT_MISMATCH );
        return vSEC_MOD_PORT_MISMATCH;
      }
      return OK;
      break;
    }

    case veEXP_NAMED_PARAM :
    {
      VeriNamedParamExp * nexp = static_cast<VeriNamedParamExp *>(exp);
      if( port->name( ) != nexp->ref() )
      {
        veri_err->append_err( ERR_ERROR, exp, vSEC_MOD_PORT_MISMATCH );
        return vSEC_MOD_PORT_MISMATCH;
      }
      VeriExp *inner_exp = static_cast<VeriExp *>(nexp->port_exp());
      nexp->set_port_ref( port );
      if( inner_exp == NULL )
        return OK;
      return check_type_ref( inner_exp, port );
      break;
    }

    case veEXP_CALLER :
    {
      VeriCallerExp *cexp = static_cast<VeriCallerExp *>(exp);
      if( cexp->call_type() == vtTASK_CALL )
      {
        veri_err->append_err( ERR_ERROR, exp, vSEC_MOD_PORT_MISMATCH );
        return vSEC_MOD_PORT_MISMATCH;
      }
      else
      {
        if( port->range_depth() != 0 )
        {
          veri_err->append_err( ERR_ERROR, exp, vSEC_MOD_PORT_MISMATCH );
          return vSEC_MOD_PORT_MISMATCH;
        }
      }
      break;
    }

    case veEXP_MINTY :
    {
      VeriMintypmaxExp *pmax = static_cast<VeriMintypmaxExp *>(exp);
      VeriExp *exp1 = static_cast<VeriExp *>(pmax->exp_child1( ) );
      VeriExp *exp2 = static_cast<VeriExp *>(pmax->exp_child2( ) );
      VeriExp *exp3 = static_cast<VeriExp *>(pmax->exp_child3( ) );

      re = check_type_ref( exp1, port );
      if( re != OK )
        return re;

      re = check_type_ref( exp2, port );
      if( re != OK )
        return re;
         
      return check_type_ref( exp3, port );
      break;
    }

    case veEXP_QUES :
    {
      VeriQuesExp *ques = static_cast<VeriQuesExp *>(exp);
      VeriExp  *choice1 = static_cast<VeriExp *>(ques->choice1( ) );
      VeriExp  *choice2 = static_cast<VeriExp *>(ques->choice2( ) );

      re = check_type_ref( choice1, port );
      if( re != OK )
        return re;
         
      return check_type_ref( choice2, port );
      break;
    }

    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(exp);
      NodeList & exp_list = mexp->exp();
      NodeList::iterator it = exp_list.begin();
      for( ; it != exp_list.end(); ++it )
      {
        re = check_type_ref( static_cast<VeriExp *>(*it), port );
        if( re != OK )
          return re;
      }
      return OK;
      break;
    }

    case veEXP_MCONCAT :
      /* TODO */;
      return OK;
      break;

    default:
      return OK;
      break;
  }
  return OK;
}

int
VeriMod::prep_ports_for_map( )
{
  _act_ports.clear();
  if( _port == NULL )
    return OK;
  if( _port->detail_type( ) == veEXP_MULTI )
  {
    VeriMultiExp *port_list = static_cast<VeriMultiExp *>(_port);
    NodeList& exp_list = port_list->exp();

    NodeList::iterator iport = exp_list.begin();

    VeriPrimaryExp *pexp = NULL;
    for( ; iport != exp_list.end(); ++iport )
    {
      pexp = static_cast<VeriPrimaryExp *>(*iport);
      if( pexp->var() == NULL || pexp->var()->tok_type() != vtVAR )
      {
        veri_err->append_err(ERR_ERROR, pexp, vSEC_MOD_PORT_MISMATCH);
        return vSEC_MOD_PORT_MISMATCH;
      }
      _act_ports.push_back( pexp->var() );
    }
    return OK;
  }
  else if( _port->detail_type( ) == vsDECL_PORT_DECL_LIST )
  {
    VeriPortDeclList *port_list = static_cast<VeriPortDeclList *>(_port);
    NodeList & port_decl_list = port_list->port_list( );

    VeriVarDecl *var_decl = NULL;

    NodeList::iterator idecl = port_decl_list.begin( );
    NodeList::iterator iport;

    VeriPrimaryExp *pexp = NULL;
    VeriArrayExp   *aexp = NULL;
    for( ; idecl != port_decl_list.end( ); ++idecl )
    {
      var_decl = static_cast<VeriVarDecl *>(*idecl);
      NodeList &vars = var_decl->vars( );
      for( iport = vars.begin(); iport != vars.end(); ++iport )
      {
        pexp = NULL;
        VeriNode *entry = *iport;
        if( entry->detail_type() == veEXP_ASSIGN )
          entry = static_cast<VeriAssignExp *>(entry)->lval();
        if( entry->detail_type( ) == veEXP_PRI )
          pexp = static_cast<VeriPrimaryExp *>(entry);
        else if( entry->detail_type( ) == veEXP_ARRAY )
        {
          aexp = static_cast<VeriArrayExp *>(entry);
          pexp = static_cast<VeriPrimaryExp *>(aexp->id());
        }
        if( pexp == NULL || pexp->var() == NULL || pexp->var()->tok_type() != vtVAR )
        {
          veri_err->append_err(ERR_ERROR, *iport, vSEC_MOD_PORT_MISMATCH);
          return vSEC_MOD_PORT_MISMATCH;
        }
        _act_ports.push_back( pexp->var() );
      }
    }
    return OK;
  }

  return vSEC_MOD_PORT_PARSE_NOT_SUPPORT;
}

namespace {
int prototype_type(int type) {
  if(veri_integral_atom(type))return veri_two_state(type)?vvBIT:vvLOGIC;
  return type==vvWIRE||type==vvREG?vvLOGIC:type;
}
bool prototype_named_type(VeriVar* a,VeriVar* b) {
  auto unpacked=[](VeriVar* v) {auto* t=v?v->aggregate_type():nullptr;return t&&t->unpacked_struct()?t:nullptr;};
  // Packed structs match their integral representation; enums retain identity.
  return (a?a->enum_type():nullptr)==(b?b->enum_type():nullptr)&&unpacked(a)==unpacked(b);
}
bool prototype_shape(const VeriArrayShape& p,const VeriArrayShape& a) {
  if(p.unpacked!=a.unpacked||p.unbound!=a.unbound)return false;
  for(int i=0;i<p.unpacked;++i) {
    auto x=p.dimensions[i],y=a.dimensions[i];
    // Equivalent fixed dimensions need the same size, not the same index labels.
    if(std::abs(int64_t(x.first)-x.second)!=std::abs(int64_t(y.first)-y.second))return false;
  }
  return true;
}
void check_modport_prototype(VeriNode* proto,VeriNode* actual,const std::string& name) {
  auto bad=[&](const std::string& reason){throw std::runtime_error("line "+std::to_string(proto->line())+": modport prototype mismatch for "+name+": "+reason);};
  if(proto->detail_type()!=actual->detail_type())bad("task/function kind");
  if(proto->detail_type()==vsDECL_FUNC_DECL) {
    auto* p=static_cast<VeriFuncDecl*>(proto);auto* a=static_cast<VeriFuncDecl*>(actual);
    if(p->is_void()!=a->is_void())bad("void return type");
    if(!p->is_void()) {
      auto width=[](VeriFuncDecl* f){return f->range()?std::abs(static_cast<VeriRangeExp*>(f->range())->range_from()-static_cast<VeriRangeExp*>(f->range())->range_to())+1:
        f->resolved_type()?f->resolved_type()->dlen():veri_type_width(f->result_type());};
      if(width(p)!=width(a)||p->is_signed()!=a->is_signed()||prototype_type(p->result_type())!=prototype_type(a->result_type())||
         !prototype_named_type(p->resolved_type(),a->resolved_type()))bad("return type");
    }
  }
  auto p=veri_subroutine_formals(proto),a=veri_subroutine_formals(actual);
  if(p.size()!=a.size())bad("argument count");
  for(size_t i=0;i<p.size();++i) {
    auto* pv=static_cast<VeriTfVar*>(veri_formal_symbol(p[i]));auto* av=static_cast<VeriTfVar*>(veri_formal_symbol(a[i]));
    if(!pv||!av)bad("unresolved argument");
    auto ps=veri_array_shape(pv),as=veri_array_shape(av);
    if(pv->inout()!=av->inout()||pv->dlen()!=av->dlen()||pv->is_signed()!=av->is_signed()||
       prototype_type(pv->net_type())!=prototype_type(av->net_type())||pv->dynamic_array()!=av->dynamic_array()||
       !prototype_shape(ps,as)||
       !prototype_named_type(veri_declared_type(pv),veri_declared_type(av)))bad("argument "+std::to_string(i+1)+" type/direction/shape");
    auto* pd=static_cast<VeriTfDecl*>(pv->father());auto* ad=static_cast<VeriTfDecl*>(av->father());
    if(ad->default_argument(av->name())&&!pd->default_argument(pv->name()))bad("default argument must also appear in prototype");
  }
}
}

int
VeriMod::map_ports( void )
{
  scope()->finish_scope();
  _modport_prototypes.clear();
  if(_is_interface) {
    NodeVec pending;if(_item)pending.push_back(_item);
    while(!pending.empty()) {
      auto* n=pending.back();pending.pop_back();
      if(n->detail_type()==vsDECL_FUNC_DECL||n->detail_type()==vsDECL_TASK_DECL) {
        auto* decl=static_cast<VeriDecl*>(n);if(decl->modport_prototype().empty())continue;
        const auto& name=n->detail_type()==vsDECL_FUNC_DECL?static_cast<VeriFuncDecl*>(n)->func_name():static_cast<VeriTaskDecl*>(n)->task_name();
        _modport_prototypes[decl->modport_prototype()][name]=n;
      } else if(n->detail_type()==vsSTMT_MOD_ITEM_LIST)n->push_for_replacement(pending);
    }
  }
  if(_is_interface)for(const auto& view:_modports)for(const auto& member:view.second) {
    auto* symbol=scope()->value_same_level(member.first);
    if(member.second==vpIMPORT) {
      auto* prototype=modport_prototype(view.first,member.first);
      // A prototype can describe an unused external method. Calling one
      // without an interface implementation is diagnosed at the call site.
      if(!symbol&&prototype)continue;
      if(!symbol||(symbol->tok_type()!=vtFUNC&&symbol->tok_type()!=vtTASK))throw std::runtime_error("unknown subroutine "+member.first+" in modport "+view.first);
      if(prototype)check_modport_prototype(prototype,symbol->tok_type()==vtFUNC?
        static_cast<VeriNode*>(static_cast<VeriFunc*>(symbol)->func()):static_cast<VeriNode*>(static_cast<VeriTask*>(symbol)->task()),view.first+"."+member.first);
    } else if(!symbol||(symbol->tok_type()!=vtVAR&&symbol->tok_type()!=vtINT))throw std::runtime_error("unknown signal "+member.first+" in modport "+view.first);
  }

  int re = prep_ports_for_map( );
  if( re != OK )
    return re;
  
  VeriModInstance *father_mod_inst = static_cast<VeriModInstance *>(father());
  if( father_mod_inst == NULL || father_mod_inst->arg() == NULL )
    return OK;

  if( father_mod_inst->arg()->detail_type() == veEXP_MULTI )
  {
    VeriMultiExp *mexp = static_cast<VeriMultiExp *>(father_mod_inst->arg());
    NodeList & exp_list = mexp->exp();

    NodeList::iterator iarg  = exp_list.begin();
    NodeList::iterator iport = _act_ports.begin();

    VeriExp *arg  = NULL;
    VeriVar *port = NULL;
    std::map<String, bool> connected;
    bool named = false, positional = false;
    for( ; iarg != exp_list.end(); ++iarg )
    {
      arg = static_cast<VeriExp *>(*iarg);
      if( arg->detail_type() == veEXP_NAMED_PARAM )
      {
        named = true;
        const String& name = static_cast<VeriNamedParamExp *>(arg)->ref();
        port = NULL;
        for( auto* candidate : _act_ports )
          if( static_cast<VeriVar *>(candidate)->name() == name )
            port = static_cast<VeriVar *>(candidate);
        if( !port || connected[name] || positional )
        {
          veri_err->append_err( ERR_ERROR, arg, vSEC_MOD_PORT_MISMATCH );
          return vSEC_MOD_PORT_MISMATCH;
        }
        connected[name] = true;
      }
      else
      {
        positional = true;
        if( named || iport == _act_ports.end() )
        {
          veri_err->append_err( ERR_ERROR, arg, vSEC_MOD_PORT_MISMATCH );
          return vSEC_MOD_PORT_MISMATCH;
        }
        port = static_cast<VeriVar *>(*iport++);
      }
      if( port->tok_type( ) == vtVAR )
      {
        re = check_type_ref( arg, port );
        if( re != OK )
          return re;
      }
      else
      {
        veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
        return vSEC_MOD_PORT_MISMATCH;
      }
    }
  }
  return OK;
}

int
VeriMod::push_for_replacement( NodeVec& mstack )
{
  if(_header_imports)mstack.push_back(_header_imports);
  if( _param != NULL )
    mstack.push_back( _param );

  if( _port != NULL )
    mstack.push_back( _port );

  if( _item != NULL )
    mstack.push_back( _item );

  return OK;
}

int
VeriMod::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriMod *tmp = new VeriMod( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _item != NULL )
  {
    tmp->_item = *(--itl);
    tmp->_item->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _port != NULL )
  {
    tmp->_port = *(--itl);
    tmp->_port->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _param != NULL )
  {
    tmp->_param = *(--itl);
    tmp->_param->set_father( tmp );
    node_list.erase( itl );
  }

  if(_header_imports) {
    itl=inl;
    tmp->_header_imports=*(--itl);
    tmp->_header_imports->set_father(tmp);
    node_list.erase(itl);
  }

  *inl = tmp;
  return OK;
}

void
VeriMod::set_fname( const SList& fnames, const IList& flines )
{
  _fname.assign( fnames.begin(), fnames.end() );
  _fline.assign( flines.begin(), flines.end() );
#ifdef DEBUG_PARSER
  //std::cout << fnames.back( ) << std::endl;
#endif
}

void
VeriMod::addModInstantiated( void )
{
  if (item() == NULL || item()->detail_type() != vsSTMT_MOD_ITEM_LIST)
    return;

  for (auto iter : ((rtl::VeriModuleItemList*)item())->item_list()) {
    if (iter->tok_type() == vtINST && iter->detail_type() == vsINST_MOD_INSTANTIATION) {
      _modInstantiated.push_back(iter);
    }
  }
}

};
