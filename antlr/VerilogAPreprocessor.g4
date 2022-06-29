lexer grammar VerilogAPreprocessor;

DEFINE: '`define' [ \t]+ [a-zA-Z_] [a-zA-Z0-9_]* '('?;
IFDEF: '`ifdef';
ELSEDEF: '`else';
ENDIFDEF: '`endif';
INCLUDE: '`include';
MACROCALL: '`' [a-zA-Z_] [a-zA-Z0-9_]* ;
NEWLINE: '\n';
RPAREN: ')';
LPAREN: '(';
COMMA: ',';
