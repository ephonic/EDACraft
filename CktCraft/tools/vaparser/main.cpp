#include "derivation.h"
#include "derYacc.hpp"
#include <iostream>
#include <fstream>
#include <list>
#include <vector>
using namespace std;

list<statement> stateList;
const char* statKw = "STATEMENT";

string GetNextToken(int& first, int& npos, const string &line, int index)
{
  first = index;
  while(line[first] == ' ' || line[first] == '=') ++first;
  npos = 1;
  while(line[first+npos] != ' ' && line[first+npos] != '=' && line[first+npos] != ';') ++npos;
  return line.substr(first, npos);
}

void dumpstatement(statement& st)
{
  printf("_describ: %s\n", st._describ.c_str());
  map<string, bitset<BIT_> >::iterator iter;
  for(iter = st._var.begin(); iter != st._var.end(); ++iter)
  {
    cout<<iter->first<<"="<<iter->second<<endl;
  }
}

int ReadFile(const char* filename)
{
  ifstream inf(filename);
  if(!inf){
    cerr<<"The File \""<<filename<<"\" Cannot open for read.\n";
    return 0;
  }
  string line;
  int index, first, npos;
  int stsize = strlen(statKw);
  statement mystat;
  mystat._type = true;

  while(!inf.eof()){
    getline(inf, line);
    if(line[0] == '#') continue;
    if(line.substr(0, stsize) == statKw){
      index = line.find(";");
      mystat._describ = line.substr(stsize+1, index-stsize);
      mystat._var.clear();
      index = line.find("VAR:");
      first = index+4;
      do{
        GetNextToken(first, npos, line, first);
        mystat._var[line.substr(first, npos)] = atoi(GetNextToken(first, npos, line, first+npos).c_str());
        first += npos;
      }while(line[first] != ';');
      stateList.push_back(mystat);
    }
  }
  cout<<"stateList size:"<<stateList.size()<<endl;
  return 1;
}

int main(int argc, char** argv)
{
  // Read The input statements.
  if(argc != 2) {
    cerr<<"Usage: "<<argv[0]<<" inputfile\n";
    return 0;
  }
  string outfile = argv[1] + string(".result");
  ofstream outf(outfile.c_str());
  set<string> mytmp;
  list<statement>::iterator iter;

  if(ReadFile(argv[1])){
    iter = stateList.begin();
    while(iter != stateList.end()){
      outf<<calculate_deriv(*iter, mytmp);
      ++iter;
    }
  }
}
