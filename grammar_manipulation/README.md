# Grammar manipulation library

This was initially an attempt to extract the whole Verilog-A grammar from the Verilog-A
specification PDF, in order to clean it up and feed it to Antlr.
This proved impractical, but what remained is a small library to manipulate grammars
by parsing BNF and applying operations like rule deletion and replacement
(which propagate to other rules which use the deleted/modified rules).
