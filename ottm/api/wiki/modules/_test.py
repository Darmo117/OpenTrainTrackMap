import sys

from ottm.api.wiki.modules import _exceptions as _ex, _parser

p = _parser.WikiScriptParser('Test')
parsed_tree = p.parse(r"""
function join(s, it) is
    return s.join(map(str, it));
end

try
    print(any([0, 1, 3], function (v) is return v > 2; end));
    print(join(`;`, [2, 3, 5, 6]));
except ValueError | TypeError as e then
    print(e);
end
""".strip())
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
