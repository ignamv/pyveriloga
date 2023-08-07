#!/bin/bash

set -e

python parse.py > bnf.txt
python preprocess.py

export CLASSPATH=".:$HOME/packages/antlr-4.10.1-complete.jar"
antlr4="java org.antlr.v4.Tool"
grun="java org.antlr.v4.gui.TestRig"

#rm *.java *.class *.interp *.tokens

echo Generating
$antlr4 BNF.g
$antlr4 -visitor -Dlanguage=Python3 BNF.g

echo Compiling
javac -g BNF*.java
echo Running
#$grun BNF tokens -tokens < bnf2.txt > tokens.txt
$grun BNF document -tree < bnf2.txt > tree.txt
#$grun BNF document -gui < bnf2.txt
