# Analyzer 
       Parsing is the process that occurs at the first stage. It process
    the user defined verilog file into abstract syntax tree (aka. AST ),
    which is an aproach of recording analytical information of verilog
    source code by using a tree structure. AST represent the exact and
    acurate meaning of the original source code.

## Pre-processor

      1. Inheritation
           Transplant from an old pre-processor is a lot easier than
         writing a new one out of lex and yacc.
           And easier for error handling.

      2. Fundamental Coding
           Lacking help from flex and bison in pre-processor operation, we have
         to build our own lexical-scanning engine and syntax-processing engine.
           In both scanning procedural, we use finite state machine to identify
         each keywords, identifiers, and other important information in verilog
         HDL source code.

      3. Compiler Directives
           Compiler directives are flags manipulating the compiling
         process, determining the final source code.
           All verilog HDL compiler directives are preceded by the '`'
         character. This character is called accent grave. It is
         different from the character ''', which is the single quote
         character.
           The scope of compiler directives extends from the point where
         it is processed, across all files processed, to the point where
         another compiler directive supersedes it or the processing
         completes.

	 We now fully support
                  * `default_nettype
                  * `nounconnected_drive
                  * `unconnected_drive
                  * `define
                  * `resetall
                  * `include
                  * `lineno
                  * `undef
                  * `ifdef
                  * `ifndef
                  * `elsif
                  * `else
                  * `endif

      4. Define structure

         * We use hash table to store all definitions.

         * Each definitions has variables and non-variable-strings,
            so we store them separately in string_contents and
            var_contents these two vectors. Each token takes one place.
            Strings and Variables appear in definitions one by one, that
            is anything besides variables are strings.

            Each define structure has these informations
              _type     : whether has variables
              _num_vars : how many variables
              _name     : define name
              _vars     : ptr of std::string, points to actual variables
              _cstrings : contents of string, in std::vector<std::string>
              _cvars    : contents of variables, in std::vector<int>
              _dfa_dag  : a directive-acyclic-graph to store whether
                          a variable is in the definition ( can use
                          std::map instead )

         * Perfect hash function : gperf
              In lexical scanning process, we have to identify whether
            a word with '`' prefix is compiler directives, we have to
            build a system to check.
              Here we use perfect hash function to perform this check.
            And we use gnu::gperf tool to generate this perfect-hash-
            function c++ code.
              For more information, we can manpage it.
            
      5. FSM Processor
           In order to identify tokens for pre-processor, we use finite
         state machine to scan our source code, generating the lexical
         token we can use for further processing. And we use fsm to
         process the tokens generated above.
           FSM graphs are in ../dot_view .

      6. If-elseif-else Structure
           Currently, along with `include directive, all if-elif-else
         structure are supported and tested.

 ## Processor
          The main parser will complete in 2 rounds.

        1st, we will perform lex and yacc engine to check static syntax
             structure error, and form whole abstract-syntax-tree at the
             same time.

        2st, we will try to form symbol table, do type deduction, check
             cyclic module instantiations, calculate const-numbers, and 
             unfold const-loop structure and const-conditional structure.

 ### Structure
                we will use a self-recursive manner of structure to illustrate
              whole syntax tree.
            
                basic information of this structure includes
              * unique and primary identifier given upon spawn
              * type which determines the basic categories of node
              * detail type including further and more specific information
              * hint cluster information to guide the parser doing analysis
              * scope information deciding the level of node in Symbol-Table
              * module, and birth module ptr for detailed-recognition
              * line and column, together with other information for debug
                 and error output
          
              p.s. considering the syntax-tree-level could be veri deep,
                 especially when encountering instantiations, we will not do
                 parsing procedural in recursive-function.
                   Every function related to parser-procedural will be non-
                 recursive.

### Lexical analyzer

          1.  Keywords
                using Annex B, IEEE-Verilog.pdf[1] to generate BNF document.

          2.  Prec information
                After pre-processing, there is only one directive left, and
             that is line directive. Now line information is correctly added
             into parsing procedural. Line records will be used to announce
             error and debug information.

          3.  non-context-free process
                Lexical process now support full coverage of verilog syntax
              standard, including those non-context-free structure.

### Syntax analyzer
          1.  yyerror and memory leak
                ( don't care at first stage )
                ( err processing will crash in yacc process )

          2.  trim and skin 
                Trimming and skinning are methods to generate abstract
              syntax tree out of analyzing tree.
                Trimming is for list structure
                Skinning is for hierarchical structure
                Both approaches will reduce the complexity of abstract-
              syntax-tree in the spawning-stage.

          3.  Non-context-free process and error check backwards
                Language support is now at full coverage, thus added all non-
              context-free structure as well. In our methods, this support
              will cause more language analysis chaos, hence requires more
              and further static syntax structural check. And it's done.

### Symbol Table
                Symbol-Table should be constructed hierarchically, according
              to each nodes' scope level.
                All nodes' scope information are determined by
              IEEE-Verilog.pdf[1]

                Symbol-Table includes the following types :
* variable type, including :
                       -- net
                       -- reg
                       -- wire
                       -- integer 
                       -- genvar
                       ...
* parameter type, including : parameter, localparam
* function-definition entry
* task-definition entry
* module instantiations' instances
* gate instantiations' instances

### Module instantiations check
                This part includes several different checks

          1. determine top module. If non-set, top-module will be the first
             crossed in parsing procedural.

          2. check for irrelevant modules, exclude them and report warnings

          3. ensure module-instantiations' acyclic attribute, we do not allow
             cyclic instantiations, thus we use topological-sorting to ensure
             this not happening. This manner is an error.

          4. we form a hash-table to store every module.

### Const-expression calculation
                We invented VeriNum class to handle everything concerning
              calculation and spawning.

          1. all kinds of integer numbers and bit-wise manner descriptions
             are currently the only const-expression-types that we accept.
          2. all numbers we accept follow strictly in section 2.5,
             IEEE-Verilog.pdf[1].
          3. calculations of numbers are currently not all correct for
             module(%), and perhaps division operation, according in
             section 2.5 & section 4.1, IEEE-Verilog.pdf[1]
          4. numbers will be truncated and appended in assignments and 
             all other operations if necessary.

### type Deduction
                Type deduction only checks bit-wise error now, meaning that
              if the operand meats the need of minimal range area of the
              operation, it's good.

### const-loop and conditional structure unfolding
                We will perform this feature in further work.

# Elaborator
       Elaboration is the process that occurs between parsing and
     simulation or RTL synthesis. It binds modules to module instances,
     builds the model hierarchy, computes parameter values, resolves
     hierarchical names, establishes net connectivity, and prepares all
     of this for simulation.

     1. simple instantiation 
     2. ...

# Build & demo
     vsyn.cpp is a demon programm to show how to call the parser to generate an AST.
     `mkdir build && cd build && cmake ..`
     `make -j 4`

# Ongoing work
     Provide an more convinient interface to access the data structures in AST.


# Main developer & Maintainer
This parser is developed by ICCAD Lab. of Fudan University. Main developer & mnaintainer:
* Yishi Yang
* Chenlei Fang
* Qicheng Huang
* Fan Yang



# References :
1. This is a book copy for IEEE Standard Verilog(R) Hardware Description
     Language, Approved 17 March 2001, Revision of IEEE Std 1364-2001
