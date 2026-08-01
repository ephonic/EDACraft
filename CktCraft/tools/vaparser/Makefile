OBJECT=vaLex.o vaYacc.o vaParser.o derYacc.o derLex.o derivation.o xyce_vcomp.o rfsim_codegen.o preparser.o preprocessorLex.o preprocessorYacc.o preprocessorMain.o adms.o switchVariableBlock.o
CXX=/g/msys64/usr/bin/g++ -g -O0 -D_GNU_SOURCE -Wno-return-type -Wno-write-strings
INC=

all: vaParser Deriv

Deriv: main.o derivation.o derYacc.o derLex.o
	$(CXX) -o Deriv main.o derivation.o derYacc.o derLex.o

main.o: main.cpp derYacc.hpp derivation.h
	$(CXX) $(INC) -c main.cpp

vaParser:$(OBJECT)
	$(CXX) -o vaParser $(OBJECT)

switchVariableBlock.o:switchVariableBlock.cpp vaParser.h vaYacc.hpp
	$(CXX) $(INC) -c switchVariableBlock.cpp

xyce_vcomp.o:xyce_vcomp.h xyce_vcomp.cpp
	$(CXX) $(INC) -c xyce_vcomp.cpp

rfsim_codegen.o:rfsim_codegen.h rfsim_codegen.cpp vaParser.h derivation.h
	$(CXX) $(INC) -c rfsim_codegen.cpp

vaLex.o:vaLex.cpp vaYacc.hpp vaParser.h
	$(CXX) $(INC) -c vaLex.cpp

vaYacc.o:vaYacc.cpp vaParser.h
	$(CXX) $(INC) -c vaYacc.cpp

vaParser.o:vaParser.cpp vaParser.h
	$(CXX) $(INC) -c vaParser.cpp

vaLex.cpp:vaLex.l
	lex -Pverilog -ovaLex.cpp vaLex.l

vaYacc.cpp vaYacc.hpp:vaYacc.y
	yacc -pverilog -d -o vaYacc.cpp vaYacc.y

derivation.o:derivation.cpp derivation.h
	$(CXX) $(INC) -c derivation.cpp

derYacc.o: derYacc.cpp derYacc.hpp derivation.h
	$(CXX) $(INC) -c derYacc.cpp

derLex.o: derLex.cpp derivation.h
	$(CXX) $(INC) -c derLex.cpp

derYacc.cpp derYacc.hpp: derYacc.y
	yacc -d -pderiv -o derYacc.cpp derYacc.y

derLex.cpp: derLex.l
	lex -P deriv -oderLex.cpp derLex.l

preparser.o : preparser.h preparser.cpp adms.h admsPreprocessor.h preprocessorYacc.h
	$(CXX) $(INC) -c preparser.cpp

preprocessorLex.o : preprocessorLex.c preprocessorYacc.h
	$(CXX) $(INC) -c preprocessorLex.c

preprocessorYacc.o : preprocessorYacc.c preprocessorYacc.h
	$(CXX) $(INC) -c preprocessorYacc.c

preprocessorMain.o : preprocessorMain.c preprocessorYacc.h
	$(CXX) $(INC) -c preprocessorMain.c

adms.o : adms.c
	$(CXX) $(INC) -c adms.c

preprocessorYacc.c preprocessorYacc.h: preprocessorYacc.y
	yacc -d -p preprocessor -o preprocessorYacc.c preprocessorYacc.y

preprocessorLex.c: preprocessorLex.l
	lex -Ppreprocessor -opreprocessorLex.c preprocessorLex.l

clean :
	/bin/rm -f  preprocessorYacc.c preprocessorYacc.h preprocessorLex.c vaParser vaLex.cpp vaYacc.cpp vaYacc.hpp derivYacc.cpp derivYacc.hpp derivLex.cpp
	/bin/rm -f $(OBJECT)
	/bin/rm -f main.o Deriv
