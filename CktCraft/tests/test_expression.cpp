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


