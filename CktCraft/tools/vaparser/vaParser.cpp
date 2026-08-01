#include <stdio.h>
#include <time.h>
#include <fstream>
#include <sstream>
#include <algorithm>
#include "preparser.h"
#include "vaParser.h"
#include "vaYacc.hpp"
#include "xyce_vcomp.h"
#include "rfsim_codegen.h"
using namespace std;

map<string, string> __DollarValue;
int __variableID = 0;
extern FILE* verilogin;
extern int verilogparse();
extern module* gModule;

string GetTempFile()
{
  time_t curTime;
  time(&curTime);
  string tmp = int2string(int(curTime));
  tmp = "vaTemp" + tmp + ".va";
  return tmp;
}

double string2double(const string &str)
{
  istringstream iss(str);
  double tmp;
  if(!(iss>>tmp)){
    exit(-1);
  }
  return tmp;
}

int str2int(const string &str)
{
  istringstream iss(str);
  int tmp;
  if(!(iss>>tmp)){
    exit(-1);
  }
  return tmp;
}

string int2string(int i)
{
  char _int[20];
  sprintf(_int, "%d", i);
  return _int;
}

string double2string(double i)
{
  char _double[20];
  sprintf(_double, "%g", i);
  return _double;
}

analogFun* analogFunctionNew(module* gmod, string name)
{
  list<analogFun*>::iterator iter = (gmod->_analogFun).begin();
  while(iter != (gmod->_analogFun).end()){
    if((*iter)->_name == name) return 0;
    ++iter;
  }
  analogFun *tmp = new analogFun;
  tmp->_name = name;
  tmp->_type = 2;
  gmod->_analogFun.push_back(tmp);
  return tmp;
}

nature* IsInNature(list<nature*> nl, string name)
{
  list<nature*>::iterator iter;
  iter = nl.begin();
  while(iter != nl.end()){
    if((*iter)->_access == name)return *iter;
    ++iter;
  }
  return NULL;
}

void SetDollarValue()
{
  // rfsim 生成模型：温度经 DeviceModel::setTemperature 注入 temp_ 成员
  // （默认 300.15K，与 OsdiModel 一致）。$vt = k*T/q，常量对齐 HSPICE/FineSim
  // KboQ = P_K/P_Q = 8.617087e-5（与 BSIMCMG common_defs.include 一致）。
  __DollarValue["$vt"] = "(1.38062E-23 * temp_ / 1.60219E-19)";
  __DollarValue["$temperature"] = "temp_";
}

string GetDollarValue(string str)
{
  return __DollarValue[str];
}

string GetVariableName(string name)
{
  ++__variableID;
  string tmp;
  tmp = "_id" + int2string(__variableID);
  return tmp;
}

void NewIfVariableBlock(module *mod)
{
  variableblock *tmp = new variableblock;

  mod->_current->_next = tmp;
  tmp->_prev = mod->_current;
  tmp->_next = NULL;
  tmp->_right = NULL;
  mod->_current = tmp;
}

void NewElseVariableBlock(module *mod)
{
  variableblock *tmp = new variableblock;
  tmp->_prev = mod->_current->_prev;
  mod->_current->_right = tmp;
  tmp->_next = NULL;
  tmp->_right = NULL;
  mod->_current = tmp;
}

void PushBackDerivate(string str, bitset<BIT_> type, list<statement> &sl, module* mod)
{
  int i=0;
  statement mystat;
  mystat._mode = 4;
  if(type == 0) return;
  for(i=0; i<mod->_net.size(); ++i){
    if(type[i] == 1) {
      mystat._describ = "d" + str + "Dv" + int2string(i) + " = 0;";
      sl.push_back(mystat);
    }
  }
  return;
}

void vaMessageError(string str, lexVal* lval)
{
  std::cerr<<"Error at file: "<<lval->_fileName<<": line: "<<lval->_line<<": "<<str;
  exit(1);
}
void vaMessageError(string str, yaccVal* yval)
{
  std::cerr<<"Error at file: "<<yval->_lex._fileName<<": line: "<<yval->_lex._line<<": "<<str;
  exit(1);
}
nature* pushBackNature(list<nature*> &nl, string access)
{
  list<nature*>::iterator iter;
  iter = nl.begin();
  while(iter != nl.end()){
    if( (*iter)->_access == access){
      std::cerr<<"Warning: Redefinition of nature attribute 'access' : name : "
        <<access<<endl;
    }
    ++iter;
  }
  nature *tmp = new nature;
  tmp->_access = access;
  nl.push_back(tmp);
  return tmp;
}

module* pushBackModule(list<module*> &ml, string name)
{
  list<module*>::iterator iter;
  iter = ml.begin();
  while(iter != ml.end()){
    if((*iter)->_name == name){
      std::cerr<<"Error: Redefinition of module with name : "
        <<name<<endl;
    }
    ++iter;
  }
  module *tmp = new module;
  tmp->_name = name;
  tmp->_attr = NULL;
  ml.push_back(tmp);
  return tmp;
}

bool pushBackTerminal(module* mod, const string &tername)
{
  vector<terminal>::iterator iter;
  iter = (mod->_port).begin();
  while(iter != (mod->_port).end()){
    if(iter->_name == tername) return false;
    ++iter;
  }
  terminal myterm;
  myterm._name = tername;
  (mod->_port).push_back(myterm);
  return true;
}

void verilogerror (const char *s)
{
  extern int __curLine;
  extern std::string __curFile;
  extern char* verilogtext;  // current token text from yacc
  cerr<<s<<" at line "<<__curLine<<" in "<<__curFile;
  if (verilogtext) cerr<<" near token: "<<verilogtext;
  cerr<<endl;
}

void AddFunctionVariable(analogFun* af, lexVal* lv, int i)
{
  // i: 1=input 2=output 3=inout。记录形参名（内联展开时按位置替换）
  // 并登记到 af->_var（函数体内标识符解析用）。
  terminal t;
  t._name = lv->_str;
  t._type = i;
  af->_interface.push_back(t);
  varType vt;
  vt._type = 2;  // real
  vt._inout = i;
  af->_var[lv->_str] = vt;
}

int AddParameter(module* gmod, string name)
{
  list<parameter>::iterator iter = gmod->_param.begin();
  while(iter != gmod->_param.end()){
    if(iter->_name == name) return 0;
    ++iter;
  }
  if(iter == gmod->_param.end())
    return 1;
  return 0;
}

int AddVariable(module* gmod, string name)
{
  variable myvar;
  myvar._name = name;
  gmod->_variable.push_back(myvar);

  return 1;
}

void SetVariableType(module* mod, string name, bitset<BIT_> type)
{
  //if(type == 0 && mod->_current->_block.find(name) == mod->_current->_block.end()) return;
  mod->_current->_block[name] = type;
}

bitset<BIT_> GetVariableType(module* mod, string name)
{
  variableblock *vrb = mod->_current;
  while(vrb != mod->_head){
    if(vrb->_block.find(name) != vrb->_block.end())
      return vrb->_block[name];
    vrb = vrb->_prev;
  }
  return mod->_head->_block[name];
  return bitset<BIT_>(0);
}

int GetNameNum(module*mod, string name)
{
  int i;
  for(i=0; i<mod->_net.size(); ++i)
  {
    if(mod->_net[i]._name == name) return i;
  }
  return -1;
}

parameter* IsInParam(module* mod, string name)
{
  list<parameter>::iterator iter = mod->_param.begin();
  while(iter != mod->_param.end()){
    if(iter->_name == name) return &(*iter);
    ++iter;
  }
  return NULL;
}

bool IsModuleVariable(module* mod, string name)
{
  list<variable>::iterator iter = mod->_variable.begin();
  while(iter != mod->_variable.end()){
    if(iter->_name == name) return true;
    ++iter;
  }
  return false;
}

analogFun *FindAnalogFun(module *mod, string name)
{
  list<analogFun*>::iterator iter;
  iter = mod->_analogFun.begin();
  while(iter != mod->_analogFun.end()){
    if((*iter)->_name == name) return *iter;
    ++iter;
  }
  return NULL;
}

void LoadSystemFunction(list<analogFun*> &anaf)
{
  analogFun *tmp;
  string sfname[] = {"sqrt", "exp", "ln", "log", "ddt", "ddx", "white_noise",
		     "max", "min", "abs", "pow", "flicker_noise", "atan",
		     "tanh", "sinh", "cosh", "sin", "cos", "tan",
		     "asin", "acos", "floor", "ceil", "hypot", "atan2",
		     "sign", "fact", "limexp",
		     // BSIM3/BSIMSOI/BJT 紧凑模型所需的 Verilog-A 系统函数
		     // 注意：exp_lim/lln 是模型内自定义的 analog function，不是系统函数
		     "analysis", "param_given",
		     "port_connected", "ac_stim", "transition", "slew",
		     "last_crossing", "timer", "above", "cross"};
  for(int i=0; i < sizeof(sfname)/sizeof(string); ++i){
    tmp = new analogFun;
    tmp->_name = sfname[i];
    tmp->_type = 0;
    anaf.push_back(tmp);
  }
}

int GetFlowNode(int p, int n)
{
  // impl here
  return 0;
}

// V(a,b) <+ expr 解糖用的伪网络（支路电流未知量，MNA 附加行）。
// 同一 (pos,neg) 只建一次；I(a,b) 读取与 V<+ 贡献共享。
int GetOrCreateBranchFlowNet(module* mod, int pos, int neg)
{
  // neg=-1（地）用 "g" 代替，避免标识符出现负号
  string key = int2string(pos) + "_" + (neg >= 0 ? int2string(neg) : string("g"));
  map<string, int>::iterator it = mod->_branchFlowNet.find(key);
  if (it != mod->_branchFlowNet.end()) return it->second;
  net brnet;
  brnet._name = "_br" + key;  // 无 $ 字符：deriv 词法不接受 $
  brnet._disp = (pos >= 0 && pos < (int)mod->_net.size()) ? mod->_net[pos]._disp : NULL;
  mod->_net.push_back(brnet);
  int idx = (int)mod->_net.size() - 1;
  mod->_branchFlowNet[key] = idx;
  mod->_branchFlowNets.insert(idx);
  return idx;
}

int IsIdentChar(char c)
{
  if(c >= '0' && c <= '9') return 2;
  if((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_') return 1;
  return 0;
}

// 标识符边界匹配的全词替换（analog function 内联用）
string ReplaceIdent(const string& src, const string& from, const string& to)
{
  if(from.empty()) return src;
  string out = src;
  size_t pos = 0;
  while((pos = out.find(from, pos)) != string::npos){
    bool leftOK = (pos == 0) || (IsIdentChar(out[pos-1]) == 0);
    size_t e = pos + from.size();
    bool rightOK = (e >= out.size()) || (IsIdentChar(out[e]) == 0);
    if(leftOK && rightOK){
      out.replace(pos, from.size(), to);
      pos += to.size();
    } else {
      pos += from.size();
    }
  }
  return out;
}

// analog function 内联的名称替换：形参→(实参)、局部→加后缀、函数名→返回变量
string AfSubstNames(string s, analogFun* af,
                    const map<string, string>& lrename,
                    const vector<string>& argDesc,
                    const string& retVar)
{
  for(size_t f = 0; f < af->_interface.size() && f < argDesc.size(); ++f)
    s = ReplaceIdent(s, af->_interface[f]._name, "(" + argDesc[f] + ")");
  for(map<string, string>::const_iterator r = lrename.begin(); r != lrename.end(); ++r)
    s = ReplaceIdent(s, r->first, r->second);
  s = ReplaceIdent(s, af->_name, retVar);
  return s;
}

// 命名块 begin : name 的局部变量解析：内层块遮蔽外层。
// 非块局部变量返回空串。
extern vector<map<string,string> > gBlockLocalStack;
string ResolveBlockLocal(const string& name)
{
  for (auto bit = gBlockLocalStack.rbegin(); bit != gBlockLocalStack.rend(); ++bit) {
    auto f = bit->find(name);
    if (f != bit->end()) return f->second;
  }
  return string();
}

vector<string> ReplaceDdt(string& str)
{
  size_t pos;
  size_t len;
  vector<string> ret;

  while((pos = str.find("DdtAns")) != string::npos)
    {
      len = 6;
      while(pos+len < str.length())
	{
	  if(str[pos+len] > '9' || str[pos+len] < '0')
	    break;

	  ++len;
	}
      ret.push_back(str.substr(pos, len));
      str.replace(pos, len, "0.0");      
    }

  return ret;
}



string ReplaceModelParam(statement &stat)
{
  string tmp, tmpname;
  int pos, ans;
  if(stat._param.size() == 0) return stat._describ;
  tmp = stat._describ;
  map<string, int>::iterator piter;
  piter = stat._param.begin();
  while(piter != stat._param.end()){
    pos = 0;
    ans = tmp.find(piter->first, pos);
    while(ans != -1){
      if((ans == 0 || IsIdentChar(tmp[ans-1]) == 0) && (IsIdentChar(tmp[ans + piter->first.size()]) == 0)){
        tmpname = piter->first;
	//        transform(tmpname.begin(), tmpname.end(), tmpname.begin(), ::tolower);
        if(piter->second == 0){
          tmp = tmp.substr(0, ans) + "model_." + tmpname + tmp.substr(ans + piter->first.size());
          pos = ans + piter->first.size() + 7;
        } else {
          tmp = tmp.substr(0, ans) +  tmpname  + tmp.substr(ans +piter->first .size());
          pos = ans + piter->first.size();
        }
      } else {
        pos = ans + piter->first.size();
      }
      ans = tmp.find(piter->first, pos);
    }
    ++piter;
  }
  return tmp;
}

string ReplaceModelParam(string& str, map<string, int>& param)
{
  string tmp, tmpname;
  int pos, ans;
  if(param.size() == 0) return str;
  tmp = str;
  map<string, int>::iterator piter;
  piter = param.begin();
  while(piter != param.end()){
    pos = 0;
    ans = tmp.find(piter->first, pos);
    while(ans != -1){
      if((ans == 0 || IsIdentChar(tmp[ans-1]) == 0) && (IsIdentChar(tmp[ans + piter->first.size()]) == 0)){
        tmpname = piter->first;
	//        transform(tmpname.begin(), tmpname.end(), tmpname.begin(), ::tolower);
        if(piter->second == 0){
          tmp = tmp.substr(0, ans) + "model_." + tmpname + tmp.substr(ans + piter->first.size());
          pos = ans + piter->first.size() + 7;
        } else {
          tmp = tmp.substr(0, ans) + tmpname  + tmp.substr(ans +piter->first .size());
          pos = ans + piter->first.size();
        }
      } else {
        pos = ans + piter->first.size();
      }
      ans = tmp.find(piter->first, pos);
    }
    ++piter;
  }
  return tmp;
}

void R_interval(yaccVal *s2, yaccVal *s4, range* &gRange, int ft, int tt)
{
  gRange = new range;
  if(s2->_str == "inf") gRange->_binf = true;
  else{ gRange->_from = s2->_value; gRange->_binf = false; }
  if(s4->_str == "inf") gRange->_einf = true;
  else{ gRange->_to = s4->_value; gRange->_einf = false; }
  gRange->_ft = ft;
  gRange->_tt = tt;

}

extern analogFun *gAnalogfunction;
extern vector<string> gBlockNameStack;
extern vector<map<string,string> > gBlockLocalStack;
extern int gBlockMangleCounter;

void blockvariable(list<string> &gVariableList)
{
  // analog function 局部变量已由 R_l_analogfunction_*_variable 登记到
  // af->_var（函数作用域）；不再并入模块变量（跨函数重名会重复声明，
  // 如 BSIM-CMG 5 个 analog function 的同名局部 delta/y）。
  if (gAnalogfunction) return;
  variable myvar;
  list<string>::iterator iter = gVariableList.begin();
  while(iter != gVariableList.end()){
    string vname = *iter;
    if (!gBlockNameStack.empty()) {
      // 命名块局部变量：唯一化命名（同名块在多个 case 分支重复出现）
      vname = vname + "__b" + int2string(gBlockMangleCounter++);
      gBlockLocalStack.back()[*iter] = vname;
    }
    myvar._name = vname;
    myvar._type = 1;
    gModule->_variable.push_back(myvar);
    ++iter;
  }
}

void R_e_bitwise(yaccVal * des, yaccVal *s1, yaccVal *s2, string sz)
{
  des = s1;
  statement &tmp = (des->_state).front();
  statement &tmp1 = (s2->_state).front();
  if(sz == "%")
    tmp._describ = "int(" + tmp._describ + ")%" + tmp1._describ;
  else
    tmp._describ += sz + tmp1._describ;
  des->_type = s1->_type | s2->_type;
  map<string, bitset<BIT_> >::iterator iter;
  iter = tmp1._var.begin();
  while(iter != tmp1._var.end()){
    tmp._var[iter->first] = iter->second;
    ++iter;
  }
  map<string, int>::iterator pit;
  pit = tmp1._param.begin();
  while(pit != tmp1._param.end()){
    tmp._param[pit->first] = pit->second;
    ++pit;
  }
  delete s2;
}

void R_d_node(list<string> &gNodeList,int gNodeDirection, void *s1, bool flag)
{
  int i;
  list<string>::iterator iter = gNodeList.begin();
  while(iter != gNodeList.end()){
    for(i=0; i<gModule->_port.size(); ++i){
      if(gModule->_port[i]._name == *iter)
        if(gModule->_port[i]._type == 0){
          gModule->_port[i]._type = gNodeDirection;
          break;
        }
        else
          if(flag)
            vaMessageError("Redefine of terminal type.", (yaccVal*)s1);
          else
            vaMessageError("Redefine of terminal type.", (lexVal*)s1);
    }
    if(i == gModule->_port.size()){
      string str = "name:" + *iter + " is not a terminal name.";
      if(flag)
        vaMessageError(str, (yaccVal*)s1);
      else
        vaMessageError(str, (lexVal*)s1);
    }
    ++iter;
  }
  gNodeList.clear();
}

void R_analogcode_tk_ident(yaccVal* &des, string sz)
{
  statement mystat;
  mystat._describ = sz;
  mystat._mode = 5;
  des = new yaccVal;
  (des->_state).push_back(mystat);
}


extern int verilogdebug;
extern int    __curLine;
extern int    __curPos;
#ifndef SKIP_MAIN
int main(int argc, char *argv[])
{
  __curLine = 0;
  __curPos  = 0;
  // 支持: vaParser <vafile> <outputname> [--format=xyce|rfsim]
  if(argc < 3){
    printf("Usage: %s <vafile> <outputname> [--format=xyce|rfsim]\n", argv[0]);
    exit(0);
  }
  bool useRfsimFormat = false;
  for (int i = 3; i < argc; ++i) {
    string arg = argv[i];
    if (arg == "--format=rfsim") useRfsimFormat = true;
  }

  string vatempname = GetTempFile();
  preparser(2, argv, vatempname);
  FILE* ivafile = fopen(vatempname.c_str(), "r");
  if(!ivafile){
    printf("Error : File %s cannot open for read.", "myvaparsertmp.va");
  }
  verilogin = ivafile;
  SetDollarValue();
  (int) verilogparse();
  if (!getenv("VA_KEEP_TEMP")) remove(vatempname.c_str());

  if (useRfsimFormat) {
    printf("Generating rfsim DeviceModel format...\n");
    try {
      RfsimGenerateHeader(gModule, argv[2]);
      RfsimGenerateSource(gModule, argv[2]);
      RfsimGenerateRegSnippet(gModule, argv[2]);
    } catch (const std::exception& e) {
      fprintf(stderr, "[vaParser] codegen exception: %s\n", e.what());
      exit(3);
    }
  } else {
    GenerateHeader(gModule, argv[2]);
    GenearteCCode(gModule, argv[2]);
  }
  printf("Temp file name :%s.\n", vatempname.c_str());
}
#endif // SKIP_MAIN
