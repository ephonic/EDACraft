/* Rewrite by zhgui */

%{
#define YYDEBUG 1
//#define YYPARSE_PARAM myadmsmain
#include "vaParser.h"

    using std::list;
    using std::cerr;

    string __curFile;
    int __curLine;
    int __curPos;

    int __modDdtNum;

    list<nature*> __natureList;
    list<discipline*> __disList;
    list<module*> __moduleList;
    list<attribute*> __attrList;

    //**Begin global points
    discipline *gDiscipline = NULL;
    module *gModule = NULL;
    string *gNatureAccess = NULL;
    double *gNatureAbsTol = NULL;
    string *gNatureUnits  = NULL;
    string *gNatureidt    = NULL;
    string *gNatureddt    = NULL;
    source *gSource = NULL;
    list<string> gNodeList;
    list<yaccVal*> gCaseList;
    list<list<yaccVal*>*> gCaseStack;   // case 嵌套栈（宏展开 case 里还有 case）
    list<int> gCaseFlagStack;
    vector<string> gBlockNameStack;              // 命名块 begin : name 栈
    vector<map<string,string> > gBlockLocalStack; // 每层的局部变量名映射(原名→唯一名)
    int gBlockMangleCounter = 0;
    attribute* __globalAttr;
    int  gNodeDirection;//1:input 2:output 3:inout
    list<string> gBranchList;
    analogFun *gAnalogfunction = NULL;
    int gVariableType; //1:int 2:real 3:string
    int gCaseFlag = 0; // 0: first case, 1: other cases
    list<string> gVariableList;
    range *gRange;
    list<statement> gStateList;
    map<string, string> gAttribute;
    //list<string> gDerivSetZero;
    map<string, bitset<BIT_> > gOutsideZero;
    //**End global points

    nature* GetNature(const string str)
    {
        using std::iterator;
        typedef list<nature*>::iterator LNiterator;
        LNiterator iter = __natureList.begin();
        while(iter != __natureList.end()){
            if((*iter)->_name == str){
                return *iter;
            }
            ++iter;
        }
        return NULL;
    }

%}

%left PREC_IF_THEN
%left tk_else

%union
{
  lexVal*  _lexval;
  yaccVal* _yaccval;
}

%token <_lexval> tk_from
%token <_lexval> tk_branch
%token <_lexval> tk_number
%token <_lexval> tk_nature
%token <_lexval> tk_aliasparameter
%token <_lexval> tk_output
%token <_lexval> tk_anystring
%token <_lexval> tk_dollar_ident
%token <_lexval> tk_or
%token <_lexval> tk_aliasparam
%token <_lexval> tk_if
%token <_lexval> tk_analog
%token <_lexval> tk_parameter
%token <_lexval> tk_discipline
%token <_lexval> tk_char
%token <_lexval> tk_anytext
%token <_lexval> tk_for
%token <_lexval> tk_while
%token <_lexval> tk_real
%token <_lexval> tk_op_shr
%token <_lexval> tk_case
%token <_lexval> tk_potential
%token <_lexval> tk_endcase
%token <_lexval> tk_inf
%token <_lexval> tk_exclude
%token <_lexval> tk_ground
%token <_lexval> tk_endmodule
%token <_lexval> tk_begin
%token <_lexval> tk_enddiscipline
%token <_lexval> tk_domain
%token <_lexval> tk_ident
%token <_lexval> tk_op_shl
%token <_lexval> tk_string
%token <_lexval> tk_integer
%token <_lexval> tk_module
%token <_lexval> tk_endattribute
%token <_lexval> tk_else
%token <_lexval> tk_end
%token <_lexval> tk_inout
%token <_lexval> tk_and
%token <_lexval> tk_bitwise_equr
%token <_lexval> tk_default
%token <_lexval> tk_function
%token <_lexval> tk_input
%token <_lexval> tk_beginattribute
%token <_lexval> tk_endnature
%token <_lexval> tk_endfunction
%token <_lexval> tk_flow

%type <_yaccval> R_admsParse
%type <_yaccval> R_l_admsParse
%type <_yaccval> R_s_admsParse
%type <_yaccval> R_discipline_member
%type <_yaccval> R_discipline_name
%type <_yaccval> R_l_discipline_assignment
%type <_yaccval> R_s_discipline_assignment
%type <_yaccval> R_discipline_naturename
%type <_yaccval> R_nature_member
%type <_yaccval> R_l_nature_assignment
%type <_yaccval> R_s_nature_assignment
%type <_yaccval> R_d_attribute_0
%type <_yaccval> R_d_attribute
%type <_yaccval> R_l_attribute
%type <_yaccval> R_s_attribute
%type <_yaccval> R_d_module
%type <_yaccval> R_modulebody
%type <_yaccval> R_netlist
%type <_yaccval> R_l_instance
%type <_yaccval> R_d_terminal
%type <_yaccval> R_l_terminal_0
%type <_yaccval> R_l_terminal
%type <_yaccval> R_s_terminal
%type <_yaccval> R_l_declaration
%type <_yaccval> R_s_declaration_withattribute
%type <_yaccval> R_d_attribute_global
%type <_yaccval> R_s_declaration
%type <_yaccval> R_d_node
%type <_yaccval> R_node_type
%type <_yaccval> R_l_terminalnode
%type <_yaccval> R_l_node
%type <_yaccval> R_s_terminalnode
%type <_yaccval> R_s_node
%type <_yaccval> R_d_branch
%type <_yaccval> R_l_branchalias
%type <_yaccval> R_s_branchalias
%type <_yaccval> R_s_branch
%type <_yaccval> R_d_analogfunction
%type <_yaccval> R_d_analogfunction_proto
%type <_yaccval> R_d_analogfunction_name
%type <_yaccval> R_l_analogfunction_declaration
%type <_yaccval> R_s_analogfunction_declaration
%type <_yaccval> R_l_analogfunction_input_variable
%type <_yaccval> R_l_analogfunction_output_variable
%type <_yaccval> R_l_analogfunction_inout_variable
%type <_yaccval> R_l_analogfunction_integer_variable
%type <_yaccval> R_l_analogfunction_real_variable
%type <_yaccval> R_variable_type
%type <_yaccval> R_d_variable_end
%type <_yaccval> R_l_parameter
%type <_yaccval> R_l_variable
%type <_yaccval> R_d_aliasparameter
%type <_yaccval> R_d_aliasparameter_token
%type <_yaccval> R_s_parameter
%type <_yaccval> R_s_variable
%type <_yaccval> R_s_parameter_name
%type <_yaccval> R_s_variable_name
%type <_yaccval> R_s_parameter_range
%type <_yaccval> R_l_interval
%type <_yaccval> R_s_interval
%type <_yaccval> R_d_interval
%type <_yaccval> R_interval_inf
%type <_yaccval> R_interval_sup
%type <_yaccval> R_analog
%type <_yaccval> R_analogcode
%type <_yaccval> R_analogcode_atomic
%type <_yaccval> R_analogcode_block
%type <_yaccval> R_analogcode_block_atevent
%type <_yaccval> R_l_analysis
%type <_yaccval> R_s_analysis
%type <_yaccval> R_d_block
%type <_yaccval> R_d_block_begin
%type <_yaccval> R_l_blockitem
%type <_yaccval> R_d_blockvariable
%type <_yaccval> R_l_blockvariable
%type <_yaccval> R_s_blockvariable
%type <_yaccval> R_d_contribution
%type <_yaccval> R_contribution
%type <_yaccval> R_source
%type <_yaccval> R_d_while
%type <_yaccval> R_d_for
%type <_yaccval> R_d_case
%type <_yaccval> R_l_case_item
%type <_yaccval> R_s_case_item
%type <_yaccval> R_s_instance
%type <_yaccval> R_instance_module_name
%type <_yaccval> R_l_instance_parameter
%type <_yaccval> R_s_instance_parameter
%type <_yaccval> R_s_assignment
%type <_yaccval> R_s_assignment_name
%type <_yaccval> R_d_conditional
%type <_yaccval> R_s_expression
%type <_yaccval> R_l_callfunction_expression
%type <_yaccval> R_l_expression
%type <_yaccval> R_s_function_expression
%type <_yaccval> R_expression
%type <_yaccval> R_e_conditional
%type <_yaccval> R_e_bitwise_equ
%type <_yaccval> R_e_bitwise_xor
%type <_yaccval> R_e_bitwise_or
%type <_yaccval> R_e_bitwise_and
%type <_yaccval> R_e_logical_or
%type <_yaccval> R_e_logical_and
%type <_yaccval> R_e_comp_equ
%type <_yaccval> R_e_comp
%type <_yaccval> R_e_bitwise_shift
%type <_yaccval> R_e_arithm_add
%type <_yaccval> R_e_arithm_mult
%type <_yaccval> R_e_unary
%type <_yaccval> R_e_atomic

%%

R_admsParse
        : R_l_admsParse
          {
          }
        ;
R_l_admsParse
        : R_s_admsParse
          {
          }
        | R_l_admsParse R_s_admsParse
          {
          }
        ;
R_s_admsParse
        : R_d_module
          {
          }
        | R_discipline_member
          {
          }
        | R_nature_member
          {
          }
        ;

R_discipline_member
        : tk_discipline R_discipline_name R_l_discipline_assignment tk_enddiscipline
          {
            __disList.push_back(gDiscipline);
            //delete gDiscipline;
          }
        ;
R_discipline_name
        : tk_ident
          {
            gDiscipline = new discipline;
            gDiscipline->_name = ($1)->_str;
          }
        ;
R_l_discipline_assignment
        : R_s_discipline_assignment
          {
          }
        | R_l_discipline_assignment R_s_discipline_assignment
          {
          }
        ;
R_s_discipline_assignment
        : tk_potential R_discipline_naturename ';'
          {
            gDiscipline->_potential = GetNature(($2)->_str);
            if(gDiscipline->_potential == NULL){
                vaMessageError("can't find nature definition\n", $2);
            }
            delete $2;
          }
        | tk_flow R_discipline_naturename ';'
          {
            gDiscipline->_flow = GetNature(($2)->_str);
            if(gDiscipline->_flow == NULL){
                vaMessageError("can't find nature definition\n", $2);
            }
            delete $2;
          }
        | tk_domain tk_ident ';'
          {
            string mylexval2 = ($2)->_str;
            if(mylexval2 == "discrete")
              gDiscipline->_domain = 0;
            else if(mylexval2 == "continuous")
              gDiscipline->_domain = 1;
            else
              vaMessageError("domain: bad value given - should be either 'discrete' or 'continuous'\n",$2);
          }
        ;
R_discipline_naturename
        : tk_ident
          {
            $$ = new yaccVal;
            ($$)->_str = ($1)->_str;
            ($$)->_lex = *($1);
          }
        ;
R_nature_member
        : tk_nature tk_ident R_l_nature_assignment tk_endnature
          {
            string mylexval2 = ($2)->_str;
            nature *mynature = NULL;
            if(gNatureAccess) 
              mynature = pushBackNature(__natureList, *gNatureAccess);
            else
              vaMessageError("attribute 'access' in nature definition not found\n",$2);
            mynature->_name = mylexval2;
            if(gNatureidt != NULL)
              mynature->_idt = *gNatureidt;
            if(gNatureddt != NULL) 
              mynature->_ddt = *gNatureddt;
            if(gNatureUnits != NULL)
              mynature->_units = *gNatureUnits;
            if(gNatureAbsTol != NULL)
              mynature->_abstol = *gNatureAbsTol;

            delete gNatureAccess;
            delete gNatureAbsTol;
            delete gNatureUnits;
            delete gNatureidt;
            delete gNatureddt;
            gNatureAccess = NULL;
            gNatureAbsTol = NULL;
            gNatureUnits = NULL;
            gNatureidt = NULL;
            gNatureddt = NULL;
          }
        ;
R_l_nature_assignment
        : R_s_nature_assignment
          {
          }
        | R_l_nature_assignment R_s_nature_assignment
          {
          }
        ;
R_s_nature_assignment
        : tk_ident '=' tk_number ';'
          {
            string mylexval3=($3)->_str;
            if(($1)->_str == "abstol")
            {
              if(gNatureAbsTol)
                vaMessageError("nature attribute defined more than once\n",$1);
              gNatureAbsTol = new double;
              *gNatureAbsTol = string2double(mylexval3);
            }
            else
              vaMessageError("unknown nature attribute\n",$1);
          }
        | tk_ident '=' tk_number tk_ident ';'
          {
            string mylexval3=($3)->_str;
            string mylexval4=($4)->_str;
            double myunit = 1.0;
            if(($1)->_str == "abstol")
            {
              if(gNatureAbsTol)
                vaMessageError("nature attribute defined more than once\n",$1);
              //gNatureAbsTol = adms_number_new(mylexval3);
            }
            else
              vaMessageError("unknown nature attribute\n",$1);
            if(0) { }
            else if((mylexval4 == "E")) myunit = 1e18;
            else if((mylexval4 == "P")) myunit = 1e15;
            else if((mylexval4 == "T")) myunit = 1e12;
            else if((mylexval4 == "G")) myunit = 1e9;
            else if((mylexval4 == "M")) myunit = 1e6;
            else if((mylexval4 == "k")) myunit = 1e3;
            else if((mylexval4 == "h")) myunit = 100;
            else if((mylexval4 == "D")) myunit = 10;
            else if((mylexval4 == "d")) myunit = 0.1;
            else if((mylexval4 == "c")) myunit = 0.01;
            else if((mylexval4 == "m")) myunit = 1e-3;
            else if((mylexval4 == "u")) myunit = 1e-6;
            else if((mylexval4 == "n")) myunit = 1e-9;
            else if((mylexval4 == "A")) myunit = 1e-10;
            else if((mylexval4 == "p")) myunit = 1e-12;
            else if((mylexval4 == "f")) myunit = 1e-15;
            else if((mylexval4 == "a")) myunit = 1e-18;
            else
              vaMessageError("can not convert symbol to valid unit\n",$4);
            gNatureAbsTol = new double;
            *gNatureAbsTol = myunit * string2double(mylexval3);
          }
        | tk_ident '=' tk_anystring ';'
          {
            if(($1)->_str == "units")
            {
              if(gNatureUnits)
                vaMessageError("nature attribute defined more than once\n",$1);
              gNatureUnits = new string;
              *gNatureUnits = ($3)->_str;
            }
            else
              vaMessageError("unknown nature attribute\n",$1);
          }
        | tk_ident '=' tk_ident ';'
          {
            string mylexval3 = ($3)->_str;
            if(($1)->_str == "access")
            {
              if(gNatureAccess)
                vaMessageError("nature attribute defined more than once\n",$1);
              gNatureAccess = new string;
              *gNatureAccess = mylexval3;
            }
            else if(($1)->_str == "idt_nature")
            {
              if(gNatureidt)
                vaMessageError("idt_nature attribute defined more than once\n",$1);
              gNatureidt = new string;
              *gNatureidt = mylexval3;
            }
            else if(($1)->_str == "ddt_nature")
            {
              if(gNatureddt)
                vaMessageError("ddt_nature attribute defined more than once\n",$1);
              gNatureddt = new string;
              *gNatureddt = mylexval3;
            }
            else
              vaMessageError("unknown nature attribute\n",$1);
          }
        ;

R_d_attribute_0
        :
          {
          }
        | R_d_attribute
          {
          }
        ;
R_d_attribute
        : tk_beginattribute R_l_attribute tk_endattribute
          {
              attribute* myattr = new attribute;
              myattr->_attrlist = gAttribute;
              __attrList.push_back(myattr);
              gAttribute.clear();
          }
        | tk_beginattribute tk_anytext
          {
            string mylexval2 = ($2)->_str;
            attribute* myattribute = new attribute;
            (myattribute->_attrlist)["ibm"] = mylexval2;
            __attrList.push_back(myattribute);
          }
        | tk_beginattribute tk_endattribute
          {
          }
        ;
R_l_attribute
        : R_s_attribute
          {
          }
        | R_l_attribute R_s_attribute
          {
          }
        ;
R_s_attribute
        : tk_ident '=' tk_anystring
          {
            string mylexval1 = ($1)->_str;
            string mylexval3 = ($3)->_str;
            gAttribute[mylexval1] = mylexval3;
          }
        ;

R_d_module
        : R_d_attribute_0 tk_module tk_ident
          {
            string mylexval3=($3)->_str;
            gModule = pushBackModule(__moduleList, mylexval3);
            gModule->_head = new variableblock;
            gModule->_head->_prev = NULL;
            gModule->_head->_next = NULL;
            gModule->_head->_right = NULL;
            gModule->_current = gModule->_head;
            LoadSystemFunction(gModule->_analogFun);
            __modDdtNum = 0;

            if(__attrList.size() != 0){
                gModule->_attr = __attrList.back();
                __attrList.pop_back();
            }
          }
        R_d_terminal R_modulebody tk_endmodule
          {
            //adms_slist_inreverse(&gModule->_assignment);
              gModule->_ddtnum = __modDdtNum;
          }
        ;
R_modulebody
        : 
          {
          }
        | R_l_declaration
          {
          }
        | R_netlist
          {
          }
        | R_l_declaration R_netlist
          {
          }
        ;
R_netlist
        : R_analog
          {
          }
        | R_l_instance
          {
          }
        | R_l_instance R_analog
          {
          }
        | R_analog R_l_instance
          {
          }
        | R_l_instance R_analog R_l_instance
          {
          }
        ;
R_l_instance
        : R_s_instance
          {
          }
        | R_l_instance R_s_instance
          {
          }
        ;
R_d_terminal
        : '(' R_l_terminal_0 ')' R_d_attribute_0 ';'
          {
            if(__attrList.size() != 0){
                gModule->_attr = __attrList.back();
                __attrList.pop_back();
            }
          }
        ;
R_l_terminal_0
        : 
          {
          }
        | R_l_terminal
          {
          }
        ;
R_l_terminal
        : R_s_terminal
          {
          }
        | R_l_terminal ',' R_s_terminal
          {
          }
        ;
R_s_terminal
        : tk_ident
          {
            string mylexval1 = ($1)->_str;
            vector<terminal>::iterator iter = gModule->_port.begin();
            while(iter != gModule->_port.end()){
                if(iter->_name == mylexval1)
                vaMessageError("Redefinition of port name.\n", $1);
                ++iter;
            }
            terminal myterm;
            myterm._name = mylexval1;
            myterm._type = 0;
            (gModule->_port).push_back(myterm);
          }
        ;
R_l_declaration
        : R_s_declaration_withattribute
          {
          }
        | R_l_declaration R_s_declaration_withattribute
          {
          }
        ;
R_s_declaration_withattribute
        : R_s_declaration
          {
          }
        | R_d_attribute_global R_s_declaration
          {
              delete __globalAttr;
              __globalAttr = NULL;
          }
        ;
R_d_attribute_global
        : R_d_attribute
          {
              __globalAttr = __attrList.back();
              __attrList.pop_back();
          }
        ;
R_s_declaration
        : R_d_node
          {
          }
        | R_d_branch
          {
          }
        | R_s_param_declaration
	  {
	  }
        | R_variable_type R_l_variable R_d_variable_end
          {
          }
        | R_d_aliasparameter
          {
          }
        | R_d_analogfunction
          {
          }
        | ';'
          {
          }
        ;

R_s_param_declaration
        : tk_parameter R_variable_type R_l_parameter R_d_variable_end
	{
	}
        | tk_parameter R_l_parameter R_d_variable_end
	{
	}
//modified by ly
R_d_node
        : R_node_type R_l_terminalnode ';'
          {
              R_d_node(gNodeList, gNodeDirection, (void*)$1, true);
              delete $1;
          }
        | tk_ground R_l_node ';'
          {
              R_d_node(gNodeList, -1, (void*)$1, false);
          }
        | tk_ident R_l_node ';'
          {
              string mylexval1=($1)->_str;
              list<discipline*>::iterator it = __disList.begin();
              while(it != __disList.end()){
                  if((*it)->_name == mylexval1){
                      break;
                  }
                  ++it;
              }
              if(it == __disList.end())
                  vaMessageError("Unknow net type.", $1);
              list<string>::iterator iter = gNodeList.begin();
              net mynet;
              mynet._disp = *it;
              while(iter != gNodeList.end()){
                  mynet._name = *iter;
                  gModule->_net.push_back(mynet);
                  ++iter;
              }
              gNodeList.clear(); 
          }
        ;
R_node_type
        : tk_input
          {
            $$ = new yaccVal;
            $$->_lex = *($1);
            gNodeDirection = 1;
          }
        | tk_output
          {
            $$ = new yaccVal;
            $$->_lex = *($1);
            gNodeDirection = 2;
          }
        | tk_inout
          {
            $$ = new yaccVal;
            $$->_lex = *($1);
            gNodeDirection = 3;
          }
        ;
R_l_terminalnode
        : R_s_terminalnode
          {
          }
        | R_l_terminalnode ',' R_s_terminalnode
          {
          }
        ;
R_l_node
        : R_s_node
          {
          }
        | R_l_node ',' R_s_node
          {
          }
        ;
R_s_terminalnode
        : tk_ident R_d_attribute_0
          {
            string mylexval1 = ($1)->_str;
            vector<terminal>::iterator iter;
            iter = gModule->_port.begin();
            while(iter != gModule->_port.end()){
                if(iter->_name == mylexval1) break;
                ++iter;
            }
            if(iter == (gModule->_port).end()){
                vaMessageError("terminal not found\n", $1);
            }
            if(iter->_type != 0)
                vaMessageError("Redefinition terminal.\n", $1);

            gNodeList.push_back(mylexval1);
            if(__attrList.size() != 0){
                delete __attrList.back();
                __attrList.pop_back();
            };
          }
        ;
R_s_node
        : tk_ident R_d_attribute_0
          {
            string mylexval1 = ($1)->_str;
            vector<net>::iterator iter = gModule->_net.begin();
            while(iter != gModule->_net.end()){
                if(iter->_name == mylexval1)
                    vaMessageError("Redefinition of net.\n", $1);
                ++iter;
            }
            gNodeList.push_back(mylexval1);
            if(__attrList.size() != 0){
                delete __attrList.back();
                __attrList.pop_back();
            };

          }
        ;

R_d_branch
        : tk_branch R_s_branch ';'
          {
          }
        ;
R_l_branchalias
        : R_s_branchalias
          {
          }
        | R_l_branchalias ',' R_s_branchalias
          {
          }
        ;
R_s_branchalias
        : tk_ident
          {
            string mylexval1 = ($1)->_str;
            gBranchList.push_back(mylexval1);
          }
        ;
R_s_branch
        : '(' tk_ident ',' tk_ident ')' R_l_branchalias
          {
            string mylexval2 = ($2)->_str;
            string mylexval4 = ($4)->_str;
            int flag = 0;
            vector<net>::iterator iter = gModule->_net.begin();
            while(iter != gModule->_net.end()){
                if(iter->_name == mylexval2) flag |= 1;
                else if(iter->_name == mylexval4) flag |= 2;
                ++iter;
            }
            if(flag != 3){
                vaMessageError("Node used in branch never declared.\n", $2);
            }
            branch mybranch;
            mybranch._type = 2;
            mybranch._pnode = mylexval2;
            mybranch._nnode = mylexval4;
            list<string>::iterator it = gBranchList.begin();
            while(it != gBranchList.end()){
                (gModule->_branchAlias)[*it] = mybranch;
                ++it;
            }
            gBranchList.clear();
          }
        | '(' tk_ident ')' R_l_branchalias
          {
            string mylexval2 = ($2)->_str;
            int flag = 0;
            vector<net>::iterator iter = gModule->_net.begin();
            while(iter != gModule->_net.end()){
                if(iter->_name == mylexval2) flag |= 1;
                ++iter;
            }
            if(flag == 0)
                vaMessageError("Node never declared.\n", $2);
            branch mybranch;
            mybranch._type = 1;
            mybranch._pnode = mylexval2;
            list<string>::iterator it = gBranchList.begin();
            while(it != gBranchList.end()){
                (gModule->_branchAlias)[*it] = mybranch;
                ++it;
            }
            gBranchList.clear();
          }
        ;

R_d_analogfunction
        : R_d_analogfunction_proto R_l_analogfunction_declaration R_analogcode_block tk_endfunction
          {
            //gAnalogfunction->_state = GetCalState($3);
	    gAnalogfunction->_state._steps = $3->_state;
	    gAnalogfunction->_state._tree = $3->_tree;
            gAnalogfunction = NULL;
          }
        ;
R_d_analogfunction_proto
        : tk_analog tk_function R_d_analogfunction_name ';'
          {
              gAnalogfunction = analogFunctionNew(gModule, ($3)->_str);
              if(gAnalogfunction == NULL)
                  vaMessageError("analog function name already defined.\n", $3);
              gAnalogfunction->_type = 2;
          }
        | tk_analog tk_function tk_integer R_d_analogfunction_name ';'
          {
              gAnalogfunction = analogFunctionNew(gModule, ($4)->_str);
              gAnalogfunction->_type = 1;
          }
        | tk_analog tk_function tk_real R_d_analogfunction_name ';'
          {
              gAnalogfunction = analogFunctionNew(gModule, ($4)->_str);
              gAnalogfunction->_type = 2;
          }
        ;

R_d_analogfunction_name
        : tk_ident
          {
          }
        ;
R_l_analogfunction_declaration
        : R_s_analogfunction_declaration
          {
          }
        | R_l_analogfunction_declaration R_s_analogfunction_declaration
          {
          }
        ;
R_s_analogfunction_declaration
        : tk_input R_l_analogfunction_input_variable ';'
          {
          }
        | tk_output R_l_analogfunction_output_variable ';'
          {
          }
        | tk_inout R_l_analogfunction_inout_variable ';'
          {
          }
        | tk_integer R_l_analogfunction_integer_variable ';'
          {
          }
        | tk_real R_l_analogfunction_real_variable ';'
          {
          }
        ;
R_l_analogfunction_input_variable
        : tk_ident
          {
              AddFunctionVariable(gAnalogfunction, $1, 1);
          }
        | R_l_analogfunction_input_variable ',' tk_ident
          {
              AddFunctionVariable(gAnalogfunction, $3, 1);
          }
        ;
R_l_analogfunction_output_variable
        : tk_ident
          {
              AddFunctionVariable(gAnalogfunction, $1, 2);
          }
        | R_l_analogfunction_output_variable ',' tk_ident
          {
              AddFunctionVariable(gAnalogfunction, $3, 2);
          }
        ;
R_l_analogfunction_inout_variable
        : tk_ident
          {
              AddFunctionVariable(gAnalogfunction, $1, 3);
          }
        | R_l_analogfunction_inout_variable ',' tk_ident
          {
              AddFunctionVariable(gAnalogfunction, $3, 3);
          }
        ;
R_l_analogfunction_integer_variable
        : tk_ident
          {
              (gAnalogfunction->_var[$1->_str])._type = 1;
          }
        | R_l_analogfunction_integer_variable ',' tk_ident
          {
              (gAnalogfunction->_var[$3->_str])._type = 1;
          }
        ;
R_l_analogfunction_real_variable
        : tk_ident
          {
              (gAnalogfunction->_var[$1->_str])._type = 2;
          }
        | R_l_analogfunction_real_variable ',' tk_ident
          {
              (gAnalogfunction->_var[$3->_str])._type = 2;
          }
        ;
R_variable_type
        : tk_integer R_d_attribute_0
          {
            gVariableType = 1;
          }
        | tk_real R_d_attribute_0
          {
            gVariableType = 2;
          }
        | tk_string R_d_attribute_0
          {
            gVariableType = 3;
          }
        ;
R_d_variable_end
        : ';'
          {
              variable myvar;
              myvar._type = gVariableType;
              list<string>::iterator iter = gVariableList.begin();
              while(iter != gVariableList.end()){
                  myvar._name = *iter;
                  (gModule->_variable).push_back(myvar);
                  ++iter;
              }
              gVariableList.clear();
          }
        ;
R_l_parameter
        : R_s_parameter
          {
          }
        | R_l_parameter ',' R_s_parameter
          {
          }
        ;
R_l_variable
        : R_s_variable
          {
          }
        | R_l_variable ',' R_s_variable
          {
          }
        ;
R_d_aliasparameter
        : R_d_aliasparameter_token tk_ident '=' tk_ident R_d_attribute_0 ';'
          {
              vaMessageError("Parameters alias not support now.", $2);
          }
        ;
R_d_aliasparameter_token
        : tk_aliasparameter
          {
          }
        | tk_aliasparam
          {
          }
        ;
R_s_parameter
        : R_s_parameter_name R_d_attribute_0
          {
              if(__attrList.size() != 0){
                parameter* myparam = &((gModule->_param).back());
                myparam->_attr = __attrList.back();
                __attrList.pop_back();
                if((myparam->_attr->_attrlist)[string("type")] == "instance")
                    myparam->_type = 1;
                else myparam->_type = 0;
              }
              else {
                (gModule->_param.back())._attr = NULL;
                (gModule->_param.back())._type = 0;
              }
          }
        ;
R_s_variable
        : R_s_variable_name R_d_attribute_0
          {
              if(__attrList.size() != 0){
                  __attrList.pop_back();
              }
          }
        ;
R_s_parameter_name
        : R_s_variable_name '=' R_s_expression R_s_parameter_range
          {
              parameter myparam;
              myparam._name = gVariableList.back();
              if(gRange != NULL){
                  myparam._range = gRange;
              }else{
                  myparam._range = NULL;
              }
              myparam._defvalue = ($3)->_value;
              // 非纯数字默认值（如 VSAT1 = VSAT）：保存表达式文本，
              // codegen 以参数成员名重写后作为成员初始化表达式
              {
                  const string& dv = ($3->_state).front()._describ;
                  bool pureNum = !dv.empty();
                  for (char c : dv) {
                      if (!(isdigit(c) || c=='.' || c=='e' || c=='E' || c=='+' || c=='-' || c==' ')) {
                          pureNum = false; break;
                      }
                  }
                  myparam._defexpr = pureNum ? string() : dv;
              }
              if(!AddParameter(gModule, myparam._name)){
                  vaMessageError("Redefine of parameter.", $1);
              }
              gModule->_param.push_back(myparam);
              gRange = NULL;
              gVariableList.clear();
          }
        ;
R_s_variable_name
        : tk_ident
          {
              string tmp = $1->_str;
              gVariableList.push_back($1->_str);
              delete $1;
          }
        | tk_ident '[' tk_number ':' tk_number ']'
          {
              vaMessageError("Array not support now.", $1);
          }
        ;
R_s_parameter_range
        : 
          {
          }
        | R_l_interval
          {
          }
        ;
R_l_interval
        : R_s_interval
          {
          }
        | R_l_interval R_s_interval
          {
	    //              vaMessageError("Muti interval describe of parameter not support now.", $2);
          }
        ;
R_s_interval
        : tk_from R_d_interval
          {
              gRange->_type = 1;
          }
        | tk_exclude R_d_interval
          {
              gRange->_type = 2;
          }
        | tk_exclude R_s_expression
          {
            // `exclude 0.0`（无 from 区间）：gRange 尚未分配，先建再标型，
            // 否则空指针解引用（BSIM-CMG 的参数形式）。
            if(gRange == NULL){
                gRange = new range;
                gRange->_binf = true;
                gRange->_einf = true;
            }
            gRange->_type = 2;
          }
        ;
//modified by ly
R_d_interval 
        : '(' R_interval_inf R_interval_seg R_interval_sup ')'
          {
              R_interval($2, $4, gRange, 1,1);
          }
        | '(' R_interval_inf R_interval_seg R_interval_sup ']'
          {
              R_interval($2, $4, gRange, 1,2);
          }
        | '[' R_interval_inf R_interval_seg R_interval_sup ')'
          {
              R_interval($2, $4, gRange, 2,1);
          }
        | '[' R_interval_inf R_interval_seg R_interval_sup ']'
          {
              R_interval($2, $4, gRange, 2,2);
          }
        | R_s_expression
          {
              vaMessageError("expression interval not support now.", $1);
          }
        ;

R_interval_seg
        : ':'
	{
	}
	| ','
	{
	}
        ;

R_interval_inf
        : R_s_expression
          {
              $$=$1;
          }
        | '-' tk_inf
          {
              $$ = new yaccVal;
              $$->_str = "inf";
          }
        ;
R_interval_sup
        : R_s_expression
          {
              $$=$1;
          }
        | tk_inf
          {
              $$ = new yaccVal;
              $$->_str = "inf";
          }
        | '+' tk_inf
          {
              $$ = new yaccVal;
              $$->_str = "inf";
          }
        ;
R_analog
        : tk_analog R_analogcode
          {
              //gModule->_analog=adms_analog_new(YY($2));
              list<statement>::iterator iter;
	      if($2 != NULL)
		{
		  iter = $2->_state.begin();
		  while(iter != $2->_state.end()){
		    gModule->_main._steps.push_back(*iter);
		    ++iter;
		  }
		}
          }
        ;
R_analogcode
        : R_analogcode_atomic
          {
              $$ = $1;
              while(gStateList.size() != 0){
                  $$->_state.push_front(gStateList.back());
                  gStateList.pop_back();
              }
          }
        | R_analogcode_block
          {
              $$=$1;
          }
        ;
R_analogcode_atomic
        : R_d_attribute_0 R_d_blockvariable
          {
              $$=$2;
              if(__attrList.size() != 0){
                __attrList.pop_back();
              }
          }
        | R_d_contribution
          {
              $$=$1;
              //($$->_state.front())._describ += ";";
          }
        | R_s_assignment ';'
          {
              $$=$1;
              ($$->_state.front())._describ += ";";
          }
        | R_d_conditional
          {
              $$=$1;
              statement mystat;
              mystat._mode = 4;
              mystat._type = false;
              map<string, bitset<BIT_> >::iterator iter;
              if(gOutsideZero.size() > 0){
                iter = gOutsideZero.begin();
                while(gOutsideZero.end() != iter){
                  mystat._describ = GetZeroDerivation(iter->first, iter->second);
                  $$->_state.push_front(mystat);
                  ++iter;
                }
              }
              gOutsideZero.clear();
          }
        | R_d_while
          {
              $$=$1;
          }
        | R_d_case
          {
              $$=$1;
          }
        | R_d_for
          {
              $$=$1;
          }
        | tk_dollar_ident '(' R_l_callfunction_expression ')' ';'
          {
            //modified by ly
	    if($1->_str == "$strobe")
	      {
		$$ = new yaccVal;
		statement mystat;
		map<string, int>::iterator piter;
		mystat._param = ($3->_state).front()._param;
		mystat._describ = "printf(" + ($3->_state).front()._describ;
		list<statement>::iterator iter = $3->_state.begin();
		++iter;
		while(iter != $3->_state.end()) {
		  mystat._describ +=  ", " + (*iter)._describ;
		  piter = (*iter)._param.begin();
		  while(piter != (*iter)._param.end())
		    {
		      mystat._param.insert(*piter);
		      ++piter;
		    }
		  ++iter;
		}
		mystat._describ += ");";
		
		mystat._mode = 1;
		($$->_state).push_back(mystat);
	      }
	    else if($1->_str == "$finish")
	      {
		$$ = new yaccVal;
		statement mystat;
		mystat._describ = "exit(" + ($3->_state).front()._describ + ");";
		mystat._mode = 1;
		($$->_state).push_back(mystat);
	      }
	    else
	      {
		R_analogcode_tk_ident($$, $1->_str + "(" + $3->_str + ");");
		($$->_state.front())._describ += ";";
	      }
	    SetVariableType(gModule, $1->_str, 0);
          }
        | tk_dollar_ident '(' ')' ';'
          {
              R_analogcode_tk_ident($$, $1->_str + "();");
          }
        | tk_dollar_ident ';'
          {
              vaMessageError("system variable ", $1);
          }
        | ';'
          {
              //vaMessageError("");
              $$ = new yaccVal;
          }
        ;
R_analogcode_block
        : R_d_block
          {
            $$ = $1;
          }
        | R_analogcode_block_atevent R_d_block
          {
            $$ = $2;
          }
        ;
R_analogcode_block_atevent
        : '@' '(' tk_ident '(' R_l_analysis ')' ')'
          {
              vaMessageError("@ control not supported\n",$3);
          }
        | '@' tk_ident
          {
              string tmp = $2->_str;
              //vaMessageError("@ control not supported\n",$2);
          }
        | '@' '(' tk_ident ')'
          {
              // @(initial_step) 等事件块：内联展开（块内语句无条件顺序执行）。
              // initial_step 语义为实例初始化，通常只做幂等的参数派生计算，
              // DC/瞬态每次 eval 重算结果一致。其他事件类型（cross/above 等）
              // 本编译器不支持，但块语句仍保留以便后续扩展。
              string tmp = $3->_str;
          }
        ;
R_l_analysis
        : R_s_analysis
          {
          }
        | R_l_analysis ',' R_s_analysis
          {
          }
        ;
R_s_analysis
        : tk_anystring
          {
          }
        ;
R_d_block
        : R_d_block_begin tk_end
          {
            $$ = new yaccVal;
          }
        | R_d_block_begin ':' tk_ident tk_end
          {
            $$ = new yaccVal;
          }
        | R_d_block_begin R_l_blockitem tk_end
          {
            $$ = $2;
          }
        | R_d_block_begin ':' tk_ident
          {
            // 进入命名块：建立局部作用域（块内 real 声明用唯一名，引用映射）
            gBlockNameStack.push_back($3->_str);
            gBlockLocalStack.push_back(map<string,string>());
          }
          R_l_blockitem tk_end
          {
            gBlockNameStack.pop_back();
            gBlockLocalStack.pop_back();
            $$ = $5;
          }
        ;
R_d_block_begin
        : R_d_attribute_0 tk_begin
          {
              if(__attrList.size() != 0){
                __attrList.pop_back();
              }
          }
        ;
R_l_blockitem
        : R_analogcode
          {
              $$ = $1;
          }
        | R_l_blockitem R_analogcode
          {
	    yaccVal * t1, *t2, *t3;
              $$ = $1;
	      t1 = $$, t2 = $1, t3 = $2;

	      if($2 != NULL && $2->_state.size() != 0)
		{
		  list<statement>::iterator iter = $2->_state.begin();
		  while(iter != $2->_state.end()){
		    $$->_state.push_back(*iter);
		    ++iter;
		  }
		}

	      delete $2;
          }
        ;
//modified by ly
R_d_blockvariable
        : tk_integer R_l_blockvariable ';'
          {
	    $$ = new yaccVal;
	    $$->_str = "";
	    blockvariable(gVariableList);
	    gVariableList.clear();
          }
        | tk_real R_l_blockvariable ';'
          {
	    $$ = new yaccVal;
	    $$->_str = "";
	    blockvariable(gVariableList);
	    gVariableList.clear();
          }
        | tk_string R_l_blockvariable ';'
          {
	    $$ = new yaccVal;
	    $$->_str = "";
	    blockvariable(gVariableList);
	    gVariableList.clear();
          }
        ;
R_l_blockvariable
        : R_s_blockvariable
          {
          }
        | R_l_blockvariable ',' R_s_blockvariable
          {
          }
        ;
R_s_blockvariable
        : tk_ident
          {
              gVariableList.push_back($1->_str);
          }
        | tk_ident '[' tk_number ':' tk_number ']'
          {
              vaMessageError("Array not support now.", $1);
          }
        ;
R_d_contribution
        : R_contribution R_d_attribute_0 ';'
          {
              if(__attrList.size() != 0){
                __attrList.pop_back();
              }
              $$ = $1;
          }
        ;
R_contribution
        : R_source '<' '+' R_s_expression
          {
              bitset<BIT_> tmp;
              statement mystat;
              mystat._describ = (($4->_state).front())._describ;
              mystat._mode = 2;
              mystat._type = true;
              mystat._var = (($4->_state).front())._var;
              mystat._param = $4->_state.front()._param;
              if(gSource->_type == 0 || gSource->_type == 3){
                  // 噪声专用贡献（V(a,b) <+ white_noise(...)）：确定性分析下
                  // 无方程（不是 0V 源），整条跳过，不建伪网络。
                  if(mystat._describ == "0" && mystat._var.empty() && mystat._param.empty()){
                      $$ = $1;
                      delete $4;
                      gSource = NULL;
                  } else {
                  // ===== V(a,b) <+ expr / Temp 等电位贡献：解糖为 MNA 支路电流未知量 =====
                  // 伪网络 $br(pos,neg) 承载支路电流 Ibr：
                  //   KCL: f[pos] += Ibr, f[neg] -= Ibr
                  //   电压方程: f[brIdx] += (V(pos)-V(neg)) - expr
                  // expr 中的 I(a,b) 读取已被 access 规则映射为同一 Ibr。
                  int posNode = gSource->_pos;
                  int negNode = (gSource->_nodenum == 2) ? gSource->_neg : -1;
                  int brIdx = GetOrCreateBranchFlowNet(gModule, posNode, negNode);
                  string posName = gModule->_net[posNode]._name;
                  string negName = (negNode >= 0) ? gModule->_net[negNode]._name : "";
                  string brVar  = "V" + gModule->_net[brIdx]._name;
                  static int beqNum = 0;
                  string beqVar = "__beq" + int2string(beqNum++);

                  // 支路电压变量声明（若模型未曾读取）
                  bitset<BIT_> bitPos; bitPos[posNode] = 1;
                  gModule->_dervar["dV" + posName + "Dv" + int2string(posNode)] = posNode;
                  bitset<BIT_> bitNeg;
                  if(negNode >= 0){
                      bitNeg[negNode] = 1;
                      gModule->_dervar["dV" + negName + "Dv" + int2string(negNode)] = negNode;
                  }
                  bitset<BIT_> bitBr; bitBr[brIdx] = 1;
                  gModule->_dervar["d" + brVar + "Dv" + int2string(brIdx)] = brIdx;

                  // 依赖集合 = 支路两端电压 + RHS 依赖
                  bitset<BIT_> depBits = bitPos | bitNeg;
                  map<string, bitset<BIT_> >::iterator vit;
                  for(vit = mystat._var.begin(); vit != mystat._var.end(); ++vit)
                      depBits |= vit->second;

                  // (1) 赋值: __beq<N> = (V(pos) - V(neg)) - (expr);
                  statement beq;
                  beq._mode = 0;
                  beq._type = true;
                  if(negNode >= 0)
                      beq._describ = beqVar + " = (V" + posName + " - V" + negName + ") - (" + mystat._describ + ");";
                  else
                      beq._describ = beqVar + " = (V" + posName + ") - (" + mystat._describ + ");";
                  beq._var["V" + posName] = bitPos;
                  if(negNode >= 0) beq._var["V" + negName] = bitNeg;
                  for(vit = mystat._var.begin(); vit != mystat._var.end(); ++vit)
                      beq._var[vit->first] = vit->second;
                  beq._param = mystat._param;
                  // 模块变量与导数变量注册
                  variable beqv; beqv._name = beqVar; beqv._type = 2;
                  gModule->_variable.push_back(beqv);
                  for(int i = 0; i < BIT_; ++i)
                      if(depBits[i]) gModule->_tmpdervar["d" + beqVar + "Dv" + int2string(i)] = 1;

                  // (2) V 方程: I($br) <+ __beq<N>
                  statement veq;
                  veq._mode = 2;
                  veq._type = true;
                  veq._describ = beqVar;
                  veq._var[beqVar] = depBits;
                  veq._param = mystat._param;
                  source* srcVeq = new source;
                  srcVeq->_nodenum = 1;
                  srcVeq->_pos = brIdx;
                  srcVeq->_type = 1;
                  for(int i = 0; i < BIT_; ++i)
                      if(depBits[i]) gModule->_matstructrue[brIdx][i] = 1;
                  // 回退方程（Ibr=0）可能需要在未激活支路 stamp 对角元
                  gModule->_matstructrue[brIdx][brIdx] = 1;

                  // (3) KCL pos: I(pos) <+ Ibr
                  statement kclP;
                  kclP._mode = 2;
                  kclP._type = true;
                  kclP._describ = brVar;
                  kclP._var[brVar] = bitBr;
                  source* srcKclP = new source;
                  srcKclP->_nodenum = 1;
                  srcKclP->_pos = posNode;
                  srcKclP->_type = 1;
                  gModule->_matstructrue[posNode][brIdx] = 1;

                  $$ = $1;
                  ($$->_state).push_back(beq);
                  ($$->_state).push_back(veq);
                  ($$->_state).push_back(kclP);
                  gModule->_contribute.push_back(srcVeq);
                  gModule->_contribute.push_back(srcKclP);

                  // (4) KCL neg: I(neg) <+ -Ibr
                  if(negNode >= 0){
                      statement kclN;
                      kclN._mode = 2;
                      kclN._type = true;
                      kclN._describ = "(-" + brVar + ")";
                      kclN._var[brVar] = bitBr;
                      source* srcKclN = new source;
                      srcKclN->_nodenum = 1;
                      srcKclN->_pos = negNode;
                      srcKclN->_type = 1;
                      gModule->_matstructrue[negNode][brIdx] = 1;
                      ($$->_state).push_back(kclN);
                      gModule->_contribute.push_back(srcKclN);
                  }
                  delete $4;
                  gSource = NULL;
                  }  // end else (非噪声 V<+ 解糖)
              } else {
                  // ===== 电流/功率流贡献（原逻辑） =====
                  map<string, bitset<BIT_> >::iterator iter;
                  iter = mystat._var.begin();
                  while(iter != mystat._var.end()){
                      tmp |= iter->second;
                      ++iter;
                  }
                  for(int i=0; i<gModule->_net.size(); ++i){
                      if(tmp[i] != 0){
                          gModule->_matstructrue[gSource->_pos][i] = 1;
                          if(gSource->_nodenum == 2)
                              gModule->_matstructrue[gSource->_neg][i] = 1;
                      }
                  }
                  $$ = $1;
                  ($$->_state).push_back(mystat);
                  delete $4;
                  gModule->_contribute.push_back(gSource);
                  gSource = NULL;
              }
          }
        ;
R_source
        : tk_ident '(' tk_ident ',' tk_ident ')'
          {
              int pos = -1, neg = -1;
              nature* tmp;
              $$ = new yaccVal;
              $$->_str = $1->_str + "(" + $3->_str + "," + $5->_str + ")";
              string pname = $3->_str, nname = $5->_str;
              // branch 别名作为 source 实参 → 展开为 branch 节点
              map<string, branch>::iterator brIt = gModule->_branchAlias.find(pname);
              if(brIt != gModule->_branchAlias.end()){ pname = brIt->second._pnode; nname = brIt->second._nnode; }
              for(int i=0; i<gModule->_net.size(); ++i){
                  if(gModule->_net[i]._name == pname) pos = i;
                  else if(gModule->_net[i]._name == nname) neg = i;
              }
              if(pos == -1)
                  vaMessageError("first node not defined.", $1);
              if(neg == -1)
                  vaMessageError("second node not defined.", $1);
              tmp = IsInNature(__natureList, $1->_str);
              if(tmp == NULL){
                  vaMessageError("Access not defined.", $1);
              } else {
                  gSource = new source;
                  gSource->_nodenum = 2;
                  gSource->_pos = pos;
                  gSource->_neg = neg;
                  if(tmp->_name == "Voltage"){
                      gSource->_type = 0;
                  } else if(tmp->_name == "Current"){
                      gSource->_type = 1;
                  } else if(tmp->_name == "Power")
		    {
		      gSource->_type = 2;
		    } else if(tmp->_name == "Temperature")
		    {
		      gSource->_type = 3;
		    } else {
                      vaMessageError("contrubite source must be Voltage or Current.", $1);
                  }
              }
          }
        | tk_ident '(' tk_ident ')'
          {
              int pos = -1, neg = -1;
              nature* tmp;
              $$ = new yaccVal;
              $$->_str = $1->_str + "(" + $3->_str + ")";
              string pname = $3->_str, nname;
              bool twoNodeBranch = false;
              // branch 别名（单节点 source 实参）→ branch 节点；
              // 双节点 branch（如 I(br_a_ci)）恢复 nodenum=2 的 KCL 对侧 stamp
              map<string, branch>::iterator brIt = gModule->_branchAlias.find(pname);
              if(brIt != gModule->_branchAlias.end()){
                  pname = brIt->second._pnode;
                  if(brIt->second._type == 2){ nname = brIt->second._nnode; twoNodeBranch = true; }
              }
              for(int i=0; i<gModule->_net.size(); ++i){
                  if(gModule->_net[i]._name == pname) pos = i;
                  if(twoNodeBranch && gModule->_net[i]._name == nname) neg = i;
              }
              if(pos == -1)
                  vaMessageError("Node not defined.", $1);
              if(twoNodeBranch && neg == -1)
                  vaMessageError("Node not defined.", $1);
              tmp = IsInNature(__natureList, $1->_str);
              if(tmp == NULL){
                  vaMessageError("Access not defined.", $1);
              } else {
                  gSource = new source;
                  gSource->_nodenum = twoNodeBranch ? 2 : 1;
                  gSource->_pos = pos;
                  if(twoNodeBranch) gSource->_neg = neg;
                  if(tmp->_name == "Voltage"){
                      gSource->_type = 0;
                  } else if(tmp->_name == "Current"){
                      gSource->_type = 1;
                  }
		   else if(tmp->_name == "Power")
		    {
		      gSource->_type = 2;
		    } else if(tmp->_name == "Temperature")
		    {
		      gSource->_type = 3;
		    } else{
                      vaMessageError("contrubite source must be Voltage or Current.", $1);
                  }
              }
          }
        ;
R_d_while
        : tk_while '(' R_s_expression ')' R_analogcode
          {
	    //              cout<<"Warning: while loop detected.\n";
	      $$ = new yaccVal;
              statement mystat;
              mystat._describ = "while(" + $3->_state.front()._describ + "){";
              mystat._mode = 0;
              mystat._type = false;
              map<string, int>::iterator piter;
              piter = $3->_state.front()._param.begin();
              while(piter != $3->_state.front()._param.end()){
                  mystat._param[piter->first] = piter->second;
                  ++piter;
              }
              $$->_state.push_back(mystat);
              list<statement>::iterator iter;
              iter = $5->_state.begin();
              while(iter != $5->_state.end()){
                  if(iter->_var.size() != 0){
                      cout<<(++(iter->_var.begin()))->first<<(++(iter->_var.begin()))->second<<"\t"<<iter->_var.size()<<endl;
                      vaMessageError("The expression under \"for\" loop must indepent to Voltages.\n", $1);
                  }
                  //iter->_describ += ";";
                  $$->_state.push_back(*iter);
                  ++iter;
              }
              mystat._describ = "}";
              $$->_state.push_back(mystat);
              delete $1;
              delete $3;
              delete $5;
          }
        ;
R_d_for
        : tk_for '(' R_s_assignment ';' R_s_expression ';' R_s_assignment ')' R_analogcode
          {
              //cout<<"Warning: for loop detected.\n";
              $$ = new yaccVal;
              statement mystat;
              mystat._describ = "for(" + $3->_state.front()._describ + "; " +
                  $5->_state.front()._describ + "; " + $7->_state.front()._describ + "){";
              mystat._param = $3->_state.front()._param;
              mystat._mode = 0;
              mystat._type = false;
              map<string, int>::iterator piter;
              piter = $5->_state.front()._param.begin();
              while(piter != $5->_state.front()._param.end()){
                  mystat._param[piter->first] = piter->second;
                  ++piter;
              }
              piter = $7->_state.front()._param.begin();
              while(piter != $7->_state.front()._param.end()){
                  mystat._param[piter->first] = piter->second;
                  ++piter;
              }
              $$->_state.push_back(mystat);
              list<statement>::iterator iter;
              iter = $9->_state.begin();
              while(iter != $9->_state.end()){
                  if(iter->_var.size() != 0){
                      cout<<(++(iter->_var.begin()))->first<<(++(iter->_var.begin()))->second<<"\t"<<iter->_var.size()<<endl;
                      vaMessageError("The expression under \"for\" loop must indepent to Voltages.\n", $1);
                  }
                  //iter->_describ += ";";
                  $$->_state.push_back(*iter);
                  ++iter;
              }
              mystat._describ = "}";
              $$->_state.push_back(mystat);
              delete $1;
              delete $3;
              delete $5;
              delete $7;
              delete $9;
          }
        ;
R_d_case
        : tk_case '(' R_s_expression ')'
          {
            // 进入新 case：压栈（嵌套 case 互不干扰），flag 复位
            gCaseStack.push_back(new list<yaccVal*>());
            gCaseFlagStack.push_back(gCaseFlag);
            gCaseFlag = 0;
          }
          R_l_case_item tk_endcase
          {
	    // handle the cases here. calculate the derivations here.
	    list<yaccVal*>::iterator iter;
	    list<yaccVal*>* myCases = gCaseStack.back();
	    gCaseStack.pop_back();
	    gCaseFlag = gCaseFlagStack.back();
	    gCaseFlagStack.pop_back();
	    int numcases = myCases->size();

	    map<string, bitset<BIT_> >::iterator bit_iter;
	    vector<map<string, bitset<BIT_> > > inside;

	    SwitchBlockVariable(gModule, gOutsideZero, inside, numcases);

	    if(inside.size() != numcases)
	      {
		vaMessageError("Case syntax error.\n", $1);
	      }

	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    $$ = new yaccVal;
	    mystat._describ = "switch(" + ($3->_state.front())._describ + "){";
	    mystat._param = $3->_state.front()._param;
	    $$->_state.push_back(mystat);
	    mystat._param.clear();

	    int caseno = 0;
	    list<statement>::iterator state_iter;
	    // all the cases
	    for(iter = myCases->begin(); iter != myCases->end(); ++iter)
	      {
		state_iter = (*iter)->_state.begin();
		while(state_iter != (*iter)->_state.end())
		  {
		    $$->_state.push_back(*state_iter);
		    state_iter++;
		  }

		bit_iter = inside[caseno].begin();
		mystat._mode = 4;
		while(bit_iter != inside[caseno].end())
		  {
		    mystat._describ = GetZeroDerivation(bit_iter->first, bit_iter->second);
		    $$->_state.push_back(mystat);
		    ++bit_iter;
		  }

		mystat._mode = 0;
		mystat._describ = "break;";
		$$->_state.push_back(mystat);
		
		++caseno;
	      }
	    

	    mystat._mode = 0;
	    mystat._describ = "}";
	    $$->_state.push_back(mystat);

	    // clear all the cases
	    for(iter = myCases->begin(); iter != myCases->end(); ++iter)
	      delete *iter;

	    myCases->clear();
	    delete myCases;

	    delete $3;
          }
        ;
R_l_case_item
        : R_s_case_item
          {
	    //    $$ = $1;
	    gCaseStack.back()->push_back($1);
          }
        | R_l_case_item R_s_case_item
          {
	    //  ($$->_state).push_back(($2->_state).front());
	    //  delete $2;
	    gCaseStack.back()->push_back($2);
          }
        ;
R_s_case_item
        : R_l_expression ':' R_analogcode
          {
	    if(gCaseFlag == 0)
	      {
		NewIfVariableBlock(gModule);
		gCaseFlag = 1;
	      }
	    else
	      {
		NewElseVariableBlock(gModule);
	      }
	    // only insert the necessary code; leave the derivations to the full case handler
	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    $$ = new yaccVal;
	    mystat._describ = "case " + ($1->_state.front())._describ + ":";
	    mystat._param = $3->_state.front()._param;
	    $$->_state.push_back(mystat);
	    mystat._param.clear();

	    list<statement>::iterator it;
	    it = $3->_state.begin();
	    while(it != $3->_state.end()) {
	      $$->_state.push_back(*it);
	      ++it;
	    }
	    
          }
        | tk_default ':' R_analogcode
          {
	    if(gCaseFlag == 0)
	      {
		NewIfVariableBlock(gModule);
		gCaseFlag = 1;
	      }
	    else
	      {
		NewElseVariableBlock(gModule);
	      }
	    // only insert the necessary code; leave the derivations to the full case handler
	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    $$ = new yaccVal;
	    mystat._describ = "default:";
	    mystat._param = $3->_state.front()._param;
	    $$->_state.push_back(mystat);
	    mystat._param.clear();

	    list<statement>::iterator it;
	    it = $3->_state.begin();
	    while(it != $3->_state.end()) {
	      $$->_state.push_back(*it);
	      ++it;
	    }
          }
        | tk_default R_analogcode
          {
	    if(gCaseFlag == 0)
	      {
		NewIfVariableBlock(gModule);
		gCaseFlag = 1;
	      }
	    else
	      {
		NewElseVariableBlock(gModule);
	      }
	    
	    // only insert the necessary code; leave the derivations to the full case handler
	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    $$ = new yaccVal;
	    mystat._describ = "default:";
	    mystat._param = $2->_state.front()._param;
	    $$->_state.push_back(mystat);
	    mystat._param.clear();

	    list<statement>::iterator it;
	    it = $2->_state.begin();
	    while(it != $2->_state.end()) {
	      $$->_state.push_back(*it);
	      ++it;
	    }
          }
        ;
R_s_instance
        : R_instance_module_name '#' '(' R_l_instance_parameter ')' tk_ident '(' R_l_node ')' ';'
          {
          }
        ;
R_instance_module_name
        : tk_ident
          {
              vaMessageError("instance module not support now.", $1);
          }
        ;
R_l_instance_parameter
        : R_s_instance_parameter
          {
          }
        | R_l_instance_parameter ',' R_s_instance_parameter
          {
          }
        ;
R_s_instance_parameter
        : '_' tk_ident '(' R_s_expression ')'
          {
          }
        ;
R_s_assignment
        : R_s_assignment_name '=' R_s_expression
          {
              string dvarname;
              $$ = $3;
              $$->_str = $1->_str;
              ($$->_state.front())._describ = $1->_str + " = " + ($$->_state.front())._describ;
              bitset<BIT_> tmpbit;
              map<string, bitset<BIT_> >::iterator iter;
              iter = $3->_state.front()._var.begin();
              while(iter != $3->_state.front()._var.end()){
                  tmpbit = tmpbit | iter->second;
                  ++iter;
              }
              ($$->_state.front())._mode = 0;
              if(tmpbit != 0){
                  $$->_state.front()._type = true;
                  for(int i=0; i<gModule->_net.size(); ++i){
                      dvarname = "d" + $1->_str + "Dv" + int2string(i);
                      if(tmpbit[i] != 0) gModule->_tmpdervar[dvarname] = 1;
                  }
                  //SetVariableType(gModule, $1->_str, tmpbit);
              } else {
                  $$->_state.front()._type = false;
              }
              SetVariableType(gModule, $1->_str, tmpbit);
              delete $1;
          }
        | R_d_attribute R_s_assignment_name '=' R_s_expression
          {
              __attrList.pop_back();
              $$ = $4;
              $$->_str = $2->_str;
              ($$->_state.front())._describ = $2->_str + " = " + ($$->_state.front())._describ;
              SetVariableType(gModule, $1->_str, $$->_type);
          }
        | R_s_assignment_name '[' R_expression ']' '=' R_s_expression
          {
              vaMessageError("Array not support now.", $1);
          }
        ;
R_s_assignment_name
        : tk_ident
          {
              $$ = new yaccVal;
              // 命名块局部变量 LHS 解析（delta → delta__b3）
              string blk = ResolveBlockLocal($1->_str);
              $$->_str = blk.empty() ? $1->_str : blk;
          }
        ;
R_d_conditional
        : tk_if '(' R_s_expression ')' R_analogcode
          {
              statement mystat;
              mystat._mode = 0;
              mystat._type = false;
              $$ = new yaccVal;
              mystat._describ = "if(" + ($3->_state.front())._describ + "){";
              mystat._param = $3->_state.front()._param;
              $$->_state.push_back(mystat);
              mystat._param.clear();
              list<statement>::iterator it;
              it = $5->_state.begin();
              while(it != $5->_state.end()){
                  $$->_state.push_back(*it);
                  ++it;
              }
              map<string, bitset<BIT_> >  inside;
              IfBlockVariable(gModule, gOutsideZero, inside);
              map<string, bitset<BIT_> >::iterator iter;
              mystat._mode = 4;
              iter = inside.begin();
              while(iter != inside.end()){
                mystat._describ = GetZeroDerivation(iter->first, iter->second);
                $$->_state.push_back(mystat);
                ++iter;
              }
              mystat._mode = 0;
              mystat._describ = "}";
              $$->_state.push_back(mystat);
              delete $3;
              delete $5;
          } %prec PREC_IF_THEN
        | tk_if '(' R_s_expression ')' R_analogcode tk_else R_analogcode
          {

	    yaccVal *t1, *t2, *t3;
	    t1 = $3; t2 = $5; t3 = $7;
	    
            vector<map<string, bitset<BIT_> > > inside;
            map<string, bitset<BIT_> > insideif, insideelse;
            map<string, bitset<BIT_> >::iterator iter;
            SwitchBlockVariable(gModule, gOutsideZero, inside, 2);
            if(inside.size() != 2){
              vaMessageError("Error while deal with if-else statement.\n", $1);
            } else {
              insideif = inside[0];
              insideelse = inside[1];
            }
            statement mystat;
            mystat._mode = 0;
            mystat._type = false;
            $$ = new yaccVal;
            mystat._describ = "if(" + ($3->_state.front())._describ + "){";
            mystat._param = $3->_state.front()._param;
            $$->_state.push_back(mystat);
            mystat._param.clear();
            mystat._mode = 4;
            list<statement>::iterator it;
            it = $5->_state.begin();
            while(it != $5->_state.end()){
              $$->_state.push_back(*it);
              ++it;
            }
            iter = insideif.begin();
            while(iter != insideif.end()){
              mystat._describ = GetZeroDerivation(iter->first, iter->second);
              $$->_state.push_back(mystat);
              ++iter;
            }
            mystat._describ = "} else {";
            mystat._mode = 0;
            $$->_state.push_back(mystat);
            mystat._mode = 4;
            it = $7->_state.begin();
            while(it != $7->_state.end()){
              $$->_state.push_back(*it);
              ++it;
            }
            iter = insideelse.begin();
            while(iter != insideelse.end()){
              mystat._describ = GetZeroDerivation(iter->first, iter->second);
              $$->_state.push_back(mystat);
              ++iter;
            }
            mystat._describ = "}";
            mystat._mode = 0;
            $$->_state.push_back(mystat);
            delete $3;
            delete $5;
            delete $7;
          }
        ;
R_s_expression
        : R_expression
          {
              $$ = $1;
          }
        ;
R_l_callfunction_expression
        : R_s_expression
          {
              $$ = $1;
              $$->_num = 1;
          }
        | R_l_callfunction_expression ',' R_s_expression
          {
              ($$->_state).push_back(($3->_state).front());
              $$->_num += 1;
              delete $3;
          }
        ;
R_l_expression
        : R_s_function_expression
          {
              $$ = $1;
              $$->_num = 1;
          }
        | R_l_expression ',' R_s_function_expression
          {
              $$ = $1;
              ($$->_state).push_back(($3->_state).front());
              delete $3;
              $$->_num += 1;
          }
        ;
R_s_function_expression
        : R_expression
          {
            $$=$1;
          }
        ;
R_expression
        : R_e_conditional
          {
            $$=$1;
          }
        ;
R_e_conditional
        : R_e_bitwise_equ
          {
            $$=$1;
          }
        | R_e_bitwise_equ '?' R_e_bitwise_equ ':' R_e_bitwise_equ
          {
              $$ = $1;
              statement &tmp = ($$->_state).front();
              statement &tmp1 = ($3->_state).front();
              statement &tmp2 = ($5->_state).front();
              tmp._describ += "?" + tmp1._describ + " : " + tmp2._describ;
              $$->_type = $5->_type | $3->_type;
              map<string, bitset<BIT_> >::iterator iter;
              iter = tmp1._var.begin();
              (tmp._var).clear();
              while(iter != tmp1._var.end()){
                  tmp._var[iter->first] = iter->second;
                  ++iter;
              }
              iter = tmp2._var.begin();
              while(iter != tmp2._var.end()){
                  tmp._var[iter->first] = iter->second;
                  ++iter;
              }
              map<string, int>::iterator pit;
              pit = tmp1._param.begin();
              while(pit != tmp1._param.end()){
                  tmp._param[pit->first] = pit->second;
                  ++pit;
              }
              pit = tmp2._param.begin();
              while(pit != tmp2._param.end()){
                  tmp._param[pit->first] = pit->second;
                  ++pit;
              }
              delete $3;
              delete $5;
          }
        ;

//modified by ly
R_e_bitwise_equ
        : R_e_bitwise_xor
          {
              $$ = $1;
          }
        | R_e_bitwise_equ tk_bitwise_equr R_e_bitwise_xor
          {
              R_e_bitwise($$, $1, $3, "^~");
          }
        | R_e_bitwise_equ '~' '^' R_e_bitwise_xor
          {
              R_e_bitwise($$, $1, $4, "~^");
          }
        ;
R_e_bitwise_xor
        : R_e_bitwise_or
          {
            $$=$1;
          }
        | R_e_bitwise_xor '^' R_e_bitwise_or
          {
             R_e_bitwise($$, $1, $3, "^");
          }
        ;
R_e_bitwise_or
        : R_e_bitwise_and
          {
            $$=$1;
          }
        | R_e_bitwise_or '|' R_e_bitwise_and
          {
             R_e_bitwise($$, $1, $3, "|");
          }
        ;
R_e_bitwise_and
        : R_e_logical_or
          {
            $$=$1;
          }
        | R_e_bitwise_and '&' R_e_logical_or
          {
             R_e_bitwise($$, $1, $3, "&");
          }
        ;
R_e_logical_or
        : R_e_logical_and
          {
            $$=$1;
          }
        | R_e_logical_or tk_or R_e_logical_and
          {
             R_e_bitwise($$, $1, $3, "||");
          }
        ;
R_e_logical_and
        : R_e_comp_equ
          {
            $$=$1;
          }
        | R_e_logical_and tk_and R_e_comp_equ
          {
              R_e_bitwise($$, $1, $3, "&&");
          }
        ;
R_e_comp_equ
        : R_e_comp
          {
            $$=$1;
          }
        | R_e_comp_equ '=' '=' R_e_comp
          {
             R_e_bitwise($$, $1, $4, "==");
          }
        | R_e_comp_equ '!' '=' R_e_comp
          {
             R_e_bitwise($$, $1, $4, "!=");
          }
        ;
R_e_comp
        : R_e_bitwise_shift
          {
            $$=$1;
          }
        | R_e_comp '<' R_e_bitwise_shift
          {
              R_e_bitwise($$, $1, $3, "<");
          }
        | R_e_comp '<' '=' R_e_bitwise_shift
          {
              R_e_bitwise($$, $1, $4, "<=");
          }
        | R_e_comp '>' R_e_bitwise_shift
          {
              R_e_bitwise($$, $1, $3, ">");
          }
        | R_e_comp '>' '=' R_e_bitwise_shift
          {
              R_e_bitwise($$, $1, $4, ">=");
          }
        ;
R_e_bitwise_shift
        : R_e_arithm_add
          {
            $$=$1;
          }
        | R_e_bitwise_shift tk_op_shr R_e_arithm_add
          {
              R_e_bitwise($$, $1, $3, ">>");
          }
        | R_e_bitwise_shift tk_op_shl R_e_arithm_add
          {
              R_e_bitwise($$, $1, $3, "<<");
          }
        ;
R_e_arithm_add
        : R_e_arithm_mult
          {
            $$=$1;
          }
        | R_e_arithm_add '+' R_e_arithm_mult
          {
              R_e_bitwise($$, $1, $3, "+");
          }
        | R_e_arithm_add '-' R_e_arithm_mult
          {
              R_e_bitwise($$, $1, $3, "-");
          }
        ;
R_e_arithm_mult
        : R_e_unary
          {
              $$=$1;
          }
        | R_e_arithm_mult '*' R_e_unary
          {
              R_e_bitwise($$, $1, $3, "*");
          }
        | R_e_arithm_mult '/' R_e_unary
          {
              R_e_bitwise($$, $1, $3, "/");
          }
        | R_e_arithm_mult '%' R_e_unary
          {
              R_e_bitwise($$, $1, $3, "%");
          }
        ;
R_e_unary
        : R_e_atomic
          {
              $$ = $1;
          }
        | '+' R_e_unary
          {
              $$ = $2;
          }
        | '-' R_e_unary
          {
              // 递归单目：支持 `- -x`（宏展开 `-`MACRO 产生的双负号）
              $$ = $2;
              $$->_value = -($$->_value);
              (($$->_state).front())._describ = "(-" + (($$->_state).front())._describ + ")";
          }
        | '!' R_e_atomic
          {
	    $$ = $2;
	    (($$->_state).front())._describ = "(!(" + (($$->_state).front())._describ + "))";
	    //              vaMessageError("Unsupport !", $2);
          }
        | '~' R_e_atomic
          {
              vaMessageError("Unsupport ~", $2);
          }
        ;
R_e_atomic
        : tk_number
          {
              statement mystat;
              mystat._describ = $1->_str;
              $$ = new yaccVal;
              $$->_value = string2double($1->_str);
              ($$->_state).push_back(mystat);
          }
        | tk_number tk_ident
          {
              string myunit;
              if(0) { }
              else if(($2->_str == "E")) myunit = "1e18";
              else if(($2->_str == "P")) myunit = "1e15";
              else if(($2->_str == "T")) myunit = "1e12";
              else if(($2->_str == "G")) myunit = "1e9";
              else if(($2->_str == "M")) myunit = "1e6";
              else if(($2->_str == "k")) myunit = "1e3";
              else if(($2->_str == "h")) myunit = "100";
              else if(($2->_str == "D")) myunit = "10";
              else if(($2->_str == "d")) myunit = "0.1";
              else if(($2->_str == "c")) myunit = "0.01";
              else if(($2->_str == "m")) myunit = "1e-3";
              else if(($2->_str == "u")) myunit = "1e-6";
              else if(($2->_str == "n")) myunit = "1e-9";
              else if(($2->_str == "A")) myunit = "1e-10";
              else if(($2->_str == "p")) myunit = "1e-12";
              else if(($2->_str == "f")) myunit = "1e-15";
              else if(($2->_str == "a")) myunit = "1e-18";
              else
                  vaMessageError("can not convert symbol to valid unit\n",$2);
              statement mystat;
              mystat._describ = $1->_str + "*" + myunit;
              $$ = new yaccVal;
              $$->_value = string2double($1->_str) * string2double(myunit);
              ($$->_state).push_back(mystat);
          }
        | tk_char
          {
            vaMessageError("%s: character are not handled\n",$1);
          }
        | tk_anystring
          {
              statement mystat;
              mystat._describ = "\"" + $1->_str + "\"";
              $$ = new yaccVal;
              $$->_str = $1->_str;
              $$->_state.push_back(mystat);
          }
        | tk_ident
          {
              $$ = new yaccVal;
              statement mystat;
              parameter *mypar;
              int typ;
              bitset<BIT_> mytype;
              if(gAnalogfunction)
              {
                  // 函数体内标识符：先查形参/局部变量（电压无关），
                  // 再查模块变量与参数（如模型参数引用）
                  if(gAnalogfunction->_var.count($1->_str)){
                      mystat._describ = $1->_str;
                  } else if(IsModuleVariable(gModule, $1->_str)){
                      mystat._describ = $1->_str;
                      mytype = GetVariableType(gModule, $1->_str);
                      if(mytype != 0) (mystat._var)[$1->_str] = mytype;
                  } else if(mypar = IsInParam(gModule, $1->_str)) {
                      mystat._describ = $1->_str;
                      if(mypar->_type == 1) typ = 1;
                      else typ = 0;
                      mystat._param[$1->_str] = typ;
                  } else {
                      vaMessageError("identifier never declared",$1);
                  }
              }
              else
              {
                  // 命名块局部变量优先（内层块遮蔽外层）
                  string blk = ResolveBlockLocal($1->_str);
                  if (!blk.empty()) {
                      mystat._describ = blk;
                      mytype = GetVariableType(gModule, blk);
                      if (mytype != 0) (mystat._var)[blk] = mytype;
                  } else if(IsModuleVariable(gModule, $1->_str)){
                      mystat._describ = $1->_str;
                      mytype = GetVariableType(gModule, $1->_str);
                      if(mytype != 0) (mystat._var)[$1->_str] = mytype;
                  } else if(mypar = IsInParam(gModule, $1->_str)) {
                      mystat._describ = $1->_str;
                      if(mypar->_type == 1) typ = 1;
                      else typ = 0;
                      mystat._param[$1->_str] = typ;
                  } else {
                      if(GetNameNum(gModule, $1->_str) != -1) mystat._describ = $1->_str;
                      else if(gModule->_branchAlias.count($1->_str)) mystat._describ = $1->_str;  // branch 别名: 由 access 规则展开
                      else vaMessageError("identifier never declared",$1);
                  }
              }
              ($$->_state).push_back(mystat);
              $$->_type = mytype;
          }
        | tk_dollar_ident
          {
              string mystr;
              mystr = GetDollarValue($1->_str);
              $$ = new yaccVal;
              statement mystat;
              mystat._describ = mystr;
              ($$->_state).push_back(mystat);
          }
        | tk_ident '[' R_expression ']'
          {
              vaMessageError("Array not support now.", $1);
          }
        | tk_dollar_ident '(' R_l_expression ')'
          {
	    $$ = new yaccVal;
	    statement mystat;
	    map<string, int>::iterator piter;
	    mystat._param = ($3->_state).front()._param;
	    if($1->_str == "$param_given")
	      {
		// $param_given(NAME) → given_<name>_ 成员（.model 显式设置后置 1）
		string pname = ($3->_state).front()._describ;
		if(pname.size() >= 2 && pname.front() == '"' && pname.back() == '"')
		  pname = pname.substr(1, pname.size() - 2);
		mystat._describ = "given_" + pname + "_";
	      }
	    else if($1->_str == "$strobe")
	      {
		mystat._describ = "printf(\"" + ($3->_state).front()._describ + "\")";		
		mystat._mode = 5;
	      }
	    else if($1->_str == "$simparam")
	      {
		// $simparam("gmin", 1e-12) → 生成模型成员 simparam_<name>_，
		// 默认值取第二实参表达式（codegen 以成员初始化形式发出）。
		string spname = ($3->_state).front()._describ;
		// 去掉字符串字面量的引号
		if(spname.size() >= 2 && spname.front() == '"' && spname.back() == '"')
		  spname = spname.substr(1, spname.size() - 2);
		string dflt = "0.0";
		if(($3->_state).size() >= 2) dflt = ($3->_state).back()._describ;
		gModule->_simparamDflt[spname] = dflt;
		mystat._describ = "simparam_" + spname + "_";
	      }
	    else if($1->_str == "$vt")
	      {
		// $vt(T) = k*T/q（带显式温度实参；无参 $vt 走 GetDollarValue→temp_）
		// Constants aligned to HSPICE/FineSim: KboQ = 8.617087e-5
		mystat._describ = "(1.38062E-23 * (" + ($3->_state).front()._describ + ") / 1.60219E-19)";
	      }
	    else
	      mystat._describ = "(0)";
	    SetVariableType(gModule, $1->_str, 0);
	    ($$->_state).push_back(mystat);
	    
	    //              vaMessageError("DollarIdent function.", $1);
          }
        | tk_ident '(' R_l_expression ')'
          {
              int pos, neg;
              list<statement>::iterator iter;
              bitset<BIT_> tmpbit;
              statement mystat;
              string tmp;
              if(IsInNature(__natureList, $1->_str)){
                  if($3->_num == 1){
                      iter = $3->_state.begin();
                      string argName = (*iter)._describ;
                      map<string, branch>::iterator brIt = gModule->_branchAlias.find(argName);
                      if(brIt != gModule->_branchAlias.end() && brIt->second._type == 2){
                          // V(br)/Temp(br) 双节点 branch 别名 → 展开为 V(pnode, nnode)
                          string pnode = brIt->second._pnode;
                          string nnode = brIt->second._nnode;
                          pos = GetNameNum(gModule, pnode);
                          neg = GetNameNum(gModule, nnode);
                          if(pos == -1 || neg == -1)vaMessageError("Branch node not defined.", $1);
                          tmpbit[pos] = 1;
                          mystat._var[$1->_str + pnode] = tmpbit;
                          tmp = "d" + $1->_str + pnode + "Dv" + int2string(pos);
                          gModule->_dervar[tmp] = pos;
                          $$ = new yaccVal;
                          mystat._describ = "(" + $1->_str + pnode;
                          tmpbit = 0;
                          tmpbit[neg] = 1;
                          mystat._var[$1->_str + nnode] = tmpbit;
                          tmp = "d" + $1->_str + nnode + "Dv" + int2string(neg);
                          gModule->_dervar[tmp] = neg;
                          mystat._describ += " - " + $1->_str + nnode + ")";
                          $$->_state.push_back(mystat);
                          ($$->_type)[pos] = 1;
                          ($$->_type)[neg] = 1;
                          delete $3;
                      } else {
                          if(brIt != gModule->_branchAlias.end()) argName = brIt->second._pnode;  // 单节点 branch
                          pos = GetNameNum(gModule, argName);
                          if(pos == -1)vaMessageError("Acess must take a port num.", $1);
                          tmpbit[pos] = 1;
                          mystat._var[$1->_str + argName] = tmpbit;
                          tmp = "d" + $1->_str + argName + "Dv" + int2string(pos);
                          gModule->_dervar[tmp] = pos;
                          $$ = new yaccVal;
                          mystat._describ = $1->_str + argName;
                          $$->_state.push_back(mystat);
                          ($$->_type)[pos] = 1;
                          delete $3;
                      }
                  }else if($3->_num == 2){
                      iter = $3->_state.begin();
                      pos = GetNameNum(gModule, (*iter)._describ);
                      if(pos == -1)vaMessageError("Acess must take port nums.", $1);
                      neg = GetNameNum(gModule, (*(++iter))._describ);
                      if(neg == -1)vaMessageError("Acess must take a port num.", $1);
                      nature* nat = IsInNature(__natureList, $1->_str);
                      if(nat != NULL && nat->_name == "Current"){
                          // I(a,b) 读取 → 该 node pair 的 V<+ 支路电流未知量 Ibr
                          // （若对应 V(a,b) <+ 尚未出现，先建伪网络，
                          //   该支路最终必须有 V<+ 否则矩阵奇异）
                          int brIdx = GetOrCreateBranchFlowNet(gModule, pos, neg);
                          string brVar = "V" + gModule->_net[brIdx]._name;
                          tmpbit = 0;
                          tmpbit[brIdx] = 1;
                          gModule->_dervar["d" + brVar + "Dv" + int2string(brIdx)] = brIdx;
                          $$ = new yaccVal;
                          mystat._var[brVar] = tmpbit;
                          mystat._describ = brVar;
                          $$->_state.push_back(mystat);
                          ($$->_type)[brIdx] = 1;
                      } else {
                      iter = $3->_state.begin();
                      tmpbit[pos] = 1;
                      tmp = "d" + $1->_str + (*iter)._describ + "Dv" + int2string(pos);
                      gModule->_dervar[tmp] = pos;
                      mystat._var[$1->_str + (*iter)._describ] = tmpbit;
                      $$ = new yaccVal;
                      mystat._describ = "(" + $1->_str + (*iter)._describ;
                      ++iter;
                      tmpbit = 0;
                      tmpbit[neg] = 1;
                      tmp = "d" + $1->_str + (*iter)._describ + "Dv" + int2string(neg);
                      gModule->_dervar[tmp] = neg;
                      mystat._describ += " - " + $1->_str + (*iter)._describ + ")";
                      mystat._var[$1->_str + (*iter)._describ] = tmpbit;
                      $$->_state.push_back(mystat);
                      ($$->_type)[pos] = 1;
                      ($$->_type)[neg] = 1;
                      }
                      delete $3;
                  }else{
                      vaMessageError("Too many ports of access.", $1);
                  }
              }else{
                  analogFun *af = FindAnalogFun(gModule, $1->_str);
                  if(af == NULL){
                      vaMessageError("Undefined access of function: " + $1->_str, $1);
                  }else{
                      if(af->_type == 0 || af->_type == 1 || af->_type == 2){
                          $$ = $3;
			  yaccVal * t = $3;
                          if(af->_name == "ddt"){
                              map<string, bitset<BIT_> >::iterator mit;
                              mit = $$->_state.back()._var.begin();
                              while(mit != $$->_state.back()._var.end()){
                                  tmpbit |= mit->second;
                                  ++mit;
                              }
                              tmp = int2string(__modDdtNum);
                              SetVariableType(gModule, "DdtExp"+tmp, tmpbit);
                              SetVariableType(gModule, "DdtAns"+tmp, tmpbit);
                              mystat._describ = "DdtExp" + tmp + " = " + ($$->_state.back())._describ + ";";
                              mystat._var = $$->_state.back()._var;
                              mystat._param = $$->_state.back()._param;
                              mystat._mode = 0;
                              if(mystat._var.size() != 0) mystat._type = true;
                              gStateList.push_back(mystat);
			      //   mystat._describ = "stateVariable_.SetCurrentStateVariable(States::DdtVal" + tmp + ", DdtExp" + tmp + ");";
			      //  mystat._var.clear();
			      //  mystat._type = false;
			      // gStateList.push_back(mystat);
                              mystat._mode = 0;
			      //      mystat._describ = "DdtAns" + tmp + " = equation->DoDdt(stateVariable_, States::DdtVal" + tmp + ");";
			      mystat._describ = "DdtAns" + tmp + " = DdtExp" + tmp + ";";
                              gStateList.push_back(mystat);
                              for(int i=0; i<gModule->_net.size(); ++i){
                                  if(tmpbit[i] != 0){
                                      mystat._describ = "dDdtAns" + tmp + "Dv" + int2string(i) + " = " + "dDdtExp" + tmp + "Dv" + int2string(i) + " * _der0;";
                                      mystat._mode = 4;
                                      gModule->_tmpdervar["dDdtAns" + tmp + "Dv" + int2string(i)] = 1;
                                      gModule->_tmpdervar["dDdtExp" + tmp + "Dv" + int2string(i)] = 1;
                                      gStateList.push_back(mystat);
                                  }
                              }
                              ++__modDdtNum;
                              tmp = "DdtAns" + tmp;
                              ($$->_state.back())._describ = tmp;
                              ($$->_state.back())._var.clear();
                              tmpbit = GetVariableType(gModule, tmp);
                              if(tmpbit != 0)($$->_state.back())._var[tmp] = tmpbit;
                          } else if (af->_name == "ddx"){
                            // ddx(expr, V(node)): 仅用于 opvar 输出（cd/gd 等），
                            // 不影响 f/jac 仿真结果。暂以 0.0 近似（opvar 值不可比）。
                              $$->_state.clear();
                              mystat._describ = "0.0";
                              mystat._mode = 0;
                              $$->_state.push_back(mystat);
                          } else if (af->_name == "limexp"){
                            // limexp(x) → exp(x)：工作区内与 openvaf 一致；
                            // 极端饱和区（x 很大）openvaf 会限幅，此处不限（TODO）
                              ($$->_state.back())._describ = "exp(" + ($$->_state.back())._describ + ")";
                          } else if (af->_name == "analysis"){
                              $$->_state.clear();
                              mystat._describ = "1.0";
                              mystat._mode = 0;
                              $$->_state.push_back(mystat);
                          } else if (af->_name == "param_given"){
                              ($$->_state.back())._describ = "given_" + ($$->_state.back())._describ + "_";
                          } else if (af->_name == "port_connected"){
                              $$->_state.clear();
                              mystat._describ = "1.0";
                              mystat._mode = 0;
                              $$->_state.push_back(mystat);
                          } else if (af->_name == "ac_stim" || af->_name == "last_crossing" || af->_name == "timer" || af->_name == "above" || af->_name == "cross"){
                              $$->_state.clear();
                              mystat._describ = "0.0";
                              mystat._mode = 0;
                              $$->_state.push_back(mystat);
                          } else if (af->_name == "transition" || af->_name == "slew"){
                              // pass through first arg (already in $$)
                          } else if (af->_name == "white_noise" || af->_name == "flicker_noise"){
                              $$->_state.clear();
                              mystat._describ = "0";
                              mystat._mode = 0;
                              $$->_state.push_back(mystat);
                          } else if (af->_name == "ln") {
                              ($$->_state.back())._describ = "log(" + ($$->_state.back())._describ + ")";
                          } else if (af->_name == "log") {
                              ($$->_state.back())._describ = "log10(" + ($$->_state.back())._describ + ")";
                          } else if (af->_name == "abs") {
                              ($$->_state.back())._describ = "fabs(" + ($$->_state.back())._describ + ")";
                          } else if (af->_name == "pow" || af->_name == "max" || af->_name == "min") {
                              if($3->_num != 2) vaMessageError("pow must take 2 params.", $1);
                              ($$->_state.front())._describ = $1->_str + "(" + ($$->_state.front())._describ + ", " + ($$->_state.back())._describ + ")";
                              // 合并第二实参的 _var/_param（否则其中的模型参数
                              // 不会替换为成员名、电压依赖跟踪也会丢失）
                              {
                                map<string, bitset<BIT_> >::iterator vit2 = ($$->_state.back())._var.begin();
                                while(vit2 != ($$->_state.back())._var.end()){
                                  ($$->_state.front())._var[vit2->first] = vit2->second;
                                  ++vit2;
                                }
                                map<string, int>::iterator pit2 = ($$->_state.back())._param.begin();
                                while(pit2 != ($$->_state.back())._param.end()){
                                  ($$->_state.front())._param[pit2->first] = pit2->second;
                                  ++pit2;
                                }
                              }
                              $$->_state.pop_back();
                          } else if (af->_type == 2) {
                              // ===== 用户 analog function 调用：内联展开 =====
                              // f(a1..an) → 形参替换为实参表达式、局部变量/返回值加
                              // 唯一后缀，函数体语句内联到 gStateList（随当前语句前发射）。
                              static int afInlineNum = 0;
                              string suffix = "__af" + int2string(afInlineNum++);
                              string retVar = af->_name + suffix;

                              // 收集实参（表达式文本 + 电压依赖 + 参数引用）
                              vector<string> argDesc;
                              vector<map<string, bitset<BIT_> > > argVar;
                              vector<map<string, int> > argParam;
                              for(list<statement>::iterator ait = $3->_state.begin();
                                  ait != $3->_state.end(); ++ait){
                                  argDesc.push_back(ait->_describ);
                                  argVar.push_back(ait->_var);
                                  argParam.push_back(ait->_param);
                              }
                              if(getenv("VA_DEBUG_AF")){
                                  fprintf(stderr, "[af] %s: interface=", af->_name.c_str());
                                  for(size_t _f = 0; _f < af->_interface.size(); ++_f)
                                      fprintf(stderr, "%s ", af->_interface[_f]._name.c_str());
                                  fprintf(stderr, "| args=");
                                  for(size_t _a = 0; _a < argDesc.size(); ++_a)
                                      fprintf(stderr, "[%s] ", argDesc[_a].c_str());
                                  fprintf(stderr, "| locals=");
                                  for(map<string, varType>::iterator _l = af->_var.begin(); _l != af->_var.end(); ++_l)
                                      fprintf(stderr, "%s ", _l->first.c_str());
                                  fprintf(stderr, "| bodysteps=%d\n", (int)af->_state._steps.size());
                                  for(list<statement>::iterator _b = af->_state._steps.begin(); _b != af->_state._steps.end(); ++_b)
                                      fprintf(stderr, "[af body] %s\n", _b->_describ.c_str());
                              }

                              // 形参索引
                              map<string, int> formalIdx;
                              for(size_t fi = 0; fi < af->_interface.size(); ++fi)
                                  formalIdx[af->_interface[fi]._name] = (int)fi;

                              // 局部变量（af->_var 中非形参）重命名并声明
                              map<string, string> lrename;
                              for(map<string, varType>::iterator lit = af->_var.begin();
                                  lit != af->_var.end(); ++lit){
                                  if(formalIdx.count(lit->first)) continue;
                                  lrename[lit->first] = lit->first + suffix;
                                  variable lv; lv._name = lit->first + suffix; lv._type = 2;
                                  gModule->_variable.push_back(lv);
                              }
                              variable rv; rv._name = retVar; rv._type = 2;
                              gModule->_variable.push_back(rv);

                              // 名称替换：形参→(实参表达式)、局部→加后缀、函数名→返回变量

                              // 内联函数体
                              bitset<BIT_> bodyDeps;
                              for(list<statement>::iterator fit = af->_state._steps.begin();
                                  fit != af->_state._steps.end(); ++fit){
                                  statement ns = *fit;
                                  ns._describ = AfSubstNames(fit->_describ, af, lrename, argDesc, retVar);
                                  // _var 重映射：形参→实参依赖、局部/函数名→重命名
                                  map<string, bitset<BIT_> > nvar;
                                  for(map<string, bitset<BIT_> >::iterator vit3 = fit->_var.begin();
                                      vit3 != fit->_var.end(); ++vit3){
                                      if(formalIdx.count(vit3->first)){
                                          int fi = formalIdx[vit3->first];
                                          if(fi < (int)argVar.size()){
                                              for(map<string, bitset<BIT_> >::iterator av = argVar[fi].begin();
                                                  av != argVar[fi].end(); ++av)
                                                  nvar[av->first] = av->second;
                                          }
                                      } else if(lrename.count(vit3->first)){
                                          nvar[lrename[vit3->first]] = vit3->second;
                                      } else if(vit3->first == af->_name){
                                          nvar[retVar] = vit3->second;
                                      } else {
                                          nvar[vit3->first] = vit3->second;
                                      }
                                  }
                                  ns._var = nvar;
                                  // 实参的模型参数引用传入内联语句（否则替换不成成员名）
                                  for(size_t _ai = 0; _ai < argParam.size(); ++_ai){
                                      for(map<string, int>::iterator ap = argParam[_ai].begin();
                                          ap != argParam[_ai].end(); ++ap)
                                          ns._param[ap->first] = ap->second;
                                  }
                                  bitset<BIT_> deps;
                                  for(map<string, bitset<BIT_> >::iterator vit4 = nvar.begin();
                                      vit4 != nvar.end(); ++vit4) deps |= vit4->second;
                                  bodyDeps |= deps;
                                  // LHS 导数临时变量注册
                                  size_t eqp = fit->_describ.find('=');
                                  if(eqp != string::npos){
                                      string lhs = fit->_describ.substr(0, eqp);
                                      while(!lhs.empty() && (lhs.back()==' '||lhs.back()=='\t')) lhs.pop_back();
                                      string lhsNew = lrename.count(lhs) ? lrename[lhs]
                                                        : (lhs == af->_name ? retVar : lhs);
                                      for(int i = 0; i < BIT_; ++i)
                                          if(deps[i]) gModule->_tmpdervar["d" + lhsNew + "Dv" + int2string(i)] = 1;
                                  }
                                  gStateList.push_back(ns);
                              }

                              // 调用点表达式 → 返回变量
                              $$ = new yaccVal;
                              mystat._describ = retVar;
                              if(bodyDeps != 0) mystat._var[retVar] = bodyDeps;
                              ($$->_type) = bodyDeps;
                              $$->_state.push_back(mystat);
                          } else {
                              ($$->_state.back())._describ = $1->_str + "(" + ($$->_state.back())._describ + ")";
                          }
                      }
                      else {
                          vaMessageError("Analog function not impl yet.", $1);
                      }
                  }
              }
          }
        | '(' R_expression ')'
          {
            $$ = $2;
            $$->_state.front()._describ = "(" + $$->_state.front()._describ + ")";
          }
        ;
%%

void verilogerror(char *)
{
}

void adms_veriloga_setint_yydebug(const int val)
{
  yydebug=val;
}
