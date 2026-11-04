#ifndef c_token_status_hpp_
#define c_token_status_hpp_

enum c_token_status{
  TOK_START    =  10000,

  DIGIT_ST1    =  10001,
  DIGIT_ST2    =  10002,
  DIGIT_ST3    =  10003,
  DIGIT_ST4    =  10004,
  DIGIT_ST5    =  10005,
  DIGIT_ST6    =  10006,
  DIGIT_ST7    =  10007,
  DIGIT_ST8    =  10008,
  DIGIT_ST9    =  10009,
  DIGIT_ST10   =  10010,

  COMM_ST      =  10015,
  COMM_ST_1    =  10016,
  COMM_ST_2    =  10017,
  COMM_ST_3    =  10018,
  COMM_ST_4    =  10019,

  P_J_ST       =  10020,
  P_J_ST_1     =  10021,
  P_J_ST_2     =  10022,
  P_J_ST_3     =  10023,
  P_J_ST_4     =  10024,

  J_ST         =  10025,
  J_ST_1       =  10026,
  J_ST_2       =  10027,
  J_ST_3       =  10028,
  J_ST_4       =  10029,

  PLUS_ST      =  10030,
  MINUS_ST     =  10038,
  STAR_ST      =  10042,
  DIV_ST       =  10046,
  MOD_ST       =  10050,
  AND_ST       =  10064,
  OR_ST        =  10068,
  XOR_ST       =  10072,
  NOT_ST       =  10076,
  TRAN_ST      =  10080,
  EQUAL_ST     =  10085,
  LESS_ST      =  10090,
  LESS_ST_1    =  10091,
  GREATER_ST   =  10095,
  GREATER_ST_1 =  10096,

  IDENT_ST     =  10100,

  DOT_ST       =  10105,
  DOT_ST_1     =  10106,
  DOT_ST_2     =  10107,

  QUOTE_ST     =  10190,
  QUOTE_ST_1   =  10191,
  SIG_QUOTE_ST =  10200,
  S_QUOTE_ST_1 =  10201,
};

enum cp_var_status{
  cparser_dec_status         =  1,
  cparser_var_status         =  2,

  cparser_enum_status        =  5,
  cparser_enum_var_status    =  6,
  cparser_union_status       = 10,
  cparser_union_var_status   = 11,
  cparser_struct_status      = 15,
  cparser_struct_var_status  = 16,
  cparser_func_status        = 20,
  cparser_func_var_status    = 21,
  cparser_func_para_var_status = 22,

  cparser_above_def          = 25,

  cparser_iteration_status   = 25,
  cparser_selection_status   = 30,
  cparser_compound_status    = 35,
};

enum cp_var_type_status{
  cstatus_VOID                =  1,
  cstatus_CHAR                =  2,
  cstatus_SHORT               =  3,
  cstatus_INT                 =  4,
  cstatus_FLOAT               =  5,
  cstatus_DOUBLE              =  6,
  cstatus_BOOL                =  8,

  cstatus_SIGNED              = 9,
  cstatus_UNSIGNED            = 10,
  cstatus_UCHAR               = 11,
  cstatus_USHORT              = 12,
  cstatus_UINT                = 13,
  cstatus_ULONG               = 14,
  cstatus_ULONGLONG           = 15,

  cstatus_LONG                = 16,
  cstatus_LONGLONG            = 17,
  cstatus_LDOUBLE             = 18,

  cstatus_ENUM                = 19,
  cstatus_UNION               = 20,
  cstatus_STRUCT              = 21,

  cstatus_CHAR_STAR           = 30,
  cstatus_SHORT_STAR          = 31,
  cstatus_INT_STAR            = 32,
  cstatus_FLOAT_STAR          = 33,
  cstatus_DOUBLE_STAR         = 34,
  cstatus_BOOL_STAR           = 36,

  cstatus_UCHAR_STAR          = 37,
  cstatus_USHORT_STAR         = 38,
  cstatus_UINT_STAR           = 39,
  cstatus_ULONG_STAR          = 40,
  cstatus_ULONGLONG_STAR      = 41,

  cstatus_LONG_STAR           = 42,
  cstatus_LONGLONG_STAR       = 43,
  cstatus_LDOUBLE_STAR        = 44,

  cstatus_ENUM_STAR           = 45,
  cstatus_UNION_STAR          = 46,
  cstatus_STRUCT_STAR         = 47,
};
#endif
