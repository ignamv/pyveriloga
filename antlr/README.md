# Verilog-A compiler

This is a WIP compiler for the Verilog-A language.
It parses and compiles a (currently small) subset of the language to a shared library
to be called from other code.

Supported language features:

* Natures, disciplines
* Modules, ports, nets
* Analog contributions
* Conditionals, blocks
* Variables

The goal is to be able to compile the standard CMC models like BSIMBULK,
in order to do fast parallel evaluation for model fitting.

## Status

I haven't worked on this for a while, but please reach out if you are interested
on developing it further, or even to let me know if this would be useful to you.

You might also want to look into [OpenVAF](https://openvaf.semimod.de/),
which is a more mature and very professional open-source Verilog-A compiler 
written in Rust.
