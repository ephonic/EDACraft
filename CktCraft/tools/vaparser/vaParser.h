#ifndef VAPARSER_H_
#define VAPARSER_H_

#include <bitset>
#include <string>
#include <vector>
#include <list>
#include <map>
#include <set>
#include <iostream>
#include <stdlib.h>

using namespace std;

#define BIT_ 32

struct source{
    int _nodenum;
    int _pos;
    int _neg;
    int _type;
};

struct attribute{
    map<string, string> _attrlist;
};

struct range{
    double _from;
    double _to;
    bool _binf;
    bool _einf;
    int _ft; //1:( 2:[
    int _tt; //1:) 2:]
    int _type; //1:include 2:exclude 3:none
};

struct parameter{
    string _name;
    double _defvalue;
    string _defexpr;   // 非纯数字默认值表达式（如 VSAT1 = VSAT），空串=纯数字
    range *_range;
    int    _type; //0 for normal parameter
                  //1 for instance parameter
    attribute *_attr;
};

struct variable{
    string _name;
    int _type; //1:int 2:real 3:string
    string _alias;
};

struct variableblock{
    map<string, bitset<BIT_> > _block;
    variableblock *_prev;
    variableblock *_next;
    variableblock *_right;
};

struct statement{
    string _describ;
    map<string, bitset<BIT_> > _var;
    map<string, int> _param;
    bool _type; //false neednot to derivate.
                //true  need to derivate.
    int  _level; //0 main loop
                 //1 sublevel loop. EX. if(){sublevel}else{sublevel} 
                 //2 ...
    int _mode;  //1:system function 2:contribution 0:mornal
};

struct TREE{
    TREE *_left;
    TREE *_right;
    string _type;
    string _name;
};

struct branch{
    int _type;
    string _pnode;
    string _nnode;
};

struct calStatement{
    list<statement> _steps;
    TREE *_tree;
};

struct terminal{
    string _name;
    int _type; //1:input 2:output 3:inout
};

struct varType{
    int _type; //1:int 2:real
    int _inout; //1:input 2:output 3:inout
};

struct analogFun{
    string _name;
    int    _type;//0:system 1:integer 2:real(double) 
    vector<terminal> _interface;
    calStatement _state;
    map<string, varType> _var;
};

struct nature{
    string _name;
    string _units;
    string _access;
    string _idt;
    string _ddt;
    double _abstol;
};

struct discipline{
    string _name;
    nature *_potential;
    nature *_flow;
    int _domain; //0: discrete, 1: continuous
};

struct net{
    string _name;
    discipline *_disp;
};

struct module{
    string _name;
    attribute *_attr;
    attribute *_attrPort;
    vector<terminal> _port;
    map<string, branch> _branchAlias;
    vector<net> _net;
    list<parameter> _param;
    list<variable> _variable;
    variableblock *_head;
    variableblock *_current;
    calStatement _main;
    list<analogFun*> _analogFun;
    map<string, int> _dervar;
    map<int, map<int, int> > _matstructrue;
    list<source*> _contribute;
    int _ddtnum;
    map<string, int> _tmpdervar;
    map<string, string> _simparamDflt;  // $simparam 名 -> 默认值表达式（codegen 发成员）
    map<string, int> _branchFlowNet;    // "pos_neg" -> 伪网络索引（V<+ 支路电流未知量）
    set<int> _branchFlowNets;           // 全部伪网络索引（codegen 回退方程用）
};

struct lexVal{
    string _str;
    string _fileName;
    int    _line;
};

struct loop{
    int _type; //1:for 2:while
    string _expression;
    list<statement> _state;
};

struct swb{
    int _type; //1:if,else 2:switch
    string _expression;
    int _num;
    vector<list<statement> > _state;
};

struct yaccVal{
    string _str;
    lexVal _lex;
    double _value;
    list<statement> _state;
    TREE *_tree;
    bitset<BIT_> _type;
    loop *_loop;
    swb *_if;
    int _num;
};

void vaMessageError(string str, lexVal* lval);
void vaMessageError(string str, yaccVal* yval);
nature* pushBackNature(list<nature*> &nl, string access);
module* pushBackModule(list<module*> &ml, string name);
bool pushBackTerminal(module* mod, const string &tername);
double string2double(const string &str);
string int2string(int i);
string double2string(double i);
int str2int(const string &str);
int GetFlowNode(int, int);
analogFun* analogFunctionNew(module* gmod, string name);
calStatement GetState(yaccVal *);
void AddFunctionVariable(analogFun*, lexVal*, int);
int AddParameter(module* gmod, string name);
int AddVariable(module* gmod, string name);
nature* IsInNature(list<nature*> nl, string name);
string ReplaceModelParam(statement &);
string ReplaceModelParam(string &, map<string, int> &);
vector<string>  ReplaceDdt(string&);
string GetDollarValue(string str);
string GetVariableName(string name);
int GetOrCreateBranchFlowNet(module*, int, int);
string ReplaceIdent(const string&, const string&, const string&);
string AfSubstNames(string, analogFun*, const map<string, string>&,
                    const vector<string>&, const string&);
string ResolveBlockLocal(const string&);
void SetVariableType(module*, string var, bitset<BIT_> type);
bitset<BIT_> GetVariableType(module*, string ident);
void NewIfVariableBlock(module *);
void NewElseVariableBlock(module *);
void MergeVariableBlock(module *);
analogFun *FindAnalogFun(module *, string);
void PushBackDerivate(string, bitset<BIT_>, list<statement>&, module*);
int veriloglex();
void verilogerror (const char *s);
int GetNameNum(module*mod, string name);
parameter* IsInParam(module*, string);
void LoadSystemFunction(list<analogFun*> &);
bool IsModuleVariable(module*, string);
std::string calculate_deriv_replace(const statement& input_state, std::set<std::string>& temp_map, vector<vector<string> >& dddts);
std::string calculate_deriv(const statement& input_state, std::set<std::string>& temp_map);
void R_interval(yaccVal *, yaccVal *, range* &, int, int);
void blockvariable(list<string> &);
void R_e_bitwise(yaccVal *, yaccVal *, yaccVal *, string);
void R_d_node(list<string>&, int, void *, bool);
void R_analogcode_tk_ident(yaccVal* &, string);

typedef map<string, bitset<BIT_> > VariableType;
string GetZeroDerivation(const string &str, bitset<BIT_> tp);
int IfBlockVariable(module *mod, VariableType &outside, VariableType &inside);
int SwitchBlockVariable(module *mod, VariableType &outside,
                        vector<VariableType> &inside, int number);

#endif
