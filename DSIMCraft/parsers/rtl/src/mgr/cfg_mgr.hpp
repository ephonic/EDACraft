/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : cfg_mgr.hpp
 * Summary  : class Cfg_mgr will hold verilog synthesis configurations
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef MGR_CFG_MGR_HPP_
#define MGR_CFG_MGR_HPP_

#include "singleton.hpp"

#include <string>

#include "general_err.hpp"

namespace rtl
{

  using pavio_singleton::Singleton;

/* 
 * class Cfg_mgr :
 *       configuration manager, holds every verilog synthesis
 *     configurations. Mainly set by tcl-scripts for synthesis,
 *     or verilog HDL source file itself.
 *
 *       Has void clean_up( void ) function to clear inner data, back to status
 *     after initialization of init() if has.
 *
 *   contents :
 *       verilog_unconnected_drive : pull0 | pull1
 *       verilog_nonconnected_drive : pull0 | pull1
 *       default_nettype : tr0, wire, tran ...
 *
 */
class Cfg_mgr : public Singleton<Cfg_mgr>
{
  friend class Singleton<Cfg_mgr>;
  
  public:
    Cfg_mgr( void )
      : _module_container_size( 524287 )
      , _symbol_table_size( 524287 )
      , _node_pool_size( 0x1 << 17 )
      , _node_pool_hash_mod( 0x1ffff )
    {};

    ~Cfg_mgr( void ) {};

    // self-explanative mutators
    void set_veri_unconn ( int t ) { _veri_unconn  = t ; }
    void set_veri_nonconn( int t ) { _veri_nonconn = t ; }
    void set_veri_default_nettype( int t ) { _default_nettype = t ; }
    
    // self-explanative accessors
    int veri_unconn ( void ) const { return _veri_unconn ; }
    int veri_nonconn( void ) const { return _veri_nonconn; }
    int veri_default_nettype( void ) const { return _default_nettype; }

    int module_container_size( void ) const { return _module_container_size; }
    int symbol_table_size( void ) const { return _symbol_table_size; }
    int node_pool_size( void ) const { return _node_pool_size; }
    int node_pool_hash_mod( void ) const { return _node_pool_hash_mod; }
    
    // clear inner data, back to status after initialization.
    void clean_up( void ) { clear(); };

  protected:

    // clear everything, back to status after construction.
    void clear( void );

  private:
    // general part
    int _module_container_size;
    int _symbol_table_size;
    int _node_pool_size;
    int _node_pool_hash_mod;

    // verilog part
    int _veri_unconn;
    int _veri_nonconn;
    int _default_nettype;
};

};
#endif // MGR_CFG_MGR_HPP_
