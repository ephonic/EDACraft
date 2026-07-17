// test_lexer.cpp - lexer unit tests
#include "parser/token.hpp"
#include <gtest/gtest.h>
using namespace rfsim;

TEST(Lexer, NumberWithSuffixes) {
    { Lexer lx("1k"); Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, 1000.0); }
    { Lexer lx("1meg"); Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, 1e6); }
    { Lexer lx("1u"); Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, 1e-6); }
    { Lexer lx("1.5p"); Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, 1.5e-12); }
    { Lexer lx("1e-9"); Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, 1e-9); }
    { Lexer lx("1kohm"); Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, 1000.0); }
}

TEST(Lexer, CaseInsensitiveWords) {
    Lexer lx("MOSFET mosfet");
    Token t1 = lx.next(), t2 = lx.next();
    ASSERT_EQ(t1.kind, TokenKind::Word); EXPECT_EQ(t1.text, "mosfet");
    ASSERT_EQ(t2.kind, TokenKind::Word); EXPECT_EQ(t2.text, "mosfet");
}

TEST(Lexer, ContinuationLine) {
    Lexer lx("R1 n1 n2\n+ 1k");
    EXPECT_EQ(lx.next().text, "r1");
    EXPECT_EQ(lx.next().text, "n1");
    EXPECT_EQ(lx.next().text, "n2");
    Token c = lx.next(); ASSERT_EQ(c.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(c.value, 1000.0);
}

TEST(Lexer, Comments) {
    Lexer lx("* this is a comment\nR1 n1 n2 1k ; inline comment\n");
    Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Word); EXPECT_EQ(t.text, "r1");
}

TEST(Lexer, Punctuation) {
    Lexer lx(".model name ( a=1 )");
    EXPECT_EQ(lx.next().kind, TokenKind::Dot);
    Token w = lx.next(); EXPECT_EQ(w.kind, TokenKind::Word); EXPECT_EQ(w.text, "model");
    (void)lx.next(); // skip "name"
    EXPECT_EQ(lx.next().kind, TokenKind::LParen);
}

TEST(Lexer, SignedNumber) {
    Lexer lx("-3.14");
    Token t = lx.next(); ASSERT_EQ(t.kind, TokenKind::Number); EXPECT_DOUBLE_EQ(t.value, -3.14);
}
