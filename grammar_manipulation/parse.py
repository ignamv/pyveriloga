from bs4 import BeautifulSoup, NavigableString

with open("/home/ignacio/programacion/OpenVAF/VerilogA_grammar.html") as fd:
    contents = fd.read()

soup = BeautifulSoup(contents, features="lxml")


def recurse(node, monospace=False):
    if isinstance(node, NavigableString):
        if str(node).strip():
            yield str(node).strip().replace("\n", " "), monospace
    elif node.name == "br":
        yield "\n", False
    else:
        if node.name == "p":
            yield "\n", False
        monospace = monospace or (
            node.name == "font" and node.attrs.get("face") == "monospace"
        )
        for child in node.children:
            yield from recurse(child, monospace)


for string, monospace in recurse(soup.find("body")):
    if "A." in string:
        print("// SECTION " + string + "\n")
    else:
        if monospace:
            string = "'" + string.replace("\\", "\\\\").replace("'", "\\'") + "'"
        print(string, end=" " if string != "\n" else "")
