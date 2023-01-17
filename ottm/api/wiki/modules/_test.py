import sys
from ottm.api.wiki.modules import _parser, _exceptions as _ex

p = _parser.WikiScriptParser('<module>')
parsed_tree = p.parse(r'''
s = "a\\nb\u005cb";
print(repr(s), s);
s = """\
a\\tb\\\
  b\n\"""
  c\
""";
print(repr(s), s);
'''.strip())
print(parsed_tree)
module = p.transform(parsed_tree)
print(module)
try:
    module.execute()
except _ex.WikiScriptException as e:
    print(f'{type(e).__name__} @ [{e.line}, {e.column}]: {e}', file=sys.stderr)
