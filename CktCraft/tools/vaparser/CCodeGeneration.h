#ifndef C_CODE_GENERATION_H
#define C_CODE_GENERATION_H

#include "vaParser.h"
#include <string>
using std::string;

//void ModelCardGenerator(module*, const string &file);
void ModelCardGeneratorH(module* mod, const string &filename);
void ModelCardGeneratorC(module* mod, const string &filename);

void OutputSyntax(module* mod);
void OutputH(module* mod, const char *ofname);
void OutputC(module* mod, const char *ofname);
string EquationGenerator(module* mod);
string JacobiGenerator(module* mod);
#endif
