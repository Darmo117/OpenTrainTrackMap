import sys
from ottm.api.wiki.modules import _parser, _exceptions as _ex

p = _parser.WikiScriptParser('<module>')
parsed_tree = p.parse(r"""
function f(n) is
    if n == 0 or n == 1 then
        return 1;
    end
    return n * f(n - 1);
end
print(f(5));
print(attrs(f));
""".strip())
print(parsed_tree)
module = p.transform(parsed_tree)
print(module)
try:
    module.execute()
except _ex.WikiScriptException as e:
    print(f'{type(e).__name__} @ [{e.line}, {e.column}]: {e}', file=sys.stderr)
