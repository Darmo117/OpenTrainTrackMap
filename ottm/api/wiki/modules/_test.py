import sys
from ottm.api.wiki.modules import _parser, _exceptions as _ex

p = _parser.WikiScriptParser('<module>')
parsed_tree = p.parse(r"""
fun op(a, b, f) is
    return f(a, b);
end
l = [];
for i in range(4) do
    fun f(a, b) is
        return i + a * b;
    end
    l.append((fun (a, b) is return i + a * b; end, f));
end
for f1, f2 in l do
    print(op(3, 2, f1), op(3, 2, f2));
end
""".strip())
print(parsed_tree)
module = p.transform(parsed_tree)
print(module)
try:
    module.execute()
except _ex.WikiScriptException as e:
    print(f'{type(e).__name__} @ [{e.line}, {e.column}]: {e}', file=sys.stderr)
