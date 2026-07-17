// expression.hpp — .param 表达式求值器
// 支持: + - * / ^ ( ) 与函数调用、变量引用、数值字面量（含单位后缀）
//
// C2 增强（Phase C）：
//   - 多参函数：agauss(nom,abs,sgm) / pow(b,e) / min/max(a,b) / atan2 / if(cond,a,b) 等
//   - 条件表达式：cond ? a : b
//   - 逻辑/比较运算符：&& || ! == != < > <= >= （结果 0.0/1.0）
//   - 用户自定义函数：.func name(args) 'body'（通过 multiFuncs 注册）
#ifndef RFSIM_PARSER_EXPRESSION_HPP
#define RFSIM_PARSER_EXPRESSION_HPP

#include "../rfsim.hpp"
#include <functional>
#include <map>
#include <string>
#include <vector>

namespace rfsim {

// 表达式求值上下文：变量名(小写) -> 值，函数名(小写) -> 实现
struct EvalContext {
    std::map<std::string, double> vars;
    // 单参函数（向后兼容：sin/cos/exp/...）
    std::map<std::string, std::function<double(double)>> funcs;
    // C2：多参函数（agauss/pow/min/max/atan2/if/用户 .func）。优先于 funcs。
    std::map<std::string, std::function<double(const std::vector<double>&)>> multiFuncs;
};

// 求值表达式文本。失败返回 false 并填充 errMessage。
bool evaluateExpression(std::string_view expr, const EvalContext& ctx,
                        double& outValue, std::string& errMessage);

// 预置常用函数（单参 sin/cos/.../exp/log/sqrt/abs + 多参 agauss/pow/min/max/...）到 ctx
void registerBuiltinFunctions(EvalContext& ctx);

} // namespace rfsim

#endif // RFSIM_PARSER_EXPRESSION_HPP
