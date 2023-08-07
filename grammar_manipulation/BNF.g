grammar BNF;

document: (SECTION | bnfrule)*;
bnfrule: IDENTIFIER DEFINED_AS definition;
definition:
      IDENTIFIER # Identifier
    | EMPTY # Empty
    | LITERAL # Literal
    | CHARACTERCLASS # Charclass
    | IMPOSSIBLE # Impossible
    | LPAREN definition RPAREN # Parenthesized
    | LBRACKET definition RBRACKET # Bracketed
    | LBRACE definition RBRACE # Braced
    | definition definition # Concatenate
    | definition PIPE definition # Alternative
    ;


SECTION: '// SECTION' (~[\n])+ '\n';
IDENTIFIER: [a-zA-Z$][a-zA-Z0-9_$]*;
LBRACE: '{';
RBRACE: '}';
LPAREN: '(';
RPAREN: ')';
CHARACTERCLASS: '[' ~' ' ( '\\' . | ~']' )* ']';
LBRACKET: '[';
RBRACKET: ']';
DEFINED_AS: '::=';
PIPE: '|';
//NEWLINE: '\n';
LITERAL: '\'' ('\\\'' | ~['\n])+ '\'';
WHITESPACE: [ \n] -> skip;
IMPOSSIBLE: 'Ø';
EMPTY: 'ε';
