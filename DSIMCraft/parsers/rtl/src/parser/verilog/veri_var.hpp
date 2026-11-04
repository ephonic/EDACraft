/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_var.hpp
 * Summary  : verilog syntax analyzer true node class : variable
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_VAR_HPP_
#define PARSER_VERILOG_VERI_VAR_HPP_

#include <stdexcept>
#include "veri_node.hpp"

#include <memory>
#include <vector>
#include <string>

namespace rtl
{

class VeriNum;
class VeriVar;
class VeriSeqBlock;
// Shared semantic identity lets handles and signatures retain a forward alias
// before its later typedef is visited. Syntax clones never copy this binding.
struct VeriClassBinding {
  VeriSeqBlock* definition=nullptr;
  std::shared_ptr<VeriClassBinding> alias;
  VeriSeqBlock* get() const {auto* p=this;while(p->alias)p=p->alias.get();return p->definition;}
  void complete(const std::shared_ptr<VeriClassBinding>& target) {
    for(auto* p=target.get();p;p=p->alias.get())
      if(p==this)throw std::runtime_error("cyclic forward class typedef");
    alias=target;
  }
};
struct VeriVirtualInterface { std::string name,view; VeriMod* prototype=nullptr; };
struct VeriPackedField { std::string name; int offset; VeriVar* symbol; };

struct VeriSymbolRangeRec
{
  VeriSymbolRangeRec( int f, int t, int b )
    : from(f)
    , to(t)
    , bits(b)
  {}

  int from;
  int to;
  int bits;
};

/*
 * class VeriSysVar :
 *     Verilog syntax analyzer true node : system variable
 *     system variable is prefixed by '$'
 */
class VeriSysVar : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;
  typedef std::ofstream Ofstream;

  public:
    VeriSysVar( Uint idx, int line, int col, CString& name,
                VeriMod *mod )
      :  VeriNode( idx, vtSYS_VAR, vtSYS_VAR, line, col, mod )
      ,  _name(name)
    {}

    virtual ~VeriSysVar() { clear(); }

    // accessors
    CString& name( void ) const { return _name; }

    // mutators
    void set_name( CString& v ) { _name = v; }

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriSysVar() {};

  private:
    String _name;
};


/*
 * class VeriVar :
 *     Verilog syntax analyzer true node : variable
 */
class VeriVar : public VeriNode
{
  typedef std::string      String;
  typedef const String     CString;
  typedef std::vector<int> IVec;
  typedef std::vector< VeriSymbolRangeRec > SymbolRanges;

  public:
    VeriVar( Uint idx, int line, int col, CString& name, short inout,
             short net_type, short is_signed, short vec_scalar,
             short drive_from, short drive_to, int dstart, int dend,
             VeriNode *decl, VeriNum **val, int total_cnt, VeriMod *mod, int symbol_kind = vtVAR )
      :
         VeriNode( idx, symbol_kind, symbol_kind, line, col, mod )
      , _name(name)
      , _inout(inout)
      , _net_type(net_type)
      , _is_signed(is_signed)
      , _vec_scalar(vec_scalar)
      , _drive_from(drive_from)
      , _drive_to(drive_to)
      , _dstart(dstart)
      , _dend(dend)
      , _dlen(abs(dend-dstart)+1)
      , _decl(decl)
      , _val(val)
      , _total_cnt(total_cnt)
    { }

    virtual ~VeriVar() { clear(); }

    VeriSeqBlock* class_type() const {return _class_type?_class_type->get():nullptr;}
    void set_class_type(VeriSeqBlock* type) {
      _class_type=type?std::make_shared<VeriClassBinding>():nullptr;
      if(_class_type)_class_type->definition=type;
    }
    void set_class_type_from(VeriVar* type) {_class_type=type->class_binding();_virtual_interface=type->virtual_interface();}
    const std::shared_ptr<VeriVirtualInterface>& virtual_interface() const {return _virtual_interface;}
    void set_virtual_interface(std::shared_ptr<VeriVirtualInterface> type) {_virtual_interface=std::move(type);}
    const std::shared_ptr<VeriClassBinding>& class_binding() const {return _class_type;}
    void set_forward_class_type() {_class_type=std::make_shared<VeriClassBinding>();}
    void complete_forward_class_type(VeriVar* type) {
      if(!type->class_binding()||type->range_depth())
        throw std::runtime_error("forward class typedef requires a scalar class type");
      _class_type->complete(type->class_binding());
    }
    void infer_associative_index(VeriVar* type) {
      _class_type=type->class_binding();_enum_type=type->enum_type();_aggregate_type=type->aggregate_type();
      _net_type=type->net_type();_is_signed=type->is_signed();
      _dstart=type->dstart();_dend=type->dend();_dlen=type->dlen();
    }
    bool unpacked_struct() const {return _unpacked_struct;}
    void set_unpacked_struct() {_unpacked_struct=true;}
    bool port_redeclared() const {return _port_redeclared;}
    void set_port_redeclared() {_port_redeclared=true;}
    bool interface_port() const { return !_interface_type.empty(); }
    const std::string& interface_type() const { return _interface_type; }
    const std::string& interface_modport() const { return _interface_modport; }
    VeriMod* interface_instance() const { return _interface_instance; }
    void set_interface_port(const std::string& type,const std::string& view) { _interface_type=type;_interface_modport=view; }
    void bind_interface(VeriMod* instance,const std::string& view) { _interface_instance=instance;_interface_modport=view; }
    VeriVar* aggregate_type() const { return _aggregate_type; }
    void set_aggregate_type(VeriVar* type) { _aggregate_type=type; }
    std::vector<VeriPackedField>& packed_fields() { return _packed_fields; }
    VeriVar* enum_type() const { return _enum_type; }
    void set_enum_type(VeriVar* type) { _enum_type=type; }
    // Declaration order, owned by the parser node pool, rebuilt per clone.
    std::vector<VeriNum*>& enum_values() { return _enum_values; }
    std::vector<std::string>& enum_names() { return _enum_names; }

    // accessors
    CString& name   ( void ) const { return _name;        }
    short inout     ( void ) const { return _inout;       }
    short net_type  ( void ) const { return _net_type;    }
    short is_signed ( void ) const { return _is_signed;   }
    short vec_scalar( void ) const { return _vec_scalar;  }
    short drive_from( void ) const { return _drive_from;  }
    short drive_to  ( void ) const { return _drive_to;    }
    int   dstart    ( void ) const { return _dstart;      }
    int   dend      ( void ) const { return _dend;        }
    int   dlen      ( void ) const { return _dlen;        }

    // depth starts from 1
    void  get_range ( unsigned int depth, int& start, int& end, int& bits );
    int   range_depth( void ) const { return _range.size(); }
    bool dynamic_array() const {return _dynamic_array;}
    void set_dynamic_array(bool value) {_dynamic_array=value;}
    int container_kind(unsigned axis=0) const {return axis<_container_dimensions.size()?_container_dimensions[axis].first:axis?vrSINGLE:_container_kind;}
    int container_bound(unsigned axis=0) const {return !axis?_container_bound:axis<_container_bounds.size()?_container_bounds[axis]:-1;}
    void set_dimension_bound(unsigned axis,int bound) {if(_container_bounds.size()<=axis)_container_bounds.resize(axis+1,-1);_container_bounds[axis]=bound;if(!axis)_container_bound=bound;}
    VeriVar* associative_key_type(unsigned axis=0) const {return axis<_container_dimensions.size()?_container_dimensions[axis].second:axis?nullptr:_associative_key_type;}
    void set_dimension_container(unsigned axis,int kind,VeriVar* key=nullptr) {if(_container_dimensions.size()<=axis)_container_dimensions.resize(axis+1,{vrSINGLE,nullptr});_container_dimensions[axis]={kind,key};if(!axis){set_container(kind,_container_bound);set_associative_key_type(key);}}
    void set_associative_key_type(VeriVar* type) {_associative_key_type=type;}
    void set_container(int kind,int bound=-1) {_container_kind=kind;_container_bound=bound;_dynamic_array=kind>=vrOPEN;}


    VeriNum * get_one_num( const IVec& dimen, int is_whole, int dstart, int dend );

    // mutators
    void set_name       ( CString& v ) { _name        = v; }
    void set_inout      ( short v    ) { _inout       = v; }
    void set_net_type   ( short v    ) { _net_type    = v; }
    void set_is_signed  ( short v    ) { _is_signed   = v; }
    void set_vec_scalar ( short v    ) { _vec_scalar  = v; }
    void set_drive_from ( short v    ) { _drive_from  = v; }
    void set_drive_to   ( short v    ) { _drive_to    = v; }

    int  set_one_num( const IVec& dimen, int is_whole, int dstart,
                      int dend, VeriNum *val );

    void add_range( int start, int end )
    {
      _range.push_back( SymbolRanges::value_type(
                              VeriSymbolRangeRec( start,
                                                  end,
                                                  abs(end - start) + 1 )
                                                )
                      );
    }

    virtual void clear( void );

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriVar() {};

    int calc_dimen_cnt( int start_lvl );
    int determin_idx( const IVec& dimen );

  private:
    std::shared_ptr<VeriVirtualInterface> _virtual_interface;
    std::shared_ptr<VeriClassBinding> _class_type; // Semantic declaration binding, rebuilt by elaboration.
    VeriVar* _aggregate_type=nullptr;
    std::vector<VeriPackedField> _packed_fields;
    VeriVar* _enum_type=nullptr;
    std::vector<VeriNum*> _enum_values;
    std::vector<std::string> _enum_names;
    std::string _interface_type, _interface_modport;
    VeriMod* _interface_instance=nullptr; // Non-owning, rebuilt per elaboration.
    String _name;

    short  _inout;
    short  _net_type;

    short  _is_signed;
    short  _vec_scalar;

    short  _drive_from;
    short  _drive_to;

    int    _dstart;
    int    _dend;
    int    _dlen;

    SymbolRanges _range;
    std::vector<std::pair<int,VeriVar*>> _container_dimensions;
    std::vector<int> _container_bounds;
    int _container_kind=vrSINGLE,_container_bound=-1;
    VeriVar* _associative_key_type=nullptr; // Non-owning semantic binding, rebuilt per elaboration.
    bool _dynamic_array=false,_port_redeclared=false,_unpacked_struct=false;

    VeriNode  *_decl;
    VeriNum  **_val;
    int        _total_cnt;
};

/*
 * class VeriTfVar :
 *     Verilog syntax analyzer true node : tf-variable
 */
class VeriTfVar : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;

  public:
    VeriTfVar( Uint idx, int line, int col, CString& name, short inout,
               short net_type, short is_signed, VeriNode *decl, int dstart,
               int dend, VeriNum *val, VeriMod *mod )
      :  VeriNode( idx, vtTFVAR, vtTFVAR, line, col, mod )
      , _name(name)
      , _inout(inout)
      , _net_type(net_type)
      , _is_signed(is_signed)
      , _dstart(dstart)
      , _dend(dend)
      , _dlen(abs(dend-dstart)+1)
      , _decl(decl)
      , _val(val)
    {}

    virtual ~VeriTfVar() { clear(); }

    VeriSeqBlock* class_type() const {return _class_type?_class_type->get():nullptr;}
    void set_class_type(VeriSeqBlock* type) {
      _class_type=type?std::make_shared<VeriClassBinding>():nullptr;
      if(_class_type)_class_type->definition=type;
    }
    void set_class_type_from(VeriVar* type) {_class_type=type->class_binding();_virtual_interface=type->virtual_interface();}
    const std::shared_ptr<VeriVirtualInterface>& virtual_interface() const {return _virtual_interface;}
    void set_virtual_interface(std::shared_ptr<VeriVirtualInterface> type) {_virtual_interface=std::move(type);}
    // accessors
    CString& name  ( void ) const { return _name;        }
    short inout    ( void ) const { return _inout;       }
    short net_type ( void ) const { return _net_type;    }
    short is_signed( void ) const { return _is_signed;   }
    VeriNum *get_val( void );

    int range_depth() const { return int(_dimensions.size()); }
    void add_range(int first,int last,bool open=false) {
      _dimensions.push_back({first,last});_open_dimensions.push_back(open);
    }
    bool dynamic_array() const {return _dynamic_array;}
    void set_dynamic_array(bool value) {_dynamic_array=value;}
    int container_kind(unsigned axis=0) const {return axis<_container_dimensions.size()?_container_dimensions[axis].first:axis?vrSINGLE:_container_kind;}
    int container_bound(unsigned axis=0) const {return !axis?_container_bound:axis<_container_bounds.size()?_container_bounds[axis]:-1;}
    void set_dimension_bound(unsigned axis,int bound) {if(_container_bounds.size()<=axis)_container_bounds.resize(axis+1,-1);_container_bounds[axis]=bound;if(!axis)_container_bound=bound;}
    VeriVar* associative_key_type(unsigned axis=0) const {return axis<_container_dimensions.size()?_container_dimensions[axis].second:axis?nullptr:_associative_key_type;}
    void set_dimension_container(unsigned axis,int kind,VeriVar* key=nullptr) {if(_container_dimensions.size()<=axis)_container_dimensions.resize(axis+1,{vrSINGLE,nullptr});_container_dimensions[axis]={kind,key};if(!axis){set_container(kind,_container_bound);set_associative_key_type(key);}}
    void set_associative_key_type(VeriVar* type) {_associative_key_type=type;}
    void set_container(int kind,int bound=-1) {_container_kind=kind;_container_bound=bound;_dynamic_array=kind>=vrOPEN;}

    bool open_range(unsigned depth) const {return _open_dimensions.at(depth-1);}
    bool has_open_ranges() const {for(bool open:_open_dimensions)if(open)return true;return false;}
    bool unbound_ranges() const {
      for(size_t i=0;i<_dimensions.size();++i)if(_open_dimensions[i]&&_dimensions[i].second<0)return true;
      return false;
    }
    void bind_open_range(unsigned depth,int count) {
      if(!open_range(depth)||count<1)throw std::runtime_error("invalid unsized formal dimension binding");
      _dimensions.at(depth-1)={0,count-1};
    }
    void get_range(unsigned depth,int& first,int& last,int& count) const {
      const auto& range=_dimensions.at(depth-1);first=range.first;last=range.second;
      count=int(std::abs(int64_t(first)-last)+1);
    }
    int   dstart( void ) const { return _dstart; }
    int   dend  ( void ) const { return _dend;   }
    int   dlen  ( void ) const { return _dlen;   }
 
    // mutators
    void set_name     ( CString& v ) { _name      = v; }
    void set_inout    ( short v    ) { _inout     = v; }
    void set_net_type ( short v    ) { _net_type  = v; }
    void set_is_signed( short v    ) { _is_signed = v; }
    void set_dstart( int v ) { _dstart = v; }
    void set_dend( int v ) { _dend = v; }
    void set_dlen( int v ) { _dlen = v; }
    void set_val( VeriNum *val );

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriTfVar() {};

  private:
    std::shared_ptr<VeriVirtualInterface> _virtual_interface;
    std::shared_ptr<VeriClassBinding> _class_type;
    std::vector<std::pair<int,int>> _dimensions;
    std::vector<bool> _open_dimensions;
    std::vector<std::pair<int,VeriVar*>> _container_dimensions;
    std::vector<int> _container_bounds;
    int _container_kind=vrSINGLE,_container_bound=-1;
    VeriVar* _associative_key_type=nullptr; // Non-owning semantic binding, rebuilt per elaboration.
    bool _dynamic_array=false;
    String _name;

    short  _inout;
    short  _net_type;
    short  _is_signed;

    int    _dstart;
    int    _dend;
    int    _dlen;

    VeriNode  *_decl;
    VeriNum   *_val;
};


/*
 * class VeriParam :
 *     Verilog syntax analyzer true node : parameter
 */
class VeriParam : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;

  public:
    VeriParam( Uint idx, int line, int col, CString& name,
               short is_int, short is_local, short is_signed,
               VeriNode *decl, int dstart, int dend,
               VeriNum *val, VeriMod *mod )
      :  VeriNode( idx, vtPARAM, vtPARAM, line, col, mod )
      , _name(name)
      , _is_int(is_int)
      , _is_local(is_local)
      , _is_signed(is_signed)
      , _is_head_override( IS_FALSE)
      , _dstart(dstart)
      , _dend(dend)
      , _dlen(abs(dend-dstart)+1)
      , _decl(decl)
      , _val(val)
    {}

    VeriParam( Uint idx, int line, int col, CString& name,
               VeriNode *decl, int dstart, int dend,
               VeriNum *val, VeriMod *mod )
      :  VeriNode( idx, vtPARAM, vtPARAM, line, col, mod )
      , _name(name)
      , _is_int(IS_FALSE)
      , _is_local(IS_FALSE)
      , _is_signed(IS_FALSE)
      , _is_head_override(IS_TRUE)
      , _dstart(dstart)
      , _dend(dend)
      , _dlen(abs(dend-dstart)+1)
      , _decl(decl)
      , _val(val)
    {}

    virtual ~VeriParam() { clear(); }

    VeriVar* enum_type() const { return _enum_type; }
    void set_enum_type(VeriVar* type) { _enum_type=type; }

    // accessors
    CString& name  ( void ) const { return _name;        }
    short is_int   ( void ) const { return _is_int;      }
    short is_local ( void ) const { return _is_local;    }
    short is_signed( void ) const { return _is_signed;   }
    short is_head_override( void ) const { return _is_head_override; }
    VeriNum *get_val( void );
    VeriNode *decl( void ) { return _decl; }

    int   dstart( void ) const { return _dstart; }
    int   dend  ( void ) const { return _dend;   }
    int   dlen  ( void ) const { return _dlen;   }
 
    // mutators
    void set_name     ( CString& v ) { _name      = v; }
    void set_is_int   ( short v    ) { _is_int    = v; }
    void set_is_local ( short v    ) { _is_local  = v; }
    void set_is_signed( short v    ) { _is_signed = v; }
    void set_no_override( void ) { _is_head_override = IS_FALSE; }
    void set_dstart( int v ) { _dstart = v; }
    void set_dend( int v ) { _dend = v; }
    void set_dlen( int v ) { _dlen = v; }
    void set_val( VeriNum *val );

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriParam() {};

  private:
    VeriVar* _enum_type=nullptr;
    String _name;

    short  _is_int;
    short  _is_local;
    short  _is_signed;

    short  _is_head_override;

    int    _dstart;
    int    _dend;
    int    _dlen;

    VeriNode  *_decl;
    VeriNum   *_val;
};

/*
 * class VeriInt :
 *     Verilog syntax analyzer true node : integer
 */
class VeriInt : public VeriNode
{
  typedef std::string       String;
  typedef const String      CString;
  typedef std::vector<int > IVec;
  typedef std::vector< VeriSymbolRangeRec > SymbolRanges;

  public:
    VeriInt( Uint idx, int line, int col, CString& name,
             VeriNode *decl, VeriNum **val, int total_cnt, VeriMod *mod )
      :  VeriNode( idx, vtINT, vtINT, line, col, mod )
      , _name(name)
      , _decl(decl)
      , _val(val)
      , _total_cnt(total_cnt)
    {}

    virtual ~VeriInt() { clear(); }

    // accessors
    CString& name  ( void ) const { return _name; }
 
    // depth starts from 1
    void  get_range( unsigned int depth, int& start, int& end, int& bits );
    int   range_depth( void ) const { return _range.size(); }
    bool dynamic_array() const {return _dynamic_array;}
    void set_dynamic_array(bool value) {_dynamic_array=value;}
    int container_kind(unsigned axis=0) const {return axis<_container_dimensions.size()?_container_dimensions[axis].first:axis?vrSINGLE:_container_kind;}
    int container_bound(unsigned axis=0) const {return !axis?_container_bound:axis<_container_bounds.size()?_container_bounds[axis]:-1;}
    void set_dimension_bound(unsigned axis,int bound) {if(_container_bounds.size()<=axis)_container_bounds.resize(axis+1,-1);_container_bounds[axis]=bound;if(!axis)_container_bound=bound;}
    VeriVar* associative_key_type(unsigned axis=0) const {return axis<_container_dimensions.size()?_container_dimensions[axis].second:axis?nullptr:_associative_key_type;}
    void set_dimension_container(unsigned axis,int kind,VeriVar* key=nullptr) {if(_container_dimensions.size()<=axis)_container_dimensions.resize(axis+1,{vrSINGLE,nullptr});_container_dimensions[axis]={kind,key};if(!axis){set_container(kind,_container_bound);set_associative_key_type(key);}}
    void set_associative_key_type(VeriVar* type) {_associative_key_type=type;}
    void set_container(int kind,int bound=-1) {_container_kind=kind;_container_bound=bound;_dynamic_array=kind>=vrOPEN;}


    VeriNum * get_one_num( const IVec& dimen, int is_whole, int dstart, int dend );

    // mutators
    void set_name (CString& v) { _name = v; }

    void add_range( int start, int end )
    {
      _range.push_back( SymbolRanges::value_type(
                              VeriSymbolRangeRec( start,
                                                  end,
                                                  abs(end - start) + 1 )
                                                )
                      );
    }

    int  set_one_num( const IVec& dimen, int is_whole, int dstart,
                      int dend, const VeriNum *val );

    virtual void clear( void );

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriInt() {};

    int calc_dimen_cnt( int start_lvl );
    int determin_idx( const IVec& dimen );

  private:
    String _name;

    SymbolRanges _range;
    std::vector<std::pair<int,VeriVar*>> _container_dimensions;
    std::vector<int> _container_bounds;
    int _container_kind=vrSINGLE,_container_bound=-1;
    VeriVar* _associative_key_type=nullptr; // Non-owning semantic binding, rebuilt per elaboration.
    bool _dynamic_array=false;

    VeriNode  *_decl;
    VeriNum  **_val;
    int        _total_cnt;
};

/*
 * class VeriGenVar :
 *     Verilog syntax analyzer true node : genvar
 */
class VeriGenVar : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;

  public:
    VeriGenVar( Uint idx, int line, int col, CString& name,
                VeriNode *decl, VeriNum *val, VeriMod *mod )
      :  VeriNode( idx, vtGENVAR, vtGENVAR, line, col, mod )
      , _name(name)
      , _decl(decl)
      , _val(val)
    {}

    virtual ~VeriGenVar() { clear(); }

    // accessors
    CString& name  ( void ) const { return _name;        }
    VeriNum *get_val ( void );

    // mutators
    void set_name( CString& v ) { _name = v; }
    void set_val( VeriNum *node );

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriGenVar() {};

  private:
    String _name;

    VeriNode  *_decl;
    VeriNum   *_val;
};

class VeriLabelId : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;

  public:
    VeriLabelId( Uint idx, int line, int col, CString& name,
               VeriNode *block, VeriMod *mod )
      :  VeriNode( idx, vtLABEL, vtLABEL, line, col, mod )
      , _name( name )
      , _label_block( block )
    {}

    virtual ~VeriLabelId() { clear(); }

    // accessors
    CString  & name ( void ) const { return _name;   }
    VeriNode * label( void ) { return _label_block;  }

    // mutators
    void set_name ( CString & v ) { _name = v; }
    void set_block( VeriNode *v ) { _label_block = v; }

    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    VeriLabelId() {};

  private:
    String    _name;
    VeriNode *_label_block;
};

};
#endif // PARSER_VERILOG_VERI_NODE_HPP_
