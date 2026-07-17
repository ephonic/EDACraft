// test_expression.cpp 鈥?琛ㄨ揪寮忔眰鍊煎櫒鍗曞厓娴嬭瘯
#include "parser/expression.hpp"
#include <gtest/gtest.h>

using namespace rfsim;

TEST(Expression, BasicArithmetic) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    double v = 0; std::string err;

    EXPECT_TRUE(evaluateExpression("1+2*3", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 7.0);

    EXPECT_TRUE(evaluateExpression("(1+2)*3", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 9.0);

    EXPECT_TRUE(evaluateExpression("2^10", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1024.0);

    EXPECT_TRUE(evaluateExpression("1k", ctx, v, err));  // 鍗曚綅鍚庣紑
    EXPECT_DOUBLE_EQ(v, 1000.0);
}

TEST(Expression, Variables) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    ctx.vars["wn"] = 1e-6;
    ctx.vars["vdd"] = 1.2;
    double v = 0; std::string err;

    EXPECT_TRUE(evaluateExpression("2*wn", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 2e-6);

    EXPECT_TRUE(evaluateExpression("vdd/2", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 0.6);
}

TEST(Expression, Functions) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    double v = 0; std::string err;

    EXPECT_TRUE(evaluateExpression("sqrt(4)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 2.0);

    EXPECT_TRUE(evaluateExpression("abs(-5)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 5.0);

    EXPECT_TRUE(evaluateExpression("exp(0)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);
}

TEST(Expression, Errors) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    double v = 0; std::string err;

    EXPECT_FALSE(evaluateExpression("unknownvar", ctx, v, err));
    EXPECT_FALSE(evaluateExpression("1+", ctx, v, err));
    EXPECT_FALSE(evaluateExpression("(1+2", ctx, v, err));
}

// ===== C2（Phase C）增强测试 =====

TEST(Expression, C2MultiArgFunctions) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    double v = 0; std::string err;

    EXPECT_TRUE(evaluateExpression("pow(2,10)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1024.0);

    EXPECT_TRUE(evaluateExpression("min(3,1,2)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);

    EXPECT_TRUE(evaluateExpression("max(3,1,2)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 3.0);

    EXPECT_TRUE(evaluateExpression("atan2(1,1)", ctx, v, err));
    EXPECT_NEAR(v, 0.7853981633974483, 1e-12);  // π/4

    // agauss 确定性求值取名义值（monte-carlo 均值）
    EXPECT_TRUE(evaluateExpression("agauss(5,0.1,3)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 5.0);

    // 单参函数仍可用（向后兼容）
    EXPECT_TRUE(evaluateExpression("sqrt(16)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 4.0);
}

TEST(Expression, C2TernaryConditional) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    ctx.vars["vdd"] = 1.2;
    double v = 0; std::string err;

    EXPECT_TRUE(evaluateExpression("vdd > 1.0 ? 3.3 : 1.8", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 3.3);

    EXPECT_TRUE(evaluateExpression("vdd < 1.0 ? 3.3 : 1.8", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.8);

    // if(cond,a,b) 函数形式等价
    EXPECT_TRUE(evaluateExpression("if(vdd > 1.0, 3.3, 1.8)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 3.3);

    // 嵌套三元（右结合）
    EXPECT_TRUE(evaluateExpression("1 ? (0 ? 10 : 20) : 30", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 20.0);
}

TEST(Expression, C2LogicalOperators) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    double v = 0; std::string err;

    EXPECT_TRUE(evaluateExpression("1 && 1", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);

    EXPECT_TRUE(evaluateExpression("1 && 0", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 0.0);

    EXPECT_TRUE(evaluateExpression("0 || 1", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);

    EXPECT_TRUE(evaluateExpression("!0", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);

    EXPECT_TRUE(evaluateExpression("!5", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 0.0);

    // 比较
    EXPECT_TRUE(evaluateExpression("3 == 3", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);
    EXPECT_TRUE(evaluateExpression("3 != 4", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);
    EXPECT_TRUE(evaluateExpression("2 <= 2", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 1.0);
    EXPECT_TRUE(evaluateExpression("5 >= 6", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 0.0);

    // 组合：逻辑表达式参与算术
    EXPECT_TRUE(evaluateExpression("(3 > 2) * 10", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 10.0);
}

TEST(Expression, C2PdkStyleExpressions) {
    // PDK .param 中常见的表达式：几何参数 + 表达式引用
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    ctx.vars["dxln"] = 1e-8;
    ctx.vars["scale_mos"] = 0.9;
    double v = 0; std::string err;

    // HSPICE 风格：lmin = '6.3e-7 - dxln'
    EXPECT_TRUE(evaluateExpression("6.3e-7 - dxln", ctx, v, err));
    EXPECT_NEAR(v, 6.2e-7, 1e-18);

    // 嵌套：w_eff = 'w * scale_mos - dxlw'
    ctx.vars["w"] = 2e-6;
    EXPECT_TRUE(evaluateExpression("w * scale_mos - dxln", ctx, v, err));
    EXPECT_NEAR(v, 2e-6 * 0.9 - 1e-8, 1e-18);

    // 条件选择工艺角参数
    ctx.vars["tt"] = 1.0;
    EXPECT_TRUE(evaluateExpression("tt > 0.5 ? 0.5 : 0.45", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 0.5);
}

TEST(Expression, C2UserDefinedFunc) {
    // .func 注册：用户自定义多参函数（如 .func mydelay(a,b) 'a*exp(-b)'）
    EvalContext ctx;
    registerBuiltinFunctions(ctx);
    ctx.multiFuncs["mydelay"] = [](const std::vector<double>& a) -> double {
        if (a.size() < 2) return 0.0;
        return a[0] * std::exp(-a[1]);
    };
    double v = 0; std::string err;
    EXPECT_TRUE(evaluateExpression("mydelay(2, 0)", ctx, v, err));
    EXPECT_DOUBLE_EQ(v, 2.0);
    EXPECT_TRUE(evaluateExpression("mydelay(1, 1)", ctx, v, err));
    EXPECT_NEAR(v, std::exp(-1.0), 1e-12);
}



