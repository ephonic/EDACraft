/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_mod_container.hpp
 * Summary  : verilog syntax analyzer :: module container
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */
#ifndef PARSER_VERILOG_VERI_MOD_CONTAINER_
#define PARSER_VERILOG_VERI_MOD_CONTAINER_

#include <cstdlib>
#include <string>
#include <list>
#include <map>
#include <vector>

namespace rtl
{

class VeriNode;
class VeriMod;
class VeriAstDrawer;
/*
 * class VeriModContainer :
 *     Verilog syntax-analyzer class deals with module check and other
 *   related operations.
 *
 *     Need to call int init() before processing.
 *     Has void clean_up() function to clean up inner data, back to status after
 *   init().
 */

class VeriModContainer
{
  typedef std::string               String;
  typedef const String              CString;
  typedef unsigned int              Uint;
  typedef std::list< VeriMod *>     ModList;
  typedef std::list< VeriNode *>    NodeList;
  typedef std::vector< VeriNode * > NodeVec;

  private:
    struct VeriModNode
    {
      VeriModNode( CString& name, VeriMod *data, VeriModNode *next )
        : _name( name )
        , _data( data )
        , _next( next )
      { }

      ~VeriModNode() {};

      String       _name;
      VeriMod     *_data;
      VeriModNode *_next;
    };

    struct ModDagNode
    {
      typedef std::map< String, ModDagNode * > ModDagMap;
      
      ModDagNode( CString& name, VeriMod *mod )
        : _name( name )
        , _mod( mod )
        , _used( IS_FALSE )
        , _into_this( 0 )
        , _acyclic( IS_FALSE )
      {}

      String      _name;
      VeriMod    *_mod;
      ModDagMap   _children;
      NodeList    _inst;

      int         _used;
      int         _into_this;
      int         _acyclic;
    };

    typedef std::map< String, ModDagNode * > ModDagMap;
    typedef std::map<int, ModDagMap >        MBucket;

    typedef std::vector< ModDagNode * >      ModDagVec;

  public:
    VeriModContainer( void )
      : _size(0)
      , _hash_list(NULL)
      , _top_module(NULL)
    {};

    ~VeriModContainer( void )
    {
      clear();
    };

    // for initialization, create space for hash container
    int init( Uint size );

    // data will be deleted in destruction function
    int insert( CString& name, VeriMod *data );

    // add module instantiation connection
    int add_mod_conn( VeriMod *mod, const NodeList& inst_node );

    int parse_modules( CString& top_module );

    // no memory change
    VeriMod* module( CString& name );

    int dump_all_modules( CString& dir, VeriAstDrawer *drawer );

    // return all modules for dfg-convertion, and only for this purpose
    const ModList& all_modules( void ) { return _modules; }

    // return names of modules that are instantiated but not defined
    std::vector<String> missing_modules( void );
    std::vector<String> root_modules( void ) const;

    // clean up inner data, back to status after init()
    void clean_up( void );

    // for debug usage, print out hash container load information to stdout
    void print( void );

  protected:
    bool hash_cmp33( CString& src, CString& des )
    { return (src == des); }

    Uint hash_key33( CString& name )
    {
      const char *p = name.c_str();
      Uint  nhash = 5381;
      while( (*p) != '\0' )
      {
        nhash += (nhash << 5) + *p;
        ++p;
      }
      return nhash;
    }

    int summarize_modules( void );

    int exclude_irrelevant( void );

    int check_cycle( void );

    int parse_modules( void );

    // delete data by your self, cannot be deleted in verilog parser processing
    int hash_delete ( CString& name );

    // clearn up everything, back to status after construction
    void clear( void );

    void clear_mod_graph( ModDagMap& map );

  protected: // for bucket
    void bucket_push( int idx, CString& key, ModDagNode *mod )
    {
      MBucket::iterator it = _mod_bucket.find( idx );
      if( it != _mod_bucket.end() )
        it->second.insert( ModDagMap::value_type(key,mod) );
      else
      {
        ModDagMap mod_map;
        mod_map.insert( ModDagMap::value_type(key,mod) );
        _mod_bucket.insert( MBucket::value_type( idx, mod_map ) );
      }
    }

    void bucket_erase( int idx, CString& key )
    {
      MBucket::iterator it = _mod_bucket.find( idx );
      if( it != _mod_bucket.end() )
        it->second.erase( key );
    }

    int bucket_exist( int idx )
    {
      MBucket::iterator it = _mod_bucket.find( idx );
      if( it != _mod_bucket.end() )
      {
        if( it->second.size() != 0 )
          return IS_TRUE;
      }
      return IS_FALSE;
    }

    ModDagNode * bucket_get_zero( )
    {
      MBucket::iterator it = _mod_bucket.find( 0 );
      if( it != _mod_bucket.end() )
      {
        if( it->second.size() != 0 )
          return it->second.begin()->second;
      }
      return NULL;
    }

    int bucket_exist( int idx, CString& key )
    {
      MBucket::iterator it = _mod_bucket.find( idx );
      if( it == _mod_bucket.end() )
        return IS_FALSE;

      ModDagMap::iterator is = it->second.find( key );
      if( is == it->second.end() )
        return IS_FALSE;

      return IS_TRUE;
    }

    int bucket_elem_num( )
    {
      MBucket::iterator imb = _mod_bucket.begin();
      int cnt = 0;
      for( ; imb != _mod_bucket.end(); ++imb )
        cnt += imb->second.size();
      return cnt;
    }

    String bucket_all_elem( )
    {
      MBucket::iterator imb = _mod_bucket.begin();
      ModDagMap::iterator iss;
      String ret = "";
      for( ; imb != _mod_bucket.end(); ++imb )
      {
        for( iss = imb->second.begin(); iss != imb->second.end(); ++iss )
          ret.append( iss->first + "  " );
      }
      return ret;
    }

  private:
    Uint          _size;
    VeriModNode **_hash_list;
    ModList       _modules;
    ModDagNode   *_top_module;

    ModDagMap     _mods_in_graph;
    ModDagMap     _mods_not_used;
    MBucket       _mod_bucket;
};

};

#endif // PARSER_VERILOG_VERI_MOD_CONTAINER_
