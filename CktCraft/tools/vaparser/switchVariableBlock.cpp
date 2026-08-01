#include "vaParser.h"
#include "vaYacc.hpp"
using namespace std;

typedef map<string, bitset<BIT_> > VariableType;

string GetZeroDerivation(const string& str, bitset<BIT_> tp)
{
  string tmp;
  int i=0, flag = 0;
  if(tp != 0) flag = 1;
  while(tp != 0){
    if(tp[0] == 1) tmp += "d" + str + "Dv" + int2string(i) + " = ";
    tp = tp >> 1;
    ++i;
  }
  tmp += "0.0;";
  if(flag) return tmp;
  else return "";
}

int IfBlockVariable(module* mod, VariableType &outside,
                    VariableType &inside)
{
  variableblock *curblock, *parblock;
  curblock = mod->_current;
  parblock = curblock->_prev;
  VariableType::iterator iter = curblock->_block.begin();
  while(iter != curblock->_block.end()){
    bitset<BIT_> tmp;
    bitset<BIT_> tmp1 = parblock->_block[iter->first];
    tmp = (tmp1 & iter->second) ^ iter->second;
    if(tmp != 0){
      outside[iter->first] = tmp;
    }
    tmp = (tmp1 & iter->second) ^ tmp1;
    if(tmp != 0){
      inside[iter->first] = tmp;
    }
    parblock->_block[iter->first] =
      parblock->_block[iter->first] | iter->second;
    ++iter;
  }
  parblock->_next = NULL;
  delete curblock;
  mod->_current = parblock;
  return 1;
}

int SwitchBlockVariable(module* mod, VariableType &outside,
                        vector<VariableType> &inside, int num)
{
  if(num < 2) return 0;
  inside.resize(num);
  variableblock **curblock, *parblock;
  curblock = new variableblock*[num];
  parblock = mod->_current->_prev;
  int i=1;
  curblock[0] = parblock->_next;
  while(i<num){
    curblock[i] = curblock[i-1]->_right;
    ++i;
  }

  bitset<BIT_> tmp, tmp1;
  VariableType &par = parblock->_block;

  /// first get the total switch block variable map
  /// Find the variable in all block by the way.
  VariableType total;
  map<string, int> varinall;
  VariableType::iterator iter;
  for(i=0; i<num; ++i){
    if(curblock[i] == NULL) continue;
    iter = curblock[i]->_block.begin();
    while(iter != curblock[i]->_block.end()){
      total[iter->first] = total[iter->first] | iter->second;
      varinall[iter->first] = varinall[iter->first] + 1;
      ++iter;
    }
  }
  /// Get the inside variable map pre block.
  for(i=0; i<num; ++i){
    if(curblock[i] == NULL) continue;
    iter = curblock[i]->_block.begin();
    while(iter != curblock[i]->_block.end()){
      if(varinall[iter->first] == num){
        tmp1 = total[iter->first];
        tmp = (tmp1 & iter->second) ^ tmp1;
        if(tmp != 0) inside[i][iter->first] = tmp;
      } else {
        tmp1 = par[iter->first] | total[iter->first];
        tmp = (tmp1 & iter->second) ^ tmp1;
        if(tmp != 0) inside[i][iter->first] = tmp;
      }
      ++iter;
    }
  }
  /// Then Get the outside variable map
  /// Setup the variable map at the upper level.
  iter = total.begin();
  while(iter != total.end()){
    if(varinall[iter->first] != num)
    {
      tmp1 = par[iter->first];
      tmp = (tmp1 & iter->second) ^ iter->second;
      if(tmp != 0) outside[iter->first] = tmp;
      par[iter->first] = par[iter->first] | iter->second;
    } else {
      par[iter->first] = iter->second;
    }
    ++iter;
  }
  parblock->_next = NULL;
  mod->_current = parblock;
  for(i=0; i<num; ++i) delete curblock[i];
  delete [] curblock;
  return 1;
}
