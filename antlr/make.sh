#!/bin/bash

set -e

export CLASSPATH=".:$HOME/packages/antlr-4.10.1-complete.jar"
antlr4="java org.antlr.v4.Tool"
grun="java org.antlr.v4.gui.TestRig"

echo Generating
$antlr4 -o generated -Werror -Dlanguage=Python3 VerilogALexer.g4
$antlr4 -o generated -Werror -no-listener -visitor -Dlanguage=Python3 VerilogAParser.g4

#mkdir -p generated
#mv VerilogA{Lexer,Parser}*.{py,interp,tokens} generated
touch generated/__init__.py
