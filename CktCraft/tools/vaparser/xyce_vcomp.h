#ifndef XYCE_VCOMP_H_
#define XYCE_VCOMP_H_

#include "vaParser.h"
#include <string>
#include <fstream>
using std::string;


void GenerateHeader(module* mod, const string &filename);
void GenearteCCode(module* mod, const string &filename);

void EquationGenerator(module* mod, std::ofstream& ofs);
void JacobiGenerator(module* mod, std::ofstream& ofs);

#endif
