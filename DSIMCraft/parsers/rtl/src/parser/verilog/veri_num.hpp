/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_num.hpp
 * Summary  : verilog syntax number analyzer class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PARSER_VERILOG_VERI_NUM_HPP_
#define PARSER_VERILOG_VERI_NUM_HPP_

#include <string>
#include <vector>
#include <stdint.h>

#include "general_err.hpp"
#include "veri_node.hpp"

namespace rtl
{

/*
 * class VeriNum :
 *     verilog parser number analyzer.
 *
 *     Call parse() function to parse.
 *     Call clean_up() function to clean up inner data, back to status after
 *   init().
 */
 
class VeriNum : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;

  public:
    VeriNum( Uint idx, int line, int col, VeriMod *mod )
      :  VeriNode( idx, vtNUM, vtNUM, line, col, mod )
      , _radix( vDEC )
      , _bits( 0 )
      , _val_x(NULL)
      , _vbits( 0 )
      , _val(NULL)
      , _no_xz(IS_TRUE)
      , _is_signed(IS_FALSE)
    {}

    VeriNum( Uint idx, const VeriNum *num );
    
    virtual ~VeriNum( void )
    {
      if( _val_x != NULL )
        delete[] _val_x;
      _val_x = NULL;

      if( _val != NULL )
        delete[] _val;
      _val = NULL;
    }
    
    // parser
    int parse( const char* in, int len );

    // accessor   
    int  radix   ( void ) const { return _radix;    }
    int  bits    ( void ) const { return _bits;     }  
    int  no_xz   ( void ) const { return _no_xz;    }
    int  is_signed  ( void ) const { return _is_signed;   }
    int real_width() const {return _real_width;}
    double real_value() const;
    void set_real(double value,int width=64);
    void real_to_integral(int width,bool truncate=false);
    bool string_type() const {return _string_type;}
    std::string string_value() const;
    void to_string_value();

    const uint8_t* val_x( void ) const { return _val_x;  }
    const uint32_t * val( void ) const { return _val;    }

    // mutators
    void set_signed( void ) { _is_signed = IS_TRUE; }
    void set_unsigned( void ) { _is_signed = IS_FALSE; }

    void init_val( int is_signed, int bits );
    void to_two_state( void );

    ///< return whether the val is 1 bit or not, used for true and false value
    int  is_one_bit( void ) ;
    uint32_t one_bit_value( void );
    int  is_zero( void );

    int get_first_int( void );
    int get_certain_bit( int bit );

    // change value into other[start:end]
    int replace_value( int is_whole, int shift, int start,
                       int end, const VeriNum *other );

    // change value[start:end] into other
    int refresh_value( int is_whole, int shift, int start,
                       int end, const VeriNum *other );

    int unary_operation( int op );
    int binary_operation( int op, const VeriNum *other );
    int truncate_assign( int new_bits );
    int upward_case_eq( const VeriNum *other );
    
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
    int _real_width=0;
    bool _string_type=false;
    int lower( char *str );
    int cpy_string_with_extra_char( const char* in, char *out, int start, int len );
    int determin_bits( const char *in, int len );

    int bin_atoi( const char *str );
    int hex_atoi( const char *str );
    int oct_atoi( const char *str );
    int dec_atoi( const char *str );

    int determin_boh_head( char first_char, uint8_t *rem );
    int append_boh_no_xz( int c, const uint8_t *rem );
    int append_boh_with_xz( int c, const uint8_t *rem );
    int turn_into_xz_mode( void );
    int align_bits( void );
    int high_end_padding( int bits );

    String string_result( void ) const;
    String string_radix( void ) const;
    String string_sign( void ) const;
    String string_valx( void ) const;
    String string_val( void ) const;

    uint8_t bit_and( uint8_t a, uint8_t b );
    uint8_t bit_or( uint8_t a, uint8_t b );
    uint8_t bit_xor( uint8_t a, uint8_t b );
    uint8_t bit_xnor( uint8_t a, uint8_t b );
    uint8_t bit_neg( uint8_t a );
    uint8_t bit_add( uint8_t a, uint8_t b, uint8_t c_in, uint8_t& sum ); // return c_out

    int reduce_value( bool conjunction, bool invert );
    int divide_modulo( const VeriNum *other, bool modulo );
    int shift_value( const VeriNum *other, bool left, bool arithmetic );
    int assign_bit_value( const std::vector<uint8_t>& bits, bool sign );
    int increment( void );
    int decrement( void );
    int lrs_one_round( int bits );
    int lls_one_round( int bits );
    int ars_one_round( int bits );

    int uadd ( void );   // +
    int usub ( void );   // -
    int uneg ( void );   // ~
    int uand ( void );   // &
    int uor  ( void );   // |
    int unand( void );   // ~&
    int unor ( void );   // ~|
    int uxnor( void );   // ~^
    int unot ( void );   // !
    int uxor ( void );   // ^

    int align_signed_bits( VeriNum *other );

    int bnand ( VeriNum *other );   // ~&
    int bnor  ( VeriNum *other );   // ~|
    int bxnor ( VeriNum *other );   // ~^
    int bsand ( VeriNum *other );   // &
    int bsxor ( VeriNum *other );   // ^
    int bsor  ( VeriNum *other );   // |
    int bdand ( VeriNum *other );   // &&
    int bdor  ( VeriNum *other );   // ||

    int bpow  ( VeriNum *other );   // **
    int bmod  ( VeriNum *other );   // %
    int bmul  ( VeriNum *other );   // *
    int bdiv  ( VeriNum *other );   // /
    int badd  ( VeriNum *other );   // +
    int bsub  ( VeriNum *other, uint8_t& carry );   // -
    int blrs  ( VeriNum *other );   // >>
    int blls  ( VeriNum *other );   // <<
    int bars  ( VeriNum *other );   // >>>
    int bals  ( VeriNum *other );   // <<<
    int brel( VeriNum *other, int op );
    int bleq  ( VeriNum *other );   // ==
    int blieq ( VeriNum *other );   // !=
    int bceq  ( VeriNum *other );   // ===
    int bcieq ( VeriNum *other );   // !==

  private:
    enum veri_num_status
    {
      vnSTART        = 0,
      vnUNSIGNED     = 1,
      vnDEFAULT      = 2,
     
      vnSIGN_PROCESS = 3,
      vnSIGN         = 4,
     
      vnBASE         = 5,
      vnDEC_0        = 6,
      vnDEC_1        = 7,
      vnBOH_0        = 8,
      vnBOH_1        = 9,
//      vnPROCESS      = 12,
    };

    static const int INT_BIN_RATIO;
    static const int INT_HEX_RATIO;
    static const int INT_OCT_RATIO;
    static const int INT_DEC_RATIO;
                 
    static const int INT_BIN_BIT;
    static const int INT_OCT_BIT;
    static const int INT_DEC_BIT;
    static const int INT_HEX_BIT;
                 
    static const int MAX_BITS_BIT ;
    static const int DEFAULT_BITS;
    static const int MAX_POWEE;
    
  private:
    int       _radix;      ///< self-explanative

    int       _bits;       ///< length for val_x
    uint8_t  *_val_x;      ///< _val[_bits] , for x,z included number, value

    int       _vbits;      ///< length for val
    uint32_t *_val;        ///< for known numbers
    int       _no_xz;      ///< no x or z
    int       _is_signed;  ///< is two's complete or not
};

};

#endif // PARSER_VERILOG_VERI_NUM_HPP_
