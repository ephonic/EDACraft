/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_node_pool.hpp
 * Summary  : node memory pool
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_NODE_POOL_HPP_
#define PARSER_VERILOG_VERI_NODE_POOL_HPP_


#include <vector>

namespace rtl
{

class VeriNode;

/*
 *    Every VeriNode derived class object will be registered in
 *  this pool immediately after spawn
 *  
 */
class VeriNodePool
{
  typedef unsigned int        Uint;
  typedef std::vector<Uint>   UVec;

  public:
    struct Node4Pool
    {
      VeriNode  *node;
      Node4Pool *next;
    };

  public:
    VeriNodePool( )
      : _toss_max( 1023 )
      , _size( 0 )
      , _hash_mod( 0 )
      , _cnt( 0 )
      , _nodes( NULL )
      , _tosses( NULL )
      , _toss_top( 0 )
    {}

    ~VeriNodePool( void ) { clear(); }

    int init( Uint size, Uint hash_mod );

    Uint next_id( void );

    int insert( VeriNode *node );

    VeriNode *node( Uint idx );

    int toss_node( Uint idx );
  
    void clear( void );
    void clean_up( void );

  protected:
    int clear_tosses( void );

  private:
    const Uint _toss_max;

  private:
    Uint        _size;
    Uint        _hash_mod;
    Uint        _cnt;
    Node4Pool **_nodes;

    UVec        _idx_recycle;
    Uint       *_tosses;
    Uint        _toss_top;
};

};
#endif // PARSER_VERILOG_VERI_NODE_POOL_HPP_
