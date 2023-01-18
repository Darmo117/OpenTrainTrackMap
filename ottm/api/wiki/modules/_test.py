import sys

from ottm.api.wiki.modules import _exceptions as _ex, _parser

p = _parser.WikiScriptParser('main')
parsed_tree = p.parse(r'''
print(return);
print(attrs(yo));
'''.strip())
print(parsed_tree)
try:
    module = p.transform(parsed_tree)
except _ex.WikiScriptException as e:
    print(f'{type(e).__name__} at [{e.line}, {e.column}]: {e}', file=sys.stderr)
else:
    print(repr(module))
    try:
        module.execute()
    except _ex.WikiScriptException as e:
        print(f'{type(e).__name__} at [{e.line}, {e.column}]: {e}', file=sys.stderr)
