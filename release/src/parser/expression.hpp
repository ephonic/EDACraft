// expression.hpp — .param 表达式求值器
// 支持: + - * / ^ ( ) 与函数调用、变量引用、数值字面量（含单位后缀）
#ifndef RFSIM_PARSER_EXPRESSION_HPP
#define RFSIM_PARSER_EXPRESSION_HPP

#include "../rfsim.hpp"
#include <functional>
#include <map>
#include <string>

namespace rfsim {

// 表达式求值上下文：变量名(小写) -> 值，函数名(小写) -> 实现
struct EvalContext {
    std::map<std::string, double> vars;
    std::map<std::string, std::function<double(double)>> funcs;
};

// 求值表达式文本。失败返回 false 并填充 errMessage。
bool evaluateExpression(std::string_view expr, const EvalContext& ctx,
                        double& outValue, std::string& errMessage);

// 预置常用函数（sin/cos/.../exp/log/sqrt/abs/pow/...）到 ctx
void registerBuiltinFunctions(EvalContext& ctx);

} // namespace rfsim

#endif // RFSIM_PARSER_EXPRESSION_HPP
