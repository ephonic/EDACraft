/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_num.cpp
 * Summary  : verilog syntax number analyzer
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include <iostream> 
#include <cstring>
#include <cmath>
#include <algorithm>

#include "veri_err_token.hpp"
#include "verilog_token.hpp"

#include "veri_num.hpp"
#include "veri_symbol_table.hpp"

#include "veri_parser.hpp"

/*
 * in comparison :
 *    a - b == a + ~b + 1;
 * 
 * if( a < b ), a - b has no carry, and result is non-zero
 * if( a = b ), a - b has    carry, and result is     zero
 * if( a > b ), a - b has    carry, and result is non-zero
 */

namespace rtl
{

const int VeriNum::INT_BIN_RATIO = 32;
const int VeriNum::INT_OCT_RATIO = 10;
const int VeriNum::INT_DEC_RATIO = 8;
const int VeriNum::INT_HEX_RATIO = 8;

const int VeriNum::INT_BIN_BIT   = 1;
const int VeriNum::INT_OCT_BIT   = 3;
const int VeriNum::INT_DEC_BIT   = 4;
const int VeriNum::INT_HEX_BIT   = 4;

const int VeriNum::MAX_BITS_BIT  = 9;
const int VeriNum::DEFAULT_BITS  = 32;
const int VeriNum::MAX_POWEE     = 0xffff;

double VeriNum::real_value() const {
  if(_real_width) {
    if(_real_width==32){float value;uint32_t bits=_val[0];std::memcpy(&value,&bits,4);return value;}
    double value;uint64_t bits=uint64_t(_val[0])|(uint64_t(_val[1])<<32);std::memcpy(&value,&bits,8);return value;
  }
  const bool negative=_is_signed==IS_TRUE&&_bits&&const_cast<VeriNum*>(this)->get_certain_bit(_bits-1)==V1;
  double value=negative?-1:0;
  for(int i=_bits-int(negative);i-->0;)value=value*2+(const_cast<VeriNum*>(this)->get_certain_bit(i)==V1);
  return value;
}
void VeriNum::set_real(double value,int width) {
  init_val(IS_TRUE,width);_real_width=width;
  if(width==32){float rounded=float(value);std::memcpy(_val,&rounded,4);}
  else {uint64_t bits;std::memcpy(&bits,&value,8);_val[0]=uint32_t(bits);_val[1]=uint32_t(bits>>32);}
}
void VeriNum::real_to_integral(int width,bool truncate) {
  const double value=truncate?std::trunc(real_value()):std::round(real_value());
  init_val(IS_TRUE,width);
  if(!std::isfinite(value)){turn_into_xz_mode();for(int i=0;i<width;++i)_val_x[i]=VX;return;}
  double remaining=std::fabs(value);
  for(int bit=0;bit<width&&remaining>=1;++bit){if(std::fmod(remaining,2)>=1)_val[bit/32]|=uint32_t(1)<<(bit%32);remaining=std::floor(remaining/2);}
  if(value<0){uint64_t carry=1;for(int i=0;i<_vbits;++i){uint64_t next=uint64_t(~_val[i])+carry;_val[i]=uint32_t(next);carry=next>>32;}if(width%32)_val[_vbits-1]&=(uint32_t(1)<<(width%32))-1;}
}
std::string VeriNum::string_value() const {
  if(_real_width)throw std::runtime_error("real cannot be converted to string");
  std::string text;
  for(int byte=(_bits+7)/8;byte-->0;) {
    unsigned value=0;
    for(int bit=0;bit<8;++bit)if(byte*8+bit<_bits&&const_cast<VeriNum*>(this)->get_certain_bit(byte*8+bit)==V1)value|=1u<<bit;
    if(value)text+=char(value);
  }
  return text;
}
void VeriNum::to_string_value() {
  const auto text=string_value();std::string bits;
  for(unsigned char byte:text)for(int bit=8;bit-->0;)bits+=((byte>>bit)&1)?'1':'0';
  if(bits.empty())bits="00000000";
  const auto spelling=std::to_string(bits.size())+"'b"+bits;
  if(parse(spelling.c_str(),spelling.size())!=OK)throw std::runtime_error("invalid constant string conversion");
  _string_type=true;
}
 
VeriNum::VeriNum( Uint idx, const VeriNum *num )
  :  VeriNode( idx, vtNUM, vtNUM, 0, 0, NULL )
  , _radix( vDEC )
  , _bits( 0 )
  , _vbits( 0 )
  , _no_xz( IS_TRUE )
  , _is_signed( IS_FALSE )
  , _val_x( NULL )
  , _val( NULL )
{
  if( num == NULL )
    return;

  _radix     = num->_radix;
  _bits      = num->_bits;
  _vbits     = num->_vbits;
  _no_xz     = num->_no_xz;
  _is_signed = num->_is_signed;
  _real_width = num->_real_width;
  _string_type = num->_string_type;

  if( num->_val_x != NULL )
  {
    _val_x = new uint8_t[_bits];
    memcpy( _val_x, num->_val_x, sizeof(uint8_t) * _bits );
  }

  if( num->_val != NULL )
  {
    _val = new uint32_t[_vbits];
    memcpy( _val, num->_val, sizeof(uint32_t) * _vbits );
  }
}

/*
 * change value[start:end] into other
 */
int
VeriNum::refresh_value( int is_whole, int shift,
                        int start, int end, const VeriNum *val )
{
  if( is_whole == IS_TRUE )
  {
    if( val->_bits != _bits )
      return vNUM_ASSIGN_OVERLOAD;
    else
    {
      if( _val != NULL )
      {
        memcpy( _val, val->_val, sizeof( uint32_t ) * _vbits );
        return OK;
      }

      else if( _val_x != NULL )
      {
        memcpy( _val_x, val->_val_x, sizeof( uint8_t ) * _bits );
        return OK;
      }
      return OK;
    }
  }
  else
  {
    if( (abs(end-start) + 1) != val->_bits )
      return vNUM_ASSIGN_OVERLOAD;
    else
    {
      if( _val != NULL )
      {
        /* TODO */
        memcpy( _val, val->_val, _vbits * sizeof(uint32_t) );
        return OK;
      }
      else if( _val_x != NULL )
      {
        int idx = start - shift;
        memcpy( &(_val_x[idx]), val->_val_x, (abs(end-start)+1) * sizeof(uint8_t) );
        return OK;
      }
      return OK;
    }
  }
}

/*
 * change value into other[start:end]
 */
int
VeriNum::replace_value( int is_whole, int shift, int start, int end,
                        const VeriNum *other )
{
  _radix = other->_radix;
  _no_xz = other->_no_xz;
  _is_signed = other->_is_signed;

  if( is_whole == IS_TRUE )
  {
    _bits  = other->_bits;
    _vbits = other->_vbits;
  }
  else
  {
    _bits = abs(end-start) + 1;
    _vbits = _bits / INT_BIN_RATIO + (_bits % INT_BIN_RATIO ? 1 : 0 );

    start = start - shift;
    end   = end   - shift;
  }

  delete[] _val_x;
  delete[] _val;

  _val_x = NULL;
  _val = NULL;

  if( other->_val_x != NULL )
  {
    _val_x = new uint8_t[_bits];

    if( is_whole == IS_TRUE )
    {
      memcpy( _val_x, other->_val_x, sizeof(uint8_t) * _bits );
      return OK;
    }
    else
      memset( _val_x, 0, sizeof(uint8_t) * _bits );

    for( int i = start; i < end; ++i )
      _val_x[i] = other->_val_x[i];
    return OK;
  }
  else
    _val_x = NULL;

  if( other->_val != NULL )
  {
    _val = new uint32_t[_vbits];

    if( is_whole == IS_TRUE )
    {
      memcpy( _val, other->_val, sizeof(uint32_t) * _vbits );
      return OK;
    }
    else
      memset( _val, 0, sizeof(uint32_t) * _vbits );

    int last_pac   = end   % INT_BIN_RATIO;
    int first_pac  = start % INT_BIN_RATIO;
    int last_vbit  = end   / INT_BIN_RATIO;
    int first_vbit = start / INT_BIN_RATIO;

    for( int i = first_pac; i < INT_BIN_RATIO; ++i )
    {
      _val[first_vbit] =      _val[first_vbit]
                         | (( other->_val[first_vbit] & (0x1 << i) ) >> i);
    }

    for( int i = first_vbit; i < last_vbit; ++i )
    {
      for( int j = 0; j < INT_BIN_RATIO; ++j )
        _val[i] = _val[i] | ((other->_val[i] & (0x1 << j)) >> j);
    }

    for( int i = 0; i < last_pac; ++i )
    {
      _val[last_vbit] =      _val[last_vbit]
                         | (( other->_val[last_vbit] & (0x1 << i) ) >> i);
    }
  }
  else
    _val = NULL;
  return OK;
}

int
VeriNum::lower( char *str )
{
  for( unsigned int i = 0; i < strlen(str); ++i )
  {
    if( str[i] >= 'A' && str[i] <= 'Z' )
      str[i] = str[i] - 'A' + 'a';
    if( str[i] == '?' )
      str[i] = 'z';
  }
  return OK;
}

int
VeriNum::cpy_string_with_extra_char( const char *in, char *out,
                                     int start, int end )
{
  if( (end - start) == 0 )
    return vNFORMAT;

  for( int i = start; i < end; ++i )
  {
    if( in[i] != '_' )
    {
      (*out) = in[i];
      ++out;
    }
  }
  return OK;
}

int
VeriNum::determin_bits( const char *in, int len )
{
  if( len > MAX_BITS_BIT  )
    return -1;
  else
    return atoi(in);
}

void
VeriNum::init_val( int is_signed, int bits )
{
  _real_width=0;
  _string_type=false;
  _is_signed = is_signed;
  _bits      = bits;
  int last_pac = _bits % INT_BIN_RATIO;
  _vbits     = _bits / INT_BIN_RATIO + (last_pac == 0 ? 0 : 1 );
  _no_xz     = IS_TRUE;

  delete[] _val_x;
  delete[] _val;
  _val = new uint32_t[_vbits];
  _val_x = NULL;

  memset( _val, 0x0, sizeof( uint32_t ) * _vbits );
}

int
VeriNum::parse( const char* in, int len )
{ 
  std::string spelling(in,size_t(len));
  if(spelling.find('\'')==std::string::npos&&spelling.find_first_of(".eE")!=std::string::npos) {
    spelling.erase(std::remove(spelling.begin(),spelling.end(),'_'),spelling.end());
    size_t consumed=0;double value=std::stod(spelling,&consumed);
    if(consumed!=spelling.size())throw std::runtime_error("invalid real literal");
    set_real(value);return OK;
  }
  int  status = vnSTART;       ///< self-explanative
  int  cpos, ppos;
  int  re = OK;                ///< return value

  clear( );

  char *str = new char[ len + 1 ];      ///< parsing string
  memset( str, 0, len + 1 );
  strncpy( str, in, len );
  lower(str);

  char *process = new char[ len + 1 ];  ///< process pool for string
  memset( process, 0x0, len + 1 );

  do
  {
    for( cpos = 0, ppos = 0; cpos <= len ; ++cpos )
    {
      switch( status )
      {
        case vnSTART:
          switch( str[cpos] )
          {
            case '\'' :
              status = vnSIGN_PROCESS;
              _bits  = DEFAULT_BITS;
              ++ppos;
              break;

            case '0'  :
              status  = vnUNSIGNED;
              _bits   = DEFAULT_BITS;
              _radix  = vDEC;
              _is_signed = IS_TRUE; // Unsized decimal zero is a signed integer.
              ++ppos;
              break;

            case '1' : case '2' : case '3' : case '4' : case '5' :
            case '6' : case '7' : case '8' : case '9' :
              status = vnDEFAULT;
              break;
        
            default :
              re = vNINVAL_CHAR;
              break;
          }
          break;

        case vnUNSIGNED :
          switch( str[cpos] )
          {
            case '0' : case '1' : case '2' : case '3' : case '4' : 
            case '5' : case '6' : case '7' : case '8' : case '9' : case '_' :
              break;
        
            case '\0':
              if( cpos == 1 )
                --ppos;
              re = cpy_string_with_extra_char( str, process, ppos, cpos );
              break;
        
            default: 
              re = vNINVAL_CHAR;
              break;
          }
          break;

        case vnDEFAULT :
          switch( str[cpos] )
          {
            case '0' : case '1' : case '2' : case '3' : case '4' : 
            case '5' : case '6' : case '7' : case '8' : case '9' : case '_' :
              break;

            case '\0' :
              re = cpy_string_with_extra_char( str, process, ppos, cpos );
              _bits   = DEFAULT_BITS;
              _radix  = vDEC;
              _is_signed = IS_TRUE;
              break;

            case '\'' :
              re = cpy_string_with_extra_char( str, process, ppos, cpos );
              status = vnSIGN_PROCESS;
              break;

            default :  
              re = vNINVAL_CHAR;
              break;
          }  
          break;
 
        case vnSIGN_PROCESS :
          if( _bits == 0 )
          {
            _bits = determin_bits( process, strlen(process) );
            memset( process, 0x0, len );
          }

          if( _bits == -1 )
          {
            re = vNBITS_TOO_LARGE;
            _bits = 0;
            break;
          }
          status = vnSIGN;
          --cpos;
          break;

        case vnSIGN :
          switch( str[cpos] )
          {
            case 's' : 
              if( _is_signed == IS_FALSE )
                _is_signed = IS_TRUE;
              else
                re = vNDOUBLE_TWOS_COMP;
              break;
        
            case 'd' : status = vnDEC_0; _radix = vDEC; ppos = cpos + 1; break;
            case 'b' : status = vnBOH_0; _radix = vBIN; ppos = cpos + 1; break;
            case 'h' : status = vnBOH_0; _radix = vHEX; ppos = cpos + 1; break;
            case 'o' : status = vnBOH_0; _radix = vOCT; ppos = cpos + 1; break;
        
            default: 
              re = vNINVAL_CHAR;
              break;
          }   
          break;

        case vnDEC_0 :
          switch( str[cpos] )
          {
            case ' ' : case '\t' : case '\b' : case '\r' : case '\f' :
              ++ppos;
              break;

            default:
              --cpos;
              status = vnDEC_1;
              break;
          }
          break;

        case vnDEC_1:
          switch( str[cpos] )
          {
            case '0' : case '1' : case '2' : case '3' : case '4' : case '5' :
            case '6' : case '7' : case '8' : case '9' : case '_' :
              if( _no_xz == IS_FALSE )
                re = vNDEC_X_Z;
              break;
         
            case 'x' : case 'z' :
              if( _no_xz == IS_TRUE )
                _no_xz = IS_FALSE;
              else
                re = vNDEC_X_Z;
              break;

            case '\0' :
              re = cpy_string_with_extra_char( str, process, ppos, cpos );
              break;
            
            default: 
              re = vNINVAL_CHAR;
              break;
          }
          break;

        case vnBOH_0 :
          switch( str[cpos] )
          {
            case ' ' : case '\t' : case '\b' : case '\r' : case '\f' :
              ++ppos;
              break;

            default:
              --cpos;
              status = vnBOH_1;
              break;
          }
          break;

        case vnBOH_1 :
          switch( str[cpos] )
          {
            case '0' : case '1' : case '_' :
              break;

            case 'x' : case 'z' :
              _no_xz = IS_FALSE;
              break;

            case '2' : case '3' : case '4' : case '5' : case '6' : case '7' :
              if( _radix == vBIN )
                return vNINVAL_CHAR;
              break;

            case '8' : case '9' : case 'a' : case 'b' : case 'c' :
            case 'd' : case 'e' : case 'f' :
              if( _radix != vHEX )
                return vNINVAL_CHAR;
              break;

            case '\0' :
              re = cpy_string_with_extra_char( str, process, ppos, cpos );
              break;

            default: 
              re = vNINVAL_CHAR; break;
          }
          break;
           
        default:
          re = vNUNKNOWN;
          break;
      }

      if( re != OK )
        break;
    }
  }while(0);

  // process
  if( re == OK )
  {
    switch( _radix )
    {
      case vBIN : re = bin_atoi( process ); break;
      case vOCT : re = oct_atoi( process ); break;
      case vDEC : re = dec_atoi( process ); break;
      case vHEX : re = hex_atoi( process ); break;

      default :
        break;  
    }
  }

  if( str != NULL )
    delete[] str;
  if( process != NULL )
    delete[] process;

  return re;
}

int
VeriNum::determin_boh_head( char first_char, uint8_t *rem )
{
  int c = 0;
  switch( first_char )
  {
    case '0' :                                        rem[0] = V0; c = 1; break;
    case '1' :                                        rem[0] = V1; c = 1; break;
    case '2' :                           rem[0] = V1; rem[1] = V0; c = 2; break;
    case '3' :                           rem[0] = V1; rem[1] = V1; c = 2; break;
    case '4' :              rem[0] = V1; rem[1] = V0; rem[2] = V0; c = 3; break;
    case '5' :              rem[0] = V1; rem[1] = V0; rem[2] = V1; c = 3; break;
    case '6' :              rem[0] = V1; rem[1] = V1; rem[2] = V0; c = 3; break;
    case '7' :              rem[0] = V1; rem[1] = V1; rem[2] = V1; c = 3; break;
    case '8' : rem[0] = V1; rem[1] = V0; rem[2] = V0; rem[3] = V0; c = 4; break;
    case '9' : rem[0] = V1; rem[1] = V0; rem[2] = V0; rem[3] = V1; c = 4; break;
    case 'a' : rem[0] = V1; rem[1] = V0; rem[2] = V1; rem[3] = V0; c = 4; break;
    case 'b' : rem[0] = V1; rem[1] = V0; rem[2] = V1; rem[3] = V1; c = 4; break;
    case 'c' : rem[0] = V1; rem[1] = V1; rem[2] = V0; rem[3] = V0; c = 4; break;
    case 'd' : rem[0] = V1; rem[1] = V1; rem[2] = V0; rem[3] = V1; c = 4; break;
    case 'e' : rem[0] = V1; rem[1] = V1; rem[2] = V1; rem[3] = V0; c = 4; break;
    case 'f' : rem[0] = V1; rem[1] = V1; rem[2] = V1; rem[3] = V1; c = 4; break;

    case 'x' :                                        rem[0] = VX; c = 1; break;
    case 'z' :                                        rem[0] = VZ; c = 1; break;
     
    default:
      break;
  }
  return c;
}

int
VeriNum::append_boh_no_xz( int c, const uint8_t *rem )
{
  // Storage covers the declared width, including implicit zero padding.
  // Unary complement/negation must visit those high words too.
  int last_pac = _bits % INT_BIN_RATIO;
  _vbits = _bits / INT_BIN_RATIO + (last_pac != 0 ? 1 : 0);
  _val = new uint32_t[ _vbits ];
  memset( _val, 0, sizeof(uint32_t)*_vbits );

  uint8_t res;
  int idx, bcnt, wcnt;
  for( bcnt = 0, wcnt = c-1; bcnt < _vbits; ++bcnt )
  {
    for( idx = 0; idx < INT_BIN_RATIO; ++idx, --wcnt )
    {
      res = wcnt < 0 ? 0 : rem[wcnt];
      _val[bcnt] = _val[bcnt] | ( res << idx ) ;
    }
  }
  return OK;
}

int
VeriNum::append_boh_with_xz( int c, const uint8_t *rem )
{
  _val_x = new uint8_t[_bits];
  memset( _val_x, 0, sizeof(uint8_t)*_bits );

  uint8_t res;
  uint8_t high_end;
  if( rem[0] == VX )
    high_end = VX;
  else if( rem[0] == VZ )
    high_end = VZ;
  else
    high_end = V0;

  for( int s = 0, i = 0; i < _bits; ++i )
  {
    s = c - i - 1;
    if( s < 0 )
      res = high_end;
    else
      res = rem[s];
    _val_x[i] = res;
  }
  return OK;
}

int
VeriNum::hex_atoi( const char *in )
{
  int len = strlen(in);
  int rem_len = len * INT_HEX_BIT + 1;
  uint8_t *rem = new uint8_t[rem_len];
  memset( rem, 0, rem_len );

  int c = determin_boh_head( in[0], rem );
  int k = (c != 0 ? 1 : 0);
  in = &(in[k]);
  len -= k;

  for( int i = 0; i < len; ++i )
  {
    switch( in[i] )
    {
      case '0' : rem[c] = V0; rem[1+c] = V0; rem[2+c] = V0; rem[3+c] = V0; c += 4; break;
      case '1' : rem[c] = V0; rem[1+c] = V0; rem[2+c] = V0; rem[3+c] = V1; c += 4; break;
      case '2' : rem[c] = V0; rem[1+c] = V0; rem[2+c] = V1; rem[3+c] = V0; c += 4; break;
      case '3' : rem[c] = V0; rem[1+c] = V0; rem[2+c] = V1; rem[3+c] = V1; c += 4; break;
      case '4' : rem[c] = V0; rem[1+c] = V1; rem[2+c] = V0; rem[3+c] = V0; c += 4; break;
      case '5' : rem[c] = V0; rem[1+c] = V1; rem[2+c] = V0; rem[3+c] = V1; c += 4; break;
      case '6' : rem[c] = V0; rem[1+c] = V1; rem[2+c] = V1; rem[3+c] = V0; c += 4; break;
      case '7' : rem[c] = V0; rem[1+c] = V1; rem[2+c] = V1; rem[3+c] = V1; c += 4; break;
      case '8' : rem[c] = V1; rem[1+c] = V0; rem[2+c] = V0; rem[3+c] = V0; c += 4; break;
      case '9' : rem[c] = V1; rem[1+c] = V0; rem[2+c] = V0; rem[3+c] = V1; c += 4; break;
      case 'a' : rem[c] = V1; rem[1+c] = V0; rem[2+c] = V1; rem[3+c] = V0; c += 4; break;
      case 'b' : rem[c] = V1; rem[1+c] = V0; rem[2+c] = V1; rem[3+c] = V1; c += 4; break;
      case 'c' : rem[c] = V1; rem[1+c] = V1; rem[2+c] = V0; rem[3+c] = V0; c += 4; break;
      case 'd' : rem[c] = V1; rem[1+c] = V1; rem[2+c] = V0; rem[3+c] = V1; c += 4; break;
      case 'e' : rem[c] = V1; rem[1+c] = V1; rem[2+c] = V1; rem[3+c] = V0; c += 4; break;
      case 'f' : rem[c] = V1; rem[1+c] = V1; rem[2+c] = V1; rem[3+c] = V1; c += 4; break;
   
      case 'x' : rem[c] = VX; rem[1+c] = VX; rem[2+c] = VX; rem[3+c] = VX; c += 4; break;
      case 'z' : rem[c] = VZ; rem[1+c] = VZ; rem[2+c] = VZ; rem[3+c] = VZ; c += 4; break;
       
      default:
        break;
    }
  }

  // Sized literals retain the low bits even when the textual digits are wider.

  if( _no_xz == IS_FALSE )
  {
    append_boh_with_xz( c, rem );
    delete[] rem;
  }
  else
  {
    append_boh_no_xz( c, rem );
    delete[] rem;
  }
  return OK;
}

int
VeriNum::oct_atoi( const char *in )
{
  int len = strlen(in);
  int rem_len = len * INT_OCT_BIT + 1;
  uint8_t *rem = new uint8_t[rem_len];
  memset( rem, 0, rem_len );

  int c = determin_boh_head( in[0], rem );
  int k = (c != 0 ? 1 : 0);
  in = &(in[k]);
  len -= k;

  for( int i = 0; i < len; ++i )
  {
    switch( in[i] )
    {
      case '0' : rem[c] = V0; rem[1+c] = V0; rem[2+c] = V0; c += 3; break;
      case '1' : rem[c] = V0; rem[1+c] = V0; rem[2+c] = V1; c += 3; break;
      case '2' : rem[c] = V0; rem[1+c] = V1; rem[2+c] = V0; c += 3; break;
      case '3' : rem[c] = V0; rem[1+c] = V1; rem[2+c] = V1; c += 3; break;
      case '4' : rem[c] = V1; rem[1+c] = V0; rem[2+c] = V0; c += 3; break;
      case '5' : rem[c] = V1; rem[1+c] = V0; rem[2+c] = V1; c += 3; break;
      case '6' : rem[c] = V1; rem[1+c] = V1; rem[2+c] = V0; c += 3; break;
      case '7' : rem[c] = V1; rem[1+c] = V1; rem[2+c] = V1; c += 3; break;
   
      case 'x' : rem[c] = VX; rem[1+c] = VX; rem[2+c] = VX; c += 3; break;
      case 'z' : rem[c] = VZ; rem[1+c] = VZ; rem[2+c] = VZ; c += 3; break;
       
      default:
        break;
    }
  }

  // Sized literals retain the low bits even when the textual digits are wider.

  if( _no_xz == IS_FALSE )
  {
    append_boh_with_xz( c, rem );
    delete[] rem;
  }
  else
  {
    append_boh_no_xz( c, rem );
    delete[] rem;
  }
  return OK;
}

int
VeriNum::bin_atoi( const char *in )
{
  int len = strlen(in);
  int rem_len = len * INT_BIN_BIT + 1;
  uint8_t *rem = new uint8_t[rem_len];
  memset( rem, 0, rem_len );

  int c = determin_boh_head( in[0], rem );
  int k = (c != 0 ? 1 : 0);
  in = &(in[k]);
  len -= k;

  for( int i = 0; i < len; ++i )
  {
    switch( in[i] )
    {
      case '0' : rem[c] = V0; ++c; break;
      case '1' : rem[c] = V1; ++c; break;
      case 'x' : rem[c] = VX; ++c; break;
      case 'z' : rem[c] = VZ; ++c; break;
       
      default:
        break;
    }
  }

  // Sized literals retain the low bits even when the textual digits are wider.

  if( _no_xz == IS_FALSE )
  {
    append_boh_with_xz( c, rem );
    delete[] rem;
  }
  else
  {
    append_boh_no_xz( c, rem );
    delete[] rem;
  }
  return OK;
}

int
VeriNum::dec_atoi( const char *in )
{
  int len = strlen(in);
  int rem_len = len * INT_DEC_BIT + 1;
  uint8_t *remain_stream = new uint8_t[rem_len];
  memset( remain_stream, 0, rem_len );

  int c = 0;
  uint8_t high = V0;
  switch( in[0] )
  {
    case 'x' : high = VX; c = 1; break;
    case 'z' : high = VZ; c = 1; break;
    default  : break;
  }
  in = &(in[c]);
  len -= c;

  int div = 0;
  int rem = 0;

  char *str = new char[ len + 1 ];
  char *cbak = str;
  memset( str, 0, len + 1 );
  strncpy( str, in, len );

  while( *str != '\0' )
  {
    rem = 0;
    for( unsigned int i = 0; i < strlen(str); ++i )
    {
      div = (str[i] & 0xf) + rem * vDEC;
      str[i] = (div >> 1) | 0x30;
      rem = div & 0x1;
    }
    remain_stream[c++] = rem;

    if( *str == '0' )
    {
      *str = '\0';
      ++str;
    }
  }
  delete[] cbak;

  if( high != V0 )
  {
    remain_stream[c] = high;
    ++c;
  }

  // Sized literals retain the low bits even when the textual digits are wider.

  if( _no_xz == IS_FALSE )
  {
    _val_x = new uint8_t[_bits];
    memset( _val_x, 0x0, sizeof( uint8_t ) * _bits );

    uint8_t high_end;
    if( remain_stream[0] == VX )
      high_end = VX;
    else if( remain_stream[0] == VZ )
      high_end = VZ;
    else
      high_end = V0;

    uint8_t res;
    for( int i = 0; i < _bits; ++i )
    {
      if( i > (c-1) )
        res = high_end;
      else
        res = remain_stream[i];

      _val_x[i] = res;
    }
  }
  else
  {
    int last_pac = _bits % INT_BIN_RATIO;
    _vbits = _bits / INT_BIN_RATIO + (last_pac != 0 ? 1 : 0);
    _val = new uint32_t[ _vbits ];
    memset( _val, 0x0, sizeof( uint32_t ) * _vbits );
   
    int idx, bcnt, wcnt;
    uint8_t res = V0;
    for( bcnt = 0, wcnt = 0; bcnt < _vbits; ++bcnt )
    {
      for( idx = 0; idx < INT_BIN_RATIO; ++idx, ++wcnt )
      {
        res = (wcnt > (c-1)) ? (uint8_t)(V0) : remain_stream[wcnt];
        _val[bcnt] = _val[bcnt] | ( res << idx ) ;
      }
    }
    delete[] remain_stream;
  }

  return OK;
}

int
VeriNum::turn_into_xz_mode( void )
{
  if( _val_x == NULL && _val != NULL )
  {
    _val_x = new uint8_t[_bits];
    memset( _val_x, 0x0, sizeof( uint8_t ) * _bits );

    int i,j,cnt;
    for( i = 0, cnt = 0; i < _vbits; ++i )
    {
      for( j = 0; j < INT_BIN_RATIO && cnt < _bits; ++j, ++cnt )
        _val_x[cnt] = (_val[i] >> j) & 0x1;
    }

    delete[] _val;
    _val = NULL;
  }
  return OK;
}

int
VeriNum::high_end_padding( int bits )
{
  if( _bits >= bits )
    return OK;
/*
  if( _bits == bits )
  {
    if( _val != NULL )
    {
      int  last_idx  = _bits % INT_BIN_RATIO;
      uint8_t high_end  = _val[_vbits-1] >> ( INT_BIN_RATIO - last_idx );
      if( high_end != 0x0 )
        _val[_vbits-1] = _val[_vbits-1] | ((uint32_t)0xffffffff << last_idx );
    }
    return OK;
  }
*/
  if( _val != NULL )
  {
    int  last_idx  = _bits % INT_BIN_RATIO;
    int  new_vbits =  bits / INT_BIN_RATIO + ((bits % INT_BIN_RATIO) ? 1 : 0);
    uint8_t high_end  = _val[_vbits-1] >> ((last_idx == 0 ? INT_BIN_RATIO : last_idx) - 1);

    uint32_t * new_val = new uint32_t[new_vbits];
    if( high_end == 0x1 )
      high_end = 0xff;

    if( _is_signed == IS_TRUE )
      memset( new_val, high_end, sizeof( uint32_t ) * new_vbits );
    else
      memset( new_val, 0, sizeof( uint32_t ) * new_vbits );

    memcpy( new_val, _val, sizeof( uint32_t ) * _vbits );

    if( _is_signed == IS_TRUE && high_end == 0xff && last_idx != 0 )
      new_val[_vbits-1] = new_val[_vbits-1] | ((uint32_t)0xffffffff << last_idx );

    delete[] _val;
    _val   = new_val;
    _vbits = new_vbits;
    _bits  = bits;
    align_bits();
  }

  if( _val_x != NULL )
  {
    uint8_t high_end = _val_x[_bits-1];

    uint8_t *new_val_x = new uint8_t[bits];

    if( _is_signed == IS_TRUE )
      memset( new_val_x, high_end, sizeof( uint8_t ) * bits );
    else
      memset( new_val_x, 0, sizeof( uint8_t ) * bits );

    memcpy( new_val_x, _val_x, sizeof( uint8_t ) * _bits );

    delete[] _val_x;
    _val_x = new_val_x;
    _bits  = bits;
  }

  return OK;
}

int
VeriNum::is_one_bit( void )
{
  if( _val != NULL )
  {
    if( _vbits == 1 && ((_val[0] >> 1) == 0) )
      return IS_TRUE;
    return IS_FALSE;
  }
   
  if( _val_x != NULL )
  {
    if( _bits == 1 && ((_val_x[0] >> 1) == 0) )
      return IS_TRUE;
    return IS_FALSE;
  }

  return IS_FALSE;
}

uint32_t
VeriNum::one_bit_value( void )
{
  if( _val != NULL )
    return _val[0];
  else if( _val_x != NULL )
    return _val_x[0];

  return V0;
}

int
VeriNum::get_first_int( void )
{
  if( _val != NULL )
    return (int)_val[0];
  else
    return 0;
}

int
VeriNum::get_certain_bit( int bit )
{
  if( bit < 0 || bit >= _bits )
    return 0;

  if( _val != NULL )
  {
    int vidx = bit / INT_BIN_RATIO;
    int vpac = bit % INT_BIN_RATIO;
    // Sized decimal literals can have fewer allocated words than their
    // declared width (e.g. 62'd1). The missing high words are zero padding.
    if( vidx >= _vbits ) return 0;
    return (_val[vidx] & ((uint32_t)0x1 << vpac )) >> vpac;
  }

  if( _val_x != NULL )
    return _val_x[bit];

  return 0;
}

void
VeriNum::clear( void )
{
  _real_width=0;
  _string_type=false;
  _radix    = 0;
  _bits     = 0;
  _vbits    = 0;
  _no_xz    = 0;
  _is_signed   = IS_FALSE;

  if( _val_x != NULL )
    delete[] _val_x;
  _val_x = NULL;

  if( _val != NULL )
    delete[] _val;
  _val      = NULL;
}


void
VeriNum::clean_up( void )
{
  _real_width=0;
  _string_type=false;
  _radix    = 0;
  _bits     = 0;
  _vbits    = 0;
  _no_xz    = 0;
  _is_signed   = IS_FALSE;

  if( _val_x != NULL )
    delete[] _val_x;
  _val_x = NULL;

  if( _val != NULL )
    delete[] _val;
  _val      = NULL;
}

int
VeriNum::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriNum::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << string_result( );

  ofile << dot_str_tail( tok_type() );

  return OK;
}

int
VeriNum::check_child_validation( void )
{
  return OK;
}

int
VeriNum::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriNum::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriNum::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

std::string
VeriNum::string_result( void ) const
{
  String re  = "NUM : " + int2string( _bits ) + "\'[";
         re += string_sign( ) + string_radix() + "]";
  if( _val_x != NULL ) re += string_valx( );
  if( _val != NULL ) re += string_val( );
  re += "\\n";
  return re;
}

std::string
VeriNum::string_radix( void ) const
{
  switch( _radix )
  {
    case vBIN : return "B";
    case vOCT : return "O";
    case vDEC : return "D";
    case vHEX : return "H";
    default   : return " ";
  }
}

std::string
VeriNum::string_sign( void ) const
{
  if( _is_signed == IS_TRUE )
    return "S";
  else
    return "";
}

std::string
VeriNum::string_valx( void ) const
{
  String re = "";
  for( int i = _bits - 1; i >= 0; --i )
  {
    switch( _val_x[i] )
    {
      case V0 : re += "0";  break;
      case V1 : re += "1";  break;
      case VX : re += "X";  break;
      case VZ : re += "Z";  break;
      default : break;
    }
    if( (i != 0) && ((i & 0x3) == 0) )
      re += "_";
  }
  return re;
}

std::string
VeriNum::string_val( void ) const
{
  String re = "";
  int i,j;
  char t = 0;

  if( _vbits == 1 )
  {
    re += int2string( _val[0] );
    return re;
  }

  for( i = _vbits - 1; i >= 0; --i )
  {
    for( j = INT_BIN_RATIO - 1; j >= 0; --j )
    {
      t = ((_val[i] >> j) & 0x1) | 0x30;
      re += t;
      if( (i != 0 || j != 0) && ((j & 0x3) == 0) )
        re += "_";
    }
  }
  return re;
}

uint8_t
VeriNum::bit_add( uint8_t a, uint8_t b, uint8_t c_in, uint8_t& sum ) // return c_out
{
  uint8_t ct1 = bit_and( a, b );
  uint8_t ct2 = bit_and( b, c_in );
  uint8_t ct3 = bit_and( a, c_in );
  uint8_t ct  = bit_or( ct1, ct2 );
  
  sum = bit_xor( bit_xor( a, b ), c_in );
  return bit_or( ct, ct3 );
}

uint8_t
VeriNum::bit_and( uint8_t a, uint8_t b )
{
  switch( a )
  {
    case V0:
      switch( b )
      {
        case V0: return V0;
        case V1: return V0;
        case VX: return V0;
        case VZ: return V0;
      }
      break;

    case V1:
      switch( b )
      {
        case V0: return V0;
        case V1: return V1;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VX:
      switch( b )
      {
        case V0: return V0;
        case V1: return VX;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VZ:
      switch( b )
      {
        case V0: return V0;
        case V1: return VZ;
        case VX: return VZ;
        case VZ: return VZ;
      }
      break;
  }
  return VX;
}

uint8_t
VeriNum::bit_or( uint8_t a, uint8_t b )
{
  switch( a )
  {
    case V0:
      switch( b )
      {
        case V0: return V0;
        case V1: return V1;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case V1:
      switch( b )
      {
        case V0: return V1;
        case V1: return V1;
        case VX: return V1;
        case VZ: return V1;
      }
      break;

    case VX:
      switch( b )
      {
        case V0: return VX;
        case V1: return V1;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VZ:
      switch( b )
      {
        case V0: return VZ;
        case V1: return V1;
        case VX: return VZ;
        case VZ: return VZ;
      }
      break;
  }
  return VX;
}

uint8_t
VeriNum::bit_xor( uint8_t a, uint8_t b )
{
  switch( a )
  {
    case V0:
      switch( b )
      {
        case V0: return V0;
        case V1: return V1;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case V1:
      switch( b )
      {
        case V0: return V1;
        case V1: return V0;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VX:
      switch( b )
      {
        case V0: return VX;
        case V1: return VX;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VZ:
      switch( b )
      {
        case V0: return VZ;
        case V1: return VZ;
        case VX: return VZ;
        case VZ: return VZ;
      }
      break;
  }
  return VX;
}

uint8_t
VeriNum::bit_xnor( uint8_t a, uint8_t b )
{
  switch( a )
  {
    case V0:
      switch( b )
      {
        case V0: return V1;
        case V1: return V0;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case V1:
      switch( b )
      {
        case V0: return V0;
        case V1: return V1;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VX:
      switch( b )
      {
        case V0: return VX;
        case V1: return VX;
        case VX: return VX;
        case VZ: return VZ;
      }
      break;

    case VZ:
      switch( b )
      {
        case V0: return VZ;
        case V1: return VZ;
        case VX: return VZ;
        case VZ: return VZ;
      }
      break;
  }
  return VX;
}

uint8_t
VeriNum::bit_neg( uint8_t a )
{
  switch( a )
  {
    case V0: return V1;
    case V1: return V0;
    case VX: return VX;
    case VZ: return VZ;
  }
 
  return VX;
}

int
VeriNum::unary_operation( int op )
{
  if(_string_type)throw std::runtime_error("operator requires integral operands");
  if(_real_width) {
    const double value=real_value();
    if(op==vtUADD)return OK;
    if(op==vtUSUB){set_real(-value,_real_width);return OK;}
    if(op==vtUNOT){init_val(IS_FALSE,1);_val[0]=value==0;return OK;}
    throw std::runtime_error("operator requires integral operand");
  }
  if( _val_x == NULL && _val == NULL )
    return vNVALUE_USED_WITHOUT_INIT;

  switch( op )
  {
    case vtUADD  : return uadd ( ); // +
    case vtUSUB  : return usub ( ); // -
    case vtUNEG  : return uneg ( ); // ~
    case vtUAND  : return uand ( ); // &
    case vtUOR   : return uor  ( ); // |
    case vtUNAND : return unand( ); // ~&
    case vtUNOR  : return unor ( ); // ~|
    case vtUXNOR : return uxnor( ); // ~^
    case vtUNOT  : return unot ( ); // !
    case vtUXOR  : return uxor ( ); // ^
    default      : return vNUNARY_OP_NOT_FOUND;
  }
}

int
VeriNum::binary_operation( int op, const VeriNum *other )
{
  if(_string_type||other->_string_type) {
    const int comparison=string_value().compare(other->string_value());bool value=false;
    switch(op) {
      case vtBLEQ:case vtBCEQ:value=comparison==0;break;
      case vtBLIEQ:case vtBCIEQ:value=comparison!=0;break;
      case vtBLT:value=comparison<0;break;case vtBLE:value=comparison<=0;break;
      case vtBGT:value=comparison>0;break;case vtBGE:value=comparison>=0;break;
      default:throw std::runtime_error("operator requires integral operands");
    }
    init_val(IS_FALSE,1);_val[0]=value;return OK;
  }
  if(_real_width||other->_real_width) {
    if(op==vtBDAND||op==vtBDOR) {
      auto truth=[](const VeriNum* number)->int {
        if(number->real_width())return number->real_value()!=0?V1:V0;
        int result=V0;
        for(int i=0;i<number->bits();++i) {
          const int bit=const_cast<VeriNum*>(number)->get_certain_bit(i);
          if(bit==V1)return V1;
          if(bit==VX||bit==VZ)result=VX;
        }
        return result;
      };
      const int a=truth(this),b=truth(other);
      const int value=op==vtBDAND?(a==V0||b==V0?V0:a==VX||b==VX?VX:V1):
        (a==V1||b==V1?V1:a==VX||b==VX?VX:V0);
      return assign_bit_value(std::vector<uint8_t>(1,uint8_t(value)),false);
    }
    const int width=std::max(_real_width,other->_real_width);double a=real_value(),b=other->real_value();double value=0;bool boolean=false;
    if(width==32){a=static_cast<float>(a);b=static_cast<float>(b);}
    switch(op) {
      case vtBADD:value=a+b;break;case vtBSUB:value=a-b;break;
      case vtBMUL:value=a*b;break;case vtBDIV:value=a/b;break;case vtBPOW:value=std::pow(a,b);break;
      case vtBLEQ:value=a==b;boolean=true;break;case vtBLIEQ:value=a!=b;boolean=true;break;
      case vtBLT:value=a<b;boolean=true;break;case vtBGT:value=a>b;boolean=true;break;
      case vtBLE:value=a<=b;boolean=true;break;case vtBGE:value=a>=b;boolean=true;break;
      default:throw std::runtime_error("operator requires integral operands");
    }
    if(boolean){init_val(IS_FALSE,1);_val[0]=value!=0;}else set_real(value,width);
    return OK;
  }
  if( _val_x == NULL && _val == NULL )
    return vNVALUE_USED_WITHOUT_INIT;

  if( other->_val_x == NULL && other->_val == NULL )
    return vNVALUE_USED_WITHOUT_INIT;

  uint8_t carry = 0;
  VeriNum *tmp = new VeriNum( idx(), other );
  int re = OK;
  switch( op )
  {
    case vtBWLEQ: case vtBWLNEQ: {
      align_signed_bits(tmp);bool unknown=false,mismatch=false;
      for(int i=0;i<bits();++i) {
        int a=get_certain_bit(i),b=tmp->get_certain_bit(i);
        if(b==VX||b==VZ)continue;
        if(a==VX||a==VZ)unknown=true;else if(a!=b)mismatch=true;
      }
      re=assign_bit_value(std::vector<uint8_t>(1,mismatch?(op==vtBWLNEQ?V1:V0):unknown?VX:op==vtBWLEQ?V1:V0),false);
      break;
    }
    case vtBNAND : re =  bnand( tmp );          break; // ~&
    case vtBNOR  : re =  bnor ( tmp );          break; // ~|
    case vtBXNOR : re =  bxnor( tmp );          break; // ~^
    case vtBSAND : re =  bsand( tmp );          break; // &
    case vtBSXOR : re =  bsxor( tmp );          break; // ^
    case vtBSOR  : re =  bsor ( tmp );          break; // |
    case vtBDAND : re =  bdand( tmp );          break; // &&
    case vtBDOR  : re =  bdor ( tmp );          break; // ||

    case vtBPOW  : re =  bpow ( tmp );          break; // **
    case vtBMOD  : re =  bmod ( tmp );          break; // %
    case vtBMUL  : re =  bmul ( tmp );          break; // *
    case vtBDIV  : re =  bdiv ( tmp );          break; // /
    case vtBADD  : re =  badd ( tmp );          break; // +
    case vtBSUB  : re =  bsub ( tmp, carry );   break; // -
    case vtBLT: case vtBGT: case vtBLE: case vtBGE:
      re = brel(tmp,op); break;
    case vtBLRS  : re =  blrs ( tmp );          break; // >>
    case vtBLLS  : re =  blls ( tmp );          break; // <<
    case vtBARS  : re =  bars ( tmp );          break; // >>>
    case vtBALS  : re =  bals ( tmp );          break; // <<<
    case vtBLEQ  : re =  bleq ( tmp );          break; // ==
    case vtBLIEQ : re =  blieq( tmp );          break; // !=
    case vtBCEQ  : re =  bceq ( tmp );          break; // ===
    case vtBCIEQ : re =  bcieq( tmp );          break; // !==
    default      : re =  vNBINARY_OP_NOT_FOUND; break; 
  }
  delete tmp;
  return re;
}

int
VeriNum::upward_case_eq( const VeriNum *other )
{
  if( _val_x == NULL && _val == NULL )
    return vNVALUE_USED_WITHOUT_INIT;

  if( other->_val_x == NULL && other->_val == NULL )
    return vNVALUE_USED_WITHOUT_INIT;

  VeriNum *tmp = new VeriNum( idx(), other );

  align_signed_bits( tmp );

  if( _val != NULL && tmp->_val != NULL )
  {
    uint8_t re = V1;
    for( int i = 0; i < _vbits; ++i )
    {
      if( _val[i] != tmp->_val[i] )
      {
        re = V0;
        break;
      }
    }
    delete[] _val;
    _bits  = 1;
    _vbits = 1;
    _val   = new uint32_t[1];
    _val[0] = re;
    delete tmp;
    return re;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( tmp->_val != NULL )
    tmp->turn_into_xz_mode();

  uint8_t re = V1;
  if( _val_x != NULL )
  {
    for( int i = 0; i < _bits; ++i )
    {
      if( _val[i] == VX )
        continue;

      if( _val[i] == VZ && tmp->_val[i] != VZ )
      {
        re = V0;
        break;
      }

      if( _val[i] != tmp->_val[i] )
      {
        re = V0;
        break;
      }
    }
    delete[] _val_x;
    _bits  = 1;
    _vbits = 1;
    _val_x = new uint8_t[1];
    _val_x[0] = re;
  }
  delete tmp;
  return re;
}


int
VeriNum::align_bits( void )
{
  const int remainder = _bits % INT_BIN_RATIO;
  if( _val != NULL && _vbits > 0 && remainder != 0 )
    _val[_vbits-1] &= uint32_t(0xffffffff) >> (INT_BIN_RATIO-remainder);
  return OK;
}

int
VeriNum::assign_bit_value( const std::vector<uint8_t>& bits, bool sign ) {
  String text=std::to_string(bits.size())+(sign?"'sb":"'b");
  for(auto it=bits.rbegin();it!=bits.rend();++it)text+=*it==VX?'x':*it==VZ?'z':*it==V1?'1':'0';
  return parse(text.c_str(),text.size());
}

int
VeriNum::reduce_value( bool conjunction, bool invert ) {
  bool unknown=false,controlling=false;
  for(int bit=0;bit<_bits;++bit) {
    const int value=get_certain_bit(bit);
    if(value>=VX)unknown=true;
    else if(value==(conjunction?V0:V1))controlling=true;
  }
  int value=controlling?(conjunction?V0:V1):unknown?VX:(conjunction?V1:V0);
  if(invert&&value<VX)value=1-value;
  return assign_bit_value(std::vector<uint8_t>(1,value),false);
}

int
VeriNum::shift_value( const VeriNum *other, bool left, bool arithmetic ) {
  const bool sign=_is_signed==IS_TRUE;
  std::vector<uint8_t> result(_bits,0);
  uint64_t amount=0;
  for(int bit=0;bit<other->_bits;++bit) {
    const int value=const_cast<VeriNum*>(other)->get_certain_bit(bit);
    if(value==VX||value==VZ)return assign_bit_value(std::vector<uint8_t>(_bits,VX),sign);
    if(value==V1) {
      if(bit>=63)amount=uint64_t(_bits);
      else amount=std::min(uint64_t(_bits),amount+(uint64_t(1)<<bit));
    }
  }
  const int fill=arithmetic&&sign?get_certain_bit(_bits-1):V0;
  for(int bit=0;bit<_bits;++bit) {
    const int64_t source=left?int64_t(bit)-int64_t(amount):int64_t(bit)+int64_t(amount);
    result[bit]=source>=0&&source<_bits?get_certain_bit(int(source)):left?V0:fill;
  }
  return assign_bit_value(result,sign);
}

int
VeriNum::divide_modulo( const VeriNum *other, bool modulo ) {
  const int width=std::max(_bits,other->_bits);
  const bool sign=_is_signed==IS_TRUE&&other->_is_signed==IS_TRUE;
  VeriNum left(0,this),right(0,other);
  if(!sign){left.set_unsigned();right.set_unsigned();}
  left.truncate_assign(width);right.truncate_assign(width);
  std::vector<uint8_t> numerator(width),denominator(width),quotient(width,0),remainder(width+1,0);
  bool nonzero=false;
  for(int bit=0;bit<width;++bit) {
    const int a=left.get_certain_bit(bit),b=right.get_certain_bit(bit);
    if(a>=VX||b>=VX)return assign_bit_value(std::vector<uint8_t>(width,VX),sign);
    numerator[bit]=a;denominator[bit]=b;nonzero=nonzero||b;
  }
  if(!nonzero)return assign_bit_value(std::vector<uint8_t>(width,VX),sign);
  auto negate=[](std::vector<uint8_t>& bits){int carry=1;for(auto& bit:bits){int sum=(1-bit)+carry;bit=sum&1;carry=sum>>1;}};
  const bool negative_left=sign&&numerator.back(),negative_right=sign&&denominator.back();
  if(negative_left)negate(numerator);if(negative_right)negate(denominator);
  for(int bit=width-1;bit>=0;--bit) {
    for(int i=width;i>0;--i)remainder[i]=remainder[i-1];remainder[0]=numerator[bit];
    int order=remainder[width]?1:0;
    if(!order)for(int i=width-1;i>=0;--i)if(remainder[i]!=denominator[i]){order=remainder[i]>denominator[i]?1:-1;break;}
    if(order>=0){int borrow=0;for(int i=0;i<=width;++i){int sub=int(remainder[i])-(i<width?denominator[i]:0)-borrow;remainder[i]=sub&1;borrow=sub<0;}quotient[bit]=1;}
  }
  remainder.resize(width);
  if(modulo){if(negative_left)negate(remainder);return assign_bit_value(remainder,sign);}
  if(negative_left!=negative_right)negate(quotient);
  return assign_bit_value(quotient,sign);
}

void
VeriNum::to_two_state( void )
{
  if(_val_x==NULL)return;
  _vbits=(_bits+INT_BIN_RATIO-1)/INT_BIN_RATIO;
  auto* known=new uint32_t[_vbits]();
  for(int bit=0;bit<_bits;++bit)
    if(_val_x[bit]==V1)known[bit/INT_BIN_RATIO]|=uint32_t(1)<<(bit%INT_BIN_RATIO);
  delete[] _val;delete[] _val_x;_val=known;_val_x=NULL;_no_xz=IS_TRUE;
}

int
VeriNum::truncate_assign( int new_bits )
{
  if(_real_width){real_to_integral(new_bits);return OK;}
  new_bits = abs(new_bits);

  if( _bits < new_bits )
    return high_end_padding( new_bits );
  else if( _bits > new_bits )
  {
    int i;
    if( _val != NULL )
    {
      int last_idx  = new_bits % INT_BIN_RATIO;
      int new_vbits = new_bits / INT_BIN_RATIO + (last_idx != 0 ? 1 : 0 );

      uint32_t *new_val = new uint32_t[new_vbits];
      memset( new_val, 0x0, sizeof(uint32_t) * new_vbits );
      
      for( i = 0; i < new_vbits-1; ++i )
        new_val[i] = _val[i];

      if( last_idx != 0 )
        new_val[i] = _val[i] & ( (uint32_t)0xffffffff >> (INT_BIN_RATIO - last_idx) );
      else
        new_val[i] = _val[i];

      delete[] _val;
      _val   = new_val;
      _bits  = new_bits;
      _vbits = new_vbits;

      return OK;
    }

    if( _val_x != NULL )
    {
      uint8_t *new_val_x = new uint8_t[new_bits];
      memset( new_val_x, 0x0, sizeof(uint8_t) * new_bits );

      for( i = 0; i < new_bits; ++i )
        new_val_x[i] = _val_x[i];

      delete[] _val_x;
      _val_x = new_val_x;
      _bits  = new_bits;

      return OK;
    }
  }
  return OK;
}

int
VeriNum::increment( void )
{
  if( _val != NULL )
  {
    uint64_t tmp = 1;
    for( int i = 0; i < _vbits; ++i )
    {
      tmp = (uint64_t)_val[i] + tmp;
      _val[i] = (uint32_t)(tmp & 0xffffffff );
      tmp = (tmp & 0xffffffff00000000) >> 32;
    }
    align_bits( );
    return OK;
  }

  if( _val_x != NULL )
  {
    uint8_t carry = 1;
    for( int i = 0; i < _bits; ++i )
      carry = bit_add( _val_x[i], 0, carry, _val_x[i] );
  }
  return OK;
}

int
VeriNum::decrement( void )
{
  if( _val != NULL )
  {
    uint64_t tmp = 0;
    for( int i = 0; i < _vbits; ++i )
    {
      tmp = (uint64_t)_val[i] + 1 + tmp;
      _val[i] = (uint32_t)(tmp & 0xffffffff );
      tmp = (tmp & 0xffffffff00000000) >> 32;
    }
    align_bits( );
    return OK;
  }

  if( _val_x != NULL )
  {
    uint8_t carry = 0;
    for( int i = 0; i < _bits; ++i )
      carry = bit_add( _val_x[i], 0x1, carry, _val_x[i] );
  }
  return OK;
}

int
VeriNum::uneg ( void )   // ~
{
  if( _val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = uint32_t(0xffffffff) - _val[i];
    align_bits( );
  }

  if( _val_x != NULL )
  {
    for( int i = 0; i < _bits; ++i )
    {
      if( _val_x[i] == V0 )
        _val_x[i] = V1;
      else if( _val_x[i] == V1 )
        _val_x[i] = V0;
      else
        _val_x[i] = VX;
    }
  }

  return OK;
}

int
VeriNum::uand( void ) { return reduce_value(true,false); }


int
VeriNum::uor( void ) { return reduce_value(false,false); }


int
VeriNum::unand( void ) { return reduce_value(true,true); }


int
VeriNum::unor( void ) { return reduce_value(false,true); }


int
VeriNum::uxnor( void )   // ~^
{
  int result=uxor();if(result!=OK)return result;
  if(_val)_val[0]^=1;
  return OK;
}

int
VeriNum::unot( void ) { return reduce_value(false,true); }


int
VeriNum::uxor ( void )   // ^
{
  uint8_t value=V0;
  for(int bit=0;bit<_bits;++bit)value=bit_xor(value,get_certain_bit(bit));
  delete[] _val;delete[] _val_x;_val=NULL;_val_x=NULL;
  _bits=1;_vbits=1;_is_signed=IS_FALSE;
  _no_xz=value==V0||value==V1?IS_TRUE:IS_FALSE;
  if(_no_xz==IS_TRUE){_val=new uint32_t[1];_val[0]=value;}
  else {_val_x=new uint8_t[1];_val_x[0]=VX;}
  return OK;
}

int
VeriNum::align_signed_bits( VeriNum *other )
{
  if( _bits > other->_bits )
    other->high_end_padding( _bits );
  else
    other->high_end_padding( other->_bits );

  if( _bits < other->_bits )
    high_end_padding( other->_bits );
  else
    high_end_padding( _bits );
  return OK;
}

int
VeriNum::bnand ( VeriNum *other )   // ~&
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = uint32_t(0xffffffff) - (other->_val[i] & _val[i]);
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  for( int i = 0; i < _bits; ++i )
    _val[i] = bit_neg( bit_and( _val[i], other->_val[i] ) );

  return OK;
}

int
VeriNum::bnor  ( VeriNum *other )   // ~|
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = uint32_t(0xffffffff) - (other->_val[i] | _val[i]);
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  for( int i = 0; i < _bits; ++i )
    _val[i] = bit_neg( bit_or( _val[i], other->_val[i] ) );

  return OK;
}

int
VeriNum::bxnor ( VeriNum *other )   // ~^
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = uint32_t(0xffffffff) - (other->_val[i] ^ _val[i]);
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  for( int i = 0; i < _bits; ++i )
    _val[i] = bit_xnor( _val[i], other->_val[i] );

  return OK;
}

int
VeriNum::bsand ( VeriNum *other )   // &
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = other->_val[i] & _val[i];
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  for( int i = 0; i < _bits; ++i )
    _val[i] = bit_and( _val[i], other->_val[i] );

  return OK;
}

int
VeriNum::bsxor ( VeriNum *other )   // ^
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = other->_val[i] ^ _val[i];
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  for( int i = 0; i < _bits; ++i )
    _val[i] = bit_xor( _val[i], other->_val[i] );

  return OK;
}

int
VeriNum::bsor  ( VeriNum *other )   // |
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    for( int i = 0; i < _vbits; ++i )
      _val[i] = other->_val[i] | _val[i];
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  for( int i = 0; i < _bits; ++i )
    _val[i] = bit_or( _val[i], other->_val[i] );

  return OK;
}

int
VeriNum::bdand ( VeriNum *other )   // &&
{
  uor( );
  if( one_bit_value() == 0x0 )
    return OK;

  other->uor( );

  uint8_t re = bit_and( static_cast<uint8_t>(one_bit_value()),
                        static_cast<uint8_t>(other->one_bit_value()) );

  if( _val != 0 )
    _val[0] = re;

  if( _val_x != 0 )
    _val_x[0] = re;
  return OK;
}

int
VeriNum::bdor  ( VeriNum *other )   // ||
{
  uor( );
  if( one_bit_value() == 0x1 )
    return OK;

  other->uor( );

  uint8_t re = bit_or( static_cast<uint8_t>(one_bit_value()),
                       static_cast<uint8_t>(other->one_bit_value()) );

  if( _val != 0 )
    _val[0] = re;

  if( _val_x != 0 )
    _val_x[0] = re;
  return OK;
}

int
VeriNum::uadd ( void )   // +
{
  return OK;
}

int
VeriNum::usub ( void )   // -
{
  if(_val_x != NULL && std::any_of(_val_x,_val_x+_bits,[](uint8_t bit){return bit==VX||bit==VZ;})) {
    std::fill(_val_x,_val_x+_bits,uint8_t(VX));return OK;
  }
  int re = uneg( );
  if( re != OK )
    return re;

  re = increment( );
  return re;
}

int
VeriNum::badd  ( VeriNum *other )   // +
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    uint64_t tmp = 0;
    for( int i = 0; i < _vbits; ++i )
    {
      tmp = (uint64_t)_val[i] + (uint64_t)other->_val[i] + tmp;
      _val[i] = (uint32_t)(tmp & 0xffffffff );
      tmp = (tmp & 0xffffffff00000000) >> 32;
    }
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  if( _val_x != NULL )
  {
    uint8_t carry = 1;
    for( int i = 0; i < _bits; ++i )
      carry = bit_add( _val_x[i], other->_val_x[i], carry, _val_x[i] );
  }

  return OK;
}

int
VeriNum::bsub  ( VeriNum *other, uint8_t &carry )   // -
{
  align_signed_bits( other );

  other->usub( );

  if( _val != NULL && other->_val != NULL )
  {
    uint64_t tmp = 0;
    for( int i = 0; i < _vbits; ++i )
    {
      tmp = (uint64_t)_val[i] + (uint64_t)other->_val[i] + tmp;
      _val[i] = (uint32_t)(tmp & 0xffffffff );
      tmp = (tmp & 0xffffffff00000000) >> 32;
    }
    carry = (uint8_t)tmp;
    align_bits( );
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  if( _val_x != NULL )
  {
    carry = 1;
    for( int i = 0; i < _bits; ++i )
      carry = bit_add( _val_x[i], other->_val_x[i], carry, _val_x[i] );
  }

  return OK;
}

int
VeriNum::lrs_one_round( int bits )
{
  if( bits > INT_BIN_RATIO )
    return OK;

  if( _val != NULL )
  {
    int i = 0;
    for( i = 0; i < _vbits - 1; ++i )
    {
      _val[i] = _val[i] >> bits;
      _val[i] =   _val[i]
                | ( ( _val[i+1]
                      & ((uint32_t)(0xffffffff) >> (INT_BIN_RATIO - bits)) )
                      << ( INT_BIN_RATIO - bits )
                  );
    }
    if( bits == INT_BIN_RATIO )
      _val[i] = 0x0;
    else
      _val[i] = _val[i] >> bits;
  }

  return OK;
}

int
VeriNum::lls_one_round( int bits )
{
  if( bits > INT_BIN_RATIO )
    return OK;

  if( _val != NULL )
  {
    int i;
    for( i = _vbits - 1; i > 0; --i )
    {
      _val[i] = _val[i] << bits;
      _val[i] =   _val[i]
                | ( ( _val[i-1]
                      & ((uint32_t)(0xffffffff) << (INT_BIN_RATIO - bits)) )
                      >> ( INT_BIN_RATIO - bits )
                  );
    }
    if( bits == INT_BIN_RATIO )
      _val[i] = 0x0;
    else
      _val[i] = _val[i] << bits;

    align_bits( );
  }

  return OK;
}

int
VeriNum::ars_one_round( int bits )
{
  if( bits > INT_BIN_RATIO )
    return OK;

  if( _val != NULL )
  {
    int  last_idx  = _bits % INT_BIN_RATIO;
    uint8_t high_end =     _val[_vbits-1]
                       >> ( (last_idx == 0 ? INT_BIN_RATIO : last_idx) - 1);
    int i;
    for( i = 0; i < _vbits - 1; ++i )
    {
      _val[i] = _val[i] >> bits;
      _val[i] =   _val[i]
                | ( ( _val[i+1]
                      & ((uint32_t)(0xffffffff) >> (INT_BIN_RATIO - bits)) )
                      << ( INT_BIN_RATIO - bits )
                  );
    }

    if( high_end != 0x0 )
      _val[_vbits-1] = _val[_vbits-1] | ((uint32_t)0xffffffff << last_idx );
    else
      memset( &(_val[i]), 0, sizeof(uint32_t));

    _val[i] = _val[i] >> bits;
    align_bits( );
  }

  return OK;
}

int
VeriNum::blrs( VeriNum *other ) { return shift_value(other,false,false); }

int
VeriNum::blls( VeriNum *other ) { return shift_value(other,true,false); }

int
VeriNum::bars( VeriNum *other ) { return shift_value(other,false,true); }

int
VeriNum::bals( VeriNum *other ) { return shift_value(other,true,false); }

int
VeriNum::brel( VeriNum *other, int op )
{
  // Compare extended bits directly. Subtraction's final carry is not a
  // signed ordering test and was wrong at zero and word/sign boundaries.
  const bool sign=_is_signed==IS_TRUE && other->_is_signed==IS_TRUE;
  const int width=std::max(_bits,other->_bits);
  const int left_sign=sign?get_certain_bit(_bits-1):V0;
  const int right_sign=sign?other->get_certain_bit(other->_bits-1):V0;
  int order=0;bool unknown=false;
  for(int i=width-1;i>=0;--i) {
    const int left=i<_bits?get_certain_bit(i):left_sign;
    const int right=i<other->_bits?other->get_certain_bit(i):right_sign;
    if(left==VX || left==VZ || right==VX || right==VZ)unknown=true;
    else if(!order && left!=right)order=left<right?-1:1;
  }
  if(sign && left_sign!=right_sign)order=left_sign==V1?-1:1;
  const bool result=op==vtBLT?order<0:op==vtBGT?order>0:op==vtBLE?order<=0:order>=0;
  init_val(IS_FALSE,1);
  if(unknown) {turn_into_xz_mode();_val_x[0]=VX;}
  else _val[0]=result?1:0;
  return OK;
}

int
VeriNum::bleq  ( VeriNum *other )   // ==
{
  align_signed_bits( other );

  if( _val != NULL && other->_val != NULL )
  {
    uint8_t re = V1;
    for( int i = 0; i < _vbits; ++i )
    {
      if( _val[i] != other->_val[i] )
      {
        re = V0;
        break;
      }
    }
    delete[] _val;
    _bits  = 1;
    _vbits = 1;
    _val   = new uint32_t[1];
    _val[0] = re;
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  if( _val_x != NULL )
  {
    uint8_t re = V1;
    for( int i = 0; i < _bits; ++i )
    {
      if(    _val[i] == VX || other->_val[i] == VX
          || _val[i] == VZ || other->_val[i] == VZ )
      {
        re = VX;
        break;
      }
      if( _val[i] != other->_val[i] )
      {
        re = V0;
        break;
      }
    }
    delete[] _val_x;
    _bits  = 1;
    _vbits = 1;
    _val_x = new uint8_t[1];
    _val_x[0] = re;
  }
  return OK;
}

int
VeriNum::blieq ( VeriNum *other )   // !=
{
  int re = bleq( other );
  if( re != OK )
    return re;

  if( _val != NULL )
    _val[0] = 0x1 - _val[0];

  if( _val_x != NULL )
  {
    if( _val_x[0] == V1 )
      _val_x[0] = V0;
    else if( _val_x[0] == V0 )
      _val_x[0] = V1;
  }

  return OK;
}

int
VeriNum::bceq  ( VeriNum *other )   // ===
{
  align_signed_bits(other);
  uint32_t result=1;
  for(int bit=0;bit<_bits;++bit) {
    if(get_certain_bit(bit)!=other->get_certain_bit(bit)) {result=0;break;}
  }
  delete[] _val;delete[] _val_x;
  _val_x=NULL;_val=new uint32_t[1];_val[0]=result;
  _bits=1;_vbits=1;_no_xz=IS_TRUE;set_unsigned();
  return OK;
}

int
VeriNum::bcieq ( VeriNum *other )   // !==
{
  int re = bceq( other );
  if( re != OK )
    return re;

  if( _val != NULL )
    _val[0] = 0x1 - _val[0];

  return OK;
}

int
VeriNum::bmul  ( VeriNum *other )   // *
{
  uint8_t high_end = V0;
  uint8_t other_high_end = V0;
 
  int last_idx = _bits % INT_BIN_RATIO;
  int other_last_idx = other->_bits % INT_BIN_RATIO;

  align_signed_bits( other );

  if( other->_is_signed == IS_TRUE )
  {
    if( other->_val != NULL )
      other_high_end = other->_val[_vbits-1]
                       >> ( ( other_last_idx == 0 ? INT_BIN_RATIO : other_last_idx ) - 1 );
    if( other->_val_x != NULL )
      other_high_end = other->_val_x[_bits-1];

    if( other_high_end != V0 )
    {
      other->decrement();
      other->uneg();
    }
  }

  if( _is_signed == IS_TRUE )
  {
    if( other->_val != NULL )
      high_end  = _val[_vbits-1] >> ((last_idx == 0 ? INT_BIN_RATIO : last_idx) - 1);
    if( other->_val_x != NULL )
      high_end = _val_x[_bits-1];

    if( high_end != V0 )
    {
      decrement();
      uneg();
    }
  }
 
  if( _val != NULL && other->_val != NULL )
  {
    int new_bits = _bits << 1;
    int new_vbits = new_bits / INT_BIN_RATIO + ((new_bits%INT_BIN_RATIO) ? 1 : 0);

    uint64_t *products = new uint64_t[_vbits << 1];
    memset( products, 0, sizeof(uint64_t) * _vbits << 1 );

    int i,j;
    uint64_t p1,p2,p3,p4;
    for( i = 0; i < _vbits; ++i )
    {
      for( j = 0; j < _vbits; ++j )
      {
        p1 =   (uint64_t)(_val[j] & 0xffff)
             * (uint64_t)(other->_val[i] & 0xffff);

        p2 =   (uint64_t)(_val[j] & 0xffff)
             * (uint64_t)((other->_val[i] & 0xffff0000) >> (INT_BIN_RATIO>>1));
        p2 = p2 << (INT_BIN_RATIO>>1);

        p3 =   (uint64_t)((_val[j] & 0xffff0000) >> (INT_BIN_RATIO>>1))
             * (uint64_t)(other->_val[i] & 0xffff);
        p3 = p3 << (INT_BIN_RATIO>>1);

        p4 =   (uint64_t)((_val[j] & 0xffff0000) >> (INT_BIN_RATIO>>1))
             * (uint64_t)((other->_val[i] & 0xffff0000) >> (INT_BIN_RATIO>>1));

        products[i+j] += p1 + p2 + p3;
        products[i+j+1] += p4;
      }
    }
    uint32_t *tres = new uint32_t[new_vbits];
    memset( tres, 0, sizeof(uint32_t) * new_vbits );
    for( i = 1; i < new_vbits; ++i )
    {
      tres[i-1] = products[i-1] & 0xffffffff;
      products[i] += (products[i-1] & 0xffffffff00000000) >> INT_BIN_RATIO;
    }
    tres[i-1] = products[i-1] & 0xffffffff;
    delete[] products;
    delete[] _val;

    for( i = new_vbits; i > _vbits; --i )
    {
      if( tres[i-1] != 0x0 )
        break;
    }

    _vbits = i;
    _bits = _vbits * INT_BIN_RATIO;
    _val = new uint32_t[_vbits];

    for( i = 0; i < _vbits; ++i )
      _val[i] = tres[i];

    delete[] tres;

    if( _is_signed == IS_TRUE && high_end != V0 )
    {
      uneg();
      increment();
    }
   
    if( other->_is_signed == IS_TRUE && other_high_end != V0 )
    {
      uneg();
      increment();
    }
    return OK;
  }

  if( _val != NULL )
    turn_into_xz_mode();

  if( other->_val != NULL )
    other->turn_into_xz_mode();

  if( _val_x != NULL )
  {
    int new_bits = _bits << 1;
    int i,j;

    uint8_t **products = new uint8_t*[_bits];
    for( i = 0; i < _bits; ++i )
    {
      products[i] = new uint8_t[_bits];
      memset(products[i], 0, sizeof(uint8_t)*_bits);
    }

    for( i = 0; i < _bits; ++i )
    {
      for( j = 0; j < _bits; ++j )
        products[i][j] = bit_and( _val_x[j], other->_val_x[i] );
    }

    uint8_t *tres = new uint8_t[new_bits];
    uint8_t *carry_first = new uint8_t[new_bits-1];
    memset( tres, 0, sizeof(uint8_t) * new_bits );
    memset( carry_first, 0, sizeof(uint8_t) * (new_bits-1) );

    uint8_t carry = 0;
    for( i = 0; i < _bits - 1; ++i )
    {
      carry = 0;
      tres[i] = products[i][0];

      for( j = 1; j < _bits; ++j )
        carry = bit_add( products[i][j], products[i+1][j], carry, products[i+1][j] );
      carry_first[i] = carry;
    }
    tres[i] = products[i][0];

    carry = 0;
    for( j = 1; j < _bits; ++j )
    {
      carry = bit_add( products[i][j], carry_first[j-1], carry, products[i][j] );
      tres[i+j] = products[i][j];
    }
    tres[i+j] = carry;

    for( i = 0; i < _bits; ++i )
      delete[] products[i];
    delete[] products;
    delete[] carry_first;

    for( i = new_bits; i > _bits; --i )
    {
      if( tres[i-1] != V0 )
        break;
    }

    _bits = i;
    delete[] _val_x;
    _val_x = new uint8_t[_bits];

    for( i = 0; i < _bits; ++i )
      _val_x[i] = tres[i];

    delete[] tres;
    if( _is_signed == IS_TRUE && high_end != V0 )
    {
      uneg();
      increment();
    }
   
    if( other->_is_signed == IS_TRUE && other_high_end != V0 )
    {
      uneg();
      increment();
    }
  }
  return OK;
}

int
VeriNum::bdiv( VeriNum *other ) { return divide_modulo(other,false); }

int
VeriNum::bpow  ( VeriNum *other )   // **
{
  if( other->_val_x != NULL || _val_x != NULL )
  {
    if( _val != NULL )
      turn_into_xz_mode( );
    for( int i = 0; i < _bits; ++i )
      _val_x[i] = VX;
    return OK;
  }

  uint8_t high_end = V0;
  uint8_t other_high_end = V0;
 
  int last_idx = _bits % INT_BIN_RATIO;
  int other_last_idx = other->_bits % INT_BIN_RATIO;

  align_signed_bits( other );

  if( other->_is_signed == IS_TRUE )
  {
    if( other->_val != NULL )
      other_high_end = other->_val[_vbits-1]
                       >> ( ( other_last_idx == 0 ? INT_BIN_RATIO : other_last_idx ) - 1 );
    if( other->_val_x != NULL )
      other_high_end = other->_val_x[_bits-1];

    if( other_high_end != V0 )
    {
      other->decrement();
      other->uneg();
    }
  }

  if( _is_signed == IS_TRUE )
  {
    if( other->_val != NULL )
      high_end  = _val[_vbits-1] >> ((last_idx == 0 ? INT_BIN_RATIO : last_idx) - 1);
    if( other->_val_x != NULL )
      high_end = _val_x[_bits-1];

    if( high_end != V0 )
    {
      decrement();
      uneg();
    }
  }
 
  if( _bits < other->_bits )
    high_end_padding( other->_bits );

  if( _val != NULL && other->_val != NULL )
  {
    if( other->_vbits > 1 || _vbits > 1 )
      return vNOP_NOT_SUPPORT;

    _val[0] = (uint32_t)pow( (double)_val[0] , (double)other->_val[0] );

    if( _is_signed == IS_TRUE && high_end != V0 )
    {
      uneg();
      increment();
    }
   
    if( other->_is_signed == IS_TRUE && other_high_end != V0 )
    {
      uneg();
      increment();
    }
    return OK;
  }
  return OK;
}

int
VeriNum::bmod( VeriNum *other ) { return divide_modulo(other,true); }

}
