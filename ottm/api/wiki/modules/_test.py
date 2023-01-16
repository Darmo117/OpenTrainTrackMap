import sys
from ottm.api.wiki.modules import _parser, _exceptions as _ex

p = _parser.WikiScriptParser('<module>')
parsed_tree = p.parse(r'print(1, 2, sep=":", end=".");')
print(parsed_tree)
module = p.transform(parsed_tree)
print(module)
try:
    module.execute()
except _ex.WikiScriptException as e:
    print(f'{type(e).__name__} @ [{e.line}, {e.column}]: {e}', file=sys.stderr)
