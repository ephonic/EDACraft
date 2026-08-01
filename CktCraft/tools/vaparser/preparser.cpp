#include <stdio.h>
#include <stdlib.h>
#include "preparser.h"
#include "adms.h"
#include "admsPreprocessor.h"
#include "preprocessorYacc.h"
#include <cstring>
using std::string;

int preparser(int argc, char* argv[], const string& tempname)
{
    //if(argc != 2){
    //    printf("Error : using %s vafile.", argv[0]);
    //    exit(0);
    //}
    char *myverilogamsfile = argv[1];
    const char *mytmpverilogamsfile = tempname.c_str();
    p_slist myli;

    p_preprocessor mypreprocessor=(p_preprocessor)malloc(sizeof(t_preprocessor));
    FILE* myverilogamsfilefh=adms_file_open_read(myverilogamsfile);

    // 前置规范化（两层）：
    // 1. 反斜杠续行（`\'+换行）合并为单行——adms 预处理器不支持，且宏定义
    //    体内的续行符会以字面 "\n" 泄漏到输出。
    // 2. 括号未闭合时的换行合并为空格——宏调用的实参列表允许跨行书写
    //    （无反斜杠），adms 预处理器无法解析，会静默截断宏展开。
    //    状态机跳过 // 与 /* */ 注释和字符串字面量，避免误合并。
    string joinedname = tempname + ".join.va";
    {
        FILE* jf = fopen(joinedname.c_str(), "wb");
        if (jf) {
            enum { NORMAL, LINE_COMMENT, BLOCK_COMMENT, STR } state = NORMAL;
            int parenDepth = 0;
            int c, next;
            bool atLineStart = true;  // 块注释结束后抑制多余换行
            while ((c = fgetc(myverilogamsfilefh)) != EOF) {
                if (state == LINE_COMMENT) {
                    fputc(c, jf);
                    if (c == '\n') state = NORMAL;
                    continue;
                }
                if (state == BLOCK_COMMENT) {
                    if (c == '*') {
                        next = fgetc(myverilogamsfilefh);
                        if (next == '/') { state = NORMAL; }
                        else { fputc(c, jf); if (next != EOF) fputc(next, jf); continue; }
                        fputc('*', jf); fputc('/', jf);
                        continue;
                    }
                    fputc(c, jf);
                    continue;
                }
                if (state == STR) {
                    fputc(c, jf);
                    if (c == '\\') {  // 字符串内转义
                        next = fgetc(myverilogamsfilefh);
                        if (next != EOF) fputc(next, jf);
                    } else if (c == '"') {
                        state = NORMAL;
                    }
                    continue;
                }
                // NORMAL
                if (c == '"') { state = STR; fputc(c, jf); continue; }
                if (c == '/') {
                    next = fgetc(myverilogamsfilefh);
                    if (next == '/') { state = LINE_COMMENT; fputc(c, jf); fputc(next, jf); continue; }
                    if (next == '*') { state = BLOCK_COMMENT; fputc(c, jf); fputc(next, jf); continue; }
                    fputc(c, jf);
                    if (next != EOF) { fputc(next, jf); }
                    continue;
                }
                if (c == '\\') {
                    next = fgetc(myverilogamsfilefh);
                    if (next == '\r') next = fgetc(myverilogamsfilefh);
                    if (next == '\n') continue;      // 反斜杠续行：丢弃
                    fputc('\\', jf);
                    if (next == EOF) break;
                    fputc(next, jf);
                    continue;
                }
                if (c == '(') { ++parenDepth; fputc(c, jf); continue; }
                if (c == ')') { if (parenDepth > 0) --parenDepth; fputc(c, jf); continue; }
                if (c == '\n' && parenDepth > 0) { fputc(' ', jf); continue; }  // 括号内换行→空格
                fputc(c, jf);
            }
            fclose(jf);
            fclose(myverilogamsfilefh);
            myverilogamsfilefh = adms_file_open_read(joinedname.c_str());
        } else {
            rewind(myverilogamsfilefh);  // 失败则退回原文件
        }
    }

    FILE* ofh=fopen(mytmpverilogamsfile,"wb");
    if(!ofh)
        adms_message_fatal(("%s: failed to open file [write mode]\n",mytmpverilogamsfile))
    adms_preprocessor_setfile_input(myverilogamsfilefh);
    mypreprocessor->cur_line_position=1;
    mypreprocessor->cur_char_position=1;
    mypreprocessor->cur_message=NULL;
    mypreprocessor->fid=myverilogamsfilefh;
    mypreprocessor->filename=adms_kclone(myverilogamsfile);
    mypreprocessor->buffer=NULL;
    mypreprocessor->cur_continuator_position=NULL;
    adms_preprocessor_valueto_main((p_preprocessor_main)malloc(sizeof(t_preprocessor_main)));
    pproot()->Defined=NULL;
    pproot()->Scanner=NULL;
    pproot()->Text=NULL;
    pproot()->cr_filename=adms_kclone(myverilogamsfile);
    pproot()->cr_scanner=mypreprocessor;
    pproot()->error=0;
    adms_slist_push(&pproot()->skipp_text,(p_adms)(long)(0));
    //pproot()->includePath=getlist_from_argv(argc,argv,"-I","directory");
    adms_slist_push(&pproot()->includePath,(p_adms)".");
    //adms_preprocessor_get_define_from_argv(argc,argv);
    adms_preprocessor_define_add_default("insideADMS");
    adms_message_verbose(("create temporary file %s\n",mytmpverilogamsfile))
    (int) preprocessorparse();
    if (pproot()->error || getenv("VA_DEBUG_PREPARSER")) {
        fprintf(stderr, "[preparser] error count = %d\n", pproot()->error);
        if (pproot()->cr_scanner && pproot()->cr_scanner->cur_message)
            fprintf(stderr, "[preparser] cur_message = %s\n", pproot()->cr_scanner->cur_message);
        fprintf(stderr, "[preparser] last line = %d\n", pproot()->cr_scanner ? pproot()->cr_scanner->cur_line_position : -1);
        long n = 0; for (p_slist l = pproot()->Text; l; l = l->next) ++n;
        fprintf(stderr, "[preparser] text nodes = %ld\n", n);
    }
    /* save preprocessed Verilog-AMS file */
    fputs("# 1 \"",ofh);
    fputs(pproot()->cr_scanner->filename,ofh);
    fputs("\"\n",ofh);
    adms_slist_inreverse(&pproot()->Text);
    for(myli=pproot()->Text;myli;myli=myli->next)
        fputs(((p_preprocessor_text)(myli->data))->_str,ofh);
    fclose(ofh);
    fclose(myverilogamsfilefh);
    remove(joinedname.c_str());
    // Skip all frees - preprocessorparse may corrupt heap.
    // This is a short-lived code generation tool, memory leak is acceptable.
    return 0;
}
