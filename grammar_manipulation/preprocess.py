import re

with open("bnf.txt") as fd:
    input_ = fd.read()


replacements = {
    "[ 'a' - 'zA' - 'Z0' - '9_$' ]": "[a-zA-Z0-9_$]",
    "[ 'a' - 'zA' - 'Z_' ]": "[a-zA-Z_]",
    "[ 'a-zA-Z0-9_$' ]": "[a-zA-Z0-9_$]",
    "\\n": "'\\n'",
    "{ _ | decimal_digit}": "{ decimal_digit }",
    "; \n": "';' \n",
    " ? ": " '?' ",
    " : ": " ':' ",
}
output = input_
for needle, replacement in replacements.items():
    output = output.replace(needle, replacement)

firstpart, separator, secondpart = output.partition("real_identifier ::=")

firstpart = re.sub(r"\[([^ '])", "[ \\1", firstpart)
firstpart = re.sub(r"([^ '])\]", "\\1 ]", firstpart)

output = firstpart + separator + secondpart

with open("bnf2.txt", "w") as fd:
    fd.write(output)
