/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_node_pool.cpp
 * Summary  : node memory pool functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include "general_err.hpp"

#include "veri_node.hpp"
#include "veri_node_pool.hpp"

#include <cstring>

namespace rtl
{

int
VeriNodePool::init( Uint size, Uint hash_mod )
{
  _size     = size;
  _hash_mod = hash_mod;
  _cnt      = 0;
  _toss_top = 0;

  if( _nodes == NULL )
  {
    _nodes = new Node4Pool*[_size];
    memset( _nodes, 0x0, sizeof( Node4Pool * ) * _size );
  }

  if( _tosses == NULL )
  {
    _tosses = new Uint[_toss_max];
    memset( _tosses, 0x0, sizeof(Uint) * _toss_max );
  }
  return OK;
}

void
VeriNodePool::clear( void )
{
  Node4Pool *p = NULL;

  if( _nodes != NULL )
  {
    for( Uint i = 0; i < _size; ++i )
    {
      while( _nodes[i] != NULL )
      {
        p = _nodes[i];
        _nodes[i] = p->next;
        delete p->node;
        delete p;
      }
    }
    delete[] _nodes;
  }
  _nodes = NULL;

  if( _tosses != NULL )
    delete[] _tosses;
  _tosses = NULL;

  _cnt = 0;
  _toss_top = 0;
  _idx_recycle.clear();
}

void
VeriNodePool::clean_up( void )
{
  Node4Pool *p = NULL;

  if( _nodes != NULL )
  {
    for( Uint i = 0; i < _size; ++i )
    {
      while( _nodes[i] != NULL )
      {
        p = _nodes[i];
        _nodes[i] = p->next;
        delete p->node;
        delete p;
      }
    }
  }

  if( _tosses != NULL )
    memset( _tosses, 0x0, sizeof(Uint) * _toss_max );
  else
  {
    _tosses = new Uint[_toss_max];
    memset( _tosses, 0x0, sizeof(Uint) * _toss_max );
  }

  _cnt = 0;
  _toss_top = 0;
  _idx_recycle.clear();
}

unsigned int
VeriNodePool::next_id( void )
{
  if( !_idx_recycle.empty() )
  {
    int re = _idx_recycle.back( );
    _idx_recycle.pop_back( );
    return re;
  }
  else
    return ++_cnt;
}

int
VeriNodePool::insert( VeriNode *node )
{
  if( _nodes == NULL )
    return ERR;

  Uint i = node->idx() & _hash_mod;
  
  Node4Pool *p = new Node4Pool;
  p->node = node;
  p->next = _nodes[i];
  _nodes[i] = p;

  return OK;
}

VeriNode *
VeriNodePool::node( Uint idx )
{
  if( _nodes == NULL )
    return NULL;

  Uint i = idx & _hash_mod;

  Node4Pool *p = _nodes[i];

  while( p != NULL )
  {
    if( p->node->idx() == idx )
      return p->node;
    p = p->next;
  }
  return NULL;
}

int
VeriNodePool::toss_node( Uint idx )
{
  if( _toss_top >= _toss_max )
    clear_tosses( );

  _tosses[_toss_top++] = idx;
  return OK;
}

int
VeriNodePool::clear_tosses( void )
{
  if( _nodes == NULL )
    return ERR;

  Uint idx, hidx;
  Node4Pool *p = NULL;
  Node4Pool *q = NULL;

  for( unsigned int i = 0 ; i < _toss_top; ++i )
  {
    idx  = _tosses[i];
    hidx = idx & _hash_mod;

    if( _nodes[hidx] == NULL )
      continue;
    else if( _nodes[hidx] != NULL && _nodes[hidx]->node->idx() == idx )
    {
      p = _nodes[hidx]->next;
      delete _nodes[hidx]->node;
      delete _nodes[hidx];
      _nodes[hidx] = p;
      _idx_recycle.push_back( idx );
    }
    else
    {
      q = _nodes[hidx];
      p = _nodes[hidx]->next;
      while( p != NULL )
      {
        if( p->node->idx() == idx )
        {
          q->next = p->next;
          delete p->node;
          delete p;
          _idx_recycle.push_back( idx );
          break;
        }
        else
        {
          q = p;
          p = p->next;
        }
      }
    }
  }

  memset( _tosses, 0x0, sizeof(Uint) * _toss_max );
  _toss_top = 0;

  return OK;
}

};
