#include "derivation.h"

extern int derivdebug;
using std::map;
using std::string;
using std::bitset;
using std::set;

int   __derindex;
int   string_len;
char* string_ptr;
string __derivResult;
string __selfResult;
map<string, bitset<BIT_> > __varmap;

bool VarCheckDependence(const char* var, int index)
{
  return (__varmap[var])[index] == 1;
}

const char *mathFun[] =
{
  "Fun:sin(x)",             "cos(x)",
  "Fun:cos(x)",             "-sin(x)",
  "Fun:exp(x)",             "exp(x)",
  "Fun:log(x)",             "1/(x)",
  "Fun:log10(x)",           "log(10)/(x)",
  "Fun:tan(x)",             "(1+tan(x)*tan(x))",
  "Fun:asin(x)",            "1/sqrt(1-x*x)",
  "Fun:acos(x)",            "-1/sqrt(1-x*x)",
  "Fun:atan(x)",            "1/(1+x*x)",
  "Fun:asinh(x)",           "1/sqrt(1+x*x)",
  "Fun:acosh(x)",           "1/(sqrt(1+x)*sqrt(1-x))",
  "Fun:atanh(x)",           "1/(1-x*x)",
  "Fun:sinh(x)",            "cosh(x)",
  "Fun:cosh(x)",            "sinh(x)",
  "Fun:tanh(x)",            "(1-tanh(x)*tanh(x))",
  "Fun:sqrt(x)",            "1/(2*sqrt(x))",
  "Fun:abs(x)",             "((x>=0.0)?1:-1)",
  "Fun:fabs(x)",            "((x>=0.0)?1:-1)",
  "Fun:pow(x, y)",          "pow(x, y-1)*y*D(x)", // "pow(x,y-1)*y*D(x) + pow(x,y)*log(x)*D(y)"
  "Fun:max(x, y)",          "((x>y)?D(x):D(y))",
  "Fun:min(x, y)",          "((x<y)?D(x):D(y))",
  "Fun:hypot(x, y)",        "(x*D(x)+y*D(y))/sqrt(x*x+y*y)",
  "Fun:atan2(x, y)",        "(y*D(x)-x*D(y))/(x*x+y*y)",
  "END"
};

const char *mathFunOpt[] =
{
  "Fun:sin(x)",             "cos(x)",                           "",                 "",
  "Fun:cos(x)",             "-sin(x)",                          "",                 "",
  "Fun:exp(x)",             "TMP",                              "TMP = exp(x)",     "TMP",
  "Fun:log(x)",             "1/(x)",                            "",                 "",
  "Fun:log10(x)",           "log(10)/(x)",                      "",                 "",
  "Fun:tan(x)",             "(1+TMP*TMP)",                      "TMP = tan(x)",     "TMP",
  "Fun:asin(x)",            "1/sqrt(1-x*x)",                    "",                 "",
  "Fun:acos(x)",            "-1/sqrt(1-x*x)",                   "",                 "",
  "Fun:atan(x)",            "1/(1+x*x)",                        "",                 "",
  "Fun:asinh(x)",           "1/sqrt(1+x*x)",                    "",                 "",
  "Fun:acosh(x)",           "1/(sqrt(1+x)*sqrt(1-x))",          "",                 "",
  "Fun:atanh(x)",           "1/(1-x*x)",                        "",                 "",
  "Fun:sinh(x)",            "cosh(x)",                          "",                 "",
  "Fun:cosh(x)",            "sinh(x)",                          "",                 "",
  "Fun:tanh(x)",            "(1-TMP*TMP)",                      "TMP = tanh(x)",    "TMP",
  "Fun:sqrt(x)",            "1/(2*TMP)",                        "TMP = sqrt(x)",    "TMP",
  "Fun:abs(x)",             "(x>=0.0)?1:-1",                    "",                 "",
  "Fun:pow(x, y)",          "pow(x, y-1)*y",                    "",                 "",
  "Fun:max(x, y)",          "((x>y)?D(x):D(y))",                "",                 "",
  "Fun:min(x, y)",          "((x<y)?D(x):D(y))",                "",                 "",
  "Fun:hypot(x, y)",        "(x*D(x)+y*D(y))/sqrt(x*x+y*y)",    "",                 "",
  "Fun:atan2(x, y)",        "(y*D(x)-x*D(y))/(x*x+y*y)",        "",                 "",
  "END"
};

int CompareFunction(const char* fun, const char* fname)
{
  int max;
  int index = 4;
  while(*(fun+index) != '(') ++index;
  index -= 4;
  max = index > strlen(fname) ? index : strlen(fname);
  if(strncmp(fun+4, fname, max) == 0)
    return 0;
  return 1;
}

int GetIndexInmathFun(const char* fname)
{
  int index = 0;
  while(mathFun[index][0] == 'F'){
    if(CompareFunction(mathFun[index], fname) == 0)
      return index;
    index += 2;
  }
  return -1;
}

static bool IsIdentChar(char c)
{
  if(c == '_' || (c >= '0' && c <= '9') ||
     (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))
    return true;
  return false;
}

char* ReplaceOne(const char* tplt, const char* self, const char* der)
{
  int i=0, j=0;
  char *ans = (char*)malloc(strlen(tplt) + strlen(self) * 4 + strlen(der));
  while(tplt[i] != '\0'){
    if(tplt[i] != 'x'){
      ans[j] = tplt[i];
      ++j; ++i;
    } else {
      if(!IsIdentChar(tplt[i-1]) && !IsIdentChar(tplt[i+1])){
          memcpy(ans+j, self, strlen(self));
          j += strlen(self);
        ++i;
      } else {
        ans[j] = tplt[i];
        ++i; ++j;
      }
    }
  }
  ans[j++] = '*';
  ans[j++] = '(';
  memcpy(ans+j, der, strlen(der));
  j += strlen(der);
  ans[j++] = ')';
  ans[j] = 0;
  return ans;
}

int FindCharinString(const char* str, char target)
{
  int i = 0;
  while(str[i] != 0){
    if(str[i] == target) return i;
    ++i;
  }
  return -1;
}

char* ReplaceTwo(const char* tplt, const char* self, const char* der)
{
  char* ans = (char*) malloc(strlen(tplt) + 4*strlen(self) + 2*strlen(der));
  int si, di, i=0, j=0;
  int tmp;
  si = FindCharinString(self, ',');
  di = FindCharinString(der,  ',');
  // First Replace the D(x) and D(y) ...
  while(tplt[i] != '\0'){
    if(tplt[i] == 'D' && !IsIdentChar(tplt[i-1]) &&
      tplt[i+1] == '(' && tplt[i+3] == ')'){
      if(tplt[i+2] == 'x') {
        memcpy(ans+j, der, di);
        j += di;
        i += 4;
      } else if(tplt[i+2] == 'y') {
        tmp = strlen(der)-di-1;
        memcpy(ans+j, der+di+1, tmp);
        j += tmp;
        i += 4;
      }
      ans[j++] = tplt[i++];
  // Replace the 'x' and 'y' second
    } else if (tplt[i] == 'x') {
      if(!IsIdentChar(tplt[i-1]) && !IsIdentChar(tplt[i+1])){
          memcpy(ans+j, self, si);
          j += si;
        ++i;
      } else {
        ans[j++] = tplt[i++];
      }
    } else if (tplt[i] == 'y') {
      if(!IsIdentChar(tplt[i-1]) && !IsIdentChar(tplt[i+1])){
        tmp = strlen(self)-si-1;
          memcpy(ans+j, self+si+1, tmp);
          j += tmp;
        ++i;
      } else {
        ans[j++] = tplt[i++];
      }
  /// Copy to ans.
    } else {
      ans[j++] = tplt[i++];
    }
  }
  ans[j] = 0;
  return ans;
}

char* GetDerivFunction(const char* fname, const char* self,
                       const char* deriv, int expnum)
{
  int index = GetIndexInmathFun(fname);
  char *ans = NULL;
  if(index < 0){
    printf("Function %s is not Defined yet.\n", fname);
    return NULL;
  }
  //if(GetParameterNum(index) != expnum)
  //  derivError("Function %s take the wrong number of parameter.\n", fname);

  if(expnum == 1){
    if(GetType(deriv) == 0){
      asprintf(&ans, "0");
      return ans;
    }
    ans = ReplaceOne(mathFun[index+1], self, deriv);
  } else if(expnum == 2) {
    ans = ReplaceTwo(mathFun[index+1], self, deriv);
  }
  return ans;
}

int GetType(const char* str)
{
  if(strcmp(str, "0") == 0) return 0;
  else if(strcmp(str, "0.0") == 0) return 0;
  else if(strcmp(str, "-0") == 0) return 0;
  else if(strcmp(str, "(0)") == 0) return 0;
  else if(strcmp(str, "1") == 0) return 1;
  else if(strcmp(str, "(1)") == 0) return 1;
  else return -1;
}

char* GetExprAns(const char type, const char* first, const char* second)
{
  char *ans;
  int first_type, second_type;
  first_type = GetType(first);
  second_type = GetType(second);
  switch(type)
  {
  case '+':
    if(first_type == 0) asprintf(&ans, "%s", second);
    else if(second_type == 0) asprintf(&ans, "%s", first);
    else asprintf(&ans, "(%s+%s)", first, second);
    break;

  case '-':
    if(second_type == 0) asprintf(&ans, "%s", first);
    else if(first_type == 0) asprintf(&ans, "(-%s)", second);
    else asprintf(&ans, "(%s-%s)", first, second);
    break;

  case '*':
    if(second_type == 0 || first_type == 0) asprintf(&ans, "0");
    else if(first_type == 1) asprintf(&ans, "%s", second);
    else if(second_type == 1) asprintf(&ans, "%s", first);
    else asprintf(&ans, "%s*%s", first, second);
    break;

  case '/':
    if(first_type == 0) asprintf(&ans, "0");
    else if(second_type == 1) asprintf(&ans, "%s", first);
    else asprintf(&ans, "%s/(%s)", first, second);
    break;

  default:
    fprintf(stderr, "The Operator Type %c CAN NOT to be implement.\n", type);
    exit(-1);
  }
  return ans;
}

void derivError(const char* fmt, ...)
{
  va_list vp;
  va_start(vp, fmt);
  vfprintf(stderr, fmt, vp);
  va_end(vp);
  exit(1);
}

bool CheckAtomic(const char* expr)
{
  int len = strlen(expr);
  if(expr[0] == '(' && expr[len-1] == ')') return true;
  return false;
}

vector<string> ReplaceDdtDeriv(string& str)
{
  size_t pos1;
  size_t pos2;
  size_t len;
  vector<string> ret;

  while((pos1 = str.find("dDdtAns")) != string::npos)
    {
      pos2 = str.find("Dv", pos1);
      len = pos2 - pos1 + 2;
      while(pos1+len < str.length())
	{
	  if(str[pos1+len] > '9' || str[pos1+len] < '0')
	    break;

	  ++len;
	}
      ret.push_back(str.substr(pos1, len));
      str.replace(pos1, len, "0.0");      
    }

  return ret;
}


string calculate_deriv(const statement& input, set<string>& optvar)
{
  derivdebug = 0;
  if(input._type == false) return input._describ;
  map<string, bitset<BIT_> >::const_iterator iter;
  bitset<BIT_> total;
  iter = input._var.begin();
  while(iter != input._var.end()){
    total |= iter->second;
    ++iter;
  }
  __varmap = input._var;
  string derivString;
  string origenString;

  /// start actuality derivation calculate.
  __derindex = 0;
  while(__derindex < BIT_){
    if(total[__derindex] == 1){
      string_ptr = (char*)input._describ.c_str();
      string_len = input._describ.size();
      static bool dbg = getenv("DERIV_DEBUG") != NULL;
      if(dbg) fprintf(stderr, "[deriv] idx=%d: %s\n", __derindex, input._describ.c_str());
      int ans = derivparse();
      if(ans != 0) {
        fprintf(stderr, "[deriv FAILED] idx=%d: %s\n", __derindex, input._describ.c_str());
        printf("We met an Error .\n");
      }
      derivString += __derivResult + ";\n    ";
      if(origenString.empty()) origenString = __selfResult;
    }
    ++__derindex;
  }

  return derivString + origenString + ";\n";
}

string calculate_deriv_replace(const statement& input, set<string>& optvar, vector<vector<string> >& dddts)
{
  derivdebug = 0;
  if(input._type == false) return input._describ;
  map<string, bitset<BIT_> >::const_iterator iter;
  bitset<BIT_> total;
  iter = input._var.begin();
  while(iter != input._var.end()){
    total |= iter->second;
    ++iter;
  }
  __varmap = input._var;
  string derivString;
  string origenString;

  /// start actuality derivation calculate.
  __derindex = 0;
  while(__derindex < BIT_){
    if(total[__derindex] == 1){
      string_ptr = (char*)input._describ.c_str();
      string_len = input._describ.size();
      int ans = derivparse();
      if(ans != 0) {
        printf("We met an Error .\n");
      }
      dddts[__derindex] = ReplaceDdtDeriv(__derivResult);
      derivString += __derivResult + ";\n    ";
      if(origenString.empty()) origenString = __selfResult;
    }
    ++__derindex;
  }

  return derivString + origenString + ";\n";
}

#ifdef UNIT_test
int main()
{
  printf("Ans: %s\n", GetDerivFunction("tan", "c*d+e", "d*dcDv1+deDv1", 1));
  printf("Ans2: %s\n", GetDerivFunction("atan2", "c, d", "dcDv1, ddDv1", 2));
}
#endif
