import typing as _typ
import pathlib as _pl
import re as _re
import operator as _op

import lark as _lark

from . import _syntax_tree as _st, _types


# noinspection PyMethodMayBeStatic
class WikiScriptParser(_lark.Transformer):
    UNARY_OPS: dict[str, _typ.Callable[[_typ.Any], _typ.Any]] = {
        '-': _op.neg,
        '~': _op.inv,
        'not': _op.not_,
    }
    BINARY_OPS: dict[str, _typ.Callable[[_typ.Any, _typ.Any], _typ.Any]] = {
        '**': _op.pow,
        '*': _op.mul,
        '/': _op.truediv,
        '//': _op.floordiv,
        '%': _op.mod,
        '+': _op.add,
        '-': _op.sub,
        '&': _op.and_,
        '|': _op.or_,
        '^': _op.xor,
        '<<': _op.lshift,
        '>>': _op.rshift,
        'is': _op.is_,
        'is_not': _op.is_not,
        'in': lambda a, b: a in b,
        'not_in': lambda a, b: a not in b,
        '==': _op.eq,
        '!=': _op.ne,
        '>': _op.gt,
        '>=': _op.ge,
        '<': _op.lt,
        '<=': _op.le,
        'and': lambda a, b: a and b,
        'or': lambda a, b: a or b,
    }
    TERNARY_OPS: dict[str, _typ.Callable[[_typ.Any, _typ.Any, _typ.Any], _typ.Any]] = {
        'ifelse': lambda a, b, c: a if b else c,
    }
    ASSIGN_OPS: dict[str, _typ.Callable[[_typ.Any, _typ.Any], None]] = {
        '**=': _op.ipow,
        '*=': _op.imul,
        '/=': _op.itruediv,
        '//=': _op.ifloordiv,
        '%=': _op.imod,
        '+=': _op.iadd,
        '-=': _op.isub,
        '&=': _op.iand,
        '|=': _op.ior,
        '^=': _op.ixor,
        '<<=': _op.ilshift,
        '>>=': _op.irshift,
    }

    def __init__(self, module_name: str):
        super().__init__()
        self._module_name = module_name
        self._parser = _lark.Lark(grammar=_GRAMMAR, start='module', parser='lalr', propagate_positions=True)

    def parse(self, code: str) -> _lark.Tree:
        try:
            return self._parser.parse(code)
        except _lark.exceptions.LarkError as e:
            # TODO better error messages
            raise ValueError(e)

    def transform(self, tree: _lark.Tree) -> _types.Module:
        return super().transform(tree)

    def module(self, items) -> _types.Module:
        return _types.Module(self._module_name, items)

    # Statements

    def unpack_values(self, items) -> tuple[list[str], int, int]:
        return list(map(str, items)), items[0].line, items[0].column

    def expr_stmt(self, items) -> _st.ExpressionStatement:
        return _st.ExpressionStatement(items[0].line, items[0].column, items[0])

    def unpack_variables_stmt(self, items) -> _st.UnpackVariablesStatement:
        names, line, column = items[0]
        return _st.UnpackVariablesStatement(line, column, names=names, expr=items[2])

    def set_variable_stmt(self, items) -> _st.SetVariableStatement:
        return _st.SetVariableStatement(items[0].line, items[0].column, name=str(items[0]), operator=str(items[1]),
                                        expr=items[2])

    def set_property_stmt(self, items) -> _st.SetPropertyStatement:
        return _st.SetPropertyStatement(
            items[0].line, items[0].column,
            target=items[0], property_name=str(items[1]), operator=str(items[2]), expr=items[3]
        )

    def set_item_stmt(self, items) -> _st.SetItemStatement:
        return _st.SetItemStatement(items[0].line, items[0].column, target=items[0], key=items[1],
                                    operator=str(items[2]), expr=items[3])

    def delete_var_stmt(self, items) -> _st.DeleteVariableStatement:
        return _st.DeleteVariableStatement(items[0].line, items[0].column, name=str(items[0]))

    def delete_item_stmt(self, items) -> _st.DeleteItemStatement:
        return _st.DeleteItemStatement(items[0].line, items[0].column, target=items[0], key=items[1])

    def try_stmt(self, items):
        try_statements, *except_parts = items
        return _st.TryStatement(try_statements[0].line if try_statements else -1,
                                try_statements[0].column if try_statements else -1,
                                try_statements, except_parts)

    def try_stmt_try_part(self, items) -> list[_st.Statement]:
        return items

    def try_stmt_except_part(self, items) -> tuple[list[_st.Expression], str | None, list[_st.Statement]]:
        return items[0][0], items[0][1], items[1:]

    def try_stmt_except_errors_part(self, items) -> tuple[list[_st.Expression], str | None]:
        if isinstance(items[-1], _lark.Token):
            return items[:-1], str(items[-1])
        return items, None

    def raise_stmt(self, items) -> _st.RaiseStatement:
        return _st.RaiseStatement(items[0].line, items[0].column, items[0])

    def if_stmt(self, items):
        if_cond, if_stmts = items[0]
        elifs = []
        else_part = []
        for item in items[1:]:
            if item[0] == 'elif':
                elifs.append(item[1:])
            else:
                else_part = item[1]
        return _st.IfStatement(if_cond.line, if_cond.column, if_cond, if_stmts, elifs, else_part)

    def if_stmt_if_part(self, items) -> tuple[_st.Expression, tuple[_st.Expression, ...]]:
        return items[0], items[1:]

    def if_stmt_elif_part(self, items) -> tuple[str, _st.Expression, tuple[_st.Expression, ...]]:
        return 'elif', items[0], items[1:]

    def if_stmt_else_part(self, items) -> tuple[str, tuple[_st.Expression, ...]]:
        return 'else', items

    def for_loop_stmt(self, items):
        if isinstance(items[0], tuple):
            var_names, line, column = items[0]
        else:
            var_names, line, column = str(items[0]), items[0].line, items[0].column
        return _st.ForLoopStatement(line, column, variables_names=var_names, iterator=items[1], statements=items[2:])

    def while_loop_stmt(self, items) -> _st.WhileLoopStatement:
        return _st.WhileLoopStatement(items[0].line, items[0].column, cond=items[0], statements=items[1:])

    def break_stmt(self, _) -> _st.BreakStatement:
        return _st.BreakStatement(-1, -1)

    def continue_stmt(self, _) -> _st.ContinueStatement:
        return _st.ContinueStatement(-1, -1)

    def def_function_vararg(self, items) -> tuple[str, str]:
        return 'vararg', str(items[0])

    def function_kwarg(self, items) -> tuple[str, str, _st.Expression]:
        return 'kwarg', str(items[0]), items[1]

    def def_function_params(self, items) -> tuple[list[str], bool, dict[str, _st.Expression]]:
        args = []
        vararg = False
        kwargs = {}
        for item in items:
            match item:
                case ['vararg', name]:
                    if name in args:
                        raise SyntaxError(f'duplicate argument "{name}"')
                    args.append(name)
                    vararg = True
                case ['kwarg', name, default]:
                    if name in args or name in kwargs:
                        raise SyntaxError(f'duplicate argument "{name}"')
                    kwargs[name] = default
                case name:
                    args.append(str(name))
        return args, vararg, kwargs

    def def_function_stmt(self, items) -> _st.DefineFunctionStatement:
        line, column = items[0].line, items[0].column
        name = str(items[0])
        args, vararg, kwargs = [], False, {}
        statements = []
        if items[1:]:
            if isinstance(items[1], tuple):
                args, vararg, kwargs = items[1]
                statements = items[2:]
            else:
                statements = items[1:]
        return _st.DefineFunctionStatement(line, column, name, args, vararg, kwargs, statements)

    def return_stmt(self, items) -> _st.ReturnStatement:
        return _st.ReturnStatement(items[0].line if items else -1, items[0].column if items else -1,
                                   items[0] if items else None)

    # Expressions

    def unary_op(self, items) -> _st.UnaryOperatorExpression:
        op, expr = items
        return _st.UnaryOperatorExpression(op.line, op.column, symbol=str(op), operator=self.UNARY_OPS[str(op)],
                                           expr=expr)

    def binary_op(self, items) -> _st.BinaryOperatorExpression:
        expr1, op, expr2 = items
        return _st.BinaryOperatorExpression(expr1.line, expr1.column, symbol=str(op), operator=self.BINARY_OPS[str(op)],
                                            expr1=expr1, expr2=expr2)

    def ternary_op(self, items) -> _st.TernaryOperatorExpression:
        expr1, expr2, expr3 = items
        return _st.TernaryOperatorExpression(expr1.line, expr1.column, symbol='ifelse',
                                             operator=self.TERNARY_OPS['ifelse'],
                                             expr1=expr1, expr2=expr2, expr3=expr3)

    def get_variable(self, items) -> _st.GetVariableExpression:
        return _st.GetVariableExpression(items[0].line, items[0].column, str(items[0]))

    def get_property(self, items) -> _st.GetPropertyExpression:
        return _st.GetPropertyExpression(items[0].line, items[0].column, target=items[0], property_name=str(items[1]))

    def get_item(self, items) -> _st.GetItemExpression:
        return _st.GetItemExpression(items[0].line, items[0].column, target=items[0], key=items[1])

    def def_anon_function(self, items) -> _st.DefineAnonymousFunctionExpression:
        args, *statements = items
        return _st.DefineAnonymousFunctionExpression(-1, -1, args[0], args[1], args[2], statements)

    def function_call(self, items) -> _st.FunctionCallExpression:
        args = []
        kwargs = {}
        for item in items[1:]:
            if isinstance(item, tuple):
                kwargs[item[1]] = item[2]
            else:
                args.append(item)
        return _st.FunctionCallExpression(items[0].line, items[0].column, target=items[0], args=args, kwargs=kwargs)

    def string(self, items) -> _st.SimpleLiteralExpression:
        s: str = items[0]
        return _st.SimpleLiteralExpression(
            items[0].line, items[0].column,
            _re.sub(r'\\u([\da-fA-F]{4})', lambda m: chr(int(m.group(1), 16)),
                    _re.sub(r'\\U([\da-fA-F]{8})', lambda m: chr(int(m.group(1), 16)),
                            s[1:-1].replace(r'\n', '\n')
                            .replace(r'\t', '\t')
                            .replace(r'\"', '"')
                            .replace(r'\\', '\\')))
        )

    def int(self, items) -> _st.SimpleLiteralExpression:
        n = str(items[0])
        if n.startswith('0x'):
            nb = int(n, 16)
        elif n.startswith('0o'):
            nb = int(n, 8)
        elif n.startswith('0b'):
            nb = int(n, 2)
        else:
            nb = int(n)
        return _st.SimpleLiteralExpression(items[0].line, items[0].column, nb)

    def float(self, items) -> _st.SimpleLiteralExpression:
        return _st.SimpleLiteralExpression(items[0].line, items[0].column, float(items[0]))

    def boolean_true(self, _) -> _st.SimpleLiteralExpression:
        return _st.SimpleLiteralExpression(-1, -1, True)

    def boolean_false(self, _) -> _st.SimpleLiteralExpression:
        return _st.SimpleLiteralExpression(-1, -1, False)

    def null(self, _) -> _st.SimpleLiteralExpression:
        return _st.SimpleLiteralExpression(-1, -1, None)

    def dict(self, items) -> _st.DictLiteralExpression:
        return _st.DictLiteralExpression(items[0][0].line if items else -1, items[0][0].column if items else -1,
                                         *[(k, v) for k, v in items])

    def dict_entry(self, items) -> tuple[_st.Expression, _st.Expression]:
        return items[0], items[1]

    def list(self, items) -> _st.ListLiteralExpression:
        return _st.ListLiteralExpression(items[0].line if items else -1, items[0].column if items else -1, *items)

    def tuple(self, items) -> _st.TupleLiteralExpression:
        return _st.TupleLiteralExpression(items[0].line if items else -1, items[0].column if items else -1, *items)

    def set(self, items) -> _st.SetLiteralExpression:
        return _st.SetLiteralExpression(items[0].line if items else -1, items[0].column if items else -1, *items)

    def slice_both(self, items) -> _st.SliceLiteralExpression:
        return _st.SliceLiteralExpression(items[0].line if items else -1, items[0].column if items else -1,
                                          start=items[0], end=items[1], step=items[2] if len(items) == 3 else None)

    def slice_end(self, items) -> _st.SliceLiteralExpression:
        return _st.SliceLiteralExpression(items[0].line if items else -1, items[0].column if items else -1,
                                          end=items[0], step=items[1] if len(items) == 2 else None)

    def slice_start(self, items) -> _st.SliceLiteralExpression:
        return _st.SliceLiteralExpression(items[0].line if items else -1, items[0].column if items else -1,
                                          start=items[0], step=items[1] if len(items) == 2 else None)

    def slice_none(self, items) -> _st.SliceLiteralExpression:
        return _st.SliceLiteralExpression(items[0].line if items else -1, items[0].column if items else -1,
                                          step=items[0] if items else None)


_GRAMMAR = ''


def _init():
    global _GRAMMAR
    with (_pl.Path(__file__).parent / 'wiki_script.lark').open() as f:
        _GRAMMAR = f.read()


_init()
