/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : singleton.hpp
 * Summary  : singleton third party template head
 *            written by Pavio Yang
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#ifndef _singleton_h_
#define _singleton_h_

#include <pthread.h>

#include <cstdlib>

namespace pavio_singleton
{

/*
 *  mutex class, mutex manipulation for singleton class
 */
class Mutex
{
  public:
    Mutex( void )
    {
      pthread_mutex_init( &m_lock, NULL );
    }

    ~Mutex( void )
    {
      pthread_mutex_destroy( &m_lock );
    }

    void lock( void )
    {
      pthread_mutex_lock( &m_lock );
    }

    void unlock( void )
    {
      pthread_mutex_unlock( &m_lock );
    }

  private:
    pthread_mutex_t m_lock;
};

/*
 * self-explanative
 */
template< class T >
class Singleton
{
  public:
    inline static T* get_instance( void );
    inline static void destroy( void );

  protected:
    // prevent other clients from creating and deleting
    Singleton<T>( void ) {};
   ~Singleton<T>( void ) {};
    Singleton<T>( const Singleton<T>& );
    Singleton<T>& operator=(const Singleton<T>& );

  private:
    static T* volatile _instance;  ///< the only instance
    static Mutex _mutex;           ///< self-explanative
};

template<class T>
T* Singleton<T>::get_instance( void )
{
  if( NULL == _instance )
  {
    _mutex.lock();

    // for thread safety
    if( NULL == _instance )
    {
      _instance = new T;
      atexit( destroy );
    }
    _mutex.unlock();
  }
  return _instance;
}

template<class T>
void Singleton<T>::destroy( void )
{
  if( _instance != NULL )
  {
    delete _instance;
    _instance = NULL;
  }
}

template<class T>
T* volatile Singleton<T>::_instance = 0;

template<class T>
Mutex Singleton<T>::_mutex;

};

#endif
