import sys

from ottm.api.wiki.modules import _exceptions as _ex, _parser

p = _parser.WikiScriptParser('main')
parsed_tree = p.parse(r'''
import "yo" as yo;
print(yo);
print(attrs(yo));
'''.strip())
print(parsed_tree)
module = p.transform(parsed_tree)
print(repr(module))
try:
    module.execute()
except _ex.WikiScriptException as e:
    print(f'{type(e).__name__} @ [{e.line}, {e.column}]: {e}', file=sys.stderr)
